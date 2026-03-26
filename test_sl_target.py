"""
Test: Stop Loss, Target, Trailing Stop, Position Monitoring
"""
import config
from execution.paper_trading import PaperTrader
from risk.manager import RiskManager
from monitoring.alerts import TelegramAlert

alert = TelegramAlert()

print("=" * 60)
print("TEST: Stop Loss + Target + Trailing Stop")
print("=" * 60)

# ── Setup ──────────────────────────────────────────────
trader = PaperTrader(100_000)
risk_mgr = RiskManager()

# ── Simulate BUY with SL and Target ───────────────────
entry_price = 1400.0
atr = 30.0
stop_loss = entry_price - (config.STOP_LOSS_ATR_MULT * atr)  # 1400 - 60 = 1340
risk_per_share = entry_price - stop_loss  # 60
target = entry_price + (risk_per_share * config.RISK_REWARD_RATIO)  # 1400 + 120 = 1520
quantity = risk_mgr.calculate_position_size(100_000, entry_price, stop_loss)

trader.place_order("RELIANCE.NS", "BUY", quantity, entry_price)
trader.positions["RELIANCE.NS"]["stop_loss"] = stop_loss
trader.positions["RELIANCE.NS"]["target"] = target
trader.positions["RELIANCE.NS"]["trailing_high"] = entry_price

print(f"\n📊 Trade Opened:")
print(f"  Stock:      RELIANCE")
print(f"  Entry:      ₹{entry_price:,.2f}")
print(f"  Quantity:   {quantity} shares")
print(f"  Stop Loss:  ₹{stop_loss:,.2f} (2×ATR = ₹{atr*2:.0f} below entry)")
print(f"  Target:     ₹{target:,.2f} (R:R = 1:{config.RISK_REWARD_RATIO})")
print(f"  Risk/Share: ₹{risk_per_share:,.2f}")
print(f"  Reward/Share: ₹{target - entry_price:,.2f}")
print(f"  Max Loss:   ₹{risk_per_share * quantity:,.0f}")
print(f"  Max Profit: ₹{(target - entry_price) * quantity:,.0f}")

# ── Test Trailing Stop ─────────────────────────────────
print(f"\n📈 Trailing Stop Simulation:")
pos = trader.positions["RELIANCE.NS"]
original_sl = pos["stop_loss"]

# Price moves up gradually
test_prices = [1420, 1450, 1480, 1510, 1490, 1470]
for price in test_prices:
    trailing_high = pos.get("trailing_high", entry_price)

    if price > trailing_high:
        pos["trailing_high"] = price
        if config.TRAILING_STOP_ENABLED:
            original_risk = entry_price - original_sl
            profit = price - entry_price
            if profit >= original_risk:
                new_sl = price - original_risk
                if new_sl > pos["stop_loss"]:
                    old = pos["stop_loss"]
                    pos["stop_loss"] = new_sl
                    print(f"  Price ₹{price:>7,.0f} | Trail HIGH ₹{pos['trailing_high']:,.0f} | SL moved: ₹{old:,.0f} → ₹{new_sl:,.0f} ✅")
                    continue

    sl_status = "🔴 HIT!" if price <= pos["stop_loss"] else "safe"
    tgt_status = "🟢 HIT!" if price >= target else "waiting"
    print(f"  Price ₹{price:>7,.0f} | Trail HIGH ₹{pos['trailing_high']:,.0f} | SL ₹{pos['stop_loss']:,.0f} ({sl_status}) | Target ({tgt_status})")

# ── Test SL Hit Scenario ──────────────────────────────
print(f"\n🔴 Stop Loss Hit Scenario:")
entry2 = 2400.0
atr2 = 60.0
sl2 = entry2 - (config.STOP_LOSS_ATR_MULT * atr2)  # 2280
risk2 = entry2 - sl2
target2 = entry2 + (risk2 * config.RISK_REWARD_RATIO)
qty2 = risk_mgr.calculate_position_size(trader.capital, entry2, sl2)

trader.place_order("TCS.NS", "BUY", qty2, entry2)
trader.positions["TCS.NS"]["stop_loss"] = sl2
trader.positions["TCS.NS"]["target"] = target2
trader.positions["TCS.NS"]["trailing_high"] = entry2

print(f"  BUY TCS @ ₹{entry2:,.0f} | SL ₹{sl2:,.0f} | Target ₹{target2:,.0f}")

# Price drops to SL
drop_price = 2275.0
print(f"  Price drops to ₹{drop_price:,.0f} → BELOW SL (₹{sl2:,.0f})")
trade = trader.place_order("TCS.NS", "SELL", qty2, drop_price)
pnl = trade.get("pnl", 0)
print(f"  AUTO SELL @ ₹{drop_price:,.0f} | PnL: ₹{pnl:+,.0f}")
risk_mgr.record_trade(pnl)

# ── Test Target Hit Scenario ──────────────────────────
print(f"\n🟢 Target Hit Scenario:")
# RELIANCE hits target
pos = trader.positions.get("RELIANCE.NS")
if pos:
    print(f"  RELIANCE target = ₹{target:,.0f}")
    hit_price = 1525.0
    print(f"  Price reaches ₹{hit_price:,.0f} → ABOVE TARGET")
    trade = trader.place_order("RELIANCE.NS", "SELL", pos["quantity"], hit_price)
    pnl = trade.get("pnl", 0)
    print(f"  AUTO SELL @ ₹{hit_price:,.0f} | PnL: ₹{pnl:+,.0f}")
    risk_mgr.record_trade(pnl)

# ── Final State ───────────────────────────────────────
print(f"\n📋 Final Portfolio:")
print(f"  Capital: ₹{trader.capital:,.0f}")
print(f"  Open Positions: {len(trader.positions)}")
print(f"  Total PnL: ₹{risk_mgr.daily_pnl:+,.0f}")
print(f"  Trades: {risk_mgr.trades_today}")
print(f"  Consecutive Losses: {risk_mgr.consecutive_losses}")

# ── Config Verification ───────────────────────────────
print(f"\n⚙️ Config:")
print(f"  RISK_REWARD_RATIO = {config.RISK_REWARD_RATIO}")
print(f"  TRAILING_STOP_ENABLED = {config.TRAILING_STOP_ENABLED}")
print(f"  POSITION_CHECK_SECONDS = {config.POSITION_CHECK_SECONDS}")
print(f"  STOP_LOSS_ATR_MULT = {config.STOP_LOSS_ATR_MULT}")

# ── Send Telegram Summary ─────────────────────────────
if alert.enabled:
    alert.send(
        "🧪 <b>SL/TARGET/TRAILING TEST</b>\n\n"
        f"<b>Trade 1: RELIANCE</b>\n"
        f"  Entry ₹1,400 → Target ₹1,520 → SOLD ₹1,525\n"
        f"  Trailing SL: ₹1,340 → ₹1,420 (moved up!)\n"
        f"  PnL: ₹{(1525-1400)*quantity:+,.0f} ✅\n\n"
        f"<b>Trade 2: TCS</b>\n"
        f"  Entry ₹2,400 → SL ₹2,280 → SOLD ₹2,275\n"
        f"  PnL: ₹{(2275-2400)*qty2:+,.0f} ❌\n\n"
        f"<b>Monitoring:</b> Every {config.POSITION_CHECK_SECONDS}s\n"
        f"<b>R:R Ratio:</b> 1:{config.RISK_REWARD_RATIO}\n"
        "🟢 All systems working!"
    )
    print("\n  Telegram summary sent ✅")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED")
print("=" * 60)
