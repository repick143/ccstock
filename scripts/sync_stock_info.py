#!/usr/bin/env python3
"""个股基础信息同步脚本。

从 akshare 同步股票代码+名称，以及逐只财务指标。

用法:
    python scripts/sync_stock_info.py                    # Phase 1: 批量同步代码+名称
    python scripts/sync_stock_info.py --enrich           # Phase 2: 逐只同步财务指标（全量）
    python scripts/sync_stock_info.py --enrich --limit 50   # 只处理前 50 只
    python scripts/sync_stock_info.py --enrich --codes 601869,000001  # 指定股票
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.stock_info import sync_stock_codes, sync_stock_financials


def main():
    parser = argparse.ArgumentParser(description="同步个股基础信息")
    parser.add_argument("--enrich", action="store_true",
                        help="Phase 2: 逐只同步财务指标")
    parser.add_argument("--limit", type=int, default=None,
                        help="财务同步最大股票数（需 --enrich）")
    parser.add_argument("--codes", type=str, default=None,
                        help="财务同步指定股票代码，逗号分隔（需 --enrich）")
    args = parser.parse_args()

    if args.enrich:
        codes = None
        if args.codes:
            codes = [c.strip() for c in args.codes.split(",")]
        print(f"[sync] Phase 2: 开始同步财务指标...")
        if args.limit:
            print(f"[sync] 限 {args.limit} 只")
        if codes:
            print(f"[sync] 指定股票: {codes}")
        sync_stock_financials(codes=codes, limit=args.limit)
    else:
        print("[sync] Phase 1: 批量同步股票代码+名称...")
        sync_stock_codes()

    print("[sync] 完成。")


if __name__ == "__main__":
    main()
