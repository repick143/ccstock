#!/usr/bin/env python3
"""
从 mootdx（通达信）获取 A 股日行情数据并写入 MySQL。

用法：
    # 单只股票，落库 2 年
    python scripts/stock_daily_etl.py --codes 601869 --names 长飞光纤

    # 多只股票
    python scripts/stock_daily_etl.py --codes 601869,000001,600519 --names 长飞光纤,平安银行,贵州茅台 --years 3

    # 指定 MySQL 连接
    python scripts/stock_daily_etl.py --codes 601869 --host 127.0.0.1 --user root --password 123456

前置条件：
    1. MySQL 已安装并运行，执行 sql/create_tables.sql 建表
    2. 依赖已安装（pymysql / mootdx / pandas）
"""

from __future__ import annotations

import argparse
import sys
import warnings
from datetime import date, timedelta
from typing import List, Tuple

warnings.filterwarnings("ignore")


# ── mootdx 数据获取 ────────────────────────────────────────


def build_client():
    """创建 mootdx 行情客户端。"""
    from mootdx.quotes import Quotes

    return Quotes.factory(market="std", timeout=8)


def fetch_one_stock(code: str, years: int, client) -> List:
    """
    获取单只股票最近 N 年日 K 线。

    mootdx 限制：单次最多 800 条，超出需分页。
    数据格式：pd.DataFrame，index=dttm，列含 open/high/low/close/vol/amount/volume。
    返回值为合并、去重、按 years 过滤后的记录列表。
    """
    # fetch 阶段多加 20 天缓冲，避免因停牌导致数据不够
    fetch_cutoff = date.today() - timedelta(days=int(years * 365.25 + 20))
    fragments = []
    start = 0

    while True:
        df = client.bars(symbol=code, frequency=9, start=start, offset=800)
        if df is None or df.empty:
            break

        # 数据按日期正序排列（最老在前）
        fragments.append(df)

        if df.index[0].date() <= fetch_cutoff:
            break

        start += 800
        if start > 8000:  # 安全阀
            break

    if not fragments:
        return []

    # 合并 & 去重
    import pandas as pd

    full = pd.concat(fragments)
    full = full[~full.index.duplicated(keep="first")]
    full = full.sort_index()

    # 按 years 过滤
    filter_cutoff = date.today() - timedelta(days=int(years * 365.25))
    full = full[full.index.date >= filter_cutoff]

    if full.empty:
        return []

    # 转成数据库记录
    vol_col = "volume" if "volume" in full.columns else "vol"
    records = []
    for ts, row in full.iterrows():
        records.append(
            (
                code,
                None,  # stock_name —— 调用时按需填入
                ts.date(),
                round(float(row["open"]), 2),
                round(float(row["high"]), 2),
                round(float(row["low"]), 2),
                round(float(row["close"]), 2),
                int(row[vol_col]),
                round(float(row["amount"]), 2),
            )
        )
    return records


# ── MySQL 操作 ──────────────────────────────────────────────


def get_conn(host: str, port: int, user: str, password: str, database: str):
    import pymysql

    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def upsert_batch(conn, records: List[tuple]) -> int:
    """批量 upsert（新记录插入，已有记录更新价格字段）。"""
    sql = """
        INSERT INTO stock_daily
            (stock_code, stock_name, trade_date, open_price, high_price, low_price, close_price, volume, amount)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            stock_name  = VALUES(stock_name),
            open_price  = VALUES(open_price),
            high_price  = VALUES(high_price),
            low_price   = VALUES(low_price),
            close_price = VALUES(close_price),
            volume      = VALUES(volume),
            amount      = VALUES(amount)
    """
    with conn.cursor() as cur:
        cur.executemany(sql, records)
    conn.commit()
    return len(records)


# ── 入口 ────────────────────────────────────────────────────


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="从 mootdx 获取 A 股日行情并写入 MySQL")
    p.add_argument("--codes", required=True, help="股票代码，逗号分隔，如 601869,000001")
    p.add_argument("--names", default="", help="股票名称，逗号分隔，与 codes 对应，如 长飞光纤,平安银行")
    p.add_argument("--years", type=int, default=2, help="获取最近 N 年数据（默认 2）")
    p.add_argument("--host", default="127.0.0.1", help="MySQL 地址（默认 127.0.0.1）")
    p.add_argument("--port", type=int, default=3306)
    p.add_argument("--user", default="root")
    p.add_argument("--password", default="", help="MySQL 密码")
    p.add_argument("--database", default="ccstock")
    return p.parse_args(argv)


def main() -> None:
    args = parse_args()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    names_raw = [n.strip() for n in args.names.split(",") if n.strip()] if args.names else []
    names_map = dict(zip(codes, names_raw)) if names_raw else {}

    print(f"目标股票: {codes}")
    print(f"数据范围: 最近 {args.years} 年")
    print(f"MySQL:     {args.user}@{args.host}:{args.port}/{args.database}")
    print()

    # 1. 连接 MySQL
    print("[1/4] 连接 MySQL ...", end=" ", flush=True)
    try:
        conn = get_conn(args.host, args.port, args.user, args.password, args.database)
        print("OK")
    except Exception as e:
        print(f"FAILED — {e}")
        sys.exit(1)

    # 2. 连接 mootdx
    print("[2/4] 连接 mootdx 行情服务器 ...", end=" ", flush=True)
    try:
        client = build_client()
        print("OK")
    except Exception as e:
        print(f"FAILED — {e}")
        conn.close()
        sys.exit(1)

    total = 0

    for code in codes:
        name = names_map.get(code)
        label = f"{code}({name})" if name else code

        # 3. 获取数据
        print(f"\n[3/4] [{label}] 获取日线 ...", end=" ", flush=True)
        try:
            records = fetch_one_stock(code, args.years, client)
        except Exception as e:
            print(f"ERROR — {e}")
            continue

        if not records:
            print("无数据，跳过")
            continue

        # 填入股票名称
        if name:
            records = [(code, name) + r[2:] for r in records]

        print(f"{len(records)} 条")

        # 4. 写入 MySQL
        print(f"[4/4] [{label}] 写入 MySQL ...", end=" ", flush=True)
        try:
            n = upsert_batch(conn, records)
            total += n
            print(f"OK ({n} 条)")
        except Exception as e:
            print(f"ERROR — {e}")

    conn.close()
    print(f"\n全部完成，共写入 {total} 条记录。")


if __name__ == "__main__":
    main()


