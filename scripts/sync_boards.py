#!/usr/bin/env python3
"""板块数据同步脚本。

从 SDK 接口拉取行业 & 概念板块全量数据，写入 MySQL。

用法:
    python scripts/sync_boards.py                         # 同步行业 + 概念主表
    python scripts/sync_boards.py --members                # 同步主表 + 成分映射
    python scripts/sync_boards.py --members-only           # 仅同步成分映射
    python scripts/sync_boards.py --members --concept      # 仅同步概念成分映射
    python scripts/sync_boards.py --members --source mootdx # 概念成分走 mootdx
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# 确保 lib/ 可导入
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.board import (
    sync_concept_members_from_akshare,
    sync_concept_members_from_mootdx,
    sync_concepts_from_akshare,
    sync_industries_from_akshare,
    sync_industry_members_from_akshare,
)


def main():
    parser = argparse.ArgumentParser(description="同步行业 & 概念板块数据")
    parser.add_argument("--industry", action="store_true", help="仅同步行业板块")
    parser.add_argument("--concept", action="store_true", help="仅同步概念板块")
    parser.add_argument("--members", action="store_true", help="同步板块-个股成分映射")
    parser.add_argument("--members-only", action="store_true", help="仅同步板块-个股成分映射，不同步板块主表")
    parser.add_argument(
        "--source",
        choices=["akshare", "mootdx"],
        default="akshare",
        help="成分映射数据源；mootdx 仅支持概念映射",
    )
    parser.add_argument("--limit", type=int, default=None, help="仅同步前 N 个板块，调试用")
    args = parser.parse_args()

    do_all = not args.industry and not args.concept

    sync_boards = not args.members_only
    sync_members = args.members or args.members_only

    if sync_boards and (do_all or args.industry):
        print("[sync] 正在同步行业板块...")
        df = sync_industries_from_akshare()
        print(f"[sync] 行业板块: {len(df)} 条记录已写入")

    if sync_boards and (do_all or args.concept):
        print("[sync] 正在同步概念板块...")
        df = sync_concepts_from_akshare()
        print(f"[sync] 概念板块: {len(df)} 条记录已写入")

    if sync_members and (do_all or args.industry):
        if args.source == "mootdx":
            print("[sync] 跳过行业成分: mootdx 数据源不提供行业成分映射")
        else:
            print("[sync] 正在同步行业成分映射...")
            df = sync_industry_members_from_akshare(limit=args.limit)
            print(f"[sync] 行业成分映射: {len(df)} 条记录已写入")

    if sync_members and (do_all or args.concept):
        print("[sync] 正在同步概念成分映射...")
        if args.source == "mootdx":
            df = sync_concept_members_from_mootdx()
        else:
            df = sync_concept_members_from_akshare(limit=args.limit)
        print(f"[sync] 概念成分映射: {len(df)} 条记录已写入")

    print("[sync] 完成。")


if __name__ == "__main__":
    main()
