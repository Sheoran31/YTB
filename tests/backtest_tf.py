"""
Multi-Timeframe Backtester — Indian Market (NSE)

Tests the same strategy across 4 timeframes to find which gives
the cleanest signals for NSE (9:15 AM – 3:30 PM, 6.25 hrs/day).

Timeframes:
  daily  — Positional/swing. Full history. Can hold overnight.
  1h     — Intraday swing. 6 candles/day. 2 years history.
  15min  — Scalping. 25 candles/day. 60 days history only.
  4h     — Resampled from 1H. ~1.5 candles/day (limited in Indian market).

Intraday rules (15min, 1h, 4h):
  - Position auto square-off at 3:15 PM if not already closed.
  - No overnight holding.

Usage:
    python -m tests.backtest_tf                         # RELIANCE, all timeframes
    python -m tests.backtest_tf --ticker HDFCBANK       # Specific stock
    python -m tests.backtest_tf --all                   # Top 5 watchlist stocks
    python -m tests.backtest_tf --tf 1h                 # Single timeframe only
"""

import sys
import pandas as pd
import numpy as np
import yfinance as yf

import config
from data.signals import (
    calculate_ema, calculate_macd, calculate_rsi,
    calculate_atr, calculate_adx, calculate_volume_ratio,
)

SQUAREOFF_HOUR   = 15
SQUAREOFF_MINUTE = 15

TF_CONFIG = {
    "daily": {
        "interval": "1d",
        "period":   None,
        "start":    "2022-01-01",
        "end":      "2025-12-31",
        "intraday": False,
        "label":    "Daily (Positional)",
        "note":     "Full history. Best for swing trades. Can hold overnight.",
        "bars_per_day": 1,
    },
    "1h": {
        "interval": "1h",
        "period":   "730d",
        "start":    None,
        "end":      None,
        "intraday": True,
        "label":    "1 Hour (Intraday Swing)",
        "note":     "6 candles/day. Good balance of signal quality & frequency.",
        "bars_per_day": 6,
    },
    "15min": {
        "interval": "15m",
        "period":   "60d",
        "start":    None,
        "end":      None,
        "intraday": True,
        "label":    "15 Min (Intraday Scalping)",
        "note":     "25 candles/day. Only 60 days history. More noise, more trades.",
        "bars_per_day": 25,
    },
    "4h": {
        "interval": "1h",
        "period":   "730d",
        "start":    None,
        "end":      None,
        "intraday": True,
        "resample": "4h",
        "label":    "4 Hour (Resampled)",
        "note":     "~1.5 candles/day. Indian market too short for 4H — limited use.",
        "bars_per_day": 2,
    },
}


# ── Data fetching ─────────────────────────────────────────────────────────────

def fetch_data(ticker: str, tf: str) -> pd.DataFrame:
    cfg = TF_CONFIG[tf]
    try:
        if cfg["period"]:
            data = yf.download(ticker, period=cfg["period"],
                               interval=cfg["interval"], progress=False)
        else:
            data = yf.download(ticker, start=cfg["start"], end=cfg["end"],
                               interval=cfg["interval"], progress=False)

        if data.empty:
            return pd.DataFrame()

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        if cfg.get("resample") == "4h":
            data = data.resample("4h", origin="start_day").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum",
            }).dropna()

        # Filter to NSE market hours for intraday data
        if cfg["intraday"] and hasattr(data.index, "hour"):
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            data = data.between_time("09:15", "15:30")

        return data.dropna()
    except Exception as e:
        print(f"  Fetch error ({ticker}, {tf}): {e}")
        return pd.DataFrame()


# ── Signal generation ─────────────────────────────────────────────────────────

def get_signal(data: pd.DataFrame) -> str:
    if len(data) < 60:
        return "HOLD"

    c  = data["Close"].squeeze()
    h  = data["High"].squeeze()
    l  = data["Low"].squeeze()
    v  = data["Volume"].squeeze()

    ema20 = calculate_ema(c, 20)
    ema50 = calculate_ema(c, 50)
    _, _, macd_hist = calculate_macd(c)
    rsi   = calculate_rsi(c, config.RSI_PERIOD)
    adx   = calculate_adx(h, l, c, 14)
    volr  = calculate_volume_ratio(v, 20)

    e20  = float(ema20.iloc[-1])
    e50  = float(ema50.iloc[-1])
    mh   = float(macd_hist.iloc[-1])
    r    = float(rsi.iloc[-1])
    a    = float(adx.iloc[-1])
    vr   = float(volr.iloc[-1])

    if e20 > e50 and mh > 0 and r > config.RSI_BUY_THRESHOLD and a > config.ADX_MIN and vr > config.VOLUME_RATIO_MIN:
        return "BUY"
    if e20 < e50 or mh < 0 or r < config.RSI_SELL_THRESHOLD:
        return "SELL"
    return "HOLD"


# ── Backtest engine ───────────────────────────────────────────────────────────

def backtest_tf(ticker: str, tf: str,
                initial_capital: float = config.INITIAL_CAPITAL) -> dict:
    cfg  = TF_CONFIG[tf]
    data = fetch_data(ticker, tf)

    if data.empty or len(data) < 60:
        return {"tf": tf, "label": cfg["label"], "error": "Not enough data"}

    br_buy  = (config.BROKER_COSTS["brokerage_intraday"]
               if cfg["intraday"] else config.BROKER_COSTS["brokerage_delivery"])
    br_sell = br_buy
    stt     = (config.BROKER_COSTS["stt_intraday_sell"]
               if cfg["intraday"] else config.BROKER_COSTS["stt_delivery_sell"])

    portfolio  = initial_capital
    position   = None   # {"entry_price", "quantity", "cost_basis", "entry_bar"}
    trades     = []
    bar_values = []

    close = data["Close"].squeeze()

    for i in range(50, len(data)):
        price      = float(close.iloc[i])
        current_bar = data.index[i]

        # Mark-to-market
        if position is None:
            bar_values.append(portfolio)
        else:
            unreal = (price - position["entry_price"]) * position["quantity"]
            bar_values.append(portfolio + unreal)

        # ── Intraday square-off at 3:15 PM ──
        must_close = False
        if cfg["intraday"] and position is not None and hasattr(current_bar, "hour"):
            if (current_bar.hour > SQUAREOFF_HOUR or
                    (current_bar.hour == SQUAREOFF_HOUR
                     and current_bar.minute >= SQUAREOFF_MINUTE)):
                must_close = True

        if must_close:
            proceeds  = position["quantity"] * price * (1 - br_sell - stt)
            pnl       = proceeds - position["cost_basis"]
            portfolio += proceeds
            trades.append({"pnl": round(pnl, 2), "exit_reason": "squareoff",
                           "date": str(current_bar)})
            position = None
            continue

        signal = get_signal(data.iloc[:i + 1])

        # ── BUY entry ──
        if signal == "BUY" and position is None and price > 0:
            qty = int((portfolio * 0.9) / (price * (1 + br_buy)))
            if qty > 0:
                cost_basis = qty * price * (1 + br_buy)
                portfolio -= cost_basis
                position = {
                    "entry_price": price,
                    "quantity":    qty,
                    "cost_basis":  cost_basis,
                    "entry_bar":   current_bar,
                }

        # ── SELL exit ──
        elif signal == "SELL" and position is not None:
            proceeds  = position["quantity"] * price * (1 - br_sell - stt)
            pnl       = proceeds - position["cost_basis"]
            portfolio += proceeds
            trades.append({"pnl": round(pnl, 2), "exit_reason": "signal",
                           "date": str(current_bar)})
            position = None

    # Force-close open position at last bar
    if position is not None:
        last_price = float(close.iloc[-1])
        proceeds   = position["quantity"] * last_price * (1 - br_sell - stt)
        pnl        = proceeds - position["cost_basis"]
        portfolio += proceeds
        trades.append({"pnl": round(pnl, 2), "exit_reason": "end",
                       "date": str(data.index[-1])})

    # ── Metrics ──
    pnls   = [t["pnl"] for t in trades]
    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    total_return = (portfolio - initial_capital) / initial_capital * 100
    avg_win      = sum(wins) / len(wins) if wins else 0
    avg_loss     = sum(losses) / len(losses) if losses else 0
    profit_factor = abs(sum(wins) / sum(losses)) if losses else float("inf")

    sharpe = 0.0
    if len(bar_values) > 1:
        rets = pd.Series(bar_values).pct_change().dropna()
        if rets.std() > 0:
            annual_factor = (252 * cfg["bars_per_day"]) ** 0.5
            sharpe = rets.mean() / rets.std() * annual_factor

    return {
        "tf":             tf,
        "label":          cfg["label"],
        "note":           cfg["note"],
        "total_return":   round(total_return, 2),
        "sharpe":         round(sharpe, 2),
        "max_drawdown":   round(_max_drawdown(bar_values) * 100, 2),
        "win_rate":       round(len(wins) / max(len(pnls), 1) * 100, 1),
        "total_trades":   len(pnls),
        "avg_win":        round(avg_win, 0),
        "avg_loss":       round(avg_loss, 0),
        "profit_factor":  round(profit_factor, 2),
        "final_capital":  round(portfolio, 2),
        "total_pnl":      round(sum(pnls), 2),
    }


def _max_drawdown(values: list) -> float:
    if not values:
        return 0.0
    peak, max_dd = values[0], 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    return max_dd


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(ticker: str, results: list[dict]):
    name = ticker.replace(".NS", "")
    print(f"\n{'='*92}")
    print(f"  MULTI-TIMEFRAME BACKTEST — {name} (NSE)")
    print(f"  Market hours: 9:15 AM – 3:30 PM IST | Intraday square-off: 3:15 PM")
    print(f"{'='*92}")
    print(f"  {'Timeframe':<28} {'Return':>8} {'Sharpe':>7} {'MaxDD':>7} "
          f"{'WinRate':>8} {'Trades':>7} {'PF':>6}")
    print(f"  {'-'*82}")

    best_tf    = None
    best_score = -999

    for r in results:
        if "error" in r:
            print(f"  {r['label']:<28}  ERROR — {r['error']}")
            continue

        flag  = " ✓" if r["total_return"] > 0 and r["win_rate"] > 50 else ""
        pf    = f"{r['profit_factor']:>5.2f}" if r['profit_factor'] != float('inf') else "  INF"

        print(
            f"  {r['label']:<28} "
            f"{r['total_return']:>+7.1f}% "
            f"{r['sharpe']:>6.2f}  "
            f"{r['max_drawdown']:>6.1f}%  "
            f"{r['win_rate']:>6.1f}%  "
            f"{r['total_trades']:>6}  "
            f"{pf}{flag}"
        )

        score = r["total_return"] + (r["win_rate"] - 50) * 0.5 - r["max_drawdown"] * 0.3
        if score > best_score:
            best_score = score
            best_tf    = r

    print(f"  {'='*82}")

    if best_tf and "error" not in best_tf:
        print(f"\n  BEST TIMEFRAME : {best_tf['label']}")
        print(f"  Return         : {best_tf['total_return']:+.1f}%")
        print(f"  Win Rate       : {best_tf['win_rate']:.1f}%  |  Profit Factor: {best_tf['profit_factor']:.2f}")
        print(f"  Max Drawdown   : {best_tf['max_drawdown']:.1f}%")
        print(f"  Avg Win/Loss   : ₹{best_tf['avg_win']:+,.0f} / ₹{best_tf['avg_loss']:+,.0f}")
        print(f"  Note           : {best_tf['note']}")

    print()
    print("  INTRADAY RULES:")
    print("  • 15min / 1H / 4H — positions auto close at 3:15 PM (no overnight hold)")
    print("  • Daily — positional, can hold overnight")
    print("  • SHORT selling: use /short command in live bot (intraday only)")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args      = sys.argv[1:]
    ticker    = "RELIANCE.NS"
    run_all   = "--all" in args
    single_tf = None

    for i, a in enumerate(args):
        if a == "--ticker" and i + 1 < len(args):
            t = args[i + 1].upper()
            ticker = t if t.endswith(".NS") else t + ".NS"
        if a == "--tf" and i + 1 < len(args):
            single_tf = args[i + 1].lower()

    timeframes = ([single_tf] if single_tf and single_tf in TF_CONFIG
                  else list(TF_CONFIG.keys()))
    tickers    = config.WATCHLIST[:5] if run_all else [ticker]

    for t in tickers:
        print(f"\nFetching data for {t}...")
        results = []
        for tf in timeframes:
            label = TF_CONFIG[tf]["label"]
            print(f"  [{tf}] {label}...", end=" ", flush=True)
            r = backtest_tf(t, tf)
            results.append(r)
            if "error" in r:
                print(f"error — {r['error']}")
            else:
                print(f"done  ({r['total_trades']} trades, {r['total_return']:+.1f}%)")
        print_report(t, results)


if __name__ == "__main__":
    main()
