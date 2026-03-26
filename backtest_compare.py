"""
Backtest Comparison: Current Full-Exit vs Proposed Half-Book + Trail-to-Cost

Strategy A (CURRENT):  100% exit at SL or 100% exit at Target
Strategy B (PROPOSED): 50% exit at Target-1 (1:1 R:R), move SL to cost for remaining 50%,
                       remaining 50% exits at Target-2 (1:2 R:R) or trailing SL

Runs on top 10 liquid Nifty 50 stocks, 2-year data, prints comparison.
"""
import sys
import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ── Config ────────────────────────────────────────────────
CAPITAL = 100_000
RISK_PCT = 0.01          # 1% risk per trade
ATR_PERIOD = 14
ATR_MULT = 2.0           # SL = entry - 2*ATR
SMA_FAST = 20
SMA_SLOW = 50
RSI_PERIOD = 14
RSI_BUY = 55
RSI_SELL = 45
VOLUME_MIN = 1.5
BROKERAGE = 0.0003       # 0.03%
STT = 0.001              # 0.1% on sell

STOCKS = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "TCS.NS",
    "INFY.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "AXISBANK.NS",
]


# ── Indicators ────────────────────────────────────────────
def calc_sma(series, period):
    return series.rolling(window=period).mean()

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calc_volume_ratio(volume, period=20):
    return volume / volume.rolling(window=period).mean()


# ── Signal Generator ──────────────────────────────────────
def generate_signals(df):
    """Add BUY/SELL signals to dataframe."""
    df = df.copy()
    df["sma_fast"] = calc_sma(df["Close"], SMA_FAST)
    df["sma_slow"] = calc_sma(df["Close"], SMA_SLOW)
    df["rsi"] = calc_rsi(df["Close"], RSI_PERIOD)
    df["atr"] = calc_atr(df["High"], df["Low"], df["Close"], ATR_PERIOD)
    df["vol_ratio"] = calc_volume_ratio(df["Volume"])

    df["signal"] = "HOLD"

    buy_mask = (
        (df["sma_fast"] > df["sma_slow"]) &
        (df["rsi"] > RSI_BUY) &
        (df["vol_ratio"] > VOLUME_MIN)
    )
    sell_mask = (df["Close"] < df["sma_fast"]) | (df["rsi"] < RSI_SELL)

    df.loc[buy_mask, "signal"] = "BUY"
    df.loc[sell_mask, "signal"] = "SELL"

    return df


# ── Strategy A: Current (Full Exit) ──────────────────────
def backtest_full_exit(df, capital=CAPITAL):
    """100% exit at SL or 100% exit at Target (1:2 R:R)."""
    trades = []
    position = None
    cash = capital

    for i in range(SMA_SLOW + 1, len(df)):
        row = df.iloc[i]
        price = row["Close"]
        atr = row["atr"]

        if pd.isna(atr) or atr <= 0:
            continue

        # ── Check open position ──
        if position:
            # SL hit
            if price <= position["stop_loss"]:
                sell_value = position["qty"] * price
                cost = sell_value * (BROKERAGE + STT)
                pnl = sell_value - cost - position["cost"]
                trades.append({
                    "entry": position["entry"], "exit": price,
                    "qty": position["qty"], "pnl": pnl,
                    "type": "SL_HIT", "days": i - position["day"],
                })
                cash += sell_value - cost
                position = None

            # Target hit
            elif price >= position["target"]:
                sell_value = position["qty"] * price
                cost = sell_value * (BROKERAGE + STT)
                pnl = sell_value - cost - position["cost"]
                trades.append({
                    "entry": position["entry"], "exit": price,
                    "qty": position["qty"], "pnl": pnl,
                    "type": "TARGET_HIT", "days": i - position["day"],
                })
                cash += sell_value - cost
                position = None

            # Signal-based sell
            elif row["signal"] == "SELL":
                sell_value = position["qty"] * price
                cost = sell_value * (BROKERAGE + STT)
                pnl = sell_value - cost - position["cost"]
                trades.append({
                    "entry": position["entry"], "exit": price,
                    "qty": position["qty"], "pnl": pnl,
                    "type": "SIGNAL_SELL", "days": i - position["day"],
                })
                cash += sell_value - cost
                position = None

        # ── Open new position ──
        elif row["signal"] == "BUY" and not position:
            stop_loss = price - (ATR_MULT * atr)
            risk_per_share = price - stop_loss
            if risk_per_share <= 0:
                continue
            target = price + (risk_per_share * 2.0)  # 1:2 R:R

            risk_amount = min(cash * RISK_PCT, 1000)
            qty = int(risk_amount / risk_per_share)
            if qty <= 0:
                continue

            buy_cost = qty * price * (1 + BROKERAGE)
            if buy_cost > cash:
                continue

            cash -= buy_cost
            position = {
                "entry": price, "qty": qty, "stop_loss": stop_loss,
                "target": target, "cost": buy_cost, "day": i,
            }

    # Force close if still holding
    if position:
        price = df.iloc[-1]["Close"]
        sell_value = position["qty"] * price
        cost = sell_value * (BROKERAGE + STT)
        pnl = sell_value - cost - position["cost"]
        trades.append({
            "entry": position["entry"], "exit": price,
            "qty": position["qty"], "pnl": pnl,
            "type": "FORCE_CLOSE", "days": len(df) - position["day"],
        })
        cash += sell_value - cost

    return trades, cash


# ── Strategy B: Half-Book + Trail to Cost ─────────────────
def backtest_half_book(df, capital=CAPITAL):
    """
    Target-1 (1:1 R:R) → book 50% qty, move SL to cost (breakeven).
    Target-2 (1:2 R:R) → book remaining 50% OR trailing SL hits.
    """
    trades = []
    position = None
    cash = capital

    for i in range(SMA_SLOW + 1, len(df)):
        row = df.iloc[i]
        price = row["Close"]
        atr = row["atr"]

        if pd.isna(atr) or atr <= 0:
            continue

        # ── Check open position ──
        if position:
            risk_per_share = position["entry"] - position["original_sl"]

            # ── Phase 1: Full position, waiting for Target-1 (1:1) ──
            if not position["half_booked"]:

                # SL hit — full loss
                if price <= position["stop_loss"]:
                    sell_value = position["qty"] * price
                    cost = sell_value * (BROKERAGE + STT)
                    pnl = sell_value - cost - position["cost"]
                    trades.append({
                        "entry": position["entry"], "exit": price,
                        "qty": position["qty"], "pnl": pnl,
                        "type": "SL_HIT_FULL", "days": i - position["day"],
                    })
                    cash += sell_value - cost
                    position = None

                # Target-1 hit (1:1 R:R) — book 50%
                elif price >= position["target_1"]:
                    half_qty = position["qty"] // 2
                    if half_qty <= 0:
                        half_qty = position["qty"]  # If qty=1, sell all

                    sell_value = half_qty * price
                    cost_sell = sell_value * (BROKERAGE + STT)
                    pnl_half = (price - position["entry"]) * half_qty - cost_sell

                    trades.append({
                        "entry": position["entry"], "exit": price,
                        "qty": half_qty, "pnl": pnl_half,
                        "type": "TARGET1_HALF", "days": i - position["day"],
                    })
                    cash += sell_value - cost_sell

                    remaining = position["qty"] - half_qty
                    if remaining <= 0:
                        position = None
                    else:
                        position["qty"] = remaining
                        position["half_booked"] = True
                        position["stop_loss"] = position["entry"]  # Move SL to cost!
                        position["trailing_high"] = price

                # Signal sell — full exit
                elif row["signal"] == "SELL":
                    sell_value = position["qty"] * price
                    cost = sell_value * (BROKERAGE + STT)
                    pnl = sell_value - cost - position["cost"]
                    trades.append({
                        "entry": position["entry"], "exit": price,
                        "qty": position["qty"], "pnl": pnl,
                        "type": "SIGNAL_SELL", "days": i - position["day"],
                    })
                    cash += sell_value - cost
                    position = None

            # ── Phase 2: Half position, trailing with SL at cost ──
            else:
                # Update trailing high
                if price > position["trailing_high"]:
                    position["trailing_high"] = price
                    # Trail SL: lock in profits as price rises
                    new_sl = price - risk_per_share
                    if new_sl > position["stop_loss"]:
                        position["stop_loss"] = new_sl

                # SL hit (at cost or trailing) — breakeven or small profit
                if price <= position["stop_loss"]:
                    sell_value = position["qty"] * price
                    cost = sell_value * (BROKERAGE + STT)
                    pnl = (price - position["entry"]) * position["qty"] - cost
                    trades.append({
                        "entry": position["entry"], "exit": price,
                        "qty": position["qty"], "pnl": pnl,
                        "type": "SL_COST_HIT", "days": i - position["day"],
                    })
                    cash += sell_value - cost
                    position = None

                # Target-2 hit (1:2 R:R) — book remaining
                elif price >= position["target_2"]:
                    sell_value = position["qty"] * price
                    cost = sell_value * (BROKERAGE + STT)
                    pnl = (price - position["entry"]) * position["qty"] - cost
                    trades.append({
                        "entry": position["entry"], "exit": price,
                        "qty": position["qty"], "pnl": pnl,
                        "type": "TARGET2_FULL", "days": i - position["day"],
                    })
                    cash += sell_value - cost
                    position = None

        # ── Open new position ──
        elif row["signal"] == "BUY" and not position:
            stop_loss = price - (ATR_MULT * atr)
            risk_per_share = price - stop_loss
            if risk_per_share <= 0:
                continue
            target_1 = price + risk_per_share          # 1:1 R:R
            target_2 = price + (risk_per_share * 2.0)  # 1:2 R:R

            risk_amount = min(cash * RISK_PCT, 1000)
            qty = int(risk_amount / risk_per_share)
            if qty <= 0:
                continue

            buy_cost = qty * price * (1 + BROKERAGE)
            if buy_cost > cash:
                continue

            cash -= buy_cost
            position = {
                "entry": price, "qty": qty,
                "stop_loss": stop_loss, "original_sl": stop_loss,
                "target_1": target_1, "target_2": target_2,
                "cost": buy_cost, "day": i,
                "half_booked": False, "trailing_high": price,
            }

    # Force close remaining
    if position:
        price = df.iloc[-1]["Close"]
        sell_value = position["qty"] * price
        cost = sell_value * (BROKERAGE + STT)
        pnl = (price - position["entry"]) * position["qty"] - cost
        trades.append({
            "entry": position["entry"], "exit": price,
            "qty": position["qty"], "pnl": pnl,
            "type": "FORCE_CLOSE", "days": len(df) - position["day"],
        })
        cash += sell_value - cost

    return trades, cash


# ── Analysis ──────────────────────────────────────────────
def analyze_trades(trades, label, initial_capital=CAPITAL):
    if not trades:
        print(f"\n{'='*50}")
        print(f"  {label}: NO TRADES")
        print(f"{'='*50}")
        return {}

    df = pd.DataFrame(trades)
    total_pnl = df["pnl"].sum()
    wins = df[df["pnl"] > 0]
    losses = df[df["pnl"] <= 0]
    win_rate = len(wins) / len(df) * 100 if len(df) > 0 else 0
    avg_win = wins["pnl"].mean() if len(wins) > 0 else 0
    avg_loss = losses["pnl"].mean() if len(losses) > 0 else 0
    rr_actual = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    max_loss = df["pnl"].min()
    max_win = df["pnl"].max()
    avg_days = df["days"].mean()

    # Type breakdown
    type_counts = df["type"].value_counts().to_dict()

    return {
        "label": label,
        "total_trades": len(df),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "rr_actual": rr_actual,
        "max_win": max_win,
        "max_loss": max_loss,
        "avg_days": avg_days,
        "return_pct": (total_pnl / initial_capital) * 100,
        "type_counts": type_counts,
    }


def print_result(r):
    if not r:
        return
    print(f"\n{'='*55}")
    print(f"  {r['label']}")
    print(f"{'='*55}")
    print(f"  Total Trades:    {r['total_trades']}")
    print(f"  Wins / Losses:   {r['wins']} / {r['losses']}")
    print(f"  Win Rate:        {r['win_rate']:.1f}%")
    print(f"  Total PnL:       ₹{r['total_pnl']:,.0f}")
    print(f"  Return:          {r['return_pct']:.2f}%")
    print(f"  Avg Win:         ₹{r['avg_win']:,.0f}")
    print(f"  Avg Loss:        ₹{r['avg_loss']:,.0f}")
    print(f"  Actual R:R:      1:{r['rr_actual']:.2f}")
    print(f"  Best Trade:      ₹{r['max_win']:,.0f}")
    print(f"  Worst Trade:     ₹{r['max_loss']:,.0f}")
    print(f"  Avg Hold (days): {r['avg_days']:.1f}")
    print(f"  Exit Types:      {r['type_counts']}")


# ── Main ──────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  BACKTEST COMPARISON: Full Exit vs Half-Book + Trail")
    print("=" * 55)
    print(f"  Capital: ₹{CAPITAL:,}")
    print(f"  Risk/Trade: {RISK_PCT*100}%  |  SL: {ATR_MULT}×ATR  |  R:R: 1:2")
    print(f"  Stocks: {len(STOCKS)}")
    print(f"  Period: 2 years")
    print()

    all_a_trades = []
    all_b_trades = []

    for symbol in STOCKS:
        ticker = symbol.replace(".NS", "")
        sys.stdout.write(f"  Scanning {ticker:15s} ... ")
        sys.stdout.flush()

        try:
            data = yf.download(symbol, period="2y", progress=False)
            if data.empty or len(data) < SMA_SLOW + 20:
                print("SKIP (insufficient data)")
                continue

            # Flatten multi-level columns if needed
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            df = generate_signals(data)

            trades_a, cash_a = backtest_full_exit(df)
            trades_b, cash_b = backtest_half_book(df)

            print(f"A: {len(trades_a)} trades, ₹{sum(t['pnl'] for t in trades_a):>8,.0f}  |  "
                  f"B: {len(trades_b)} trades, ₹{sum(t['pnl'] for t in trades_b):>8,.0f}")

            all_a_trades.extend(trades_a)
            all_b_trades.extend(trades_b)

        except Exception as e:
            print(f"ERROR: {e}")

    # ── Combined Results ──
    result_a = analyze_trades(all_a_trades, "Strategy A: CURRENT (Full Exit at SL/Target)")
    result_b = analyze_trades(all_b_trades, "Strategy B: PROPOSED (Half-Book at 1:1 + Trail to Cost)")

    print_result(result_a)
    print_result(result_b)

    # ── Head-to-Head ──
    if result_a and result_b:
        print(f"\n{'='*55}")
        print(f"  HEAD-TO-HEAD COMPARISON")
        print(f"{'='*55}")
        metrics = [
            ("Win Rate",      f"{result_a['win_rate']:.1f}%",     f"{result_b['win_rate']:.1f}%"),
            ("Total PnL",     f"₹{result_a['total_pnl']:,.0f}",  f"₹{result_b['total_pnl']:,.0f}"),
            ("Return %",      f"{result_a['return_pct']:.2f}%",   f"{result_b['return_pct']:.2f}%"),
            ("Actual R:R",    f"1:{result_a['rr_actual']:.2f}",   f"1:{result_b['rr_actual']:.2f}"),
            ("Worst Trade",   f"₹{result_a['max_loss']:,.0f}",   f"₹{result_b['max_loss']:,.0f}"),
            ("Avg Hold Days", f"{result_a['avg_days']:.1f}",      f"{result_b['avg_days']:.1f}"),
        ]
        print(f"  {'Metric':<16} {'A (Current)':<18} {'B (Proposed)':<18} Winner")
        print(f"  {'-'*16} {'-'*18} {'-'*18} {'-'*8}")
        for name, va, vb in metrics:
            winner = "—"
            if name == "Worst Trade":
                winner = "A" if result_a["max_loss"] > result_b["max_loss"] else "B"
            elif name == "Win Rate":
                winner = "A" if result_a["win_rate"] > result_b["win_rate"] else "B"
            elif name == "Total PnL":
                winner = "A" if result_a["total_pnl"] > result_b["total_pnl"] else "B"
            elif name == "Return %":
                winner = "A" if result_a["return_pct"] > result_b["return_pct"] else "B"
            elif name == "Actual R:R":
                winner = "A" if result_a["rr_actual"] > result_b["rr_actual"] else "B"
            print(f"  {name:<16} {va:<18} {vb:<18} {winner}")

        # Verdict
        a_score = sum([
            result_a["win_rate"] > result_b["win_rate"],
            result_a["total_pnl"] > result_b["total_pnl"],
            result_a["rr_actual"] > result_b["rr_actual"],
            result_a["max_loss"] > result_b["max_loss"],
        ])
        b_score = 4 - a_score

        print(f"\n  VERDICT: ", end="")
        if b_score > a_score:
            print(f"Strategy B (Half-Book + Trail) WINS ({b_score}-{a_score})")
            print(f"  → Implement partial booking in trader.py")
        elif a_score > b_score:
            print(f"Strategy A (Full Exit) WINS ({a_score}-{b_score})")
            print(f"  → Current system is better, no change needed")
        else:
            print(f"TIE ({a_score}-{b_score}) — both approaches are similar")


if __name__ == "__main__":
    main()
