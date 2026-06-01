"""个股基础信息数据访问层。

股票代码+名称批量获取，财务指标逐只获取。DB 优先，缺则走 akshare。

使用示例:
    from lib.stock_info import get_stock_list, get_stock_info

    df = get_stock_list()              # 全市场
    row = get_stock_info("601869")    # 单只完整信息
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional, Tuple

import pandas as pd
import pymysql
import re

from .config import get_database_config


# ── 连接 ──────────────────────────────────────────────────

def _connect():
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


TABLE = "stock_info"

# 所有业务字段（不含 id/created_at/updated_at）
COLUMNS = [
    "stock_code", "stock_name",
    "eps", "bvps", "roe", "net_profit", "revenue",
    "gross_margin", "net_margin", "debt_ratio", "report_period",
]


def _parse_pct(s: str) -> Optional[float]:
    """解析 '15.84%' 格式的百分比字符串为浮点数。"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).replace("%", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_amount(s: str) -> Optional[float]:
    """解析 '4.95亿' 格式的金额字符串为万元。"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if not s:
        return None
    try:
        num_str = re.sub(r"[^\d\.\-]", "", s)
        val = float(num_str)
        if "亿" in s:
            val *= 10000  # 亿 → 万
        elif "万" in s:
            pass  # already 万
        else:
            pass  # 假设已是万
        return val
    except (ValueError, TypeError):
        return None


# ── 内部 DB 封装 ──────────────────────────────────────────

class _StockInfoDB:
    def __init__(self):
        self._conn: pymysql.connections.Connection | None = None

    @property
    def conn(self):
        if self._conn is None or not self._conn.open:
            self._conn = _connect()
        return self._conn

    def count(self) -> int:
        sql = f"SELECT COUNT(*) AS cnt FROM {TABLE}"
        with self.conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()["cnt"]

    def get_all(self) -> pd.DataFrame:
        """返回全部个股基础信息。"""
        sql = f"SELECT {', '.join(COLUMNS)} FROM {TABLE} ORDER BY stock_code"
        with self.conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=COLUMNS)

    def get_by_code(self, code: str) -> Optional[dict]:
        sql = f"SELECT {', '.join(COLUMNS)} FROM {TABLE} WHERE stock_code = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (code,))
            return cur.fetchone()

    def upsert_bulk_codes(self, records: List[Tuple[str, str]]) -> int:
        """批量 upsert 股票代码+名称（Phase 1）。"""
        if not records:
            return 0
        sql = f"""
            INSERT INTO {TABLE} (stock_code, stock_name)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE stock_name = VALUES(stock_name)
        """
        with self.conn.cursor() as cur:
            cur.executemany(sql, records)
        self.conn.commit()
        return len(records)

    def upsert_financial(
        self, code: str, eps: Optional[float], bvps: Optional[float],
        roe: Optional[float], net_profit: Optional[float],
        revenue: Optional[float], gross_margin: Optional[float],
        net_margin: Optional[float], debt_ratio: Optional[float],
        report_period: Optional[date],
    ) -> None:
        """更新单只股票的财务指标（Phase 2）。"""
        sql = f"""
            UPDATE {TABLE}
            SET eps=%s, bvps=%s, roe=%s, net_profit=%s, revenue=%s,
                gross_margin=%s, net_margin=%s, debt_ratio=%s,
                report_period=%s
            WHERE stock_code=%s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (eps, bvps, roe, net_profit, revenue,
                             gross_margin, net_margin, debt_ratio,
                             report_period, code))
        self.conn.commit()

    def close(self):
        if self._conn and self._conn.open:
            self._conn.close()


_db: _StockInfoDB | None = None


def _get_db() -> _StockInfoDB:
    global _db
    if _db is None:
        _db = _StockInfoDB()
    return _db


# ── 公开接口 ──────────────────────────────────────────────

def get_stock_list() -> pd.DataFrame:
    """获取全市场个股基础信息（DB 优先）。"""
    db = _get_db()
    if db.count() > 0:
        return db.get_all()
    # 空则触发同步
    return sync_stock_codes()


def get_stock_info(code: str) -> Optional[dict]:
    """获取单只股票基础信息（仅 DB）。"""
    return _get_db().get_by_code(code)


def stock_count() -> int:
    """数据库中的股票数量。"""
    return _get_db().count()


# ── 同步函数 ──────────────────────────────────────────────

def sync_stock_codes() -> pd.DataFrame:
    """Phase 1: 批量同步全市场股票代码+名称。"""
    import akshare as ak

    print("[sync_codes] 正在获取全市场股票列表...")
    df = ak.stock_info_a_code_name()
    db = _get_db()
    records = [(str(row["code"]).zfill(6), str(row["name"]))
               for _, row in df.iterrows()]
    n = db.upsert_bulk_codes(records)
    print(f"[sync_codes] 已写入 {n} 条记录")
    return df


def sync_stock_financials(codes: Optional[List[str]] = None,
                          limit: Optional[int] = None) -> int:
    """Phase 2: 逐只同步财务指标。

    参数:
        codes: 指定股票代码列表，None 则取全部
        limit: 最大处理数量，None 则不限
    返回:
        成功更新的记录数
    """
    import akshare as ak
    import time
    import warnings
    warnings.filterwarnings("ignore")

    if codes is None:
        codes = get_stock_list()["stock_code"].tolist()
    if limit is not None:
        codes = codes[:limit]

    db = _get_db()
    success = 0
    total = len(codes)

    for i, code in enumerate(codes):
        try:
            df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
            if df.empty:
                continue
            latest = df.iloc[-1]
            db.upsert_financial(
                code=code,
                eps=_parse_amount(latest.get("基本每股收益")),
                bvps=_parse_amount(latest.get("每股净资产")),
                roe=_parse_pct(latest.get("净资产收益率")),
                net_profit=_parse_amount(latest.get("净利润")),
                revenue=_parse_amount(latest.get("营业总收入")),
                gross_margin=_parse_pct(latest.get("销售毛利率")),
                net_margin=_parse_pct(latest.get("销售净利率")),
                debt_ratio=_parse_pct(latest.get("资产负债率")),
                report_period=latest.get("报告期"),
            )
            success += 1
        except Exception as e:
            pass  # skip failures silently

        if (i + 1) % 100 == 0:
            print(f"[sync_financials] {i+1}/{total} ({success} OK)")
        time.sleep(0.3)  # 避免触发限流

    print(f"[sync_financials] 完成: {success}/{total}")
    return success
