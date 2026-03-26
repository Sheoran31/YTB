"""
Test: Multiple trades — how quantity is calculated for each trade
when previous trades are still running.
"""
import config
from execution.paper_trading import PaperTrader
from risk.manager import RiskManager
from monitoring.alerts import TelegramAlert

alert = TelegramAlert()
trader = PaperTrader(100_000)
risk_mgr = RiskManager()

trades = [
    {"ticker": "RELIANCE.NS", "price": 1400, "atr": 30},
    {"ticker": "TCS.NS",      "price": 2400, "atr": 60},
    {"ticker": "HDFCBANK.NS", "price": 780,  "atr": 27},
    {"ticker": "INFY.NS",     "price": 1280, "atr": 36},
    {"ticker": "SBIN.NS",     "price": 1060, "atr": 35},
]

# Simulate current prices (some stocks moved after entry)
live_prices = {
    "RELIANCE.NS": 1430,  # up ₹30
    "TCS.NS": 2380,       # down ₹20
    "HDFCBANK.NS": 795,   # up ₹15
    "INFY.NS": 1290,      # up ₹10
    "SBIN.NS": 1050,      # down ₹10
}

print("=" * 70)
print("MULTI-TRADE POSITION SIZING — How Each Trade Is Calculated")
print("=" * 70)
print(f"\nStarting Capital: ₹{trader.capital:,.0f}")
print(f"Max Position Size: {config.MAX_POSITION_PCT*100}% of portfolio")
print(f"Risk Per Trade: {config.RISK_PER_TRADE_PCT*100}% (capped at ₹{config.MAX_LOSS_PER_TRADE:,})")
print(f"R:R Ratio: 1:{config.RISK_REWARD_RATIO}")

msg = "📊 <b>MULTI-TRADE TEST — 5 Consecutive Trades</b>\n\n"

for i, t in enumerate(trades, 1):
    ticker = t["ticker"]
    price = t["price"]
    atr = t["atr"]
    symbol = ticker.replace(".NS", "")

    # Calculate using CURRENT prices for portfolio value
    portfolio_value = trader.get_portfolio_value(live_prices)

    # Stop loss & target
    stop_loss = price - (config.STOP_LOSS_ATR_MULT * atr)
    risk_per_share = price - stop_loss
    target = price + (risk_per_share * config.RISK_REWARD_RATIO)

    # Risk-based quantity
    risk_amount = portfolio_value * config.RISK_PER_TRADE_PCT
    if risk_amount > config.MAX_LOSS_PER_TRADE:
        risk_amount = config.MAX_LOSS_PER_TRADE
    qty_by_risk = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0

    # Cap by max position size (5%)
    max_pos_value = portfolio_value * config.MAX_POSITION_PCT
    qty_by_size = int(max_pos_value / price)

    # Cap by available cash
    qty_by_cash = int(trader.capital / price)

    # Final quantity = minimum of all caps
    quantity = min(qty_by_risk, qty_by_size, qty_by_cash)
    if quantity <= 0:
        quantity = 0

    # Limiting factor
    if quantity == 0:
        limiter = "NO CASH"
    elif quantity == qty_by_cash and qty_by_cash < qty_by_risk and qty_by_cash < qty_by_size:
        limiter = "CASH LIMIT"
    elif quantity == qty_by_size and qty_by_size < qty_by_risk:
        limiter = "5% SIZE CAP"
    else:
        limiter = "RISK-BASED"

    # Position count check
    if len(trader.positions) >= config.MAX_TOTAL_POSITIONS:
        print(f"\n{'─'*70}")
        print(f"Trade {i}: {symbol} @ ₹{price:,.0f} — ❌ BLOCKED (max 5 positions)")
        msg += f"<b>Trade {i}: {symbol}</b> — ❌ BLOCKED (max positions)\n\n"
        continue

    print(f"\n{'─'*70}")
    print(f"Trade {i}: BUY {symbol} @ ₹{price:,.0f}")
    print(f"{'─'*70}")
    print(f"  Portfolio Value:    ₹{portfolio_value:,.0f} (cash ₹{trader.capital:,.0f} + positions)")
    print(f"  ATR:                ₹{atr}")
    print(f"  Stop Loss:          ₹{stop_loss:,.0f} (entry - {config.STOP_LOSS_ATR_MULT}×ATR)")
    print(f"  Target:             ₹{target:,.0f} (entry + risk × {config.RISK_REWARD_RATIO})")
    print(f"  Risk/Share:         ₹{risk_per_share:,.0f}")
    print(f"  ")
    print(f"  Qty by RISK (1%):   {qty_by_risk} shares (₹{risk_amount:,.0f} / ₹{risk_per_share:,.0f})")
    print(f"  Qty by SIZE (5%):   {qty_by_size} shares (₹{max_pos_value:,.0f} / ₹{price:,.0f})")
    print(f"  Qty by CASH:        {qty_by_cash} shares (₹{trader.capital:,.0f} / ₹{price:,.0f})")
    print(f"  ")
    print(f"  ➜ FINAL QTY:        {quantity} shares ({limiter})")
    print(f"  ➜ Position Value:   ₹{quantity * price:,.0f} ({quantity * price / portfolio_value * 100:.1f}% of portfolio)")
    print(f"  ➜ Max Loss if SL:   ₹{quantity * risk_per_share:,.0f} ({quantity * risk_per_share / portfolio_value * 100:.1f}%)")
    print(f"  ➜ Max Profit if TG: ₹{quantity * (target - price):,.0f}")

    if quantity > 0:
        trader.place_order(ticker, "BUY", quantity, price)
        trader.positions[ticker]["stop_loss"] = stop_loss
        trader.positions[ticker]["target"] = target
        print(f"  ➜ Cash After:       ₹{trader.capital:,.0f}")

    msg += (
        f"<b>Trade {i}: {symbol} @ ₹{price:,.0f}</b>\n"
        f"  Qty: {quantity} | SL: ₹{stop_loss:,.0f} | TG: ₹{target:,.0f}\n"
        f"  Value: ₹{quantity*price:,.0f} | Limiter: {limiter}\n"
        f"  Cash left: ₹{trader.capital:,.0f}\n\n"
    )

# ── Final Portfolio ────────────────────────────────────
print(f"\n{'='*70}")
print(f"FINAL PORTFOLIO STATE")
print(f"{'='*70}")
portfolio_value = trader.get_portfolio_value(live_prices)
print(f"  Cash:            ₹{trader.capital:,.0f}")
print(f"  Positions:       {len(trader.positions)}")
for sym, pos in trader.positions.items():
    lp = live_prices.get(sym, pos["entry_price"])
    unrealized = (lp - pos["entry_price"]) * pos["quantity"]
    print(f"    {sym.replace('.NS',''):12s}  {pos['quantity']:>3} × ₹{pos['entry_price']:,.0f}  "
          f"Now ₹{lp:,.0f}  PnL: ₹{unrealized:+,.0f}  "
          f"SL: ₹{pos.get('stop_loss',0):,.0f}  TG: ₹{pos.get('target',0):,.0f}")
print(f"  Portfolio Value: ₹{portfolio_value:,.0f}")
print(f"  Unrealized PnL:  ₹{portfolio_value - 100_000:+,.0f}")

msg += (
    f"<b>Final:</b>\n"
    f"  Cash: ₹{trader.capital:,.0f}\n"
    f"  Portfolio: ₹{portfolio_value:,.0f}\n"
    f"  Positions: {len(trader.positions)}/5\n"
)

if alert.enabled:
    alert.send(msg)
    print(f"\n  Telegram report sent ✅")
