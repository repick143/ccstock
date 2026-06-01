#!/usr/bin/env python3
"""板块数据同步脚本。

从 akshare（同花顺 _ths 接口）拉取行业 & 概念板块全量数据，写入 MySQL。

用法:
    python scripts/sync_boards.py              # 同步行业 + 概念
    python scripts/sync_boards.py --industry    # 仅同步行业
    python scripts/sync_boards.py --concept     # 仅同步概念
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

from lib.board import sync_industries_from_akshare, sync_concepts_from_akshare


def main():
    parser = argparse.ArgumentParser(description="同步行业 & 概念板块数据")
    parser.add_argument("--industry", action="store_true", help="仅同步行业板块")
    parser.add_argument("--concept", action="store_true", help="仅同步概念板块")
    args = parser.parse_args()

    do_all = not args.industry and not args.concept

    if do_all or args.industry:
        print("[sync] 正在同步行业板块...")
        df = sync_industries_from_akshare()
        print(f"[sync] 行业板块: {len(df)} 条记录已写入")

    if do_all or args.concept:
        print("[sync] 正在同步概念板块...")
        df = sync_concepts_from_akshare()
        print(f"[sync] 概念板块: {len(df)} 条记录已写入")

    print("[sync] 完成。")


if __name__ == "__main__":
    main()
