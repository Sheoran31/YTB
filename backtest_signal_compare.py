"""
Backtest: OLD signals (SMA only) vs NEW signals (EMA + MACD + ADX + Crossover)
Compares accuracy, win rate, PnL on 10 Nifty 50 stocks over 2 years.
"""
import sys
import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np

# ── Config ──
CAPITAL = 100_000
RISK_PCT = 0.01
ATR_PERIOD = 14
ATR_MULT = 2.0
SMA_FAST = 20
SMA_SLOW = 50
RSI_PERIOD = 14
RSI_BUY = 55
RSI_SELL = 45
VOLUME_MIN = 1.5

# Correct STT costs (delivery)
COST_BUY_PCT = 0.00118   # STT(0.1%) + stamp(0.015%) + exchange(0.003%)
COST_SELL_PCT = 0.00103   # STT(0.1%) + exchange(0.003%)
DP_PER_SELL = 15.93

STOCKS = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "TCS.NS",
    "INFY.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "AXISBANK.NS",
]


# ── Indicators ──
def calc_sma(s, p): return s.rolling(p).mean()
def calc_ema(s, p): return s.ewm(span=p, adjust=False).mean()

def calc_rsi(s, p=14):
    d = s.diff(); g = d.where(d > 0, 0.0); l = (-d).where(d < 0, 0.0)
    return 100 - (100 / (1 + g.rolling(p).mean() / l.rolling(p).mean().replace(0, 1e-10)))

def calc_atr(h, l, c, p=14):
    tr = pd.concat([h-l, (h-c.shift(1)).abs(), (l-c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(p).mean()

def calc_vol_ratio(v, p=20): return v / v.rolling(p).mean()

def calc_macd(s, f=12, sl=26, sg=9):
    ml = s.ewm(span=f, adjust=False).mean() - s.ewm(span=sl, adjust=False).mean()
    return ml, ml.ewm(span=sg, adjust=False).mean(), ml - ml.ewm(span=sg, adjust=False).mean()

def calc_adx(h, l, c, p=14):
    pdm = h.diff(); mdm = -l.diff()
    pdm = pdm.where((pdm > 0) & (pdm > mdm), 0.0)
    mdm = mdm.where((mdm > 0) & (mdm > pdm), 0.0)
    atr = calc_atr(h, l, c, p)
    pdi = 100 * (pdm.ewm(span=p, adjust=False).mean() / atr)
    mdi = 100 * (mdm.ewm(span=p, adjust=False).mean() / atr)
    dx = 100 * ((pdi - mdi).abs() / (pdi + mdi).replace(0, 1))
    return dx.ewm(span=p, adjust=False).mean()

def detect_cross(fast, slow):
    pf, ps = fast.shift(1), slow.shift(1)
    sig = pd.Series(0, index=fast.index)
    sig[(pf <= ps) & (fast > slow)] = 1
    sig[(pf >= ps) & (fast < slow)] = -1
    return sig


# ── OLD Signal (SMA only) ──
def old_signal(df):
    df = df.copy()
    c = df["Close"]; v = df["Volume"]
    sf = calc_sma(c, SMA_FAST); ss = calc_sma(c, SMA_SLOW)
    rsi = calc_rsi(c, RSI_PERIOD); vr = calc_vol_ratio(v)
    df["signal"] = "HOLD"
    df.loc[(sf > ss) & (rsi > RSI_BUY) & (vr > VOLUME_MIN), "signal"] = "BUY"
    df.loc[(c < sf) | (rsi < RSI_SELL), "signal"] = "SELL"
    return df


# ── NEW Signal (EMA + MACD + ADX + Crossover) ──
def new_signal(df):
    df = df.copy()
    c = df["Close"]; h = df["High"]; l = df["Low"]; v = df["Volume"]
    ef = calc_ema(c, SMA_FAST); es = calc_ema(c, SMA_SLOW)
    rsi = calc_rsi(c, RSI_PERIOD); vr = calc_vol_ratio(v)
    _, _, mhist = calc_macd(c)
    adx = calc_adx(h, l, c)
    cross = detect_cross(ef, es)

    df["signal"] = "HOLD"

    for i in range(SMA_SLOW + 1, len(df)):
        r = rsi.iloc[i]; vo = vr.iloc[i]; mh = mhist.iloc[i]; ax = adx.iloc[i]
        if pd.isna(r) or pd.isna(mh) or pd.isna(ax):
            continue

        # BUY: recent crossover (3 days) OR uptrend, + MACD + RSI + Volume + ADX
        recent_cross = cross.iloc[max(0, i-2):i+1].max() >= 1
        uptrend = ef.iloc[i] > es.iloc[i]

        if (recent_cross or uptrend) and mh > 0 and r > RSI_BUY and vo > VOLUME_MIN and ax > 20:
            df.iloc[i, df.columns.get_loc("signal")] = "BUY"
            continue

        # SELL: price below EMA + (RSI weak OR MACD bearish)
        # Protective: exits before SL hits
        below_ema = c.iloc[i] < ef.iloc[i]
        rsi_weak = r < RSI_SELL
        macd_bear = mh < 0

        if below_ema and (rsi_weak or macd_bear):
            df.iloc[i, df.columns.get_loc("signal")] = "SELL"

    return df


# ── Backtest Engine (with correct costs) ──
def backtest(df, capital=CAPITAL):
    trades = []
    pos = None
    cash = capital

    for i in range(SMA_SLOW + 1, len(df)):
        row = df.iloc[i]
        price = row["Close"]; atr_val = calc_atr(df["High"], df["Low"], df["Close"]).iloc[i]
        if pd.isna(atr_val) or atr_val <= 0: continue

        if pos:
            if price <= pos["sl"]:
                sell_val = pos["qty"] * price
                cost = sell_val * COST_SELL_PCT + DP_PER_SELL
                pnl = sell_val - cost - pos["cost"]
                trades.append({"pnl": pnl, "type": "SL", "days": i - pos["day"]})
                cash += sell_val - cost; pos = None
            elif price >= pos["target"]:
                sell_val = pos["qty"] * price
                cost = sell_val * COST_SELL_PCT + DP_PER_SELL
                pnl = sell_val - cost - pos["cost"]
                trades.append({"pnl": pnl, "type": "TARGET", "days": i - pos["day"]})
                cash += sell_val - cost; pos = None
            elif row["signal"] == "SELL":
                sell_val = pos["qty"] * price
                cost = sell_val * COST_SELL_PCT + DP_PER_SELL
                pnl = sell_val - cost - pos["cost"]
                trades.append({"pnl": pnl, "type": "SIGNAL", "days": i - pos["day"]})
                cash += sell_val - cost; pos = None

        elif row["signal"] == "BUY" and not pos:
            sl = price - (ATR_MULT * atr_val)
            rps = price - sl
            if rps <= 0: continue
            target = price + rps * 2.0
            risk_amt = min(cash * RISK_PCT, 1000)
            qty = int(risk_amt / rps)
            if qty <= 0: continue
            buy_cost = qty * price * (1 + COST_BUY_PCT)
            if buy_cost > cash: continue
            cash -= buy_cost
            pos = {"entry": price, "qty": qty, "sl": sl, "target": target, "cost": buy_cost, "day": i}

    if pos:
        price = df.iloc[-1]["Close"]
        sell_val = pos["qty"] * price
        cost = sell_val * COST_SELL_PCT + DP_PER_SELL
        pnl = sell_val - cost - pos["cost"]
        trades.append({"pnl": pnl, "type": "FORCE", "days": len(df) - pos["day"]})
        cash += sell_val - cost

    return trades, cash


def analyze(trades, label):
    if not trades:
        return {"label": label, "trades": 0, "pnl": 0, "win_rate": 0, "avg_rr": 0}
    df = pd.DataFrame(trades)
    wins = df[df["pnl"] > 0]; losses = df[df["pnl"] <= 0]
    aw = wins["pnl"].mean() if len(wins) else 0
    al = losses["pnl"].mean() if len(losses) else 0
    return {
        "label": label, "trades": len(df), "wins": len(wins), "losses": len(losses),
        "win_rate": len(wins)/len(df)*100, "pnl": df["pnl"].sum(),
        "avg_win": aw, "avg_loss": al, "rr": abs(aw/al) if al else 0,
        "types": df["type"].value_counts().to_dict(),
    }


def main():
    print("=" * 60)
    print("  SIGNAL ACCURACY: OLD (SMA) vs NEW (EMA+MACD+ADX)")
    print("  Costs: Correct Dhan delivery STT (0.1% each side)")
    print("=" * 60)

    all_old, all_new = [], []

    for sym in STOCKS:
        name = sym.replace(".NS", "")
        sys.stdout.write(f"  {name:15s} ... "); sys.stdout.flush()
        try:
            data = yf.download(sym, period="2y", progress=False)
            if data.empty or len(data) < SMA_SLOW + 20:
                print("SKIP"); continue
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            df_old = old_signal(data)
            df_new = new_signal(data)

            t_old, _ = backtest(df_old)
            t_new, _ = backtest(df_new)

            po = sum(t["pnl"] for t in t_old)
            pn = sum(t["pnl"] for t in t_new)
            wo = sum(1 for t in t_old if t["pnl"] > 0) / max(len(t_old), 1) * 100
            wn = sum(1 for t in t_new if t["pnl"] > 0) / max(len(t_new), 1) * 100

            better = "NEW" if pn > po else "OLD"
            print(f"OLD: {len(t_old):2d} trades ₹{po:>7,.0f} ({wo:.0f}%) | "
                  f"NEW: {len(t_new):2d} trades ₹{pn:>7,.0f} ({wn:.0f}%) | {better}")

            all_old.extend(t_old); all_new.extend(t_new)
        except Exception as e:
            print(f"ERROR: {e}")

    ro = analyze(all_old, "OLD (SMA + RSI + Volume)")
    rn = analyze(all_new, "NEW (EMA + MACD + ADX + Crossover)")

    for r in [ro, rn]:
        print(f"\n{'='*60}")
        print(f"  {r['label']}")
        print(f"{'='*60}")
        print(f"  Trades: {r['trades']} | Wins: {r.get('wins',0)} | Losses: {r.get('losses',0)}")
        print(f"  Win Rate: {r['win_rate']:.1f}%")
        print(f"  Total PnL: ₹{r['pnl']:,.0f}")
        print(f"  Avg Win: ₹{r.get('avg_win',0):,.0f} | Avg Loss: ₹{r.get('avg_loss',0):,.0f}")
        print(f"  Actual R:R: 1:{r.get('rr',0):.2f}")
        print(f"  Exit Types: {r.get('types', {})}")

    print(f"\n{'='*60}")
    print(f"  VERDICT")
    print(f"{'='*60}")
    if rn["pnl"] > ro["pnl"]:
        diff = rn["pnl"] - ro["pnl"]
        print(f"  NEW signals WIN by ₹{diff:,.0f}")
        print(f"  Win rate: {ro['win_rate']:.1f}% → {rn['win_rate']:.1f}%")
    else:
        diff = ro["pnl"] - rn["pnl"]
        print(f"  OLD signals WIN by ₹{diff:,.0f}")
    print(f"  (With correct STT costs — results are realistic)")


if __name__ == "__main__":
    main()
