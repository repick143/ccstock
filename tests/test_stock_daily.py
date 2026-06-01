""" lib.stock_daily DailyMarket unit tests. 
 All external deps are mocked. 
"""

from __future__ import annotations
from datetime import date
import pandas as pd
import pytest
from lib.stock_daily import DailyMarket


class TestBars:
    def test_db_has_enough_data(self, mock_db, mock_mootdx, sample_db_rows):
        cursor, conn = mock_db
        cursor.fetchall.return_value = sample_db_rows
        dm = DailyMarket()
        df = dm.bars("601869", frequency=9, start=0, offset=5)
        assert len(df) == 5
        assert not df.empty
        assert "close_price" in df.columns
        mock_mootdx.bars.assert_not_called()

    def test_db_empty_fills_from_mootdx(self, mock_db, mock_mootdx, sample_db_rows, sample_mootdx_df):
        cursor, conn = mock_db
        cursor.fetchall.side_effect = [[], sample_db_rows]
        mock_mootdx.bars.return_value = sample_mootdx_df
        dm = DailyMarket()
        df = dm.bars("601869", frequency=9, start=0, offset=5)
        assert len(df) == 5
        mock_mootdx.bars.assert_called_once()
        assert cursor.executemany.called

    def test_auto_fill_false(self, mock_db, mock_mootdx):
        cursor, conn = mock_db
        cursor.fetchall.return_value = []
        dm = DailyMarket(auto_fill=False)
        df = dm.bars("601869", frequency=9, start=0, offset=5)
        assert df.empty
        mock_mootdx.bars.assert_not_called()

    def test_mootdx_fails_gracefully(self, mock_db, mock_mootdx):
        cursor, conn = mock_db
        cursor.fetchall.return_value = []
        mock_mootdx.bars.side_effect = ConnectionError("mootdx unreachable")
        dm = DailyMarket()
        df = dm.bars("601869", frequency=9, start=0, offset=5)
        assert df.empty
        mock_mootdx.bars.assert_called_once()

    def test_upsert_called_with_computed_fields(self, mock_db, mock_mootdx, sample_mootdx_df):
        cursor, conn = mock_db
        cursor.fetchall.side_effect = [[], self._sample_rows()]
        mock_mootdx.bars.return_value = sample_mootdx_df
        dm = DailyMarket()
        dm.bars("601869", frequency=9, start=0, offset=5)
        if cursor.executemany.called:
            records = cursor.executemany.call_args[0][1]
            for rec in records:
                code, dt, op, hp, lp, cp, vol, amt, pc, ca, cpct = rec
                if pc is not None:
                    assert ca is not None
                    assert cpct is not None

    @staticmethod
    def _sample_rows():
        from tests.conftest import make_db_row
        return [make_db_row(trade_date=date(2026, 5, 29), close_p=402.81, pre_close=370.55)]


class TestBarsYears:
    def test_db_covers_range(self, mock_db, mock_mootdx, sample_db_rows):
        cursor, conn = mock_db
        cursor.fetchone.return_value = {"earliest": date(2024, 5, 31), "latest": date(2026, 5, 29)}
        cursor.fetchall.return_value = sample_db_rows
        dm = DailyMarket()
        df = dm.bars_years("601869", years=1)
        assert len(df) == 5
        mock_mootdx.bars.assert_not_called()

    def test_db_insufficient(self, mock_db, mock_mootdx, sample_mootdx_df, sample_db_rows):
        cursor, conn = mock_db
        cursor.fetchone.return_value = {"earliest": None, "latest": None}
        cursor.fetchall.side_effect = [[], sample_db_rows]
        mock_mootdx.bars.return_value = sample_mootdx_df
        dm = DailyMarket()
        df = dm.bars_years("601869", years=1)
        assert not df.empty
        assert mock_mootdx.bars.called


class TestGetStock:
    def test_returns_correct_range(self, mock_db, mock_mootdx, sample_db_rows):
        cursor, conn = mock_db
        cursor.fetchone.return_value = {"earliest": date(2024, 5, 31), "latest": date(2026, 5, 29)}
        cursor.fetchall.return_value = sample_db_rows
        dm = DailyMarket()
        df = dm.get_stock("601869", date(2026, 5, 25), date(2026, 5, 29))
        assert not df.empty

    def test_small_range_does_not_bug(self, mock_db, mock_mootdx, sample_db_rows):
        cursor, conn = mock_db
        cursor.fetchone.return_value = {"earliest": date(2024, 5, 31), "latest": date(2026, 5, 29)}
        cursor.fetchall.return_value = sample_db_rows
        dm = DailyMarket()
        df = dm.get_stock("601869", date(2026, 5, 25), date(2026, 5, 29))
        assert not df.empty


class TestDfToRecords:
    def test_converts_mootdx_df(self, sample_mootdx_df):
        records = DailyMarket._df_to_records("601869", sample_mootdx_df)
        assert len(records) == 5
        rec = records[0]
        assert rec[0] == "601869"
        assert isinstance(rec[1], date)
        assert rec[2] == 369.97
        assert rec[5] == 402.81

    def test_handles_nan_in_derived_fields(self, sample_mootdx_df):
        df = sample_mootdx_df.sort_index()
        df["pre_close"] = df["close"].shift(1)
        df["chg_amt"] = df["close"] - df["pre_close"]
        df["chg_pct"] = (df["chg_amt"] / df["pre_close"] * 100).round(4)
        records = DailyMarket._df_to_records("601869", df)
        assert records[0][8] is None
        assert records[1][8] is not None
        assert records[1][9] is not None
        assert records[1][10] is not None


class TestContextManager:
    def test_with_statement(self, mock_db, mock_mootdx, sample_db_rows):
        cursor, conn = mock_db
        cursor.fetchall.return_value = sample_db_rows
        with DailyMarket() as dm:
            df = dm.bars("601869", offset=3)
            assert len(df) == 5
        assert conn.close.called


class TestAutoFillBehavior:
    def test_no_unnecessary_mootdx_calls(self, mock_db, mock_mootdx):
        cursor, conn = mock_db
        cursor.fetchall.return_value = []
        df = pd.DataFrame({
            "open": [400.0], "close": [405.0], "high": [410.0], "low": [399.0],
            "vol": [100000], "amount": [4000000000.0],
            "volume": [100000], "year": [2026], "month": [5], "day": [30],
            "hour": [0], "minute": [0],
            "datetime": pd.to_datetime(["2026-05-30"]),
        })
        df.index = df["datetime"]
        df.index.name = "datetime"
        mock_mootdx.bars.return_value = df
        dm = DailyMarket()
        dm.bars("601869", offset=1)
        first_call_count = mock_mootdx.bars.call_count
        cursor.fetchall.return_value = [{
            "trade_date": date(2026, 5, 30),
            "open_price": 400.0, "high_price": 410.0, "low_price": 399.0,
            "close_price": 405.0, "volume": 100000, "amount": 4000000000.0,
            "pre_close": 402.81, "chg_amt": 2.19, "chg_pct": 0.5431,
        }]
        dm.bars("601869", offset=1)
        assert mock_mootdx.bars.call_count == first_call_count
