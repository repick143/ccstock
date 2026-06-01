#!/usr/bin/env python3
"""Migrate concept child tables to reference board_concept.id.

This is an in-place schema migration. It does not fetch any data from the
network; existing concept_code/board_code values are resolved against the
current board_concept rows.
"""

from __future__ import annotations

import sys
from pathlib import Path

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
        autocommit=False,
    )


def column_exists(cur, table: str, column: str) -> bool:
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
    return bool(cur.fetchone()["cnt"])


def index_exists(cur, table: str, index_name: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        """,
        (table, index_name),
    )
    return bool(cur.fetchone()["cnt"])


def count(cur, sql: str) -> int:
    cur.execute(sql)
    return int(cur.fetchone()["cnt"])


def migrate_stock_concept_map(cur):
    if not column_exists(cur, "stock_concept_map", "concept_id"):
        cur.execute(
            """
            ALTER TABLE stock_concept_map
            ADD COLUMN concept_id BIGINT NULL COMMENT '概念主表 ID（board_concept.id）'
            AFTER stock_code
            """
        )

    if column_exists(cur, "stock_concept_map", "concept_code"):
        cur.execute(
            """
            UPDATE stock_concept_map m
            JOIN board_concept c
              ON c.code = m.concept_code
             AND c.source = 'ths'
            SET m.concept_id = c.id
            WHERE m.concept_id IS NULL
            """
        )
        missing = count(cur, "SELECT COUNT(*) AS cnt FROM stock_concept_map WHERE concept_id IS NULL")
        if missing:
            raise RuntimeError(f"stock_concept_map has {missing} rows that cannot resolve concept_id")

        cur.execute("ALTER TABLE stock_concept_map DROP PRIMARY KEY")
        if index_exists(cur, "stock_concept_map", "idx_map_conc_code"):
            cur.execute("ALTER TABLE stock_concept_map DROP INDEX idx_map_conc_code")
        if index_exists(cur, "stock_concept_map", "idx_map_conc_source_code"):
            cur.execute("ALTER TABLE stock_concept_map DROP INDEX idx_map_conc_source_code")
        if column_exists(cur, "stock_concept_map", "source"):
            cur.execute("ALTER TABLE stock_concept_map DROP COLUMN source")
        cur.execute("ALTER TABLE stock_concept_map DROP COLUMN concept_code")
        cur.execute("ALTER TABLE stock_concept_map MODIFY concept_id BIGINT NOT NULL COMMENT '概念主表 ID（board_concept.id）'")
        cur.execute("ALTER TABLE stock_concept_map ADD PRIMARY KEY (stock_code, concept_id)")

    if not index_exists(cur, "stock_concept_map", "idx_map_concept_id"):
        cur.execute("ALTER TABLE stock_concept_map ADD KEY idx_map_concept_id (concept_id)")
    if not index_exists(cur, "stock_concept_map", "idx_map_stock_code"):
        cur.execute("ALTER TABLE stock_concept_map ADD KEY idx_map_stock_code (stock_code)")


def migrate_concept_daily(cur):
    if not column_exists(cur, "concept_daily", "concept_id"):
        cur.execute(
            """
            ALTER TABLE concept_daily
            ADD COLUMN concept_id BIGINT NULL COMMENT '概念主表 ID（board_concept.id）'
            AFTER id
            """
        )

    if column_exists(cur, "concept_daily", "board_code"):
        cur.execute(
            """
            UPDATE concept_daily d
            JOIN board_concept c
              ON c.code = d.board_code
             AND c.source = 'ths'
            SET d.concept_id = c.id
            WHERE d.concept_id IS NULL
            """
        )
        missing = count(cur, "SELECT COUNT(*) AS cnt FROM concept_daily WHERE concept_id IS NULL")
        if missing:
            raise RuntimeError(f"concept_daily has {missing} rows that cannot resolve concept_id")

        if index_exists(cur, "concept_daily", "uk_conc_daily"):
            cur.execute("ALTER TABLE concept_daily DROP INDEX uk_conc_daily")
        if index_exists(cur, "concept_daily", "idx_conc_code"):
            cur.execute("ALTER TABLE concept_daily DROP INDEX idx_conc_code")
        cur.execute("ALTER TABLE concept_daily DROP COLUMN board_code")
        cur.execute("ALTER TABLE concept_daily MODIFY concept_id BIGINT NOT NULL COMMENT '概念主表 ID（board_concept.id）'")
        cur.execute("ALTER TABLE concept_daily ADD UNIQUE KEY uk_conc_daily (concept_id, trade_date)")

    if not index_exists(cur, "concept_daily", "idx_concept_daily_concept_id"):
        cur.execute("ALTER TABLE concept_daily ADD KEY idx_concept_daily_concept_id (concept_id)")
    if not index_exists(cur, "concept_daily", "idx_conc_date"):
        cur.execute("ALTER TABLE concept_daily ADD KEY idx_conc_date (trade_date)")


def main():
    conn = connect()
    try:
        with conn.cursor() as cur:
            migrate_stock_concept_map(cur)
            migrate_concept_daily(cur)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
