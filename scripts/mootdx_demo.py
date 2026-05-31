"""
mootdx 简单 demo：获取长飞光纤（601869）最近 10 个交易日的日行情

使用说明：
    python scripts/mootdx_demo.py

首次运行会自动探测最快的数据服务器，请稍候。
"""

from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")


def fetch_daily_bars(symbol: str = "601869", count: int = 10) -> None:
    """获取并打印指定股票的最近 N 条日 K 线。"""

    from mootdx.quotes import Quotes

    print(f"[*] 正在连接行情服务器 ...")
    client = Quotes.factory(market="std", timeout=8)
    print("[*] 连接成功，正在获取数据 ...\n")

    df = client.bars(symbol=symbol, frequency=9, start=0, offset=count)

    if df is None or df.empty:
        print("[!] 未获取到数据，服务器可能无响应。")
        return

    # 保留关键列
    cols = ["open", "high", "low", "close", "volume", "amount"]
    display = df[cols].copy()
    display.index.name = "日期"

    # 价格保留两位小数
    for c in ["open", "high", "low", "close"]:
        display[c] = display[c].round(2)
    display["volume"] = display["volume"].astype(int)

    print(f"股票: {symbol}  长飞光纤  最近 {len(display)} 个交易日")
    print(f"{'─' * 60}")
    print(
        display.to_string(
            float_format=lambda x: f"{x:>8.2f}",
        )
    )


def main():
    fetch_daily_bars("601869", 10)


if __name__ == "__main__":
    main()
