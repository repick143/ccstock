#!/usr/bin/env python3
"""
从 mootdx（通达信）获取 A 股日行情数据并写入 MySQL。

配置：
    编辑 conf/config.toml，修改数据库连接等参数

用法：
    python scripts/stock_daily_etl.py --codes 601869 --names 长飞光纤
    python scripts/stock_daily_etl.py --codes 601869,000001 --years 3

    # CLI 参数可覆盖配置文件中的值
    python scripts/stock_daily_etl.py --codes 601869 --password another_pwd
"""

from __future__ import annotations

import argparse
import sys
import tomllib
import warnings
from datetime import date, timedelta
from pathlib import Path
from typing import List, Tuple

warnings.filterwarnings("ignore")

# ── 配置加载 ────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "conf" / "config.toml"

_CONFIG_CACHE: dict | None = None


def get_config() -> dict:
    """加载配置文件（带缓存）。"""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    try:
        with open(CONFIG_PATH, "rb") as f:
            _CONFIG_CACHE = tomllib.load(f)
    except Exception as e:
        print(f"[WARN] 无法加载 {CONFIG_PATH}: {e}，使用默认值", file=sys.stderr)
        _CONFIG_CACHE = {}
    return _CONFIG_CACHE


# ── mootdx 数据获取 ────────────────────────────────────────


def build_client():
    """创建 mootdx 客户端，参数来自配置文件。"""
    from mootdx.quotes import Quotes

    cfg = get_config().get("mootdx", {})
    return Quotes.factory(
        market=cfg.get("market", "std"),
        timeout=cfg.get("timeout", 8),
    )


def fetch_one_stock(code: str, years: int, client) -> List[tuple]:
    """
    获取单只股票最近 N 年日 K 线，返回 [(code, None, date, open, high, low, close, vol, amount), ...]

    mootdx 限制：单次最多 800 条，超出自动分页。
    数据按日期正序返回（最老在前）。
    """
    import pandas as pd

    fetch_cutoff = date.today() - timedelta(days=int(years * 365.25 + 20))
    fragments = []
    start = 0

    while True:
        df = client.bars(symbol=code, frequency=9, start=start, offset=800)
        if df is None or df.empty:
            break
        fragments.append(df)

        # df.index[0] 是最老的日期（数据按日期正序排列）
        if df.index[0].date() <= fetch_cutoff:
            break

        start += 800
        if start > 8000:
            break

    if not fragments:
        return []

    full = pd.concat(fragments)
    full = full[~full.index.duplicated(keep="first")]
    full = full.sort_index()

    # 计算昨收价、涨跌额、涨跌幅
    # 注：在日期过滤前计算，确保第一天的 pre_close 来自过滤前数据
    full['pre_close'] = full['close'].shift(1)
    full['chg_amt'] = full['close'] - full['pre_close']
    full['chg_pct'] = (full['chg_amt'] / full['pre_close'] * 100).round(4)

    filter_cutoff = date.today() - timedelta(days=int(years * 365.25))
    full = full[full.index.date >= filter_cutoff]

    if full.empty:
        return []

    vol_col = "volume" if "volume" in full.columns else "vol"
    records = []
    for ts, row in full.iterrows():
        records.append(
            (
                code,
                None,  # stock_name — 调用时按需填入
                ts.date(),
                round(float(row["open"]), 2),
                round(float(row["high"]), 2),
                round(float(row["low"]), 2),
                round(float(row["close"]), 2),
                int(row[vol_col]),
                round(float(row["amount"]), 2),
                round(float(row['pre_close']), 2) if pd.notna(row['pre_close']) else None,
                round(float(row['chg_amt']), 2) if pd.notna(row['chg_amt']) else None,
                round(float(row['chg_pct']), 4) if pd.notna(row['chg_pct']) else None,
            )
        )
    return records


# ── MySQL 操作 ──────────────────────────────────────────────


def get_conn(
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
):
    """建立 MySQL 连接。"""
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
    """批量 upsert（新插旧更）。"""
    sql = """
        INSERT INTO stock_daily
            (stock_code, stock_name, trade_date, open_price, high_price, low_price, close_price, volume, amount, pre_close, chg_amt, chg_pct)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            stock_name  = VALUES(stock_name),
            open_price  = VALUES(open_price),
            high_price  = VALUES(high_price),
            low_price   = VALUES(low_price),
            close_price = VALUES(close_price),
            pre_close   = VALUES(pre_close),
            chg_amt     = VALUES(chg_amt),
            chg_pct     = VALUES(chg_pct),
            volume      = VALUES(volume),
            amount      = VALUES(amount)
    """
    with conn.cursor() as cur:
        cur.executemany(sql, records)
    conn.commit()
    return len(records)


# ── 入口 ────────────────────────────────────────────────────


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    """解析命令行参数，默认值从 config.toml 读取。"""
    cfg = get_config()
    db = cfg.get("database", {})
    etl_cfg = cfg.get("etl", {})

    p = argparse.ArgumentParser(description="从 mootdx 获取 A 股日行情并写入 MySQL")
    p.add_argument("--codes", required=True, help="股票代码，逗号分隔，如 601869,000001")
    p.add_argument("--names", default="", help="股票名称，逗号分隔，如 长飞光纤,平安银行")
    p.add_argument("--years", type=int, default=etl_cfg.get("default_years", 2), help="获取最近 N 年数据")

    # MySQL 连接（默认值来自配置文件）
    p.add_argument("--host", default=db.get("host", "127.0.0.1"), help="MySQL 地址")
    p.add_argument("--port", type=int, default=db.get("port", 3306), help="MySQL 端口")
    p.add_argument("--user", default=db.get("user", "root"), help="MySQL 用户名")
    p.add_argument("--password", default=db.get("password", ""), help="MySQL 密码")
    p.add_argument("--database", default=db.get("database", "ccstock"), help="MySQL 数据库")

    return p.parse_args(argv)


def main() -> None:
    args = parse_args()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    names_raw = [n.strip() for n in args.names.split(",") if n.strip()] if args.names else []
    names_map = dict(zip(codes, names_raw)) if names_raw else {}

    print(f"目标: {codes}  |  范围: 最近 {args.years} 年")
    print(f"MySQL: {args.user}@{args.host}:{args.port}/{args.database}")
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




