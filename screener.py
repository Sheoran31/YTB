"""
Stock Screener — scans Nifty 50 stocks and finds BUY candidates.

Run daily at 9:30 AM:
    python screener.py

Filters:
    1. Price > 20-day SMA (uptrend)
    2. RSI > 55 (bullish momentum)
    3. Volume > 1.5x 20-day avg (volume breakout)
    4. ATR > 15 (enough movement to trade)
"""
import csv
import os
from datetime import datetime

import pandas as pd

import config
from data.fetcher import fetch_stock_data
from data.signals import calculate_sma, calculate_rsi, calculate_atr, calculate_volume_ratio


def screen_stock(ticker: str) -> dict | None:
    """
    Analyze a single stock against all filters.
    Returns dict with analysis if data available, None on error.
    """
    try:
        data = fetch_stock_data(ticker, period="6mo")
    except Exception as e:
        print(f"  Skipping {ticker}: {e}")
        return None

    if len(data) < config.SMA_SLOW:
        print(f"  Skipping {ticker}: not enough data ({len(data)} rows)")
        return None

    close = data["Close"].squeeze()
    volume = data["Volume"].squeeze()
    high = data["High"].squeeze()
    low = data["Low"].squeeze()

    sma_20 = calculate_sma(close, config.SMA_FAST)
    rsi = calculate_rsi(close, config.RSI_PERIOD)
    atr = calculate_atr(high, low, close, config.ATR_PERIOD)
    vol_ratio = calculate_volume_ratio(volume)

    latest_price = close.iloc[-1]
    latest_sma = sma_20.iloc[-1]
    latest_rsi = rsi.iloc[-1]
    latest_atr = atr.iloc[-1]
    latest_vol_ratio = vol_ratio.iloc[-1]

    # Apply filters
    above_sma = latest_price > latest_sma
    rsi_ok = latest_rsi > config.RSI_BUY_THRESHOLD
    volume_ok = latest_vol_ratio > config.VOLUME_RATIO_MIN
    atr_ok = latest_atr > 15

    all_pass = above_sma and rsi_ok and volume_ok and atr_ok
    signal = "BUY" if all_pass else "SKIP"

    return {
        "symbol": ticker.replace(".NS", ""),
        "price": round(float(latest_price), 2),
        "rsi": round(float(latest_rsi), 1),
        "vol_ratio": round(float(latest_vol_ratio), 1),
        "sma_20": "Above" if above_sma else "Below",
        "atr": round(float(latest_atr), 1),
        "signal": signal,
    }


def run_screener(tickers: list[str] = config.WATCHLIST) -> list[dict]:
    """Run screener on all tickers and return results."""
    print(f"\nScreener running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scanning {len(tickers)} stocks...\n")

    results = []
    for ticker in tickers:
        result = screen_stock(ticker)
        if result:
            results.append(result)

    return results


def print_results(results: list[dict]):
    """Print results as a formatted table."""
    if not results:
        print("No results to display.")
        return

    header = f"{'Symbol':<12} {'Price':>8} {'RSI':>6} {'Vol':>6} {'20-SMA':<8} {'ATR':>6} {'Signal':<8}"
    print(header)
    print("-" * len(header))

    for r in results:
        signal_icon = "BUY" if r["signal"] == "BUY" else "SKIP"
        print(
            f"{r['symbol']:<12} {r['price']:>8,.2f} {r['rsi']:>6.1f} "
            f"{r['vol_ratio']:>5.1f}x {r['sma_20']:<8} {r['atr']:>6.1f} {signal_icon:<8}"
        )

    buy_count = sum(1 for r in results if r["signal"] == "BUY")
    print(f"\nBUY signals: {buy_count}/{len(results)}")


def save_results(results: list[dict], filepath: str = "screener_results.csv"):
    """Save results to CSV with timestamp."""
    if not results:
        return

    for r in results:
        r["timestamp"] = datetime.now().isoformat()

    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)

    print(f"Results saved to {filepath}")


if __name__ == "__main__":
    results = run_screener()
    print_results(results)
    save_results(results)
