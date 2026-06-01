"""板块数据访问层。

行业 & 概念板块数据，优先从 MySQL 读取，查不到则从 akshare（同花顺）获取并落库。
板块成分股映射可从 SDK 接口同步到 board_stock_map。

使用示例:
    from lib.board import get_industries, get_concepts

    df_ind = get_industries()       # {code, name}
    df_conc = get_concepts()       # {code, name}
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple
import warnings

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
TABLE_BOARD_STOCK_MAP = "board_stock_map"


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


class _BoardStockMapDB:
    """板块-个股映射表的数据库操作。"""

    def __init__(self):
        self._conn: pymysql.connections.Connection | None = None

    @property
    def conn(self):
        """惰性连接。"""
        if self._conn is None or not self._conn.open:
            self._conn = _connect()
        return self._conn

    def replace_type(self, board_type: str, records: List[Tuple[str, str | None, str, str, str | None, str]]) -> int:
        """替换某个板块类型的全部映射。"""
        with self.conn.cursor() as cur:
            cur.execute(f"DELETE FROM {TABLE_BOARD_STOCK_MAP} WHERE board_type = %s", (board_type,))
            if records:
                cur.executemany(
                    f"""
                    INSERT INTO {TABLE_BOARD_STOCK_MAP}
                        (board_type, board_code, board_name, stock_code, stock_name, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        board_code = VALUES(board_code),
                        stock_name = VALUES(stock_name),
                        source = VALUES(source)
                    """,
                    records,
                )
        self.conn.commit()
        return len(records)

    def count(self, board_type: str | None = None) -> int:
        """返回映射记录数。"""
        if board_type:
            sql = f"SELECT COUNT(*) AS cnt FROM {TABLE_BOARD_STOCK_MAP} WHERE board_type = %s"
            params = (board_type,)
        else:
            sql = f"SELECT COUNT(*) AS cnt FROM {TABLE_BOARD_STOCK_MAP}"
            params = ()
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        return row["cnt"] if row else 0

    def close(self):
        if self._conn and self._conn.open:
            self._conn.close()


# ── 模块级缓存（避免同一次进程多个调用反复连 DB） ──────────

_industry_db: _BoardDB | None = None
_concept_db: _BoardDB | None = None
_board_stock_map_db: _BoardStockMapDB | None = None


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


def _get_board_stock_map_db() -> _BoardStockMapDB:
    global _board_stock_map_db
    if _board_stock_map_db is None:
        _board_stock_map_db = _BoardStockMapDB()
    return _board_stock_map_db


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


def sync_industry_members_from_akshare(limit: int | None = None) -> pd.DataFrame:
    """从 akshare 东方财富行业成分接口同步行业-个股映射。"""
    import akshare as ak

    boards = ak.stock_board_industry_name_em()
    records = []
    frames = []
    selected_boards = boards.head(limit) if limit else boards
    for _, board in selected_boards.iterrows():
        board_name = str(board["板块名称"])
        board_code = str(board["板块代码"])
        try:
            members = ak.stock_board_industry_cons_em(symbol=board_name)
        except Exception as exc:
            warnings.warn(f"行业成分获取失败: {board_name}({board_code}): {exc}")
            continue
        rows = _members_to_records(
            members,
            board_type="industry",
            board_code=board_code,
            board_name=board_name,
            source="akshare_em",
        )
        records.extend(rows)
        frames.append(_records_to_frame(rows))
    _get_board_stock_map_db().replace_type("industry", records)
    return pd.concat(frames, ignore_index=True) if frames else _empty_member_frame()


def sync_concept_members_from_akshare(limit: int | None = None) -> pd.DataFrame:
    """从 akshare 东方财富概念成分接口同步概念-个股映射。"""
    import akshare as ak

    boards = ak.stock_board_concept_name_em()
    records = []
    frames = []
    selected_boards = boards.head(limit) if limit else boards
    for _, board in selected_boards.iterrows():
        board_name = str(board["板块名称"])
        board_code = str(board["板块代码"])
        try:
            members = ak.stock_board_concept_cons_em(symbol=board_name)
        except Exception as exc:
            warnings.warn(f"概念成分获取失败: {board_name}({board_code}): {exc}")
            continue
        rows = _members_to_records(
            members,
            board_type="concept",
            board_code=board_code,
            board_name=board_name,
            source="akshare_em",
        )
        records.extend(rows)
        frames.append(_records_to_frame(rows))
    _get_board_stock_map_db().replace_type("concept", records)
    return pd.concat(frames, ignore_index=True) if frames else _empty_member_frame()


def sync_concept_members_from_mootdx() -> pd.DataFrame:
    """从 mootdx 通达信概念板块文件同步概念-个股映射。"""
    from mootdx.quotes import Quotes

    client = Quotes.factory(market="std", timeout=8)
    df = client.block("block_gn.dat")
    records = [
        ("concept", None, str(row["blockname"]), str(row["code"]).zfill(6), None, "mootdx")
        for _, row in df.iterrows()
        if str(row.get("code", "")).strip()
    ]
    _get_board_stock_map_db().replace_type("concept", records)
    return _records_to_frame(records)


def _members_to_records(
    members: pd.DataFrame,
    board_type: str,
    board_code: str | None,
    board_name: str,
    source: str,
) -> List[Tuple[str, str | None, str, str, str | None, str]]:
    """把不同 SDK 的成分股 DataFrame 规范化为入库记录。"""
    code_col = _first_existing_column(members, ["代码", "code", "股票代码", "证券代码"])
    name_col = _first_existing_column(members, ["名称", "name", "股票名称", "证券简称"])
    if not code_col:
        raise ValueError(f"成分股数据缺少股票代码列: {members.columns.tolist()}")

    records = []
    for _, row in members.iterrows():
        stock_code = str(row[code_col]).strip().zfill(6)
        if not stock_code:
            continue
        stock_name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else None
        records.append((board_type, board_code, board_name, stock_code, stock_name, source))
    return records


def _first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _records_to_frame(records: List[Tuple[str, str | None, str, str, str | None, str]]) -> pd.DataFrame:
    if not records:
        return _empty_member_frame()
    return pd.DataFrame(
        records,
        columns=["board_type", "board_code", "board_name", "stock_code", "stock_name", "source"],
    )


def _empty_member_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["board_type", "board_code", "board_name", "stock_code", "stock_name", "source"])


def _fetch_and_sync_industries() -> pd.DataFrame:
    return sync_industries_from_akshare()


def _fetch_and_sync_concepts() -> pd.DataFrame:
    return sync_concepts_from_akshare()
