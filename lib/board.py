"""板块数据访问层。

行业 & 概念板块数据，优先从 MySQL 读取，查不到则从 akshare（同花顺）获取并落库。

使用示例:
    from lib.board import get_industries, get_concepts

    df_ind = get_industries()       # {code, name}
    df_conc = get_concepts()       # {code, name}
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pandas as pd
import pymysql

from .config import get_database_config


# ── 连接 ──────────────────────────────────────────────────

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


# ── 常量 ──────────────────────────────────────────────────

TABLE_INDUSTRY = "board_industry"
TABLE_CONCEPT = "board_concept"


# ── 内部存取封装 ──────────────────────────────────────────

class _BoardDB:
    """板块表的数据库操作。"""

    def __init__(self, table: str):
        self._table = table
        self._conn: pymysql.connections.Connection | None = None

    @property
    def conn(self):
        """惰性连接。"""
        if self._conn is None or not self._conn.open:
            self._conn = _connect()
        return self._conn

    # ── 查询 ──────────────────────────────────────────────

    def get_all(self) -> pd.DataFrame:
        """返回全部板块记录（code, name）。"""
        sql = f"SELECT code, name FROM {self._table} ORDER BY code"
        with self.conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        if not rows:
            return pd.DataFrame(columns=["code", "name"])
        return pd.DataFrame(rows)

    def get_by_code(self, code: str) -> Optional[dict]:
        """按代码查单条板块。"""
        sql = f"SELECT code, name FROM {self._table} WHERE code = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (code,))
            return cur.fetchone()

    def get_by_name(self, name: str) -> Optional[dict]:
        """按名称查单条板块。"""
        sql = f"SELECT code, name FROM {self._table} WHERE name = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (name,))
            return cur.fetchone()

    def count(self) -> int:
        """返回表内记录数。"""
        sql = f"SELECT COUNT(*) AS cnt FROM {self._table}"
        with self.conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
        return row["cnt"] if row else 0

    # ── 写入 ──────────────────────────────────────────────

    def upsert_all(self, records: List[Tuple[str, str]]) -> int:
        """批量 upsert 板块记录。已存在同 code 则更新 name。"""
        if not records:
            return 0
        sql = f"""
            INSERT INTO {self._table} (code, name)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE name = VALUES(name)
        """
        with self.conn.cursor() as cur:
            cur.executemany(sql, records)
        self.conn.commit()
        return len(records)

    def close(self):
        if self._conn and self._conn.open:
            self._conn.close()


# ── 模块级缓存（避免同一次进程多个调用反复连 DB） ──────────

_industry_db: _BoardDB | None = None
_concept_db: _BoardDB | None = None


def _get_industry_db() -> _BoardDB:
    global _industry_db
    if _industry_db is None:
        _industry_db = _BoardDB(TABLE_INDUSTRY)
    return _industry_db


def _get_concept_db() -> _BoardDB:
    global _concept_db
    if _concept_db is None:
        _concept_db = _BoardDB(TABLE_CONCEPT)
    return _concept_db


# ── 公开接口 ──────────────────────────────────────────────

def get_industries() -> pd.DataFrame:
    """获取全部行业板块（优先 DB，空则走 akshare 并落库）。"""
    db = _get_industry_db()
    if db.count() > 0:
        return db.get_all()
    return _fetch_and_sync_industries()


def get_concepts() -> pd.DataFrame:
    """获取全部概念板块（优先 DB，空则走 akshare 并落库）。"""
    db = _get_concept_db()
    if db.count() > 0:
        return db.get_all()
    return _fetch_and_sync_concepts()


def get_industry_by_code(code: str) -> Optional[dict]:
    """按代码查行业板块（仅 DB）。"""
    return _get_industry_db().get_by_code(code)


def get_concept_by_code(code: str) -> Optional[dict]:
    """按代码查概念板块（仅 DB）。"""
    return _get_concept_db().get_by_code(code)


def get_industry_by_name(name: str) -> Optional[dict]:
    """按名称查行业板块（仅 DB）。"""
    return _get_industry_db().get_by_name(name)


def get_concept_by_name(name: str) -> Optional[dict]:
    """按名称查概念板块（仅 DB）。"""
    return _get_concept_db().get_by_name(name)


# ── 同步函数（供 ETL 脚本 / get_xxx 回退使用） ─────────────

def sync_industries_from_akshare() -> pd.DataFrame:
    """从 akshare 拉取行业板块全量并 upsert 到 DB。"""
    import akshare as ak
    df = ak.stock_board_industry_name_ths()
    db = _get_industry_db()
    records = [(str(r["code"]), str(r["name"])) for _, r in df.iterrows()]
    db.upsert_all(records)
    return df


def sync_concepts_from_akshare() -> pd.DataFrame:
    """从 akshare 拉取概念板块全量并 upsert 到 DB。"""
    import akshare as ak
    df = ak.stock_board_concept_name_ths()
    db = _get_concept_db()
    records = [(str(r["code"]), str(r["name"])) for _, r in df.iterrows()]
    db.upsert_all(records)
    return df


def _fetch_and_sync_industries() -> pd.DataFrame:
    return sync_industries_from_akshare()


def _fetch_and_sync_concepts() -> pd.DataFrame:
    return sync_concepts_from_akshare()
