#!/usr/bin/env python3
"""Import stock-board membership mappings.

This script writes the existing schema:
  - stock_industry_map(stock_code, industry_code)
  - stock_concept_map(stock_code, source, concept_code)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import pymysql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.config import get_database_config


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


def import_concepts_from_mootdx(conn) -> tuple[int, int]:
    from mootdx.quotes import Quotes

    client = Quotes.factory(market="std", timeout=8)
    df = client.block("block_gn.dat")
    pairs = df[
        (df["block_type"] == 2)
        & (df["code"].astype(str).str.fullmatch(r"\d{6}", na=False))
    ][["blockname", "code"]].dropna().drop_duplicates()
    pairs["blockname"] = pairs["blockname"].astype(str).str.strip()
    pairs["code"] = pairs["code"].astype(str).str.strip().str.zfill(6)
    pairs = pairs[(pairs["blockname"] != "") & (pairs["code"] != "")]

    source = "mootdx_tdx"
    concept_rows = [(name, name, source) for name in sorted(pairs["blockname"].unique())]
    map_rows = [(row["code"], source, row["blockname"]) for _, row in pairs.iterrows()]

    with conn.cursor() as cur:
        cur.execute("DELETE FROM stock_concept_map WHERE source = %s", (source,))
        cur.execute("DELETE FROM board_concept WHERE source = %s", (source,))
        cur.executemany(
            """
            INSERT INTO board_concept (code, name, source, source_code)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                source_code = VALUES(source_code)
            """,
            [(code, name, source, code) for code, name, source in concept_rows],
        )
        cur.executemany(
            """
            INSERT IGNORE INTO stock_concept_map (stock_code, source, concept_code)
            VALUES (%s, %s, %s)
            """,
            map_rows,
        )
    conn.commit()
    return len(concept_rows), len(map_rows)


def table_count(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
        return int(cur.fetchone()["cnt"])


def main():
    parser = argparse.ArgumentParser(description="导入行业/概念成分股映射")
    parser.add_argument("--concept", action="store_true", help="仅导入概念映射")
    parser.add_argument("--industry", action="store_true", help="行业映射暂未导入；避免混用错误口径")
    args = parser.parse_args()

    do_all = not args.concept and not args.industry
    conn = connect()
    try:
        if do_all or args.concept:
            concepts, concept_maps = import_concepts_from_mootdx(conn)
            print(f"[concept] board_concept upsert: {concepts}, stock_concept_map: {concept_maps}")

        if do_all or args.industry:
            print("[industry] skipped: mootdx 当前可用 block 文件未提供完整行业成分")

        for table in ["board_industry", "stock_industry_map", "board_concept", "stock_concept_map"]:
            print(f"[count] {table}: {table_count(conn, table)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
