#!/usr/bin/env python3
"""
批量分析 A 股股票列表，并输出基本面、短期走势、中期走势评分。

数据源：
- akshare.stock_financial_abstract_new_ths: 财务摘要
- akshare.stock_zh_a_spot_em: 东方财富全市场实时快照
- akshare.stock_zh_a_daily: 日线行情

说明：
- 日线技术指标通常使用最新可得日线；若实时快照存在，则用实时价对均线位置做补充判断。
- 本脚本优先保证批量稳定性，遇到单只股票失败会记录错误并继续。
"""

from __future__ import annotations

import argparse
import json
import math
import signal
import time
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from urllib3.exceptions import NotOpenSSLWarning

    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except Exception:
    pass

import akshare as ak
import numpy as np
import pandas as pd


pd.set_option("display.max_columns", 200)


REQUIRED_SCORE_COLUMNS = [
    "月涨幅(%)",
    "年涨幅(%)",
    "周转率",
    "成交额_亿元",
    "60日涨幅",
    "120日涨幅",
    "52周最高",
    "52周最低",
    "信号价",
    "MA5",
    "MA10",
    "MA20",
    "MA60",
    "MA120",
    "20日回撤",
    "总市值_亿元",
    "市盈率_TTM",
    "毛利率",
    "ROE",
    "营收同比",
    "归母净利润同比",
]

DEFAULT_OUTPUT_COLUMNS = [
    "股票代码",
    "股票名称",
    "行业",
    "细分赛道",
    "标签",
    "月涨幅(%)",
    "年涨幅(%)",
    "基本面打分",
    "短线打分",
    "长线打分",
    "目标价",
    "备注",
    "是否持仓股",
]


HOT_SUBTRACK_KEYWORDS = {
    "CPO光引擎": 20,
    "高速光模块": 19,
    "硅光模块": 18,
    "高速光芯片": 18,
    "AI算力芯片": 18,
    "先进封装": 17,
    "先进制程": 17,
    "ABF载板": 16,
    "PCB": 15,
    "CMP设备": 17,
    "光刻设备": 18,
    "刻蚀设备": 18,
    "薄膜沉积": 18,
    "碳化硅基板": 15,
    "车规芯片": 14,
    "存储芯片": 14,
    "光纤光缆": 12,
    "铜箔": 12,
    "电子特气": 14,
    "光刻胶": 15,
}

TAG_SCORES = {
    "全球龙头": 8,
    "国家队龙头": 8,
    "行业龙头": 7,
    "龙头": 6,
    "技术标杆": 5,
    "高毛利": 5,
    "技术壁垒高": 5,
    "产能领先": 4,
    "全产业链": 4,
    "客户优质": 3,
    "机构重仓": 3,
    "技术领先": 3,
    "技术突破": 3,
    "国产替代": 3,
    "自主可控": 3,
    "核心供应商": 3,
    "核心": 2,
    "海外拓展": 2,
    "国资背景": 2,
}


@dataclass
class FetchResult:
    data: Optional[Any]
    error: Optional[str] = None


class FetchTimeoutError(RuntimeError):
    """单次抓取超时"""


def safe_float(value: Any) -> Optional[float]:
    if value is None or value == "" or value == "--" or value == "nan":
        return None
    if isinstance(value, (float, int, np.floating, np.integer)):
        if pd.isna(value):
            return None
        return float(value)
    if isinstance(value, str):
        cleaned = (
            value.replace("%", "")
            .replace(",", "")
            .replace("亿元", "")
            .replace("亿", "")
            .replace("万元", "")
            .strip()
        )
        if cleaned in {"", "--", "None"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def zfill_code(code: Any) -> str:
    return str(code).strip().zfill(6)


def normalize_hk_code(value: Any) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    if text.endswith(".0"):
        text = text[:-2]
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return text
    return digits.zfill(5)


def symbol_for_daily(code: str) -> str:
    code = zfill_code(code)
    if code.startswith(("83", "87", "92")):
        return f"bj{code}"
    if code.startswith(("60", "68", "90")):
        return f"sh{code}"
    return f"sz{code}"


def symbol_for_xq(code: str) -> str:
    code = zfill_code(code)
    if code.startswith(("83", "87", "92")):
        return f"BJ{code}"
    if code.startswith(("60", "68", "90")):
        return f"SH{code}"
    return f"SZ{code}"


def _raise_timeout(signum, frame) -> None:  # noqa: ARG001
    raise FetchTimeoutError("request timed out")


def call_with_retry(
    func,
    *args,
    retries: int = 3,
    pause: float = 0.8,
    timeout_sec: float = 15.0,
    **kwargs,
) -> FetchResult:
    last_error = None
    for attempt in range(retries):
        try:
            old_handler = signal.signal(signal.SIGALRM, _raise_timeout)
            signal.setitimer(signal.ITIMER_REAL, timeout_sec)
            try:
                return FetchResult(data=func(*args, **kwargs))
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old_handler)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < retries - 1:
                time.sleep(pause * (attempt + 1))
    return FetchResult(data=None, error=repr(last_error))


def read_stock_list(path: Path) -> pd.DataFrame:
    encodings = ["gbk", "gb18030", "utf-8-sig", "utf-8"]
    last_error = None
    for encoding in encodings:
        try:
            df = pd.read_csv(path, encoding=encoding, dtype={"股票代码": str})
            df["股票代码"] = df["股票代码"].map(zfill_code)
            if "港股代码" in df.columns:
                df["港股代码"] = df["港股代码"].map(normalize_hk_code)
            df["原始顺序"] = range(len(df))
            for col in ["月涨幅(%)", "年涨幅(%)"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            return df
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise RuntimeError(f"读取股票列表失败: {last_error}")


def normalize_spot_df(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {}
    result = {}
    for _, row in df.iterrows():
        item = str(row.get("item", "")).strip()
        if item:
            result[item] = row.get("value")
    return result


def build_spot_snapshot_map(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    if df is None or df.empty:
        return {}

    work = df.copy()
    rename_map = {
        "代码": "股票代码",
        "名称": "股票名称",
        "最新价": "现价",
        "涨跌幅": "涨幅",
        "成交额": "成交额",
        "换手率": "周转率",
        "总市值": "总市值",
        "流通市值": "流通市值",
        "市盈率-动态": "市盈率_TTM",
        "市净率": "市净率",
        "60日涨跌幅": "60日涨幅",
        "年初至今涨跌幅": "年初至今涨跌幅",
    }
    work = work.rename(columns=rename_map)
    if "股票代码" not in work.columns:
        return {}

    work["股票代码"] = work["股票代码"].map(zfill_code)
    spot_map: Dict[str, Dict[str, Any]] = {}

    for _, row in work.iterrows():
        code = row["股票代码"]
        latest_price = safe_float(row.get("现价"))
        total_mv = safe_float(row.get("总市值"))
        float_mv = safe_float(row.get("流通市值"))
        amount = safe_float(row.get("成交额"))

        record = {
            "现价": latest_price,
            "涨幅": safe_float(row.get("涨幅")),
            "周转率": safe_float(row.get("周转率")),
            "成交额": amount,
            "成交额_亿元": amount / 1e8 if amount is not None else None,
            "流通市值_亿元": float_mv / 1e8 if float_mv is not None else None,
            "总市值_亿元": total_mv / 1e8 if total_mv is not None else None,
            "市盈率_TTM": safe_float(row.get("市盈率_TTM")),
            "市净率": safe_float(row.get("市净率")),
            "60日涨幅": safe_float(row.get("60日涨幅")),
            "年涨幅(%)": safe_float(row.get("年初至今涨跌幅")),
        }
        spot_map[code] = record

    return spot_map


def extract_financial_snapshot(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {}
    work = df.copy()
    work["report_date"] = pd.to_datetime(work["report_date"])
    latest_date = work["report_date"].max()
    latest = work.loc[work["report_date"] == latest_date].copy()
    latest["metric_name"] = latest["metric_name"].astype(str)
    metric_map = latest.set_index("metric_name")["value"].to_dict()

    def metric(name: str) -> Optional[float]:
        return safe_float(metric_map.get(name))

    return {
        "财报期": latest_date.strftime("%Y-%m-%d"),
        "营收": metric("operating_income_total"),
        "营收同比": metric("calculate_operating_income_total_yoy_growth_ratio"),
        "归母净利润": metric("parent_holder_net_profit"),
        "归母净利润同比": metric("calculate_parent_holder_net_profit_yoy_growth_ratio"),
        "毛利率": metric("sale_gross_margin"),
        "ROE": metric("index_weighted_avg_roe"),
        "资产负债率": metric("assets_debt_ratio"),
        "每股净资产": metric("calc_per_net_assets"),
        "每股收益": metric("basic_eps"),
    }


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def extract_daily_snapshot(df: pd.DataFrame, spot_price: Optional[float]) -> Dict[str, Any]:
    if df is None or df.empty:
        return {}

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    work = work.sort_values("date").reset_index(drop=True)

    close = work["close"].astype(float)
    work["ma5"] = close.rolling(5).mean()
    work["ma10"] = close.rolling(10).mean()
    work["ma20"] = close.rolling(20).mean()
    work["ma60"] = close.rolling(60).mean()
    work["ma120"] = close.rolling(120).mean()
    work["rsi14"] = calc_rsi(close, 14)
    work["ret_5d"] = close.pct_change(5) * 100
    work["ret_20d"] = close.pct_change(20) * 100
    work["ret_60d"] = close.pct_change(60) * 100
    work["ret_120d"] = close.pct_change(120) * 100
    work["amt_ma5"] = work["amount"].rolling(5).mean()
    work["amt_ma20"] = work["amount"].rolling(20).mean()
    work["volume_ma5"] = work["volume"].rolling(5).mean()
    work["close_20d_max"] = close.rolling(20).max()
    work["close_60d_max"] = close.rolling(60).max()
    work["close_120d_max"] = close.rolling(120).max()
    latest = work.iloc[-1]

    signal_price = spot_price if spot_price is not None else float(latest["close"])
    dd20 = None
    if latest["close_20d_max"] not in (None, 0) and not pd.isna(latest["close_20d_max"]):
        dd20 = (signal_price / latest["close_20d_max"] - 1) * 100

    return {
        "日线日期": latest["date"].strftime("%Y-%m-%d"),
        "收盘价": float(latest["close"]),
        "信号价": signal_price,
        "日线成交额": safe_float(latest["amount"]),
        "日线换手率": safe_float(latest["turnover"]) * 100 if pd.notna(latest["turnover"]) else None,
        "MA5": safe_float(latest["ma5"]),
        "MA10": safe_float(latest["ma10"]),
        "MA20": safe_float(latest["ma20"]),
        "MA60": safe_float(latest["ma60"]),
        "MA120": safe_float(latest["ma120"]),
        "RSI14": safe_float(latest["rsi14"]),
        "5日涨幅": safe_float(latest["ret_5d"]),
        "20日涨幅": safe_float(latest["ret_20d"]),
        "60日涨幅": safe_float(latest["ret_60d"]),
        "120日涨幅": safe_float(latest["ret_120d"]),
        "252日涨幅": safe_float(close.pct_change(252).iloc[-1] * 100) if len(close) > 252 else None,
        "5日均成交额": safe_float(latest["amt_ma5"]),
        "20日均成交额": safe_float(latest["amt_ma20"]),
        "日线52周最高": safe_float(close.tail(252).max()),
        "日线52周最低": safe_float(close.tail(252).min()),
        "20日回撤": dd20,
        "日线样本数": len(work),
    }


def score_industry_position(subtrack: str, tags: str) -> Tuple[float, str]:
    base = 8
    matched = []
    for keyword, value in HOT_SUBTRACK_KEYWORDS.items():
        if keyword in subtrack:
            base = max(base, value - 4)
            matched.append(keyword)
    tag_score = 0
    for keyword, value in TAG_SCORES.items():
        if keyword in tags:
            tag_score += value
            matched.append(keyword)
    score = min(20.0, base + min(tag_score, 12))
    reason = "、".join(dict.fromkeys(matched)) if matched else "赛道与标签信息一般"
    return score, reason


def score_market_cap(total_market_cap_billion: Optional[float]) -> Tuple[float, str]:
    if total_market_cap_billion is None:
        return 7.0, "缺少总市值数据，按中性处理"
    v = total_market_cap_billion
    if 100 <= v <= 800:
        return 15.0, f"总市值{v:.0f}亿，处于进可攻退可守区间"
    if 50 <= v < 100 or 800 < v <= 1500:
        return 12.0, f"总市值{v:.0f}亿，体量适中"
    if 20 <= v < 50 or 1500 < v <= 2500:
        return 9.0, f"总市值{v:.0f}亿，弹性或空间略受限"
    if v < 20:
        return 7.0, f"总市值{v:.0f}亿，弹性高但波动与流动性风险更大"
    return 6.0, f"总市值{v:.0f}亿，体量偏大导致赔率下降"


def score_pe(pe_ttm: Optional[float], profit_yoy: Optional[float]) -> Tuple[float, str]:
    if pe_ttm is None or pe_ttm <= 0:
        return 4.0, "PE不可用或为负，估值可信度较低"
    if pe_ttm <= 30:
        score = 20.0
    elif pe_ttm <= 50:
        score = 16.0
    elif pe_ttm <= 80:
        score = 12.0
    elif pe_ttm <= 120:
        score = 8.0
    elif pe_ttm <= 200:
        score = 4.0
    else:
        score = 1.0
    if profit_yoy is not None and profit_yoy > 30 and pe_ttm < profit_yoy * 2:
        score = min(20.0, score + 3.0)
        return score, f"PE(TTM){pe_ttm:.1f}倍，增速能部分消化估值"
    return score, f"PE(TTM){pe_ttm:.1f}倍"


def score_gross_margin(gross_margin: Optional[float]) -> Tuple[float, str]:
    if gross_margin is None:
        return 8.0, "缺少毛利率数据，按中性处理"
    if gross_margin >= 50:
        return 20.0, f"毛利率{gross_margin:.1f}%，盈利壁垒强"
    if gross_margin >= 40:
        return 17.0, f"毛利率{gross_margin:.1f}%，盈利能力优秀"
    if gross_margin >= 30:
        return 14.0, f"毛利率{gross_margin:.1f}%，盈利能力良好"
    if gross_margin >= 20:
        return 10.0, f"毛利率{gross_margin:.1f}%，处于一般水平"
    if gross_margin >= 10:
        return 6.0, f"毛利率{gross_margin:.1f}%，利润垫偏薄"
    return 2.0, f"毛利率{gross_margin:.1f}%，竞争压力较大"


def score_quality_growth(roe: Optional[float], revenue_yoy: Optional[float], profit_yoy: Optional[float]) -> Tuple[float, str]:
    score = 0.0
    reasons = []

    if roe is None:
        score += 4.0
        reasons.append("ROE缺失")
    elif roe >= 20:
        score += 10.0
        reasons.append(f"ROE {roe:.1f}%")
    elif roe >= 15:
        score += 8.0
        reasons.append(f"ROE {roe:.1f}%")
    elif roe >= 10:
        score += 6.0
        reasons.append(f"ROE {roe:.1f}%")
    elif roe >= 5:
        score += 4.0
        reasons.append(f"ROE {roe:.1f}%")
    else:
        score += 2.0
        reasons.append(f"ROE {roe:.1f}%偏低")

    if revenue_yoy is None:
        score += 3.0
    elif revenue_yoy >= 30:
        score += 7.0
        reasons.append(f"营收同比{revenue_yoy:.1f}%")
    elif revenue_yoy >= 15:
        score += 5.0
        reasons.append(f"营收同比{revenue_yoy:.1f}%")
    elif revenue_yoy > 0:
        score += 3.0
        reasons.append(f"营收同比{revenue_yoy:.1f}%")
    else:
        score += 1.0
        reasons.append(f"营收同比{revenue_yoy:.1f}%")

    if profit_yoy is None:
        score += 3.0
    elif profit_yoy >= 50:
        score += 8.0
        reasons.append(f"利润同比{profit_yoy:.1f}%")
    elif profit_yoy >= 20:
        score += 6.0
        reasons.append(f"利润同比{profit_yoy:.1f}%")
    elif profit_yoy > 0:
        score += 4.0
        reasons.append(f"利润同比{profit_yoy:.1f}%")
    else:
        score += 1.0
        reasons.append(f"利润同比{profit_yoy:.1f}%")

    return min(25.0, score), "；".join(reasons[:3])


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def pct_rank_series(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce")
    if clean.notna().sum() == 0:
        return pd.Series(np.nan, index=series.index)
    return clean.rank(pct=True)


def score_short_term(row: pd.Series) -> Tuple[float, str]:
    hot = 20 * row.get("月涨幅分位", 0.5) + 10 * row.get("年涨幅分位", 0.5)
    fund = 15 * row.get("换手率分位", 0.5) + 15 * row.get("成交额分位", 0.5)

    signal_price = row.get("信号价")
    ma5 = row.get("MA5")
    ma10 = row.get("MA10")
    ma20 = row.get("MA20")
    rsi14 = row.get("RSI14")
    ret_5d = row.get("5日涨幅")

    tech = 0.0
    if pd.notna(signal_price) and pd.notna(ma5) and signal_price >= ma5:
        tech += 8
    if pd.notna(signal_price) and pd.notna(ma10) and signal_price >= ma10:
        tech += 8
    if pd.notna(signal_price) and pd.notna(ma20) and signal_price >= ma20:
        tech += 8
    if pd.notna(ma5) and pd.notna(ma10) and pd.notna(ma20) and ma5 >= ma10 >= ma20:
        tech += 8
    if pd.notna(rsi14):
        if 50 <= rsi14 <= 75:
            tech += 4
        elif 45 <= rsi14 < 50 or 75 < rsi14 <= 80:
            tech += 2
    if pd.notna(ret_5d) and ret_5d > 0:
        tech += 4

    score = clamp(hot + fund + tech)
    reasons = [
        f"月涨幅分位{row.get('月涨幅分位', np.nan):.0%}" if pd.notna(row.get("月涨幅分位")) else "月涨幅缺失",
        f"换手率{row.get('周转率', np.nan):.2f}%" if pd.notna(row.get("周转率")) else "换手率缺失",
        f"成交额{row.get('成交额_亿元', np.nan):.1f}亿" if pd.notna(row.get("成交额_亿元")) else "成交额缺失",
    ]
    if pd.notna(signal_price) and pd.notna(ma20):
        reasons.append("价在MA20上方" if signal_price >= ma20 else "价在MA20下方")
    return score, "；".join(reasons)


def score_mid_term(row: pd.Series) -> Tuple[float, str]:
    signal_price = row.get("信号价")
    ma20 = row.get("MA20")
    ma60 = row.get("MA60")
    ma120 = row.get("MA120")

    structure = 0.0
    if pd.notna(signal_price) and pd.notna(ma20) and signal_price >= ma20:
        structure += 10
    if pd.notna(signal_price) and pd.notna(ma60) and signal_price >= ma60:
        structure += 10
    if pd.notna(signal_price) and pd.notna(ma120) and signal_price >= ma120:
        structure += 8
    elif pd.notna(signal_price) and pd.notna(ma60):
        structure += 4
    if pd.notna(ma20) and pd.notna(ma60) and ma20 >= ma60:
        structure += 6
    if pd.notna(ma60) and pd.notna(ma120) and ma60 >= ma120:
        structure += 6

    momentum = 20 * row.get("60日涨幅分位", 0.5) + 10 * row.get("120日涨幅分位", 0.5)

    pos52 = row.get("52周位置", np.nan)
    dd20 = row.get("20日回撤")
    position = 0.0
    if pd.notna(pos52):
        position += 15 * pos52
    else:
        position += 7.5
    if pd.notna(dd20):
        if dd20 >= -8:
            position += 8
        elif dd20 >= -15:
            position += 5
        elif dd20 >= -25:
            position += 2
    high_ratio = row.get("距52周高点比例")
    if pd.notna(high_ratio):
        if high_ratio >= 0.85:
            position += 7
        elif high_ratio >= 0.7:
            position += 5
        elif high_ratio >= 0.5:
            position += 2

    score = clamp(structure + momentum + position)
    reasons = [
        f"60日涨幅分位{row.get('60日涨幅分位', np.nan):.0%}" if pd.notna(row.get("60日涨幅分位")) else "60日涨幅缺失",
        f"52周位置{row.get('52周位置', np.nan):.0%}" if pd.notna(row.get("52周位置")) else "52周位置缺失",
        f"20日回撤{row.get('20日回撤', np.nan):.1f}%" if pd.notna(row.get("20日回撤")) else "20日回撤缺失",
    ]
    return score, "；".join(reasons)


def build_fundamental_score(row: pd.Series) -> Tuple[float, str]:
    industry_score, industry_reason = score_industry_position(str(row.get("细分赛道", "")), str(row.get("标签", "")))
    cap_score, cap_reason = score_market_cap(row.get("总市值_亿元"))
    pe_score, pe_reason = score_pe(row.get("市盈率_TTM"), row.get("归母净利润同比"))
    gm_score, gm_reason = score_gross_margin(row.get("毛利率"))
    qg_score, qg_reason = score_quality_growth(row.get("ROE"), row.get("营收同比"), row.get("归母净利润同比"))
    total = clamp(industry_score + cap_score + pe_score + gm_score + qg_score)
    reasons = [industry_reason, cap_reason, pe_reason, gm_reason, qg_reason]
    return total, "；".join([x for x in reasons if x])


def build_target_price(row: pd.Series) -> Tuple[Optional[float], str]:
    signal_price = row.get("信号价")
    if pd.isna(signal_price):
        return None, "缺少现价，无法估算目标价"

    fund_score = safe_float(row.get("基本面打分")) or 0.0
    short_score = safe_float(row.get("短期走势打分")) or 0.0
    mid_score = safe_float(row.get("中期走势打分")) or 0.0
    pe = row.get("市盈率_TTM")
    profit_yoy = row.get("归母净利润同比")

    base_upside = (fund_score - 50) * 0.0035 + (mid_score - 50) * 0.002 + (short_score - 50) * 0.0015
    valuation_bonus = 0.0
    if pd.notna(pe):
        if pe <= 30:
            valuation_bonus += 0.12
        elif pe <= 50:
            valuation_bonus += 0.08
        elif pe <= 80:
            valuation_bonus += 0.04
        elif pe >= 120:
            valuation_bonus -= 0.08
    if pd.notna(profit_yoy):
        if profit_yoy >= 50:
            valuation_bonus += 0.08
        elif profit_yoy >= 20:
            valuation_bonus += 0.04
        elif profit_yoy < 0:
            valuation_bonus -= 0.08

    upside = max(-0.25, min(0.8, base_upside + valuation_bonus))
    target_price = float(signal_price) * (1 + upside)
    return round(target_price, 2), f"基于综合评分推演，较现价预留{upside * 100:.1f}%空间"


def build_summary_note(row: pd.Series, target_note: str) -> str:
    parts: list[str] = []
    if pd.notna(row.get("基本面打分")):
        parts.append(f"基本面{row.get('基本面打分'):.1f}")
    if pd.notna(row.get("短期走势打分")):
        parts.append(f"短线{row.get('短期走势打分'):.1f}")
    if pd.notna(row.get("中期走势打分")):
        parts.append(f"中期{row.get('中期走势打分'):.1f}")

    basis = []
    for key in ("基本面依据", "短期依据", "中期依据"):
        value = row.get(key)
        if isinstance(value, str) and value:
            basis.append(value)
    parts.extend(basis[:2])
    if target_note:
        parts.append(target_note)
    return " | ".join(parts[:5])


def fetch_one(
    row: pd.Series,
    pause: float,
    timeout_sec: float,
    retries: int,
    spot_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    code = zfill_code(row["股票代码"])
    name = row.get("股票名称", "")
    print(f"[FETCH] {code} {name}", flush=True)

    record: Dict[str, Any] = {
        "股票代码": code,
        "股票名称": name,
        "原始顺序": row.get("原始顺序"),
        "行业": row.get("行业"),
        "细分赛道": row.get("细分赛道"),
        "标签": row.get("标签"),
        "月涨幅(%)": row.get("月涨幅(%)"),
        "年涨幅(%)": row.get("年涨幅(%)"),
        "港股代码": row.get("港股代码"),
        "基本面打分": row.get("基本面打分"),
        "短线打分": row.get("短线打分"),
        "长线打分": row.get("长线打分"),
        "目标价": row.get("目标价"),
        "备注": row.get("备注"),
        "是否持仓股": row.get("是否持仓股"),
    }

    spot_snapshot = (spot_map or {}).get(code)
    if spot_snapshot:
        record.update(spot_snapshot)
    else:
        record["spot_error"] = "东方财富实时快照缺失"
    spot_price = safe_float(record.get("现价"))

    daily_result = call_with_retry(
        ak.stock_zh_a_daily,
        symbol=symbol_for_daily(code),
        adjust="qfq",
        retries=retries,
        timeout_sec=timeout_sec,
    )
    if daily_result.error:
        record["daily_error"] = daily_result.error
    daily_snapshot = extract_daily_snapshot(daily_result.data, spot_price) if daily_result.data is not None else {}
    record.update(daily_snapshot)

    fin_result = call_with_retry(
        ak.stock_financial_abstract_new_ths,
        symbol=code,
        retries=retries,
        timeout_sec=timeout_sec,
    )
    if fin_result.error:
        record["financial_error"] = fin_result.error
    fin_snapshot = extract_financial_snapshot(fin_result.data) if fin_result.data is not None else {}
    record.update(fin_snapshot)

    if record.get("现价") is None and record.get("收盘价") is not None:
        record["现价"] = record.get("收盘价")
    if record.get("信号价") is None and record.get("收盘价") is not None:
        record["信号价"] = record.get("收盘价")
    if record.get("成交额") is None and record.get("日线成交额") is not None:
        record["成交额"] = record.get("日线成交额")
    if record.get("成交额_亿元") is None and record.get("成交额") is not None:
        record["成交额_亿元"] = record["成交额"] / 1e8
    if record.get("周转率") is None and record.get("日线换手率") is not None:
        record["周转率"] = record.get("日线换手率")
    if record.get("52周最高") is None and record.get("日线52周最高") is not None:
        record["52周最高"] = record.get("日线52周最高")
    if record.get("52周最低") is None and record.get("日线52周最低") is not None:
        record["52周最低"] = record.get("日线52周最低")
    if pd.isna(record.get("月涨幅(%)")) and record.get("20日涨幅") is not None:
        record["月涨幅(%)"] = record.get("20日涨幅")
    if pd.isna(record.get("年涨幅(%)")) and record.get("252日涨幅") is not None:
        record["年涨幅(%)"] = record.get("252日涨幅")

    if pause > 0:
        time.sleep(pause)

    return record


def add_relative_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in REQUIRED_SCORE_COLUMNS:
        if column not in out.columns:
            out[column] = np.nan

    out["月涨幅分位"] = pct_rank_series(out["月涨幅(%)"]).fillna(0.5)
    out["年涨幅分位"] = pct_rank_series(out["年涨幅(%)"]).fillna(0.5)
    out["换手率分位"] = pct_rank_series(out["周转率"]).fillna(0.5)
    out["成交额分位"] = pct_rank_series(out["成交额_亿元"]).fillna(0.5)
    out["60日涨幅分位"] = pct_rank_series(out["60日涨幅"]).fillna(0.5)
    out["120日涨幅分位"] = pct_rank_series(out["120日涨幅"]).fillna(0.5)

    out["52周位置"] = np.where(
        (pd.notna(out["52周最高"])) & (pd.notna(out["52周最低"])) & ((out["52周最高"] - out["52周最低"]) > 0),
        (out["信号价"] - out["52周最低"]) / (out["52周最高"] - out["52周最低"]),
        np.nan,
    )
    out["52周位置"] = out["52周位置"].clip(lower=0, upper=1)
    out["距52周高点比例"] = np.where(
        (pd.notna(out["52周最高"])) & (out["52周最高"] > 0),
        out["信号价"] / out["52周最高"],
        np.nan,
    )
    return out


def build_scores(df: pd.DataFrame, output_columns: Optional[List[str]] = None) -> pd.DataFrame:
    out = add_relative_features(df)

    fundamentals = out.apply(build_fundamental_score, axis=1, result_type="expand")
    out["基本面打分"] = fundamentals[0].round(1)
    out["基本面依据"] = fundamentals[1]

    short_terms = out.apply(score_short_term, axis=1, result_type="expand")
    out["短期走势打分"] = short_terms[0].round(1)
    out["短期依据"] = short_terms[1]

    mid_terms = out.apply(score_mid_term, axis=1, result_type="expand")
    out["中期走势打分"] = mid_terms[0].round(1)
    out["中期依据"] = mid_terms[1]

    out["综合打分"] = (
        out["基本面打分"] * 0.4 + out["短期走势打分"] * 0.3 + out["中期走势打分"] * 0.3
    ).round(1)
    out["综合排名"] = out["综合打分"].rank(method="min", ascending=False).astype(int)

    target_prices = out.apply(build_target_price, axis=1, result_type="expand")
    out["目标价"] = target_prices[0]
    out["目标价依据"] = target_prices[1]
    out["短线打分"] = out["短期走势打分"]
    # 交付表历史列名保留为“长线打分”，实际承载当前任务要求的中期走势维度。
    out["长线打分"] = out["中期走势打分"]
    out["备注"] = out.apply(lambda row: build_summary_note(row, str(row.get("目标价依据", ""))), axis=1)

    ordered_base = [col for col in (output_columns or DEFAULT_OUTPUT_COLUMNS) if col in out.columns]
    remaining = [col for col in out.columns if col not in ordered_base]
    out = out[ordered_base + remaining]
    return out


def build_delivery_sheet(df: pd.DataFrame, output_columns: List[str]) -> pd.DataFrame:
    delivery = df.copy()
    for column in output_columns:
        if column not in delivery.columns:
            delivery[column] = np.nan
    if "原始顺序" in delivery.columns:
        delivery = delivery.sort_values("原始顺序", ascending=True)
    return delivery[output_columns].copy()


def render_top_table(df: pd.DataFrame, columns: List[str], top_n: int) -> str:
    sub = df.reindex(columns=columns).head(top_n).copy()
    return sub.to_markdown(index=False)


def build_report(df: pd.DataFrame, as_of: str) -> str:
    ranked = df.sort_values(["综合打分", "基本面打分"], ascending=[False, False]).reset_index(drop=True)
    columns = ["股票代码", "股票名称", "综合打分", "基本面打分", "短期走势打分", "中期走势打分", "细分赛道"]
    top_overall = render_top_table(ranked, columns, 20)
    top_fund = render_top_table(
        ranked.sort_values(["基本面打分", "综合打分"], ascending=[False, False]),
        ["股票代码", "股票名称", "基本面打分", "总市值_亿元", "市盈率_TTM", "毛利率", "ROE", "归母净利润同比", "细分赛道"],
        15,
    )
    top_short = render_top_table(
        ranked.sort_values(["短期走势打分", "综合打分"], ascending=[False, False]),
        ["股票代码", "股票名称", "短期走势打分", "月涨幅(%)", "周转率", "成交额_亿元", "信号价", "MA20", "细分赛道"],
        15,
    )
    top_mid = render_top_table(
        ranked.sort_values(["中期走势打分", "综合打分"], ascending=[False, False]),
        ["股票代码", "股票名称", "中期走势打分", "60日涨幅", "120日涨幅", "52周位置", "20日回撤", "细分赛道"],
        15,
    )

    def error_mask(column: str) -> pd.Series:
        if column in df.columns:
            return df[column].notna()
        return pd.Series(False, index=df.index)

    ranked_error_mask = (
        ranked["spot_error"].notna() if "spot_error" in ranked.columns else pd.Series(False, index=ranked.index)
    ) | (
        ranked["daily_error"].notna() if "daily_error" in ranked.columns else pd.Series(False, index=ranked.index)
    ) | (
        ranked["financial_error"].notna()
        if "financial_error" in ranked.columns
        else pd.Series(False, index=ranked.index)
    )

    error_rows = ranked.loc[ranked_error_mask].reindex(
        columns=["股票代码", "股票名称", "spot_error", "daily_error", "financial_error"]
    )

    error_section = "无明显抓取失败样本。"
    if not error_rows.empty:
        error_section = error_rows.head(20).to_markdown(index=False)

    report = f"""# 股票批量评分报告

- 分析日期：{as_of}
- 样本数量：{len(df)}
- 数据口径：
  - 基本面：akshare `stock_financial_abstract_new_ths`
  - 实时快照：akshare `stock_zh_a_spot_em`
  - 趋势日线：akshare `stock_zh_a_daily`
  - 说明：若 {as_of} 当日日线尚未完全落库，则均线与涨幅基于最新可得日线；资金参与强度优先取 {as_of} 实时快照。

## 打分标准

### 1. 基本面打分（0-100）

- 产业与竞争地位：0-20
  - 依据 `细分赛道` 和 `标签` 中的龙头、技术壁垒、国产替代、产能领先等关键词。
- 当前市值：0-15
  - 100-800 亿得分最高；过小偏交易化，过大则赔率下降。
- PE 估值：0-20
  - `PE(TTM)` 越低越有利，但高利润增速会获得适度加分。
- 毛利率：0-20
  - 毛利率越高，说明产品壁垒与议价能力越强。
- 质量与成长：0-25
  - 结合 ROE、营收同比、归母净利润同比。

### 2. 短期走势打分（0-100）

- 市场热点：0-30
  - 使用表内 `月涨幅(%)`、`年涨幅(%)` 的分位数衡量资金当下偏好。
- 资金参与：0-30
  - 结合最新换手率、成交额在全样本中的分位数。
- 技术指标：0-40
  - 价位相对 MA5/MA10/MA20
  - MA5 > MA10 > MA20 结构
  - RSI14
  - 5 日动量是否转正

### 3. 中期走势打分（0-100）

- 趋势结构：0-40
  - 价位相对 MA20/MA60/MA120
  - MA20/MA60/MA120 是否保持多头排列
- 中期动量：0-30
  - 60 日、120 日涨幅分位数
- 位置管理：0-30
  - 52 周区间位置
  - 相对 52 周高点距离
  - 20 日回撤控制

### 4. 综合打分

- `综合打分 = 基本面 * 40% + 短期走势 * 30% + 中期走势 * 30%`
- 交付表字段映射：
  - `基本面打分`：基本面维度分数
  - `短线打分`：短期走势维度分数
  - `长线打分`：因原始表结构限制，该列承载“中期走势”维度分数
- `中期走势打分` 在 JSON 明细和 Markdown 报告中保留完整字段；交付 CSV/XLSX 中映射回 `长线打分`。
- `目标价`：以信号价为锚，按基本面、短线、中期综合评分及估值/利润增速修正后的空间推演，不作为精确估值。

## 综合排名 Top 20

{top_overall}

## 基本面 Top 15

{top_fund}

## 短期走势 Top 15

{top_short}

## 中期走势 Top 15

{top_mid}

## 抓取异常样本

{error_section}
"""
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="批量分析股票列表并评分")
    parser.add_argument("--input", required=True, help="输入 CSV 文件路径")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    parser.add_argument("--as-of", required=True, help="分析日期，例如 2026-05-20")
    parser.add_argument("--pause", type=float, default=0.05, help="每只股票抓取后的额外暂停秒数")
    parser.add_argument("--timeout", type=float, default=4.0, help="单次数据抓取超时秒数")
    parser.add_argument("--retries", type=int, default=1, help="单接口抓取重试次数")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    stock_df = read_stock_list(input_path)
    records = []
    total = len(stock_df)
    spot_map: Dict[str, Dict[str, Any]] = {}

    spot_result = call_with_retry(
        ak.stock_zh_a_spot_em,
        retries=max(args.retries, 1),
        pause=max(args.pause, 0.2),
        timeout_sec=max(args.timeout * 40, 180.0),
    )
    if spot_result.error:
        print(f"[WARN] 全市场实时快照抓取失败: {spot_result.error}", flush=True)
    else:
        spot_map = build_spot_snapshot_map(spot_result.data)
        print(f"[INFO] 已加载实时快照 {len(spot_map)} 条", flush=True)

    for idx, (_, row) in enumerate(stock_df.iterrows(), start=1):
        print(f"[{idx}/{total}] 开始处理 {row['股票代码']} {row['股票名称']}", flush=True)
        try:
            records.append(
                fetch_one(
                    row,
                    pause=args.pause,
                    timeout_sec=args.timeout,
                    retries=args.retries,
                    spot_map=spot_map,
                )
            )
        except Exception as exc:  # noqa: BLE001
            records.append(
                {
                    "股票代码": zfill_code(row["股票代码"]),
                    "股票名称": row.get("股票名称", ""),
                    "行业": row.get("行业"),
                    "细分赛道": row.get("细分赛道"),
                    "标签": row.get("标签"),
                    "fatal_error": repr(exc),
                }
            )
            print(f"[ERROR] {row['股票代码']} {row['股票名称']} {exc}", flush=True)

    result_df = pd.DataFrame(records)
    output_columns = [col for col in stock_df.columns if col != "原始顺序"]
    if not output_columns:
        output_columns = DEFAULT_OUTPUT_COLUMNS.copy()
    scored_df = build_scores(result_df, output_columns=output_columns)

    date_tag = args.as_of.replace("-", "")
    csv_path = output_dir / f"stock_list_scored_{date_tag}.csv"
    xlsx_path = output_dir / f"stock_list_scored_{date_tag}.xlsx"
    json_path = output_dir / f"stock_list_scored_{date_tag}.json"
    md_path = output_dir / f"stock_list_scoring_report_{date_tag}.md"

    delivery_df = build_delivery_sheet(scored_df, output_columns=output_columns)

    delivery_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    try:
        delivery_df.to_excel(xlsx_path, index=False)
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] XLSX 导出失败: {exc}", flush=True)
    scored_df.to_json(json_path, orient="records", force_ascii=False, indent=2)

    report = build_report(scored_df, args.as_of)
    md_path.write_text(report, encoding="utf-8")

    print(f"[DONE] CSV: {csv_path}", flush=True)
    if xlsx_path.exists():
        print(f"[DONE] XLSX: {xlsx_path}", flush=True)
    print(f"[DONE] JSON: {json_path}", flush=True)
    print(f"[DONE] MD: {md_path}", flush=True)


if __name__ == "__main__":
    main()
