#!/usr/bin/env python3
"""
执行 cg 自动化任务：
1. 在 cg_task/output 下创建新的时间戳目录
2. 尝试运行批量 A 股评分脚本
3. 若抓取失败或结果明显失效，则直接报错
4. 生成本次运行说明
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from batch_stock_scoring import read_stock_list


ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "cg_task" / "file" / "stock_list.csv"
OUTPUT_ROOT = ROOT / "cg_task" / "output"
BATCH_SCRIPT = ROOT / "scripts" / "batch_stock_scoring.py"
TIMEZONE_LABEL = "Asia/Shanghai"


def now_local() -> datetime:
    return datetime.now()


def resolve_python_executable() -> str:
    candidates = [
        sys.executable,
        "/Users/chenchen/.pyenv/versions/3.10.15/bin/python",
        "/usr/bin/python3",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "import akshare"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError:
            continue
        if probe.returncode == 0:
            return candidate
    raise RuntimeError("未找到可用的 Python 解释器（需要可导入 akshare）")


def build_run_dir(ts: datetime) -> Path:
    run_dir = OUTPUT_ROOT / ts.strftime("%Y%m%d%H%M")
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def read_scored_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def read_scored_json(path: Path) -> pd.DataFrame:
    return pd.read_json(path)


def expected_output_paths(run_dir: Path, as_of: str) -> dict:
    date_tag = as_of.replace("-", "")
    return {
        "csv": run_dir / f"stock_list_scored_{date_tag}.csv",
        "xlsx": run_dir / f"stock_list_scored_{date_tag}.xlsx",
        "json": run_dir / f"stock_list_scored_{date_tag}.json",
        "md": run_dir / f"stock_list_scoring_report_{date_tag}.md",
    }


def run_live_analysis(run_dir: Path, as_of: str) -> subprocess.CompletedProcess[str]:
    python_executable = resolve_python_executable()
    cmd = [
        python_executable,
        str(BATCH_SCRIPT),
        "--input",
        str(INPUT_CSV),
        "--output-dir",
        str(run_dir),
        "--as-of",
        as_of,
    ]
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def output_is_usable(paths: dict) -> tuple[bool, str]:
    csv_path = paths["csv"]
    json_path = paths["json"]
    if not csv_path.exists():
        return False, "未生成评分明细 CSV"
    if not json_path.exists():
        return False, "未生成结构化 JSON 明细"

    df = read_scored_json(json_path)
    row_count = len(df)
    if row_count == 0:
        return False, "评分结果为空"

    price_count = df["现价"].notna().sum() if "现价" in df.columns else 0
    financial_count = df["毛利率"].notna().sum() if "毛利率" in df.columns else 0
    trend_count = df["MA20"].notna().sum() if "MA20" in df.columns else 0

    if price_count == 0 and financial_count == 0 and trend_count == 0:
        return False, "实时快照、财务摘要和日线数据均未成功抓取"

    return True, f"有效样本: 现价 {price_count}/{row_count}, 毛利率 {financial_count}/{row_count}, MA20 {trend_count}/{row_count}"


def cleanup_generated_files(paths: dict) -> None:
    for path in paths.values():
        if path.exists():
            path.unlink()


def write_run_note(
    run_dir: Path,
    run_time: datetime,
    success: bool,
    as_of: str,
    sample_count: int,
    stdout: str,
    stderr: str,
    validation: str,
) -> None:
    lines = [
        "# 本次自动化运行说明",
        "",
        f"- 运行时间：{run_time.strftime('%Y-%m-%d %H:%M')}（{TIMEZONE_LABEL}）",
        f"- 交付目录：`{run_dir.relative_to(ROOT)}`",
        f"- 输入文件：`{INPUT_CSV.relative_to(ROOT)}`",
        f"- 样本数量：{sample_count}",
        f"- 运行结果：{'成功' if success else '失败'}",
        f"- 分析日期参数：`{as_of}`",
        "",
        "## 数据口径",
        "",
        "- 基本面：`akshare.stock_financial_abstract_new_ths`",
        "- 实时快照：`akshare.stock_zh_a_spot_em`（一次性拉取全市场快照后按代码映射）",
        "- 趋势日线：`akshare.stock_zh_a_daily`",
        f"- 结果有效性检查：{validation}",
    ]

    lines.extend(
        [
            "",
            "## 文件说明",
            "",
            "- `stock_list_scored_*.csv`：仅回填原始 14 列的交付表",
            "- `stock_list_scored_*.xlsx`：Excel 版本交付表",
            "- `stock_list_scored_*.json`：保留全部抓取字段、评分细项与错误信息的结构化明细",
            "- `stock_list_scoring_report_*.md`：评分标准、Top 排名和异常样本说明",
            "",
            "## 执行备注",
            "",
            "```text",
            (stdout or "").strip() or "(no stdout)",
            "```",
        ]
    )
    if stderr.strip():
        lines.extend(["", "```text", stderr.strip(), "```"])

    (run_dir / "RUN_NOTE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    run_time = now_local()
    run_dir = build_run_dir(run_time)
    as_of = run_time.strftime("%Y-%m-%d")
    stock_df = read_stock_list(INPUT_CSV)
    sample_count = len(stock_df)
    output_paths = expected_output_paths(run_dir, as_of)

    result = run_live_analysis(run_dir, as_of)
    usable, validation = output_is_usable(output_paths)

    if not usable:
        cleanup_generated_files(output_paths)
        write_run_note(
            run_dir=run_dir,
            run_time=run_time,
            success=False,
            as_of=as_of,
            sample_count=sample_count,
            stdout=result.stdout,
            stderr=result.stderr,
            validation=validation,
        )
        raise RuntimeError(f"本次任务失败，未复用历史结果：{validation}")

    write_run_note(
        run_dir=run_dir,
        run_time=run_time,
        success=True,
        as_of=as_of,
        sample_count=sample_count,
        stdout=result.stdout,
        stderr=result.stderr,
        validation=validation,
    )

    print(f"[DONE] {run_dir}")


if __name__ == "__main__":
    main()
