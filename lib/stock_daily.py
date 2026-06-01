"""
日行情数据统一访问层（lib 核心模块）。

使用策略：优先读 DB，数据不足时自动从 mootdx 补全并落库。

用法：
    from lib import DailyMarket

    dm = DailyMarket()

    # ── 与 mootdx.bars() 完全一致的接口 ──
    df = dm.bars(symbol="601869", frequency=9, start=0, offset=800)

    # ── 按年获取（更方便） ──
    df = dm.bars_years("601869", years=2)

    # ── 指定日期范围 ──
    from datetime import date
    df = dm.get_stock("601869", date(2025, 1, 1), date(2025, 12, 31))
"""

from __future__ import annotations

import warnings
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .config import get_config, get_mootdx_config
from .db import StockDailyDB


class DailyMarket:
    """
    日行情数据访问器。

    内部维护 DB 连接和 mootdx 客户端（懒加载），
    支持 with 语句自动释放资源。
    """

    def __init__(self, auto_fill: bool = True):
        """
        参数:
            auto_fill: DB 数据不足时是否自动从 mootdx 补全并写入 DB
                       设为 False 则只读 DB，不会调用 mootdx
        """
        self._auto_fill = auto_fill
        self._db: StockDailyDB | None = None
        self._mootdx_client = None

    # ── 懒加载属性 ─────────────────────────────────────

    @property
    def db(self) -> StockDailyDB:
        """获取 DB 操作实例（懒加载）。"""
        if self._db is None:
            self._db = StockDailyDB()
        return self._db

    @property
    def mootdx(self):
        """获取 mootdx 行情客户端（懒加载），参数从配置文件读取。"""
        if self._mootdx_client is None:
            from mootdx.quotes import Quotes

            cfg = get_mootdx_config()
            self._mootdx_client = Quotes.factory(
                market=cfg.get("market", "std"),
                timeout=cfg.get("timeout", 8),
            )
        return self._mootdx_client

    # ── 公开 API ───────────────────────────────────────

    def bars(
        self,
        symbol: str = "000001",
        frequency: int = 9,
        start: int = 0,
        offset: int = 800,
        **kwargs,
    ) -> pd.DataFrame:
        """
        获取日 K 线数据。

        参数与 mootdx.Quotes.bars() 完全一致，方便无缝替换：
            symbol:     股票代码，如 "601869"
            frequency:  频次，传 9（日线），暂不支持其他频次
            start:      开始偏移，0 = 从最新数据开始
            offset:     获取条数，上限 800
            **kwargs:   透传给 mootdx（如 adjust 等）

        返回:
            pd.DataFrame，index = trade_date，包含以下列：
            stock_code, trade_date, open_price, high_price, low_price,
            close_price, volume, amount, pre_close, chg_amt, chg_pct

        数据来源策略：
            1. 优先从 MySQL 读取已有数据
            2. 如果 DB 记录数不足 offset，自动从 mootdx 拉取并写入 DB
            3. 如果 auto_fill=False，只读 DB，不调用 mootdx
        """
        # 仅支持日线
        eff_offset = min(offset, 800)

        # ── 1. 优先查 DB ──
        db_df = self.db.query_latest(symbol, limit=eff_offset)

        # ── 2. DB 数据不足时补 mootdx ──
        if self._auto_fill and len(db_df) < eff_offset:
            updated = self._fetch_and_store(symbol, frequency, start, eff_offset, kwargs)
            if updated:
                # 重新从 DB 获取最新数据
                db_df = self.db.query_latest(symbol, limit=eff_offset)

        return db_df

    def bars_years(self, symbol: str, years: int = 2) -> pd.DataFrame:
        """
        获取某股票最近 N 年的日线数据。

        参数:
            symbol: 股票代码
            years:  年数，默认 2 年

        返回:
            与 bars() 相同的 DataFrame 格式

        示例:
            dm = DailyMarket()
            df = dm.bars_years("601869", years=3)
        """
        cutoff = date.today() - timedelta(days=int(years * 365.25))

        # 先查 DB 覆盖范围
        db_range = self.db.get_date_range(symbol)

        # 如果 DB 已有完整覆盖，直接返回 DB 查询结果
        if db_range[0] is not None and db_range[0] <= cutoff:
            return self.db.query_range(symbol, cutoff, date.today())

        # DB 数据不足，用 bars() 获取（自动补 mootdx）
        # 约 250 交易日/年，加 20 天缓冲
        days_needed = min(int(years * 250 + 20), 800)
        df = self.bars(symbol=symbol, frequency=9, start=0, offset=days_needed)

        # 按 years 过滤后返回
        result = df[df.index.date >= cutoff] if not df.empty else df
        return result

    def get_stock(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        获取某股票指定日期区间内的日行情。

        参数:
            symbol:     股票代码
            start_date: 开始日期
            end_date:   结束日期

        返回:
            包含该日期区间完整数据的 DataFrame
        """
        years_span = (end_date - start_date).days / 365.25 + 0.5
        # 确保至少请求 1 年数据，避免 years=0 时 cutoff=今天查不到数据
        df = self.bars_years(symbol, years=max(1, int(years_span)))
        if df.empty:
            return df
        return df[(df.index.date >= start_date) & (df.index.date <= end_date)]

    # ── 内部方法 ───────────────────────────────────────

    def _fetch_and_store(
        self,
        symbol: str,
        frequency: int,
        start: int,
        offset: int,
        mootdx_kwargs: dict,
    ) -> bool:
        """从 mootdx 获取数据并写入 DB，返回是否成功写入。"""
        try:
            df = self.mootdx.bars(
                symbol=symbol,
                frequency=frequency,
                start=start,
                offset=offset,
                **mootdx_kwargs,
            )
        except Exception as e:
            warnings.warn(f"[lib] mootdx {symbol} 获取失败: {e}")
            return False

        if df is None or df.empty:
            return False

        # 计算衍生字段（涨跌额 / 涨跌幅）
        df = df.sort_index()
        df["pre_close"] = df["close"].shift(1)
        df["chg_amt"] = df["close"] - df["pre_close"]
        df["chg_pct"] = (df["chg_amt"] / df["pre_close"] * 100).round(4)

        # 转换为 DB 记录并写入
        records = self._df_to_records(symbol, df)
        if records:
            try:
                self.db.upsert(records)
            except Exception as e:
                warnings.warn(f"[lib] {symbol} 写入 DB 失败: {e}")
                return False
        return True

    # ── 工具方法 ───────────────────────────────────────

    @staticmethod
    def _df_to_records(code: str, df: pd.DataFrame) -> List[tuple]:
        """
        将 mootdx 返回的 DataFrame 转换为 DB upsert 的记录列表。

        记录格式: (stock_code, trade_date, open_price,
                    high_price, low_price, close_price, volume, amount,
                    pre_close, chg_amt, chg_pct)
        """
        vol_col = "volume" if "volume" in df.columns else "vol"
        records: List[tuple] = []

        for ts, row in df.iterrows():
            records.append(
                (
                    code,
                    ts.date(),
                    round(float(row["open"]), 2),
                    round(float(row["high"]), 2),
                    round(float(row["low"]), 2),
                    round(float(row["close"]), 2),
                    int(row[vol_col]),
                    round(float(row["amount"]), 2),
                    (
                        round(float(row["pre_close"]), 2)
                        if pd.notna(row.get("pre_close"))
                        else None
                    ),
                    (
                        round(float(row["chg_amt"]), 2)
                        if pd.notna(row.get("chg_amt"))
                        else None
                    ),
                    (
                        round(float(row["chg_pct"]), 4)
                        if pd.notna(row.get("chg_pct"))
                        else None
                    ),
                )
            )
        return records

    # ── 资源管理 ───────────────────────────────────────

    def close(self):
        """释放数据库连接。"""
        if self._db is not None:
            self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

