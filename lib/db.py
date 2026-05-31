"""MySQL 数据库操作模块。

封装 stock_daily 表的完整 CRUD，所有查询返回 pandas DataFrame。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional, Tuple

import pandas as pd
import pymysql

from .config import get_database_config


def _connect():
    """按配置文件创建 MySQL 连接。"""
    cfg = get_database_config()
    return pymysql.connect(
        host=cfg.get("host", "127.0.0.1"),
        port=cfg.get("port", 3306),
        user=cfg.get("user", "root"),
        password=cfg.get("password", ""),
        database=cfg.get("database", "ccstock"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


# ── 查询结果行 → DataFrame 的公共转换 ─────────────────


def _rows_to_df(rows: List[dict], use_index: str = "trade_date") -> pd.DataFrame:
    """将 DictCursor 查询结果转为 DataFrame，trade_date 设为索引。"""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if use_index and use_index in df.columns:
        df[use_index] = pd.to_datetime(df[use_index])
        df = df.set_index(use_index)
    return df.sort_index()


# ── 常量 ──────────────────────────────────────────────

TABLE = "stock_daily"

# 所有入库字段（不含 id / created_at / updated_at）
COLUMNS = [
    "stock_code", "stock_name", "trade_date",
    "open_price", "high_price", "low_price", "close_price",
    "volume", "amount",
    "pre_close", "chg_amt", "chg_pct",
]

# ON DUPLICATE KEY UPDATE 时会更新的字段（不含唯一键）
UPDATE_COLS = [c for c in COLUMNS if c not in ("stock_code", "trade_date")]


# ── DB 操作类 ─────────────────────────────────────────


class StockDailyDB:
    """stock_daily 表的数据库操作封装。使用 with 语句自动释放连接。"""

    def __init__(self):
        self._conn = _connect()

    def close(self):
        """显式关闭连接。"""
        if self._conn and self._conn.open:
            self._conn.close()

    # ── 查询 ──────────────────────────────────────────

    def query_latest(self, code: str, limit: int = 800) -> pd.DataFrame:
        """
        获取某股票最近 N 条日行情（按 trade_date 倒序取 limit 条）。

        参数:
            code:  股票代码
            limit: 最多返回条数

        返回:
            DataFrame，index=trade_date
        """
        sql = f"""
            SELECT {", ".join(COLUMNS)}
            FROM {TABLE}
            WHERE stock_code = %s
            ORDER BY trade_date DESC
            LIMIT %s
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, (code, limit))
            rows = cur.fetchall()
        return _rows_to_df(rows)

    def query_range(self, code: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        获取某股票在指定日期区间内的日行情（闭区间）。

        参数:
            code:       股票代码
            start_date: 开始日期
            end_date:   结束日期

        返回:
            DataFrame，按 trade_date 正序排列
        """
        sql = f"""
            SELECT {", ".join(COLUMNS)}
            FROM {TABLE}
            WHERE stock_code = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, (code, start_date, end_date))
            rows = cur.fetchall()
        return _rows_to_df(rows)

    def count_range(self, code: str, start_date: date, end_date: date) -> int:
        """统计某股票在指定日期区间内的记录数。"""
        sql = f"SELECT COUNT(*) AS cnt FROM {TABLE} WHERE stock_code = %s AND trade_date BETWEEN %s AND %s"
        with self._conn.cursor() as cur:
            cur.execute(sql, (code, start_date, end_date))
            row = cur.fetchone()
        return row["cnt"] if row else 0

    def get_date_range(self, code: str) -> Tuple[Optional[date], Optional[date]]:
        """
        获取某股票在 DB 中的最早和最晚交易日。

        返回:
            (earliest, latest) 或 (None, None) 表示无数据
        """
        sql = f"SELECT MIN(trade_date) AS earliest, MAX(trade_date) AS latest FROM {TABLE} WHERE stock_code = %s"
        with self._conn.cursor() as cur:
            cur.execute(sql, (code,))
            row = cur.fetchone()
        if row and row["earliest"]:
            return (row["earliest"], row["latest"])
        return (None, None)

    # ── 写入 ──────────────────────────────────────────

    def upsert(self, records: List[tuple]) -> int:
        """
        批量 upsert 日行情记录。

        已存在的 (stock_code, trade_date) 记录会更新价格字段，
        不存在的则插入。

        参数:
            records: [(code, name, date, open, high, low, close, vol, amt, pre_close, chg_amt, chg_pct), ...]

        返回:
            受影响的记录数
        """
        if not records:
            return 0

        placeholders = ", ".join(["%s"] * len(records[0]))
        cols = ", ".join(COLUMNS)
        updates = ", ".join(f"{c} = VALUES({c})" for c in UPDATE_COLS)

        sql = f"""
            INSERT INTO {TABLE} ({cols})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {updates}
        """
        with self._conn.cursor() as cur:
            cur.executemany(sql, records)
        self._conn.commit()
        return len(records)

    # ── 上下文管理 ────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
