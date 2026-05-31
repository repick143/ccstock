"""测试共享夹具（fixtures）。

所有 mock 都在 conftest 中集中定义，
各测试文件按需使用。
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ── 全局配置缓存清理 ───────────────────────────────────


@pytest.fixture(autouse=True)
def reset_config_cache():
    """每个测试前重置 lib.config 的全局缓存，避免跨用例污染。"""
    import lib.config

    lib.config._config_cache = None
    yield
    lib.config._config_cache = None


# ── 样本数据 ────────────────────────────────────────────


def make_db_row(
    code: str = "601869",
    name: str | None = None,
    trade_date: date = date(2026, 5, 29),
    open_p: float = 369.97,
    high_p: float = 407.0,
    low_p: float = 365.0,
    close_p: float = 402.81,
    vol: int = 253336,
    amt: float = 9891328000.0,
    pre_close: float | None = 370.55,
    chg_amt: float | None = 32.26,
    chg_pct: float | None = 8.7060,
) -> dict:
    """构造一条模拟的 DB 查询结果行（DictCursor 格式）。"""
    return {
        "stock_code": code,
        "stock_name": name,
        "trade_date": trade_date,
        "open_price": open_p,
        "high_price": high_p,
        "low_price": low_p,
        "close_price": close_p,
        "volume": vol,
        "amount": amt,
        "pre_close": pre_close,
        "chg_amt": chg_amt,
        "chg_pct": chg_pct,
    }


@pytest.fixture
def sample_db_rows():
    """5 条模拟的 601869 日行情记录（最新 5 个交易日）。"""
    return [
        make_db_row(trade_date=date(2026, 5, 29), close_p=402.81, pre_close=370.55, chg_amt=32.26, chg_pct=8.7060),
        make_db_row(trade_date=date(2026, 5, 28), close_p=370.55, pre_close=366.10, chg_amt=4.45, chg_pct=1.2155),
        make_db_row(trade_date=date(2026, 5, 27), close_p=366.10, pre_close=363.93, chg_amt=2.17, chg_pct=0.5963),
        make_db_row(trade_date=date(2026, 5, 26), close_p=363.93, pre_close=386.03, chg_amt=-22.10, chg_pct=-5.7249),
        make_db_row(trade_date=date(2026, 5, 25), close_p=386.03, pre_close=388.66, chg_amt=-2.63, chg_pct=-0.6767),
    ]


@pytest.fixture
def sample_mootdx_df():
    """模拟 mootdx.bars() 返回的 DataFrame（日线）。"""
    df = pd.DataFrame({
        "open":     [369.97, 360.66, 362.99, 384.00, 388.66],
        "close":    [402.81, 370.55, 366.10, 363.93, 386.03],
        "high":     [407.00, 373.00, 375.00, 384.99, 389.88],
        "low":      [365.00, 351.37, 360.07, 358.48, 378.05],
        "vol":      [253336, 116443, 114706, 149897, 108557],
        "amount":   [9891328000.0, 4228195072.0, 4209160448.0, 5477699072.0, 4154673408.0],
        "year":     [2026] * 5,
        "month":    [5] * 5,
        "day":      [29, 28, 27, 26, 25],
        "hour":     [0] * 5,
        "minute":   [0] * 5,
        "datetime": pd.to_datetime(["2026-05-29", "2026-05-28", "2026-05-27", "2026-05-26", "2026-05-25"]),
        "volume":   [253336, 116443, 114706, 149897, 108557],
    })
    df.index = df["datetime"]
    df.index.name = "datetime"
    return df


# ── Mock 夹具 ──────────────────────────────────────────


@pytest.fixture
def mock_db():
    """Mock lib.db._connect()，返回 (cursor, connection) 元组。

    使用方式：
        def test_xxx(self, mock_db):
            cursor, conn = mock_db
            cursor.fetchall.return_value = [...]
    """
    with patch("lib.db._connect") as mock_connect:
        conn = MagicMock()
        conn.open = True
        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        def _close_side_effect():
            conn.open = False
        conn.close.side_effect = _close_side_effect
        mock_connect.return_value = conn
        yield (cursor, conn)


@pytest.fixture
def mock_mootdx():
    """Mock lib.stock_daily.Quotes.factory，返回 mock client。

    使用方式：
        def test_xxx(self, mock_mootdx):
            mock_mootdx.bars.return_value = sample_mootdx_df()
    """
    with patch("mootdx.quotes.Quotes.factory") as mock_factory:
        client = MagicMock()
        mock_factory.return_value = client
        yield client

