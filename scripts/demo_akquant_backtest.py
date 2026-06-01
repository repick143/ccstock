#!/usr/bin/env python3
"""
akquant 回测 Demo
================================
数据：MySQL stock_daily 表 → 601869 长飞光纤日线
策略：EMA5/20 金叉做多、死叉平仓，50% 仓位

用法：
    cd /home/cc/ccstock
    python scripts/demo_akquant_backtest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import warnings
warnings.filterwarnings("ignore")

from datetime import date

import pandas as pd
import akquant
from akquant import run_backtest, load_bar_from_df, PercentSizer, set_log_level
from akquant.strategy import Strategy
from akquant.data import Bar
from lib.stock_daily import DailyMarket


def fetch_stock_daily(stock_code: str, start: date, end: date) -> pd.DataFrame:
    """用项目 DailyMarket 封装从 MySQL 读取日线，列名对齐 load_bar_from_df。"""
    dm = DailyMarket()
    df = dm.get_stock(stock_code, start, end)
    df = df.rename(columns={
        "open_price": "open", "high_price": "high",
        "low_price": "low", "close_price": "close",
    })
    df.index.name = "date"
    df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"])
    df = df[["date", "open", "high", "low", "close", "volume"]]
    return df


class EmaCrossStrategy(Strategy):
    """EMA 快慢线交叉策略。

    快线上穿慢线 → 买入；下穿 → 平仓。
    """

    def on_start(self):
        self.fast = getattr(self, "fast", 5)
        self.slow = getattr(self, "slow", 20)
        self.set_sizer(PercentSizer(0.50))

    def _ema(self, closes: pd.Series, period: int) -> pd.Series:
        return closes.ewm(span=period, adjust=False).mean()

    def on_bar(self, bar: Bar):
        df = self.get_history_df(count=self.slow * 3)
        if df is None or len(df) < self.slow + 3:
            return

        # get_history_df 列名可能大驼峰：Date/Open/High/Low/Close/Volume
        close_col = next((c for c in ["Close", "close"] if c in df.columns), df.columns[4])
        closes = df[close_col]
        if closes.dtype == object or pd.isna(closes.iloc[-1]):
            return

        f = self._ema(closes, self.fast)
        s = self._ema(closes, self.slow)
        if pd.isna(f.iloc[-2]) or pd.isna(s.iloc[-2]):
            return

        pos = self.get_position(bar.symbol)

        if f.iloc[-2] <= s.iloc[-2] and f.iloc[-1] > s.iloc[-1]:
            if pos is None or pos <= 0:
                self.buy(tag="golden")
        elif f.iloc[-2] >= s.iloc[-2] and f.iloc[-1] < s.iloc[-1]:
            if pos is not None and pos > 0:
                self.sell(quantity=None, tag="dead")


def main():
    stock_code = "601869"
    stock_name = "长飞光纤"
    initial_cash = 1_000_000

    print(f"加载 {stock_code} {stock_name} 日线 ...")
    df = fetch_stock_daily(stock_code, date(2023, 6, 1), date(2026, 6, 1))
    print(f"  {len(df)} 条日线, {df['date'].min().date()} ~ {df['date'].max().date()}")

    bars = load_bar_from_df(df, symbol=stock_code)
    print(f"  {len(bars)} 根 Bar")

    set_log_level("WARNING")
    print(f"\n回测: 初始资金 {initial_cash:,.0f} | EMA5/20 | 50%仓位 | T+1")

    result = run_backtest(
        data=bars,
        strategy=EmaCrossStrategy,
        symbols=stock_code,
        initial_cash=initial_cash,
        commission_rate=0.00025,
        stamp_tax_rate=0.0005,
        t_plus_one=True,
        warmup_period=80,
    )

    m = result.metrics
    print("=" * 56)
    for key in ["initial_cash", "final_equity", "equity_final",
                "total_return", "cagr", "max_drawdown",
                "sharpe_ratio", "win_rate", "profit_factor"]:
        try:
            val = getattr(m, key, None)
            if val is not None:
                pct_fmt = any(x in key for x in ["return", "cagr", "drawdown", "win", "ratio"]) and isinstance(val, float)
                print(f"  {key:>18s} : {val:>14,.2%}" if pct_fmt and abs(val) < 100
                      else f"  {key:>18s} : {val:>14,.2f}")
        except Exception:
            pass

    # 直接读 trades_df
    trades = result.trades_df
    if trades is not None and len(trades) > 0:
        print(f"  {'trades_count':>18s} : {len(trades):>14d}")
        print(f"  {'PnL_sum':>18s} : {trades['pnl'].sum():>14,.2f}")
        win_rate = (trades['pnl'] > 0).mean()
        print(f"  {'win_rate_trades':>18s} : {win_rate:>13.2%}")
    else:
        print(f"  {'trades_count':>18s} : {'0':>14s}")

    orders = result.orders_df
    if orders is not None and len(orders) > 0:
        print(f"  {'orders_count':>18s} : {len(orders):>14d}")

    print("=" * 56)

    # 保存成交记录到 CSV
    if trades is not None and len(trades) > 0:
        output_dir = ROOT / "output"
        output_dir.mkdir(exist_ok=True)
        csv_path = output_dir / f"demo_trades_{stock_code}.csv"
        trades.to_csv(str(csv_path), index=False, encoding="utf-8-sig")
        print(f"\n成交记录已导出: {csv_path}")
        print(f"最近 5 笔:")
        columns = [c for c in ['exit_time', 'exit_date', 'size', 'pnl', 'return', 'commission']
                   if c in trades.columns]
        print(trades.tail(5)[columns].to_string(index=False))


if __name__ == "__main__":
    main()
