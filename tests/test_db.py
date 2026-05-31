"""lib.db 数据库操作模块单测。

所有数据库操作通过 mock_db fixture 模拟，不依赖真实 MySQL。
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from lib.db import StockDailyDB, _rows_to_df, COLUMNS


class TestRowsToDf:
    """_rows_to_df() 工具函数测试。"""

    def test_empty_rows(self):
        df = _rows_to_df([])
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_single_row(self, sample_db_rows):
        df = _rows_to_df(sample_db_rows[:1])
        assert len(df) == 1
        assert df.index.name == "trade_date"
        assert df.index[0] == pd.Timestamp("2026-05-29")
        assert df["close_price"].iloc[0] == 402.81

    def test_multiple_rows(self, sample_db_rows):
        df = _rows_to_df(sample_db_rows)
        assert len(df) == 5
        # trade_date 应成为索引，并按日期正序排列
        assert df.index[0] == pd.Timestamp("2026-05-25")
        assert df.index[-1] == pd.Timestamp("2026-05-29")

    def test_columns_match_schema(self, sample_db_rows):
        """返回的 DataFrame 应包含 COLUMNS 中除 trade_date 外的所有字段。"""
        df = _rows_to_df(sample_db_rows)
        expected = {c for c in COLUMNS if c != "trade_date"}
        assert set(df.columns) == expected


class TestStockDailyDB:
    """StockDailyDB CRUD 操作测试。所有 DB 调用通过 mock 拦截。"""

    # ── 查询 ──────────────────────────────────────────

    def test_query_latest(self, mock_db, sample_db_rows):
        cursor, conn = mock_db
        cursor.fetchall.return_value = sample_db_rows

        db = StockDailyDB()
        df = db.query_latest("601869", limit=5)

        assert len(df) == 5
        # 验证 SQL 参数
        sql = cursor.execute.call_args[0][0]
        assert "stock_code = %s" in sql
        assert "ORDER BY trade_date DESC" in sql
        assert "LIMIT %s" in sql

    def test_query_latest_empty(self, mock_db):
        cursor, conn = mock_db
        cursor.fetchall.return_value = []

        db = StockDailyDB()
        df = db.query_latest("601869", limit=5)
        assert df.empty

    def test_query_range(self, mock_db, sample_db_rows):
        cursor, conn = mock_db
        cursor.fetchall.return_value = sample_db_rows

        db = StockDailyDB()
        df = db.query_range("601869", date(2026, 5, 25), date(2026, 5, 29))
        assert len(df) == 5

        # 验证 SQL 带 BETWEEN
        sql, params = cursor.execute.call_args[0]
        assert "BETWEEN" in sql
        assert params[1] == date(2026, 5, 25)
        assert params[2] == date(2026, 5, 29)

    def test_count_range(self, mock_db):
        cursor, conn = mock_db
        cursor.fetchone.return_value = {"cnt": 42}

        db = StockDailyDB()
        cnt = db.count_range("601869", date(2026, 1, 1), date(2026, 12, 31))
        assert cnt == 42

    def test_get_date_range_found(self, mock_db):
        cursor, conn = mock_db
        cursor.fetchone.return_value = {"earliest": date(2024, 5, 31), "latest": date(2026, 5, 29)}

        db = StockDailyDB()
        earliest, latest = db.get_date_range("601869")
        assert earliest == date(2024, 5, 31)
        assert latest == date(2026, 5, 29)

    def test_get_date_range_empty(self, mock_db):
        cursor, conn = mock_db
        cursor.fetchone.return_value = {"earliest": None, "latest": None}

        db = StockDailyDB()
        earliest, latest = db.get_date_range("601869")
        assert earliest is None
        assert latest is None

    # ── 写入 ──────────────────────────────────────────

    def test_upsert_batch(self, mock_db):
        cursor, conn = mock_db

        db = StockDailyDB()
        records = [
            ("601869", None, date(2026, 5, 29), 369.97, 407.0, 365.0, 402.81, 253336, 9891328000.0, 370.55, 32.26, 8.706),
            ("601869", None, date(2026, 5, 28), 360.66, 373.0, 351.37, 370.55, 116443, 4228195072.0, 366.10, 4.45, 1.2155),
        ]
        n = db.upsert(records)
        assert n == 2
        assert cursor.executemany.called

    def test_upsert_empty(self, mock_db):
        cursor, conn = mock_db

        db = StockDailyDB()
        n = db.upsert([])
        assert n == 0
        assert not cursor.executemany.called

    def test_upsert_sql_has_on_duplicate(self, mock_db, sample_db_rows):
        """upsert 应生成 ON DUPLICATE KEY UPDATE 语句。"""
        cursor, conn = mock_db

        db = StockDailyDB()
        records = [
            ("601869", None, date(2026, 5, 29), 369.97, 407.0, 365.0, 402.81, 253336, 9891328000.0, 370.55, 32.26, 8.706),
        ]
        db.upsert(records)

        sql = cursor.executemany.call_args[0][0]
        assert "ON DUPLICATE KEY UPDATE" in sql
        assert "pre_close = VALUES(pre_close)" in sql
        assert "chg_amt = VALUES(chg_amt)" in sql

    # ── 资源管理 ──────────────────────────────────────

    def test_context_manager(self, mock_db):
        cursor, conn = mock_db
        with StockDailyDB() as db:
            db.query_latest("601869", limit=1)
        assert conn.close.called

    def test_close_idempotent(self, mock_db):
        cursor, conn = mock_db
        db = StockDailyDB()
        db.close()
        db.close()  # 第二次 close 不应抛异常
        assert conn.close.call_count == 1

