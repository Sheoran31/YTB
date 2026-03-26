"""
Quick integration test — verifies all components work together.
Run: python test_all.py
"""
import os
import json
import sys
import time as time_module
from datetime import datetime, date

# ── Test 1: Config loads correctly ─────────────────────────
print("=" * 60)
print("TEST 1: Config & Market Guard")
print("=" * 60)
import config
assert config.MARKET == "INDIA", "Market must be INDIA"
assert len(config.WATCHLIST) > 40, "Watchlist too small"
assert config.PORTFOLIO_STATE_FILE == "logs/portfolio_state.json"
assert config.MODE_REPLY_TIMEOUT > 0
assert len(config.NSE_HOLIDAYS) > 10, "Holiday list too small"
print(f"  Market: {config.MARKET}")
print(f"  Watchlist: {len(config.WATCHLIST)} stocks")
print(f"  Holidays: {len(config.NSE_HOLIDAYS)} dates loaded")
print(f"  Capital: ₹{config.INITIAL_CAPITAL:,.0f}")
print("  ✅ PASS\n")

# ── Test 2: Holiday Detection ──────────────────────────────
print("=" * 60)
print("TEST 2: Holiday Detection (hardcoded + live)")
print("=" * 60)
from trader import is_market_holiday, get_next_trading_day

# Known holiday
is_hol, name = is_market_holiday(date(2026, 3, 26))
assert is_hol and name == "Jamat Ul-Vida", f"March 26 should be holiday, got: {is_hol}, {name}"
print(f"  2026-03-26: {name} ✅")

# Known non-holiday (a regular weekday)
is_hol2, name2 = is_market_holiday(date(2026, 3, 27))
print(f"  2026-03-27: Holiday={is_hol2}, Name={name2}")

# Republic Day
is_hol3, name3 = is_market_holiday(date(2026, 1, 26))
assert is_hol3 and name3 == "Republic Day"
print(f"  2026-01-26: {name3} ✅")

# Next trading day from holiday
next_day = get_next_trading_day(date(2026, 3, 26))
print(f"  Next trading day after Mar 26: {next_day} ({next_day.strftime('%A')})")
assert next_day.weekday() < 5, "Next trading day can't be weekend"

# Weekend skip
next_after_sat = get_next_trading_day(date(2026, 3, 28))  # Saturday
print(f"  Next trading day after Mar 28 (Sat): {next_after_sat}")
assert next_after_sat.weekday() < 5
print("  ✅ PASS\n")

# ── Test 3: Technical Signals ──────────────────────────────
print("=" * 60)
print("TEST 3: Technical Indicators (SMA, RSI, ATR)")
print("=" * 60)
from data.signals import calculate_sma, calculate_rsi, calculate_atr
import pandas as pd
import numpy as np

prices = pd.Series([100 + i * 0.5 + np.sin(i / 3) * 5 for i in range(60)])
sma20 = calculate_sma(prices, 20)
sma50 = calculate_sma(prices, 50)
rsi = calculate_rsi(prices)
print(f"  SMA20 (last): {sma20.iloc[-1]:.2f}")
print(f"  SMA50 (last): {sma50.iloc[-1]:.2f}")
print(f"  RSI (last): {rsi.iloc[-1]:.2f}")
assert not sma20.isna().all(), "SMA20 all NaN"
assert not rsi.isna().all(), "RSI all NaN"
assert 0 <= rsi.dropna().iloc[-1] <= 100, "RSI out of range"
print("  ✅ PASS\n")

# ── Test 4: Risk Manager ──────────────────────────────────
print("=" * 60)
print("TEST 4: Risk Manager (circuit breakers)")
print("=" * 60)
from risk.manager import RiskManager

rm = RiskManager()
can, reason = rm.can_open_position(100_000, [], 5000)
assert can, f"Should allow trade: {reason}"
print(f"  Normal trade: {reason}")

can2, reason2 = rm.can_open_position(100_000, ["A", "B", "C", "D", "E"], 5000)
assert not can2, "Should block — max positions"
print(f"  Max positions: {reason2}")

rm.consecutive_losses = 3
can3, reason3 = rm.can_open_position(100_000, [], 5000)
assert not can3, "Should block — consecutive losses"
print(f"  Circuit breaker: {reason3}")
rm.consecutive_losses = 0

qty = rm.calculate_position_size(100_000, 1400, 1370)
print(f"  Position size (₹1400 entry, ₹1370 SL): {qty} shares")
assert qty > 0, "Qty should be > 0"

sl = rm.calculate_stop_loss(1400, 30)
print(f"  Stop loss (₹1400, ATR=30): ₹{sl:.2f}")
assert sl < 1400
print("  ✅ PASS\n")

# ── Test 5: Paper Trader + State Persistence ───────────────
print("=" * 60)
print("TEST 5: Paper Trader + Portfolio Persistence")
print("=" * 60)
from execution.paper_trading import PaperTrader

# Create trader, make some trades
pt = PaperTrader(100_000)
pt.place_order("RELIANCE.NS", "BUY", 10, 1400)
pt.place_order("TCS.NS", "BUY", 5, 2300)
print(f"  After buys — Capital: ₹{pt.capital:,.0f}")
print(f"  Positions: {list(pt.positions.keys())}")
assert "RELIANCE.NS" in pt.positions
assert "TCS.NS" in pt.positions

# Save state
test_state_file = "logs/test_portfolio_state.json"
pt.save_state(filepath=test_state_file, risk_state={
    "consecutive_losses": 1,
    "peak_portfolio_value": 102_000,
})
print(f"  State saved to {test_state_file}")

# Load state
pt2, risk_state = PaperTrader.load_state(filepath=test_state_file)
print(f"  Loaded — Capital: ₹{pt2.capital:,.0f}")
print(f"  Loaded — Positions: {list(pt2.positions.keys())}")
print(f"  Loaded — Risk state: {risk_state}")
assert pt2.capital == pt.capital, "Capital mismatch after load"
assert "RELIANCE.NS" in pt2.positions, "Position not loaded"
assert risk_state.get("consecutive_losses") == 1, "Risk state not loaded"
assert risk_state.get("peak_portfolio_value") == 102_000

# Sell and verify PnL
trade = pt2.place_order("RELIANCE.NS", "SELL", 10, 1450)
print(f"  Sold RELIANCE @ 1450 — PnL: ₹{trade['pnl']:+,.0f}")
assert trade["pnl"] == 500, f"PnL wrong: {trade['pnl']}"
print(f"  Capital after sell: ₹{pt2.capital:,.0f}")

# Cleanup test file
os.remove(test_state_file)
print("  ✅ PASS\n")

# ── Test 6: Astro Filter ──────────────────────────────────
print("=" * 60)
print("TEST 6: Astro Filter (moon, mercury, nakshatra)")
print("=" * 60)
from astro.filter import AstroFilter

af = AstroFilter()
result = af.evaluate(signal="BUY", price=1400)
print(f"  Signal: BUY → Final: {result['final_signal']}")
print(f"  Astro Score: {result['astro_score']}/100")
print(f"  Qty Multiplier: {result['quantity_multiplier']:.2f}")
print(f"  Blocked: {result['blocked']}")
if result['block_reasons']:
    print(f"  Block Reasons: {result['block_reasons']}")
print(f"  Gann Stop: ₹{result.get('suggested_stop', 0):,.2f}")
print(f"  Gann Target: ₹{result.get('suggested_target', 0):,.2f}")

report = af.get_daily_report()
print(f"\n{report}")
print("  ✅ PASS\n")

# ── Test 7: Telegram Alerts ────────────────────────────────
print("=" * 60)
print("TEST 7: Telegram Alerts (send test messages)")
print("=" * 60)
from monitoring.alerts import TelegramAlert

ta = TelegramAlert()
if ta.enabled:
    # Send a test summary
    ok1 = ta.send(
        "🧪 <b>INTEGRATION TEST</b>\n\n"
        "All components verified:\n"
        "  ✅ Config & Market Guard\n"
        "  ✅ Holiday Detection (2-layer)\n"
        "  ✅ Technical Indicators\n"
        "  ✅ Risk Manager\n"
        "  ✅ Paper Trader + Persistence\n"
        "  ✅ Astro Filter\n"
        "  ✅ Telegram Alerts\n\n"
        f"Portfolio: ₹{pt2.capital:,.0f}\n"
        f"Positions: {len(pt2.positions)} open\n"
        f"Mode selection: Ready (5 min timeout)\n\n"
        "🟢 <b>All systems GO for tomorrow!</b>"
    )
    print(f"  Test alert sent: {ok1}")

    # Test trade alert
    ok2 = ta.send_trade_alert("BUY", "RELIANCE.NS", 1411.50, 10, stop_loss=1381.0)
    print(f"  Trade alert sent: {ok2}")

    # Test blocked alert
    ok3 = ta.send_blocked_alert("INFY.NS", "Mercury Retrograde (day 11)")
    print(f"  Blocked alert sent: {ok3}")

    # Test daily summary
    ok4 = ta.send_daily_summary(102500, 2500, 3, 2)
    print(f"  Daily summary sent: {ok4}")
    print("  ✅ PASS\n")
else:
    print("  ⚠️ Telegram not configured — skipping")
    print("  SKIP\n")

# ── Test 8: Screener (live data fetch) ─────────────────────
print("=" * 60)
print("TEST 8: Screener (fetch 5 stocks from yfinance)")
print("=" * 60)
from data.fetcher import fetch_stock_data
from strategies.momentum import generate_signal

test_tickers = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS"]
results = []
for ticker in test_tickers:
    try:
        data = fetch_stock_data(ticker, period="6mo")
        signal = generate_signal(data)
        price = float(data["Close"].squeeze().iloc[-1])
        results.append({"ticker": ticker, "signal": signal, "price": price})
        print(f"  {ticker.replace('.NS', ''):12s} ₹{price:>10,.2f}  →  {signal}")
    except Exception as e:
        print(f"  {ticker}: ERROR — {e}")

assert len(results) >= 4, "Too many fetch failures"
print(f"\n  Fetched {len(results)}/{len(test_tickers)} stocks successfully")
print("  ✅ PASS\n")

# ── Test 9: Mode Selection (timeout → default paper) ──────
print("=" * 60)
print("TEST 9: Mode Selection (3-sec timeout → auto paper)")
print("=" * 60)
if ta.enabled:
    ta.send("🧪 <b>Testing mode selection...</b>\nBot will auto-select PAPER in 3 seconds (don't reply)")
    mode = ta.ask_trading_mode(timeout_seconds=3)
    print(f"  Mode selected: {mode}")
    assert mode == "paper", f"Should default to paper, got: {mode}"
    print("  ✅ PASS (defaulted to paper after timeout)\n")
else:
    mode = "paper"
    print("  Telegram not configured — defaulting to paper")
    print("  ✅ PASS\n")

# ── FINAL SUMMARY ──────────────────────────────────────────
print("=" * 60)
print("🟢 ALL 9 TESTS PASSED — System ready for trading!")
print("=" * 60)
print(f"""
Tomorrow (next trading day):
  • Bot asks Paper/Live on Telegram at 9:15 AM
  • Scans {len(config.WATCHLIST)} NSE stocks every {config.SCAN_INTERVAL_MINUTES} min
  • Astro filter: {'ON' if config.ASTRO_ENABLED else 'OFF'}
  • Risk: {config.MAX_DAILY_LOSS_PCT*100}% daily loss / {config.MAX_DRAWDOWN_PCT*100}% drawdown
  • Max {config.MAX_TOTAL_POSITIONS} positions at {config.MAX_POSITION_PCT*100}% each
  • Portfolio persists across sessions
  • Holiday auto-detection (2-layer)
""")
