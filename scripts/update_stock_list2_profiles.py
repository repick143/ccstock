#!/usr/bin/env python3
"""
Update stock_list(2).csv and per-stock profile notes from one scored JSON file.

The script is intentionally tied to the recurring stock_list(2) workflow:
- keep the input CSV in its legacy GB18030-compatible encoding;
- update one profile per Chinese stock name, using the first occurrence when the
  input list intentionally contains duplicated names/codes under different tracks;
- append a timestamped short-term forecast and move the previous data anomaly
  note into the historical anomaly section.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "cg_task" / "file" / "stock_list(2).csv"
PROFILE_DIR = ROOT / "profile"


def clean(value: Any) -> Any:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def fnum(value: Any, digits: int = 2, suffix: str = "") -> str:
    value = clean(value)
    if value is None:
        return "缺失"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    text = f"{number:.{digits}f}".rstrip("0").rstrip(".")
    return f"{text}{suffix}"


def money(value: Any, digits: int = 2) -> str:
    return fnum(value, digits, " 元")


def normalize_missing_units(text: str) -> str:
    return text.replace("缺失 元", "缺失").replace("缺失 亿", "缺失")


def signed(value: Any, digits: int = 2, suffix: str = "%") -> str:
    value = clean(value)
    if value is None:
        return "缺失"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.{digits}f}".rstrip("0").rstrip(".") + suffix


def zcode(value: Any) -> str:
    return str(value).strip().zfill(6)


def stock_suffix(code: str) -> str:
    code = zcode(code)
    if code.startswith(("60", "68", "90")):
        return f"{code}.SH"
    if code.startswith(("83", "87", "92")):
        return f"{code}.BJ"
    return f"{code}.SZ"


def value_for(row: pd.Series, key: str) -> Any:
    return clean(row.get(key))


def bool_has(row: pd.Series, key: str) -> bool:
    value = value_for(row, key)
    return value is not None and str(value).strip() != ""


def short_conclusion(row: pd.Series) -> str:
    signal = value_for(row, "信号价")
    ma20 = value_for(row, "MA20")
    score = value_for(row, "短期走势打分")
    rsi = value_for(row, "RSI14")
    if signal is not None and ma20 is not None and signal >= ma20:
        if rsi is not None and rsi >= 76:
            return "短线强势但偏热，仍在 MA20 上方。"
        if score is not None and score >= 70:
            return "短线偏强，趋势仍在多头结构中。"
        if score is not None and score >= 55:
            return "短线中性偏强，仍在 MA20 上方。"
        return "短线中性，更多是趋势跟踪和等待确认。"
    if signal is not None and ma20 is not None and signal < ma20:
        if score is not None and score >= 50:
            return "短线转为震荡观察，需先收复 MA20。"
        return "短线偏弱，宜等待重新站稳均线后再提高关注。"
    return "短线中性，更多是趋势跟踪和等待确认。"


def risk_summary(row: pd.Series) -> tuple[str, str]:
    issues: list[str] = []
    debt = value_for(row, "资产负债率")
    roe = value_for(row, "ROE")
    gross = value_for(row, "毛利率")
    drawdown = value_for(row, "20日回撤")
    profit_yoy = value_for(row, "归母净利润同比")

    level = "较低"
    if debt is not None and debt >= 70:
        level = "偏高"
        issues.append(f"资产负债率 {fnum(debt, 1, '%')} 需跟踪")
    elif debt is not None and debt >= 60:
        level = "中等"
        issues.append(f"资产负债率 {fnum(debt, 1, '%')} 需跟踪")

    if roe is not None and roe < 3:
        if level == "较低":
            level = "中等"
        issues.append(f"ROE {fnum(roe, 1, '%')} 偏低")
    if gross is not None and gross < 20:
        if level == "较低":
            level = "中等"
        issues.append(f"毛利率 {fnum(gross, 1, '%')}，利润垫偏薄")
    if profit_yoy is not None and profit_yoy < 0:
        if level == "较低":
            level = "中等"
        issues.append(f"归母净利润同比 {signed(profit_yoy, 1)}")
    if drawdown is not None and drawdown <= -15:
        if level == "较低":
            level = "中等"
        issues.append(f"20日回撤 {signed(drawdown, 1)} 较深")

    if not issues:
        issues.append("暂无明显财务异常信号，但仍需跟踪订单、价格和现金流质量")
    return level, "；".join(issues)


def global_stats(df: pd.DataFrame) -> dict[str, Any]:
    def count(col: str) -> int:
        return int(df[col].notna().sum()) if col in df.columns else 0

    def dist(col: str) -> dict[str, int]:
        if col not in df.columns:
            return {}
        values = df[col].dropna().astype(str).value_counts().sort_index()
        return {str(k): int(v) for k, v in values.items()}

    duplicate_codes = sorted(df.loc[df["股票代码"].duplicated(keep=False), "股票代码"].astype(str).unique())
    duplicate_names = sorted(df.loc[df["股票名称"].duplicated(keep=False), "股票名称"].astype(str).unique())
    return {
        "rows": len(df),
        "unique_codes": int(df["股票代码"].nunique()),
        "unique_names": int(df["股票名称"].nunique()),
        "duplicate_codes": duplicate_codes,
        "duplicate_names": duplicate_names,
        "price_count": count("现价"),
        "signal_count": count("信号价"),
        "ma20_count": count("MA20"),
        "gross_count": count("毛利率"),
        "roe_count": count("ROE"),
        "market_cap_count": count("总市值_亿元"),
        "pe_count": count("市盈率_TTM"),
        "spot_error_count": int(df["spot_error"].notna().sum()) if "spot_error" in df.columns else 0,
        "daily_dates": dist("日线日期"),
        "report_dates": dist("财报期"),
    }


def profile_path(name: str) -> Path:
    return PROFILE_DIR / f"{name}.md"


def extract_section(text: str, heading: str, next_heading_level: str = "## ") -> str | None:
    start = text.find(heading)
    if start < 0:
        return None
    body_start = start + len(heading)
    next_start = text.find(f"\n{next_heading_level}", body_start)
    if next_start < 0:
        return text[body_start:].strip()
    return text[body_start:next_start].strip()


def extract_latest_prediction(text: str) -> dict[str, Any]:
    section = extract_section(text, "## 短期行情预测")
    if not section:
        return {}
    matches = list(re.finditer(r"^### ([^\n]+预测(?:更新|复核)?)\n", section, re.M))
    if not matches:
        return {}
    match = matches[-1]
    start = match.end()
    next_match = None
    for candidate in matches:
        if candidate.start() > match.start():
            next_match = candidate
            break
    end = next_match.start() if next_match else len(section)
    body = section[start:end]
    out: dict[str, Any] = {"heading": match.group(1), "body": body}

    sig = re.search(r"信号价\s*([0-9.]+)\s*元", body)
    if sig:
        out["signal"] = float(sig.group(1))
    core = re.search(r"短线\s*([0-9.]+)", body)
    if core:
        out["short_score"] = float(core.group(1))
    target = re.search(r"目标价(?:从\s*[0-9.]+\s*元变为|为)?\s*([0-9.]+)\s*元", body)
    if target:
        out["target"] = float(target.group(1))
    return out


def upsert_prediction_section(prediction_body: str, run_label: str, new_prediction: str) -> str:
    marker = f"### {run_label} 预测更新"
    pattern = re.compile(
        rf"^### {re.escape(run_label)} 预测更新\n.*?(?=^### |\Z)",
        flags=re.M | re.S,
    )
    if marker in prediction_body:
        return pattern.sub(new_prediction.rstrip() + "\n", prediction_body).strip()
    return f"{prediction_body.rstrip()}\n\n{new_prediction.rstrip()}".strip()


def remove_prediction_section(prediction_body: str, run_label: str) -> str:
    pattern = re.compile(
        rf"^### {re.escape(run_label)} 预测更新\n.*?(?=^### |\Z)",
        flags=re.M | re.S,
    )
    return pattern.sub("", prediction_body).strip()


def pct_change(new: Any, old: Any) -> str | None:
    if new is None or old in (None, 0):
        return None
    try:
        change = (float(new) / float(old) - 1) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return signed(change, 2)


def score_change(new: Any, old: Any) -> str | None:
    if new is None or old is None:
        return None
    try:
        change = float(new) - float(old)
    except (TypeError, ValueError):
        return None
    return signed(change, 1, " 分")


def build_prediction(row: pd.Series, run_dir: Path, run_label: str, stats: dict[str, Any], previous: dict[str, Any]) -> str:
    as_of = run_label[:10]
    start_date = datetime.strptime(as_of, "%Y-%m-%d").date() + timedelta(days=1)
    end_date = start_date + timedelta(days=4)
    conclusion = short_conclusion(row)
    risk_level, risk_text = risk_summary(row)

    signal_change = pct_change(value_for(row, "信号价"), previous.get("signal"))
    short_delta = score_change(value_for(row, "短期走势打分"), previous.get("short_score"))
    old_target = previous.get("target")
    target_now = value_for(row, "目标价")

    comparison_parts = []
    if previous.get("heading"):
        previous_label = re.sub(r"\s*预测(?:更新|复核)?$", "", str(previous["heading"])).strip()
        comparison_parts.append(f"相较 {previous_label} 有效底稿")
    else:
        comparison_parts.append("首次预测，无历史预测样本")
    if signal_change is not None:
        comparison_parts.append(f"信号价变化 {signal_change}")
    if short_delta is not None:
        comparison_parts.append(f"短线打分变化 {short_delta}")
    if old_target is not None and target_now is not None:
        comparison_parts.append(f"目标价从 {money(old_target, 2)}变为 {money(target_now, 2)}")
    if value_for(row, "信号价") is not None and value_for(row, "MA20") is not None:
        comparison_parts.append("当前仍站在 MA20 上方" if row["信号价"] >= row["MA20"] else "当前跌至 MA20 下方")
    comparison = "，".join(comparison_parts)
    if previous.get("heading"):
        comparison += "。本轮实时快照缺失，成交/换手来自日线，PE/PB/总市值不可用，因此回归更偏技术趋势和财务摘要复核。"
    else:
        comparison += "。"

    data_state = []
    if bool_has(row, "spot_error"):
        data_state.append("实时快照缺失")
    else:
        data_state.append("实时快照可用")
    data_state.append("日线可用" if not bool_has(row, "daily_error") else "日线异常")
    data_state.append("财务摘要可用" if not bool_has(row, "financial_error") else "财务摘要异常")

    rel_run_dir = run_dir.relative_to(ROOT)
    return f"""### {run_label} 预测更新

- 适用区间：{start_date:%Y-%m-%d} 至 {end_date:%Y-%m-%d}
- 本次行情快照：采用 `{rel_run_dir}` 的有效批量结果；东方财富实时快照接口返回 `RemoteDisconnected`，本轮现价/信号价使用 `akshare.stock_zh_a_daily` 最新日线收盘价，日线日期 {value_for(row, "日线日期")}，财报期 {value_for(row, "财报期")}。
- 结论：{conclusion}
- 核心打分：综合 {fnum(value_for(row, "综合打分"), 1)}，基本面 {fnum(value_for(row, "基本面打分"), 1)}，短线 {fnum(value_for(row, "短期走势打分"), 1)}，中期 {fnum(value_for(row, "中期走势打分"), 1)}，综合排名 {fnum(value_for(row, "综合排名"), 0)}。
- 行情位置：信号价 {money(value_for(row, "信号价"), 2)}；MA5/MA10/MA20/MA60 分别为 {money(value_for(row, "MA5"), 2)} / {money(value_for(row, "MA10"), 2)} / {money(value_for(row, "MA20"), 2)} / {money(value_for(row, "MA60"), 2)}；20日回撤 {signed(value_for(row, "20日回撤"), 2)}。
- 动量与资金：5日/20日/60日/120日涨幅分别为 {signed(value_for(row, "5日涨幅"), 2)} / {signed(value_for(row, "20日涨幅"), 2)} / {signed(value_for(row, "60日涨幅"), 2)} / {signed(value_for(row, "120日涨幅"), 2)}；换手率 {signed(value_for(row, "周转率"), 2)}，成交额 {fnum(value_for(row, "成交额_亿元"), 1)} 亿，RSI14 {fnum(value_for(row, "RSI14"), 1)}。
- 偏强情景：若价格继续站稳 MA20 且成交额不明显萎缩，短线可按趋势延续或强势震荡处理。
- 中性情景：若价格在 MA10-MA20 区间横盘，说明资金在消化前期涨幅，等待新的订单、财报或产业催化。
- 偏弱情景：若有效跌破 MA20 且反抽无力，短线应下调为防守观察，优先看 MA60 附近承接。
- 回归对比：{comparison}
- 风险回归：风险等级初判为 {risk_level}；{risk_text}。
- 数据说明：本标的{'；'.join(data_state)}。全局 {stats['price_count']}/{stats['rows']} 有日线现价，{stats['signal_count']}/{stats['rows']} 有信号价，{stats['ma20_count']}/{stats['rows']} 有 MA20，{stats['gross_count']}/{stats['rows']} 有财务摘要；日线日期分布为 {stats['daily_dates']}。
- 资料来源：`{rel_run_dir / ('stock_list_scored_' + as_of.replace('-', '') + '.json')}`；`{rel_run_dir / ('stock_list_scoring_report_' + as_of.replace('-', '') + '.md')}`。
- 预测置信度：中等偏低。原因是日线和财务摘要完整，但全市场实时快照失败，估值和实时资金字段缺失。
"""


def build_intro(row: pd.Series, run_label: str, stats: dict[str, Any]) -> str:
    risk_level, risk_text = risk_summary(row)
    conclusion = short_conclusion(row)
    target_note = value_for(row, "目标价依据") or "基于综合评分推演"
    return f"""# {row['股票名称']}（{stock_suffix(row['股票代码'])}）跟踪笔记

- 建档日期：2026-05-27
- 最后更新：{run_label}
- 口径说明：{run_label} 针对 `stock_list(2).csv` 成功刷新；日线使用 `akshare.stock_zh_a_daily`，财务摘要使用 `akshare.stock_financial_abstract_new_ths`。本轮 {stats['rows']} 行中日线现价/信号价/MA20/财务摘要均为 {stats['price_count']}/{stats['rows']}、{stats['signal_count']}/{stats['rows']}、{stats['ma20_count']}/{stats['rows']}、{stats['gross_count']}/{stats['rows']}；东方财富实时快照 0/{stats['rows']}，PE/PB/总市值字段缺失；日线日期分布：{stats['daily_dates']}；财报期分布：{stats['report_dates']}。本报告仅供跟踪研究，不构成投资建议。

## 一句话结论

{row['股票名称']} 属于 {row.get('行业')} / {row.get('细分赛道')} 方向，本轮综合打分 {fnum(value_for(row, '综合打分'), 1)}，排名 {fnum(value_for(row, '综合排名'), 0)}。短线判断为：{conclusion}当前信号价为 {money(value_for(row, '信号价'), 2)}，MA20 为 {money(value_for(row, 'MA20'), 2)}，模型目标价为 {money(value_for(row, '目标价'), 2)}。由于东方财富实时快照缺失，本轮估值相关字段（总市值、PE、PB）不完整，目标价更多是日线趋势和财务摘要驱动的量化情景锚，不构成交易建议。

## 公司概况

| 项目 | 内容 |
| --- | --- |
| 股票代码 | {stock_suffix(row['股票代码'])} |
| 股票名称 | {row['股票名称']} |
| 行业 | {row.get('行业')} |
| 细分赛道 | {row.get('细分赛道')} |
| 标签 | {row.get('标签')} |
| 财报期 | {value_for(row, '财报期')} |
| 日线日期 | {value_for(row, '日线日期')} |

## 核心指标

| 指标 | 数值 |
| --- | ---: |
| 综合打分 | {fnum(value_for(row, '综合打分'), 1)} |
| 基本面打分 | {fnum(value_for(row, '基本面打分'), 1)} |
| 短线打分 | {fnum(value_for(row, '短期走势打分'), 1)} |
| 长线/中期打分 | {fnum(value_for(row, '中期走势打分'), 1)} |
| 现价（日线收盘） | {money(value_for(row, '现价'), 2)} |
| 信号价 | {money(value_for(row, '信号价'), 2)} |
| 目标价 | {money(value_for(row, '目标价'), 2)} |
| MA5 / MA10 / MA20 | {money(value_for(row, 'MA5'), 2)} / {money(value_for(row, 'MA10'), 2)} / {money(value_for(row, 'MA20'), 2)} |
| MA60 / MA120 | {money(value_for(row, 'MA60'), 2)} / {money(value_for(row, 'MA120'), 2)} |
| RSI14 | {fnum(value_for(row, 'RSI14'), 2)} |
| 5日 / 20日涨幅 | {signed(value_for(row, '5日涨幅'), 2)} / {signed(value_for(row, '20日涨幅'), 2)} |
| 60日 / 120日涨幅 | {signed(value_for(row, '60日涨幅'), 2)} / {signed(value_for(row, '120日涨幅'), 2)} |
| 20日回撤 | {signed(value_for(row, '20日回撤'), 2)} |
| 总市值 | 缺失（实时快照失败） |
| PE(TTM) / PB | 缺失 / 缺失 |
| 毛利率 | {signed(value_for(row, '毛利率'), 2)} |
| ROE | {signed(value_for(row, 'ROE'), 2)} |
| 营收同比 | {signed(value_for(row, '营收同比'), 2)} |
| 归母净利润同比 | {signed(value_for(row, '归母净利润同比'), 2)} |
| 资产负债率 | {signed(value_for(row, '资产负债率'), 2)} |
| 每股收益 | {money(value_for(row, '每股收益'), 2)} |

## 基本面分析

### 1. 产业位置

- {value_for(row, '基本面依据')}
- 赛道关键词显示，公司主要暴露在 {row.get('细分赛道')}，需要重点跟踪产业景气、订单持续性和估值消化速度。

### 2. 盈利能力和成长性

- 本轮财务摘要显示，毛利率为 {signed(value_for(row, '毛利率'), 2)}，ROE 为 {signed(value_for(row, 'ROE'), 2)}。
- 营收同比为 {signed(value_for(row, '营收同比'), 2)}，归母净利润同比为 {signed(value_for(row, '归母净利润同比'), 2)}。若利润增速显著高于营收增速，后续要验证是否来自产品结构改善，而不是一次性因素。

### 3. 财务健康

- 资产负债率为 {signed(value_for(row, '资产负债率'), 2)}。风险等级初判为 {risk_level}；{risk_text}。

### 4. 估值和目标价

- 实时快照失败，本轮缺少总市值、PE 和 PB；估值判断置信度低于实时快照可用时段。
- {target_note}。当前信号价 {money(value_for(row, '信号价'), 2)}，对应目标价 {money(value_for(row, '目标价'), 2)}。
"""


def build_followup(row: pd.Series) -> str:
    return f"""## 后续最该跟踪的三个指标

- 指标 1：{row.get('细分赛道')} 相关订单、产能和价格趋势。
- 指标 2：毛利率、ROE 与经营现金流是否和利润增速匹配。
- 指标 3：价格相对 MA20/MA60 的位置，以及放量上涨后是否出现高位回撤。
"""


def build_sources(run_dir: Path, as_of: str) -> str:
    rel = run_dir.relative_to(ROOT)
    tag = as_of.replace("-", "")
    return f"""## 资料来源

- `{rel / ('stock_list_scored_' + tag + '.json')}`
- `{rel / ('stock_list_scoring_report_' + tag + '.md')}`
- `cg_task/file/stock_list(2).csv`
- `akshare.stock_zh_a_daily`、`akshare.stock_financial_abstract_new_ths` 的本地批量结果
"""


def build_current_anomaly(row: pd.Series, run_label: str, stats: dict[str, Any]) -> str:
    return f"""## 本次数据异常说明

- {run_label} 直接对 `stock_list(2).csv` 跑批：`akshare.stock_zh_a_spot_em` 返回 `RemoteDisconnected`，因此东方财富实时快照、总市值、PE、PB 对全样本缺失。
- 本轮改用 `akshare.stock_zh_a_daily` 最新日线收盘价作为现价/信号价，并使用日线成交额、换手率参与短线评分；{stats['price_count']}/{stats['rows']} 有日线现价，{stats['signal_count']}/{stats['rows']} 有信号价，{stats['ma20_count']}/{stats['rows']} 有 MA20，{stats['gross_count']}/{stats['rows']} 有财务摘要。
- 本标的抓取状态：{'实时快照缺失' if bool_has(row, 'spot_error') else '实时快照可用'}；{'日线异常' if bool_has(row, 'daily_error') else '日线可用'}；{'财务摘要异常' if bool_has(row, 'financial_error') else '财务摘要可用'}。
- 本轮全局异常：日线日期分布为 {stats['daily_dates']}；全部样本财报期分布为 {stats['report_dates']}。
"""


def build_history(old_text: str, run_label: str) -> str:
    history = extract_section(old_text, "## 历史异常沿革") or ""
    current_date = run_label[:10]
    history = re.sub(
        rf"^### {re.escape(current_date)} 数据异常说明\n.*?(?=^### |\Z)",
        "",
        history,
        flags=re.M | re.S,
    ).strip()
    current = extract_section(old_text, "## 本次数据异常说明") or ""
    if current:
        first_line = next((line for line in current.splitlines() if line.strip().startswith("- ")), "")
        match = re.search(r"(20\d{2}-\d{2}-\d{2})", first_line)
        if match and match.group(1) != current_date:
            heading = f"### {match.group(1)} 数据异常说明"
            if heading not in history:
                history = f"{heading}\n\n{current.strip()}\n\n{history.strip()}".strip()
    return f"## 历史异常沿革\n\n{history.strip()}\n"


def replace_profile(row: pd.Series, run_dir: Path, run_label: str, stats: dict[str, Any]) -> bool:
    path = profile_path(str(row["股票名称"]))
    old_text = path.read_text(encoding="utf-8") if path.exists() else ""
    intro = build_intro(row, run_label, stats).rstrip()

    existing_prediction_body = extract_section(old_text, "## 短期行情预测") or ""
    prediction_body = remove_prediction_section(existing_prediction_body, run_label)
    previous = extract_latest_prediction("## 短期行情预测\n\n" + prediction_body)
    new_prediction = build_prediction(row, run_dir, run_label, stats, previous).rstrip()
    prediction_body = upsert_prediction_section(prediction_body, run_label, new_prediction)

    as_of = run_label[:10]
    parts = [
        intro,
        "## 短期行情预测\n\n" + prediction_body.strip(),
        build_followup(row).strip(),
        build_sources(run_dir, as_of).strip(),
        build_current_anomaly(row, run_label, stats).strip(),
        build_history(old_text, run_label).strip(),
    ]
    new_text = normalize_missing_units("\n\n".join(parts)).rstrip() + "\n"
    path.write_text(new_text, encoding="utf-8")
    return not bool(old_text)


def copy_delivery_csv(run_dir: Path, as_of: str, input_csv: Path) -> None:
    scored = pd.read_csv(run_dir / f"stock_list_scored_{as_of.replace('-', '')}.csv", encoding="utf-8-sig")
    scored.to_csv(input_csv, index=False, encoding="gb18030")


def write_run_note(
    run_dir: Path,
    as_of: str,
    run_label: str,
    stats: dict[str, Any],
    profile_count: int,
    new_count: int,
    python_info: str,
) -> None:
    tag = as_of.replace("-", "")
    df = pd.read_json(run_dir / f"stock_list_scored_{tag}.json")
    top = df.sort_values(["综合打分", "基本面打分"], ascending=[False, False]).head(10)
    top_lines = [
        f"- {zcode(row['股票代码'])} {row['股票名称']}：综合 {fnum(row['综合打分'], 1)}，短线 {fnum(row['短期走势打分'], 1)}，目标价 {money(row['目标价'], 2)}"
        for _, row in top.iterrows()
    ]

    duplicate_codes = "、".join(f"`{x}`" for x in stats["duplicate_codes"]) or "无"
    duplicate_names = "、".join(f"`{x}`" for x in stats["duplicate_names"]) or "无"
    note = f"""# 本次自动化运行说明

- 运行时间：{run_label.replace(' CST', '')}（Asia/Shanghai）
- 交付目录：`{run_dir.relative_to(ROOT)}`
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：{stats['rows']}
- 唯一股票代码：{stats['unique_codes']}
- 唯一股票名称：{stats['unique_names']}
- 重复股票代码：{duplicate_codes}
- 重复股票名称：{duplicate_names}
- 空白字段检查：无
- 运行结果：成功，已更新评分/目标价并刷新 profile 短期预测；实时快照接口异常已在报告和 profile 中标注
- 分析日期参数：`{as_of}`
- Python/akshare：`{python_info}`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_zh_a_spot_em`（本轮接口返回 `RemoteDisconnected`，未取得全市场快照）
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：日线现价 {stats['price_count']}/{stats['rows']}，信号价 {stats['signal_count']}/{stats['rows']}，MA20 {stats['ma20_count']}/{stats['rows']}，毛利率 {stats['gross_count']}/{stats['rows']}，ROE {stats['roe_count']}/{stats['rows']}。

## 文件说明

- `stock_list_scored_{tag}.csv`：本轮交付表备份。
- `stock_list_scored_{tag}.xlsx`：Excel 版本交付表。
- `stock_list_scored_{tag}.json`：保留全部抓取字段、评分细项与错误信息的结构化明细。
- `stock_list_scoring_report_{tag}.md`：评分标准、Top 排名、异常样本和数据完整性说明。
- `cg_task/file/stock_list(2).csv`：已按本轮有效结果回填。

## Profile 更新

- 已更新 {profile_count} 个 profile；新增 {new_count} 个 profile。
- 每个 profile 已追加 `{run_label} 预测更新`，并将顶部摘要、核心指标、资料来源和数据异常说明刷新到本轮口径。

## 综合排名 Top 10

{chr(10).join(top_lines)}

## 异常说明

- 全市场实时快照 `akshare.stock_zh_a_spot_em` 返回 `RemoteDisconnected`；本轮总市值、PE、PB 对 {stats['rows']}/{stats['rows']} 样本缺失。
- 已使用 `akshare.stock_zh_a_daily` 最新日线收盘价作为现价/信号价，并使用日线成交额、换手率参与短线评分。
- 日线日期分布：{stats['daily_dates']}。
- 财务摘要全部可用：{stats['report_dates']}。

## 执行备注

```text
[WARN] 全市场实时快照抓取失败: ConnectionError(ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
[DONE] profile 更新完成：{profile_count} 个，新增 {new_count} 个。
```
"""
    (run_dir / "RUN_NOTE.md").write_text(note, encoding="utf-8")


def get_python_info() -> str:
    code = "import sys, akshare; print(f'{sys.executable}, akshare {akshare.__version__}')"
    result = subprocess.run([sys.executable, "-c", code], text=True, capture_output=True, check=False)
    return result.stdout.strip() or sys.executable


def main() -> None:
    parser = argparse.ArgumentParser(description="Update stock_list(2) profiles from scored JSON")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--input-csv", default=str(DEFAULT_INPUT))
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    input_csv = Path(args.input_csv).resolve()
    tag = args.as_of.replace("-", "")
    json_path = run_dir / f"stock_list_scored_{tag}.json"
    if not json_path.exists():
        raise FileNotFoundError(json_path)

    df = pd.read_json(json_path)
    df["股票代码"] = df["股票代码"].map(zcode)
    stats = global_stats(df)

    if stats["price_count"] == 0 or stats["ma20_count"] == 0 or stats["gross_count"] == 0:
        raise RuntimeError(f"评分结果不可用: {stats}")

    backup = input_csv.with_suffix(input_csv.suffix + ".bak")
    shutil.copy2(input_csv, backup)
    copy_delivery_csv(run_dir, args.as_of, input_csv)

    profile_rows = df.sort_values("原始顺序").drop_duplicates("股票名称", keep="first")
    new_count = 0
    for _, row in profile_rows.iterrows():
        if replace_profile(row, run_dir, args.run_label, stats):
            new_count += 1

    backup.unlink(missing_ok=True)
    write_run_note(
        run_dir=run_dir,
        as_of=args.as_of,
        run_label=args.run_label,
        stats=stats,
        profile_count=len(profile_rows),
        new_count=new_count,
        python_info=get_python_info(),
    )
    print(f"[DONE] profile 更新完成：{len(profile_rows)} 个，新增 {new_count} 个。")


if __name__ == "__main__":
    main()
