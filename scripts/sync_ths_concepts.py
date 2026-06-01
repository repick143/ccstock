#!/usr/bin/env python3
"""Sync concept data from TongHuaShun only.

Writes:
  - board_concept
  - stock_concept_map
  - concept_daily
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import date
from io import StringIO
from pathlib import Path

import akshare as ak
import pandas as pd
import pymysql
import py_mini_racer
import requests
from akshare.datasets import get_ths_js
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.config import get_database_config

SOURCE = "ths"
REQUIRED_DAILY_COLUMNS = ("日期", "开盘价", "最高价", "最低价", "收盘价", "成交量", "成交额")


def connect():
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


def ths_headers(referer: str = "https://q.10jqka.com.cn/gn/") -> dict:
    js_code = py_mini_racer.MiniRacer()
    js_content = Path(get_ths_js("ths.js")).read_text(encoding="utf-8")
    js_code.eval(js_content)
    v_code = js_code.call("v")
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "Cookie": f"v={v_code}",
        "Referer": referer,
    }


def normalize_stock_code(value) -> str | None:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    match = re.search(r"\d{6}", text)
    return match.group(0) if match else None


def reset_schema(conn):
    with conn.cursor() as cur:
        if _column_exists(cur, "stock_concept_map", "source"):
            cur.execute("ALTER TABLE stock_concept_map DROP COLUMN source")
        if not _column_exists(cur, "stock_concept_map", "concept_id"):
            cur.execute(
                "ALTER TABLE stock_concept_map "
                "ADD COLUMN concept_id BIGINT NOT NULL COMMENT '概念主表 ID（board_concept.id）' AFTER stock_code"
            )
        if not _column_exists(cur, "concept_daily", "concept_id"):
            cur.execute(
                "ALTER TABLE concept_daily "
                "ADD COLUMN concept_id BIGINT NOT NULL COMMENT '概念主表 ID（board_concept.id）' AFTER id"
            )
    conn.commit()


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    return cur.fetchone()["cnt"] > 0


def clear_concepts(conn):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM concept_daily")
        cur.execute("DELETE FROM stock_concept_map")
        cur.execute("DELETE FROM board_concept")
    conn.commit()


def fetch_concepts() -> pd.DataFrame:
    df = ak.stock_board_concept_name_ths()
    df["code"] = df["code"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    return df[(df["code"] != "") & (df["name"] != "")].drop_duplicates("code")


def upsert_concepts(conn, concepts: pd.DataFrame):
    rows = [(row.code, row.name, SOURCE, row.code) for row in concepts.itertuples(index=False)]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO board_concept (code, name, source, source_code)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                source = VALUES(source),
                source_code = VALUES(source_code)
            """,
            rows,
        )
    conn.commit()


def get_concept_id(conn, concept_code: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM board_concept WHERE source = %s AND code = %s",
            (SOURCE, concept_code),
        )
        row = cur.fetchone()
    if not row:
        raise RuntimeError(f"concept not found in board_concept: {SOURCE}/{concept_code}")
    return int(row["id"])


def fetch_members(concept_code: str) -> list[tuple[str, str]]:
    headers = ths_headers(f"https://q.10jqka.com.cn/gn/detail/code/{concept_code}/")
    base = f"https://q.10jqka.com.cn/gn/detail/code/{concept_code}/"
    response = requests.get(base, headers=headers, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, features="lxml")
    page_info = soup.find(name="span", attrs={"class": "page_info"})
    page_count = int(page_info.text.split("/")[1]) if page_info else 1

    rows: list[tuple[str, str]] = []
    for page in range(1, page_count + 1):
        url = base if page == 1 else f"{base}page/{page}/ajax/1/"
        html = response.text if page == 1 else requests.get(url, headers=headers, timeout=20).text
        try:
            table = pd.read_html(StringIO(html))[0]
        except ValueError:
            continue
        if "代码" not in table.columns:
            continue
        for code in table["代码"]:
            stock_code = normalize_stock_code(code)
            if stock_code:
                rows.append((stock_code, concept_code))
        time.sleep(0.05)
    return list(set(rows))


def insert_members(conn, concept_id: int, rows: list[tuple[str, str]]):
    if not rows:
        return
    mapped_rows = [(stock_code, concept_id) for stock_code, _concept_code in rows]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT IGNORE INTO stock_concept_map (stock_code, concept_id)
            VALUES (%s, %s)
            """,
            mapped_rows,
        )
    conn.commit()


def fetch_daily(name: str, start_date: str, end_date: str) -> pd.DataFrame:
    return ak.stock_board_concept_index_ths(symbol=name, start_date=start_date, end_date=end_date)


def insert_daily(conn, concept_id: int, df: pd.DataFrame):
    if df.empty:
        return 0
    rows = []
    skipped = 0
    for row in df.itertuples(index=False):
        if any(pd.isna(getattr(row, col)) for col in REQUIRED_DAILY_COLUMNS):
            skipped += 1
            continue
        rows.append((
            concept_id,
            row.日期,
            float(row.开盘价),
            float(row.最高价),
            float(row.最低价),
            float(row.收盘价),
            int(row.成交量),
            float(row.成交额),
        ))
    if not rows:
        return skipped
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO concept_daily
                (concept_id, trade_date, open_price, high_price, low_price, close_price, volume, amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                open_price = VALUES(open_price),
                high_price = VALUES(high_price),
                low_price = VALUES(low_price),
                close_price = VALUES(close_price),
                volume = VALUES(volume),
                amount = VALUES(amount)
            """,
            rows,
        )
    conn.commit()
    return skipped


def count_table(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
        return int(cur.fetchone()["cnt"])


def main():
    parser = argparse.ArgumentParser(description="同步同花顺概念主表、成分股和行情")
    parser.add_argument("--start-date", default="20200101")
    parser.add_argument("--end-date", default=date.today().strftime("%Y%m%d"))
    parser.add_argument("--limit", type=int, default=None, help="调试用：仅同步前 N 个概念")
    parser.add_argument("--no-clear", action="store_true", help="不清空概念表，用于失败后续跑")
    parser.add_argument("--start-index", type=int, default=1, help="从第几个概念开始同步，1-based，用于续跑")
    parser.add_argument("--skip-daily", action="store_true", help="跳过概念行情")
    parser.add_argument("--skip-members", action="store_true", help="跳过概念成分股")
    args = parser.parse_args()

    conn = connect()
    try:
        reset_schema(conn)
        if not args.no_clear:
            clear_concepts(conn)
        concepts = fetch_concepts()
        if args.limit:
            concepts = concepts.head(args.limit)
        upsert_concepts(conn, concepts)
        print(f"[concept] board_concept: {len(concepts)}")

        total_skipped_daily_rows = 0
        selected_concepts = concepts.iloc[max(args.start_index - 1, 0):]
        for idx, row in enumerate(selected_concepts.itertuples(index=False), start=max(args.start_index, 1)):
            print(f"[{idx}/{len(concepts)}] {row.code} {row.name}", flush=True)
            concept_id = get_concept_id(conn, row.code)
            if not args.skip_members:
                try:
                    insert_members(conn, concept_id, fetch_members(row.code))
                except Exception as exc:
                    raise RuntimeError(f"THS concept members failed: {row.code} {row.name}: {exc}") from exc
            if not args.skip_daily:
                try:
                    skipped = insert_daily(conn, concept_id, fetch_daily(row.name, args.start_date, args.end_date))
                    if skipped:
                        total_skipped_daily_rows += skipped
                        print(f"  [daily] skipped invalid rows: {skipped}", flush=True)
                except Exception as exc:
                    raise RuntimeError(f"THS concept daily failed: {row.code} {row.name}: {exc}") from exc
            time.sleep(0.1)

        for table in ["board_concept", "stock_concept_map", "concept_daily"]:
            print(f"[count] {table}: {count_table(conn, table)}")
        print(f"[daily] total skipped invalid rows: {total_skipped_daily_rows}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
