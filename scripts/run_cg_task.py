#!/usr/bin/env python3
"""
执行 cg 自动化任务：
1. 在 cg_task/output 下创建新的时间戳目录
2. 尝试运行批量 A 股评分脚本
3. 若实时抓取结果明显失效，则回退为最近一次成功产物
4. 生成本次运行说明
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd

from batch_stock_scoring import fetch_one, read_stock_list


ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "cg_task" / "file" / "stock_list.csv"
OUTPUT_ROOT = ROOT / "cg_task" / "output"
BATCH_SCRIPT = ROOT / "scripts" / "batch_stock_scoring.py"
TIMEZONE_LABEL = "Asia/Shanghai"


def now_local() -> datetime:
    return datetime.now()


def build_run_dir(ts: datetime) -> Path:
    run_dir = OUTPUT_ROOT / ts.strftime("%Y%m%d%H%M")
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def read_scored_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def expected_output_paths(run_dir: Path, as_of: str) -> dict:
    date_tag = as_of.replace("-", "")
    return {
        "csv": run_dir / f"stock_list_scored_{date_tag}.csv",
        "xlsx": run_dir / f"stock_list_scored_{date_tag}.xlsx",
        "json": run_dir / f"stock_list_scored_{date_tag}.json",
        "md": run_dir / f"stock_list_scoring_report_{date_tag}.md",
    }


def run_live_analysis(run_dir: Path, as_of: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        "python3",
        str(BATCH_SCRIPT),
        "--input",
        str(INPUT_CSV),
        "--output-dir",
        str(run_dir),
        "--as-of",
        as_of,
    ]
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def preflight_live_fetch() -> tuple[bool, str]:
    stock_df = read_stock_list(INPUT_CSV)
    first = stock_df.iloc[0]
    try:
        record = fetch_one(first, pause=0.0, timeout_sec=4.0)
    except Exception as exc:  # noqa: BLE001
        return False, f"首只样本探测失败: {exc!r}"

    has_any_data = any(
        pd.notna(record.get(field))
        for field in ["现价", "MA20", "毛利率", "总市值_亿元", "ROE"]
    )
    if not has_any_data:
        return False, "首只样本探测未拿到实时快照、日线或财务摘要"
    return True, "首只样本探测通过"


def output_is_usable(csv_path: Path) -> tuple[bool, str]:
    if not csv_path.exists():
        return False, "未生成评分明细 CSV"

    df = read_scored_csv(csv_path)
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


def find_latest_success_dir(exclude_dir: Path) -> Path:
    candidates: List[Path] = []
    for child in sorted(OUTPUT_ROOT.iterdir(), reverse=True):
        if not child.is_dir() or child == exclude_dir:
            continue
        if list(child.glob("stock_list_scored_*.csv")) and list(child.glob("stock_list_scoring_report_*.md")):
            candidates.append(child)
    if not candidates:
        raise RuntimeError("未找到可复用的历史成功结果目录")
    return candidates[0]


def copy_success_artifacts(src_dir: Path, dst_dir: Path) -> List[str]:
    copied = []
    for pattern in ["stock_list_scored_*.csv", "stock_list_scored_*.xlsx", "stock_list_scored_*.json", "stock_list_scoring_report_*.md"]:
        for src in src_dir.glob(pattern):
            dst = dst_dir / src.name
            shutil.copy2(src, dst)
            copied.append(src.name)
    copied.sort()
    return copied


def write_run_note(
    run_dir: Path,
    run_time: datetime,
    mode: str,
    as_of: str,
    sample_count: int,
    stdout: str,
    stderr: str,
    validation: str,
    reused_from: Path | None,
    copied_files: List[str],
) -> None:
    lines = [
        "# 本次自动化运行说明",
        "",
        f"- 运行时间：{run_time.strftime('%Y-%m-%d %H:%M')}（{TIMEZONE_LABEL}）",
        f"- 交付目录：`{run_dir.relative_to(ROOT)}`",
        f"- 输入文件：`{INPUT_CSV.relative_to(ROOT)}`",
        f"- 样本数量：{sample_count}",
        f"- 运行模式：{'实时抓取成功' if mode == 'live' else '失败后复用历史结果'}",
        f"- 分析日期参数：`{as_of}`",
        "",
        "## 数据口径",
        "",
        "- 基本面：`akshare.stock_financial_abstract_new_ths`",
        "- 实时快照：`akshare.stock_individual_spot_xq`",
        "- 趋势日线：`akshare.stock_zh_a_daily`",
        f"- 结果有效性检查：{validation}",
    ]

    if reused_from is not None:
        lines.extend(
            [
                f"- 回退来源：`{reused_from.relative_to(ROOT)}`",
                f"- 复用文件：{', '.join(copied_files)}",
            ]
        )

    lines.extend(
        [
            "",
            "## 文件说明",
            "",
            "- `stock_list_scored_*.csv`：批量评分明细表",
            "- `stock_list_scored_*.xlsx`：Excel 版本明细表",
            "- `stock_list_scored_*.json`：结构化结果",
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

    preflight_ok, preflight_msg = preflight_live_fetch()
    if preflight_ok:
        result = run_live_analysis(run_dir, as_of)
        usable, validation = output_is_usable(output_paths["csv"])
        validation = f"{preflight_msg}；{validation}"
    else:
        result = subprocess.CompletedProcess(
            args=["preflight"],
            returncode=1,
            stdout="",
            stderr=preflight_msg,
        )
        usable = False
        validation = preflight_msg

    reused_from = None
    copied_files: List[str] = []
    mode = "live"

    if not usable:
        cleanup_generated_files(output_paths)
        reused_from = find_latest_success_dir(exclude_dir=run_dir)
        copied_files = copy_success_artifacts(reused_from, run_dir)
        mode = "reuse"

    write_run_note(
        run_dir=run_dir,
        run_time=run_time,
        mode=mode,
        as_of=as_of,
        sample_count=sample_count,
        stdout=result.stdout,
        stderr=result.stderr,
        validation=validation,
        reused_from=reused_from,
        copied_files=copied_files,
    )

    print(f"[DONE] {run_dir}")


if __name__ == "__main__":
    main()
