"""
Changfei Fiber (601869) Stock Price Prediction Framework

Uses akquant technical indicators + RandomForest to predict next trading day close price.
Run directly: python scripts/predict_601869.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import akquant as ak
from lib.stock_daily import DailyMarket

STOCK_CODE = "601869"
STOCK_NAME = "Changfei Fiber"


def fetch_data(symbol=STOCK_CODE, years=2):
    """Fetch daily bars from local DB / mootdx."""
    dm = DailyMarket()
    df = dm.bars_years(symbol, years=years)
    if df.empty:
        print("ERROR: No data retrieved.")
        sys.exit(1)
    return df.sort_index()


def add_features(df):
    """Compute technical indicators using akquant indicator classes."""
    close = df["close_price"].values.astype(float)
    high = df["high_price"].values.astype(float)
    low = df["low_price"].values.astype(float)
    vol = df["volume"].values.astype(float)

    # Moving averages
    df["SMA_5"] = ak.SMA(5).update_many(close)
    df["SMA_10"] = ak.SMA(10).update_many(close)
    df["SMA_20"] = ak.SMA(20).update_many(close)
    df["EMA_12"] = ak.EMA(12).update_many(close)
    df["EMA_26"] = ak.EMA(26).update_many(close)

    # Volatility
    df["RSI"] = ak.RSI(14).update_many(close)
    bb_up, bb_mid, bb_low = ak.BollingerBands(20, 2).update_many(close)
    df["BB_UPPER"] = bb_up
    df["BB_MID"] = bb_mid
    df["BB_LOWER"] = bb_low
    df["ATR"] = ak.ATR(14).update_many_hlc(high, low, close)

    # MACD
    macd_arr, signal_arr, hist_arr = ak.MACD(12, 26, 9).update_many(close)
    df["MACD"] = macd_arr
    df["MACD_SIG"] = signal_arr
    df["MACD_HIST"] = hist_arr

    # Momentum
    df["ROC"] = ak.ROC(10).update_many(close)
    df["MOM"] = ak.MOM(10).update_many(close)
    df["OBV"] = ak.OBV().update_many_dual(close, vol)

    # Target: next-day close price and direction
    df["TARGET_CLOSE"] = df["close_price"].shift(-1)
    df["TARGET_DIR"] = (df["TARGET_CLOSE"] > df["close_price"]).astype(int)

    return df


FEATURE_COLS = [
    "SMA_5", "SMA_10", "SMA_20", "EMA_12", "EMA_26",
    "RSI", "BB_UPPER", "BB_MID", "BB_LOWER", "ATR",
    "MACD", "MACD_SIG", "MACD_HIST",
    "ROC", "MOM", "OBV",
    "open_price", "high_price", "low_price", "close_price",
    "volume", "amount", "pre_close", "chg_amt", "chg_pct",
]


def prepare_ml_data(df):
    """Extract feature matrix + targets, drop NaN rows."""
    data = df[FEATURE_COLS + ["TARGET_CLOSE", "TARGET_DIR"]].dropna()
    return data


def train_models(data):
    """Train RandomForest for price regression and direction classification."""
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

    X = data[FEATURE_COLS].values
    y_reg = data["TARGET_CLOSE"].values
    y_cls = data["TARGET_DIR"].values

    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_reg_train, y_reg_test = y_reg[:split], y_reg[split:]
    y_cls_train, y_cls_test = y_cls[:split], y_cls[split:]

    reg = RandomForestRegressor(n_estimators=200, max_depth=8,
                                 random_state=42, n_jobs=-1)
    reg.fit(X_train, y_reg_train)
    r2 = reg.score(X_test, y_reg_test)

    cls = RandomForestClassifier(n_estimators=200, max_depth=6,
                                  random_state=42, n_jobs=-1)
    cls.fit(X_train, y_cls_train)
    acc = cls.score(X_test, y_cls_test)

    return reg, cls, r2, acc


def predict_next(reg, cls, df):
    """Predict next trading day close price and direction."""
    X_last = df[FEATURE_COLS].iloc[-1:].values
    price = float(reg.predict(X_last)[0])
    direction = bool(cls.predict(X_last)[0])
    proba = cls.predict_proba(X_last)[0]
    return price, direction, proba


def plot_results(df, pred_price, pred_dir):
    """Save prediction chart to scripts/predict_601869.png."""
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False

    last_date = df.index[-1]
    next_date = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=1)[0]
    recent = df.tail(60)
    last_close = float(df["close_price"].iloc[-1])
    change = pred_price - last_close
    pct = change / last_close * 100

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(recent.index, recent["close_price"].values,
            label="Close Price", color="#2196F3", linewidth=1.5)
    ax.fill_between(recent.index, recent["BB_UPPER"].values,
                     recent["BB_LOWER"].values, alpha=0.12, color="#2196F3")

    color = "#F44336" if pred_dir else "#4CAF50"
    marker = "^" if pred_dir else "v"
    ax.scatter([next_date], [pred_price], color=color, s=120, zorder=5, marker=marker)

    label = f"Pred: {pred_price:.2f} ({pct:+.2f}%)"
    ax.annotate(label, xy=(next_date, pred_price), fontsize=12,
                fontweight="bold", color=color, xytext=(15, 15),
                textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color=color))

    ax.set_title(f"{STOCK_NAME} ({STOCK_CODE})  |  Next Day Prediction ({next_date.date()})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))

    out = ROOT / "scripts" / "predict_601869.png"
    plt.savefig(str(out), dpi=150, bbox_inches="tight")
    print(f"Chart saved: {out}")
    plt.close()


def main():
    print("=" * 55)
    print(f"  {STOCK_NAME} ({STOCK_CODE}) - Price Prediction")
    print("=" * 55)

    print("\n[1/4] Fetching data (2 years) ...")
    df = fetch_data()
    print(f"      {len(df)} records ({df.index[0].date()} ~ {df.index[-1].date()})")

    print("[2/4] Computing indicators ...")
    df = add_features(df)
    print(f"      {len(FEATURE_COLS)} indicators computed")

    print("[3/4] Training RandomForest model ...")
    data = prepare_ml_data(df)
    reg, cls, r2, acc = train_models(data)
    print(f"      R-squared (price):  {r2:.4f}")
    print(f"      Accuracy (dir):     {acc:.4f}")

    print("[4/4] Predicting next trading day ...")
    pred_price, pred_dir, proba = predict_next(reg, cls, df)
    last_close = float(df["close_price"].iloc[-1])
    pct = (pred_price - last_close) / last_close * 100
    direction = "UP ^" if pred_dir else "DOWN v"
    confidence = max(proba) * 100

    print()
    print(f"  Latest close:      {last_close:.2f}")
    print(f"  Predicted close:   {pred_price:.2f} ({pct:+.2f}%)")
    print(f"  Direction:         {direction}  (confidence: {confidence:.1f}%)")
    print(f"  Training samples:  {len(data)}")
    print()

    print("Generating chart ...")
    try:
        plot_results(df, pred_price, pred_dir)
    except Exception as e:
        print(f"  Chart generation skipped (install matplotlib): {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
