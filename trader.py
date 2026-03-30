"""
Main Trading Pipeline — Indian Stock Market (NSE/BSE) Auto Trading Bot.

Usage:
    python trader.py               # DEFAULT: Auto mode — ask paper/live on Telegram,
                                   #   scan + trade 9:15 AM to 3:30 PM, repeat daily
    python trader.py --screener    # Run screener only + Telegram alert
    python trader.py --backtest    # Run backtest
    python trader.py --astro       # Show today's astro report only

Daily Flow (default):
    1. Wait for market open (skip holidays/weekends)
    2. Ask PAPER or LIVE mode via Telegram (5 min to reply, default: paper)
    3. Load previous portfolio state (capital, positions carry forward)
    4. Send astro daily report → Telegram
    5. Scan every 15 min → signals → trades → Telegram alerts
    6. 3:00 PM → no new positions | 3:30 PM → market close
    7. Save portfolio state + daily summary → Telegram
    8. Sleep until next trading day → repeat from step 1
"""
import os
import sys
import time as time_module
import traceback
from datetime import datetime, time, timedelta

import config
from data.fetcher import fetch_stock_data, fetch_live_prices
from data.signals import calculate_atr, calculate_rsi, calculate_adx, calculate_volume_ratio
from strategies.momentum import generate_signal
from risk.manager import RiskManager
from execution.paper_trading import PaperTrader
from astro.filter import AstroFilter
from monitoring.logger import setup_logger
from monitoring.alerts import TelegramAlert

logger = setup_logger()
alert = TelegramAlert()
astro = AstroFilter()


def is_market_holiday(check_date=None) -> tuple:
    """
    Check if a given date is an NSE holiday.
    Returns (is_holiday: bool, holiday_name: str or None).

    Two-layer detection:
      1. Hardcoded NSE_HOLIDAYS calendar in config.py (instant, works anytime)
      2. Live check via yfinance — if no NIFTY data for today after 9:30 AM,
         market is likely closed (catches unlisted holidays)
    """
    if check_date is None:
        check_date = datetime.now().date()

    date_str = check_date.strftime("%Y-%m-%d")

    # Layer 1: Hardcoded calendar
    if date_str in config.NSE_HOLIDAYS:
        return True, config.NSE_HOLIDAYS[date_str]

    # Layer 2: Live detection (only after 9:30 AM on weekdays)
    now = datetime.now()
    if check_date == now.date() and check_date.weekday() < 5 and now.hour >= 9 and now.minute >= 30:
        try:
            import yfinance as yf
            nifty = yf.download("^NSEI", period="5d", progress=False)
            if not nifty.empty:
                trading_dates = set(nifty.index.date)
                if check_date not in trading_dates:
                    return True, "Unlisted Holiday (no market data)"
        except Exception:
            pass  # yfinance failed, rely on calendar only

    return False, None


def get_next_trading_day(from_date=None):
    """Find the next trading day (skips weekends + holidays)."""
    if from_date is None:
        from_date = datetime.now().date()

    next_day = from_date + timedelta(days=1)
    while True:
        if next_day.weekday() >= 5:  # Weekend
            next_day += timedelta(days=1)
            continue
        is_hol, _ = is_market_holiday(next_day)
        if is_hol:
            next_day += timedelta(days=1)
            continue
        return next_day


def is_market_open() -> bool:
    """Check if Indian stock market is currently open (IST)."""
    now = datetime.now()

    # Weekend check
    if now.weekday() >= 5:
        return False

    # Holiday check
    is_hol, _ = is_market_holiday(now.date())
    if is_hol:
        return False

    market_open = time(config.MARKET_OPEN_HOUR, config.MARKET_OPEN_MINUTE)
    market_close = time(config.MARKET_CLOSE_HOUR, config.MARKET_CLOSE_MINUTE)
    return market_open <= now.time() <= market_close


def wait_for_market_open():
    """Wait until market opens. Skips weekends and holidays with Telegram alerts."""
    now = datetime.now()

    # ── Check if today is a holiday ────────────────────────
    is_hol, hol_name = is_market_holiday(now.date())
    if is_hol:
        next_day = get_next_trading_day(now.date())
        next_open = datetime.combine(next_day, time(config.MARKET_OPEN_HOUR, config.MARKET_OPEN_MINUTE))
        wait_seconds = (next_open - now).total_seconds()
        wait_hours = int(wait_seconds / 3600)
        wait_min = int((wait_seconds % 3600) / 60)

        # Check for upcoming holidays this week
        upcoming = []
        check = now.date() + timedelta(days=1)
        for _ in range(7):
            h, name = is_market_holiday(check)
            if h:
                upcoming.append(f"  {check.strftime('%d %b')} — {name}")
            check += timedelta(days=1)
        upcoming_text = "\n".join(upcoming) if upcoming else "  None"

        logger.info(f"TODAY IS A HOLIDAY: {hol_name}. Next trading day: {next_day}")
        alert.send(
            f"📅 <b>MARKET HOLIDAY — {hol_name}</b>\n\n"
            f"Date: {now.strftime('%A, %d %B %Y')}\n"
            f"NSE/BSE closed today.\n\n"
            f"<b>Next Trading Day:</b> {next_day.strftime('%A, %d %B %Y')}\n"
            f"Bot will auto-resume at 9:15 AM\n"
            f"Sleeping {wait_hours}h {wait_min}m\n\n"
            f"<b>Upcoming Holidays (7 days):</b>\n{upcoming_text}"
        )

        time_module.sleep(wait_seconds)
        # After waking up, re-check (in case of consecutive holidays)
        return wait_for_market_open()

    # ── Check if today is weekend ──────────────────────────
    if now.weekday() >= 5:
        next_day = get_next_trading_day(now.date())
        next_open = datetime.combine(next_day, time(config.MARKET_OPEN_HOUR, config.MARKET_OPEN_MINUTE))
        wait_seconds = (next_open - now).total_seconds()
        wait_hours = int(wait_seconds / 3600)
        wait_min = int((wait_seconds % 3600) / 60)

        day_name = "Saturday" if now.weekday() == 5 else "Sunday"
        logger.info(f"Weekend ({day_name}). Next trading day: {next_day}")
        alert.send(
            f"📅 <b>Weekend — {day_name}</b>\n"
            f"Market closed.\n"
            f"Next trading day: {next_day.strftime('%A, %d %B')}\n"
            f"Sleeping {wait_hours}h {wait_min}m"
        )

        time_module.sleep(wait_seconds)
        return wait_for_market_open()

    # ── Market closed for today (past 3:30 PM) ────────────
    market_open = time(config.MARKET_OPEN_HOUR, config.MARKET_OPEN_MINUTE)

    if now.time() >= time(config.MARKET_CLOSE_HOUR, config.MARKET_CLOSE_MINUTE):
        next_day = get_next_trading_day(now.date())
        next_open = datetime.combine(next_day, time(config.MARKET_OPEN_HOUR, config.MARKET_OPEN_MINUTE))
        wait_seconds = (next_open - now).total_seconds()
        wait_hours = int(wait_seconds / 3600)
        wait_min = int((wait_seconds % 3600) / 60)

        logger.info(f"Market closed for today. Sleeping until {next_open.strftime('%Y-%m-%d %H:%M')} ({wait_hours}h {wait_min}m)")
        alert.send(
            f"⏰ Market closed for today.\n"
            f"Sleeping until {next_open.strftime('%Y-%m-%d %H:%M')} ({wait_hours}h {wait_min}m)"
        )
        time_module.sleep(wait_seconds)
        return wait_for_market_open()

    # ── Before market open — wait for 9:15 AM ─────────────
    if now.time() < market_open:
        open_dt = now.replace(
            hour=config.MARKET_OPEN_HOUR,
            minute=config.MARKET_OPEN_MINUTE,
            second=0, microsecond=0,
        )
        wait_seconds = (open_dt - now).total_seconds()
        wait_min = int(wait_seconds / 60)

        logger.info(f"Market opens at {market_open}. Waiting {wait_min} minutes...")
        alert.send(
            f"⏰ <b>Bot Started — Waiting for Market</b>\n"
            f"Market opens at {market_open.strftime('%H:%M')}\n"
            f"Waiting {wait_min} minutes...\n"
            f"Will auto-scan every {config.SCAN_INTERVAL_MINUTES} min until 3:30 PM"
        )

        # Sleep until market opens (check every 30 seconds)
        while datetime.now().time() < market_open:
            time_module.sleep(30)

    return True


def send_heartbeat(trader, risk_mgr):
    """Send a quick position + P&L snapshot to Telegram between scans."""
    now = datetime.now()
    positions = trader.positions
    if not positions:
        alert.send(
            f"💓 <b>Heartbeat — {now.strftime('%H:%M')}</b>\n"
            f"No open positions\n"
            f"Capital: ₹{trader.capital:,.0f} | Trades: {risk_mgr.trades_today}"
        )
        return

    # Quick P&L snapshot
    tickers = [t.replace(":SHORT", "") for t in positions]
    prices = fetch_live_prices(list(set(tickers)))
    lines = []
    total_unreal = 0
    for sym, pos in positions.items():
        price_key = sym.replace(":SHORT", "")
        current = prices.get(price_key, pos["entry_price"])
        entry = pos["entry_price"]
        qty = pos["quantity"]
        is_short = pos.get("side") == "SHORT"
        unreal = ((entry - current) if is_short else (current - entry)) * qty
        total_unreal += unreal
        name = price_key.replace(".NS", "")
        d = "S" if is_short else "L"
        e = "🟢" if unreal >= 0 else "🔴"
        lines.append(f"  {e} {name} [{d}] ₹{unreal:+,.0f}")
    lines.sort(key=lambda x: -1 if "🟢" in x else 1)

    total_pnl = risk_mgr.daily_pnl + total_unreal
    alert.send(
        f"💓 <b>Heartbeat — {now.strftime('%H:%M')}</b>\n\n"
        f"<b>Positions ({len(positions)}):</b>\n"
        f"{chr(10).join(lines)}\n\n"
        f"<b>Unrealized:</b> ₹{total_unreal:+,.0f}\n"
        f"<b>Total P&L:</b> {'🟢' if total_pnl >= 0 else '🔴'} ₹{total_pnl:+,.0f}\n"
        f"Capital: ₹{trader.capital:,.0f} | Trades: {risk_mgr.trades_today}"
    )


def monitor_positions(trader, broker, risk_mgr):
    """
    Real-time position monitoring — checks SL, target, and trailing stop.
    Runs every POSITION_CHECK_SECONDS between scan cycles.
    Handles both LONG and SHORT (paper) positions.
    """
    if not trader.positions:
        return

    # Fetch live prices (lightweight — only held stocks)
    tickers = list(trader.positions.keys())
    # For SHORT positions, fetch price using base ticker (without :SHORT suffix)
    fetch_tickers = [t.replace(":SHORT", "") for t in tickers]
    fetch_tickers = list(set(fetch_tickers))  # deduplicate

    if broker and broker.connected:
        symbols = [t.replace(".NS", "") for t in fetch_tickers]
        ltp_map = broker.get_multiple_ltp(symbols)
        prices = {f"{sym}.NS": p for sym, p in ltp_map.items()}
    else:
        prices = fetch_live_prices(fetch_tickers)

    if not prices:
        return

    for ticker in tickers:
        pos = trader.positions.get(ticker)
        if not pos:
            continue

        # For SHORT positions, look up price using base ticker
        price_key = ticker.replace(":SHORT", "")
        if price_key not in prices:
            continue

        # ── SHORT position monitoring (paper only) ─────────
        if pos.get("side") == "SHORT":
            current_price = prices[price_key]
            entry = pos["entry_price"]
            stop_loss = pos.get("stop_loss", 0)
            target_2 = pos.get("target_2", 0)
            target_1 = pos.get("target_1", 0)
            trailing_low = pos.get("trailing_low", entry)
            half_booked = pos.get("half_booked", False)
            original_sl = pos.get("original_sl", stop_loss)
            original_risk = original_sl - entry  # risk per share for short
            name = price_key.replace(".NS", "")
            qty = pos["quantity"]

            # Update trailing low (price going down = good for shorts)
            if current_price < trailing_low:
                pos["trailing_low"] = current_price
                # Trailing SL for shorts: move SL down as price drops
                if half_booked and config.TRAILING_STOP_ENABLED and original_risk > 0:
                    new_sl = current_price + original_risk
                    if new_sl < stop_loss:
                        pos["stop_loss"] = new_sl
                        logger.info(f"  TRAILING SL (SHORT) {name}: ₹{stop_loss:,.2f} → ₹{new_sl:,.2f}")

            # SL hit — price went UP above stop loss
            if stop_loss > 0 and current_price >= stop_loss:
                trade = trader.place_order(price_key, "COVER", qty, current_price)
                pnl = trade.get("pnl", 0)
                risk_mgr.record_trade(pnl)
                risk_mgr.update_peak(trader.get_portfolio_value({}))
                logger.info(f"  🔴 SL HIT (SHORT) {name} @ ₹{current_price:,.2f} | PnL: ₹{pnl:+,.0f}")
                alert.send(
                    f"🔴 <b>SHORT SL HIT (Paper)</b>\n"
                    f"<b>{name}</b> @ ₹{current_price:,.2f}\n"
                    f"Entry: ₹{entry:,.2f} | SL: ₹{stop_loss:,.2f}\n"
                    f"PnL: ₹{pnl:+,.0f}"
                )
                continue

            # Target-1 hit (price went DOWN to target)
            if not half_booked and target_1 > 0 and current_price <= target_1:
                half_qty = max(1, int(qty * config.HALF_BOOK_PCT))
                if half_qty >= qty:
                    trade = trader.place_order(price_key, "COVER", qty, current_price)
                    pnl = trade.get("pnl", 0)
                    risk_mgr.record_trade(pnl)
                    risk_mgr.update_peak(trader.get_portfolio_value({}))
                    logger.info(f"  🟡 SHORT T1 HIT {name} — full cover (qty=1) | PnL: ₹{pnl:+,.0f}")
                    alert.send_trade_alert("COVER", price_key, current_price, qty, pnl=pnl)
                    continue

                trade = trader.place_order(price_key, "COVER", half_qty, current_price)
                pnl_half = trade.get("pnl", 0)
                risk_mgr.record_trade(pnl_half)
                pos["stop_loss"] = entry  # Move SL to cost (breakeven)
                pos["half_booked"] = True
                pos["trailing_low"] = current_price
                remaining = qty - half_qty
                logger.info(
                    f"  🟡 SHORT T1 HIT {name} @ ₹{current_price:,.2f} | "
                    f"Covered {half_qty} (₹{pnl_half:+,.0f}) | Remaining: {remaining}"
                )
                alert.send(
                    f"🟡 <b>SHORT TARGET-1 HIT — 50% Covered (Paper)</b>\n"
                    f"<b>{name}</b> @ ₹{current_price:,.2f}\n"
                    f"Entry: ₹{entry:,.2f} | PnL: ₹{pnl_half:+,.0f}\n"
                    f"Remaining: {remaining} qty | SL → Cost: ₹{entry:,.2f}\n"
                    f"Target-2: ₹{target_2:,.2f}"
                )
                continue

            # Target-2 hit — full cover
            if target_2 > 0 and current_price <= target_2:
                trade = trader.place_order(price_key, "COVER", qty, current_price)
                pnl = trade.get("pnl", 0)
                risk_mgr.record_trade(pnl)
                risk_mgr.update_peak(trader.get_portfolio_value({}))
                logger.info(f"  🟢 SHORT TARGET-2 HIT {name} @ ₹{current_price:,.2f} | PnL: ₹{pnl:+,.0f}")
                alert.send(
                    f"🟢 <b>SHORT TARGET-2 — Full Profit! (Paper)</b>\n"
                    f"<b>{name}</b> @ ₹{current_price:,.2f}\n"
                    f"Entry: ₹{entry:,.2f} | PnL: ₹{pnl:+,.0f}"
                )
                continue

            continue  # Skip long position logic for shorts

        current_price = prices[price_key]
        entry = pos["entry_price"]
        stop_loss = pos.get("stop_loss", 0)
        target = pos.get("target", 0)
        trailing_high = pos.get("trailing_high", entry)

        half_booked = pos.get("half_booked", False)
        original_sl = pos.get("original_sl", stop_loss)
        original_risk = entry - original_sl
        target_1 = pos.get("target_1", 0)
        target_2 = pos.get("target_2", target)
        name = ticker.replace('.NS', '')

        # ── Phase 1: Full position, waiting for Target-1 ─
        if config.HALF_BOOKING_ENABLED and not half_booked:

            # Update trailing high (no trailing SL yet in phase 1)
            if current_price > trailing_high:
                pos["trailing_high"] = current_price

            # SL hit — full loss on full qty
            if stop_loss > 0 and current_price <= stop_loss:
                qty = pos["quantity"]
                trade = trader.place_order(ticker, "SELL", qty, current_price)
                pnl = trade.get("pnl", 0)
                risk_mgr.record_trade(pnl)
                risk_mgr.update_peak(trader.get_portfolio_value({}))

                logger.info(f"  🔴 SL HIT {name} @ ₹{current_price:,.2f} | PnL: ₹{pnl:+,.0f}")
                alert.send(
                    f"🔴 <b>STOP LOSS HIT</b>\n"
                    f"<b>{name}</b> @ ₹{current_price:,.2f}\n"
                    f"Entry: ₹{entry:,.2f} | SL: ₹{stop_loss:,.2f}\n"
                    f"PnL: ₹{pnl:+,.0f}"
                )
                if broker and broker.connected:
                    broker.place_order(name, "SELL", qty, current_price,
                                       order_type="MARKET", product=config.ORDER_PRODUCT)
                continue

            # Target-1 hit (1:1 R:R) — book 50%, move SL to cost
            if target_1 > 0 and current_price >= target_1:
                total_qty = pos["quantity"]
                half_qty = max(1, int(total_qty * config.HALF_BOOK_PCT))

                if half_qty >= total_qty:
                    # Only 1 share — full exit at Target-1
                    trade = trader.place_order(ticker, "SELL", total_qty, current_price)
                    pnl = trade.get("pnl", 0)
                    risk_mgr.record_trade(pnl)
                    risk_mgr.update_peak(trader.get_portfolio_value({}))
                    logger.info(f"  🟡 T1 HIT {name} — full exit (qty=1) | PnL: ₹{pnl:+,.0f}")
                    alert.send(
                        f"🟡 <b>TARGET-1 HIT — Full Exit (qty=1)</b>\n"
                        f"<b>{name}</b> @ ₹{current_price:,.2f}\n"
                        f"Entry: ₹{entry:,.2f} | PnL: ₹{pnl:+,.0f}"
                    )
                    if broker and broker.connected:
                        broker.place_order(name, "SELL", total_qty, current_price,
                                           order_type="MARKET", product=config.ORDER_PRODUCT)
                    continue

                # Partial sell — book 50%
                trade = trader.place_order(ticker, "SELL", half_qty, current_price)
                pnl_half = trade.get("pnl", 0)
                risk_mgr.record_trade(pnl_half)

                # Move SL to cost (breakeven) for remaining qty
                pos["stop_loss"] = entry
                pos["half_booked"] = True
                pos["trailing_high"] = current_price

                remaining = total_qty - half_qty
                logger.info(
                    f"  🟡 TARGET-1 HIT {name} @ ₹{current_price:,.2f} | "
                    f"Booked {half_qty} qty (₹{pnl_half:+,.0f}) | "
                    f"Remaining: {remaining} | SL → Cost (₹{entry:,.2f})"
                )
                alert.send(
                    f"🟡 <b>TARGET-1 HIT — 50% Booked!</b>\n"
                    f"<b>{name}</b> @ ₹{current_price:,.2f}\n"
                    f"Entry: ₹{entry:,.2f}\n"
                    f"Sold: {half_qty} qty | PnL: ₹{pnl_half:+,.0f}\n"
                    f"Remaining: {remaining} qty\n"
                    f"SL moved to cost: ₹{entry:,.2f}\n"
                    f"Target-2: ₹{target_2:,.2f}"
                )
                if broker and broker.connected:
                    broker.place_order(name, "SELL", half_qty, current_price,
                                       order_type="MARKET", product=config.ORDER_PRODUCT)
                    # Cancel old SL order and place new one at cost
                    broker.place_sl_order(name, remaining, trigger_price=entry,
                                          product=config.ORDER_PRODUCT)
                continue

        # ── Phase 2: Half booked, trailing remaining qty ──
        elif config.HALF_BOOKING_ENABLED and half_booked:

            # Update trailing high & trailing SL
            if current_price > trailing_high:
                pos["trailing_high"] = current_price
                if config.TRAILING_STOP_ENABLED and original_risk > 0:
                    new_sl = current_price - original_risk
                    if new_sl > stop_loss:
                        old_sl = stop_loss
                        pos["stop_loss"] = new_sl
                        logger.info(
                            f"  TRAILING SL {name}: ₹{old_sl:,.2f} → ₹{new_sl:,.2f}"
                        )

            # SL hit (at cost or trailing) — breakeven or small profit
            if stop_loss > 0 and current_price <= stop_loss:
                qty = pos["quantity"]
                trade = trader.place_order(ticker, "SELL", qty, current_price)
                pnl = trade.get("pnl", 0)
                risk_mgr.record_trade(pnl)
                risk_mgr.update_peak(trader.get_portfolio_value({}))

                exit_type = "BREAKEVEN" if abs(current_price - entry) < 1 else "TRAIL SL"
                logger.info(f"  🟠 {exit_type} {name} @ ₹{current_price:,.2f} | PnL: ₹{pnl:+,.0f}")
                alert.send(
                    f"🟠 <b>{exit_type} — Remaining Qty Exited</b>\n"
                    f"<b>{name}</b> @ ₹{current_price:,.2f}\n"
                    f"Entry: ₹{entry:,.2f} | SL: ₹{stop_loss:,.2f}\n"
                    f"PnL: ₹{pnl:+,.0f}"
                )
                if broker and broker.connected:
                    broker.place_order(name, "SELL", qty, current_price,
                                       order_type="MARKET", product=config.ORDER_PRODUCT)
                continue

            # Target-2 hit (1:2 R:R) — book remaining
            if target_2 > 0 and current_price >= target_2:
                qty = pos["quantity"]
                trade = trader.place_order(ticker, "SELL", qty, current_price)
                pnl = trade.get("pnl", 0)
                risk_mgr.record_trade(pnl)
                risk_mgr.update_peak(trader.get_portfolio_value({}))

                logger.info(f"  🟢 TARGET-2 HIT {name} @ ₹{current_price:,.2f} | PnL: ₹{pnl:+,.0f}")
                alert.send(
                    f"🟢 <b>TARGET-2 HIT — Full Profit!</b>\n"
                    f"<b>{name}</b> @ ₹{current_price:,.2f}\n"
                    f"Entry: ₹{entry:,.2f} | Target-2: ₹{target_2:,.2f}\n"
                    f"PnL: ₹{pnl:+,.0f}"
                )
                if broker and broker.connected:
                    broker.place_order(name, "SELL", qty, current_price,
                                       order_type="MARKET", product=config.ORDER_PRODUCT)
                continue

        # ── Fallback: Half-booking disabled (original full-exit logic) ──
        else:
            # Update trailing high & trailing stop
            if current_price > trailing_high:
                pos["trailing_high"] = current_price
                if config.TRAILING_STOP_ENABLED and stop_loss > 0:
                    profit = current_price - entry
                    if profit >= original_risk:
                        new_sl = current_price - original_risk
                        if new_sl > stop_loss:
                            old_sl = stop_loss
                            pos["stop_loss"] = new_sl
                            logger.info(
                                f"  TRAILING SL {name}: ₹{old_sl:,.2f} → ₹{new_sl:,.2f}"
                            )

            # SL hit
            if stop_loss > 0 and current_price <= stop_loss:
                qty = pos["quantity"]
                trade = trader.place_order(ticker, "SELL", qty, current_price)
                pnl = trade.get("pnl", 0)
                risk_mgr.record_trade(pnl)
                risk_mgr.update_peak(trader.get_portfolio_value({}))
                logger.info(f"  🔴 SL HIT {name} @ ₹{current_price:,.2f} | PnL: ₹{pnl:+,.0f}")
                alert.send(
                    f"🔴 <b>STOP LOSS HIT</b>\n"
                    f"<b>{name}</b> @ ₹{current_price:,.2f}\n"
                    f"Entry: ₹{entry:,.2f} | SL: ₹{stop_loss:,.2f}\n"
                    f"PnL: ₹{pnl:+,.0f}"
                )
                if broker and broker.connected:
                    broker.place_order(name, "SELL", qty, current_price,
                                       order_type="MARKET", product=config.ORDER_PRODUCT)
                continue

            # Target hit
            if target > 0 and current_price >= target:
                qty = pos["quantity"]
                trade = trader.place_order(ticker, "SELL", qty, current_price)
                pnl = trade.get("pnl", 0)
                risk_mgr.record_trade(pnl)
                risk_mgr.update_peak(trader.get_portfolio_value({}))
                logger.info(f"  🟢 TARGET HIT {name} @ ₹{current_price:,.2f} | PnL: ₹{pnl:+,.0f}")
                alert.send(
                    f"🟢 <b>TARGET HIT — Profit Booked!</b>\n"
                    f"<b>{name}</b> @ ₹{current_price:,.2f}\n"
                    f"Entry: ₹{entry:,.2f} | Target: ₹{target:,.2f}\n"
                    f"PnL: ₹{pnl:+,.0f}"
                )
                if broker and broker.connected:
                    broker.place_order(name, "SELL", qty, current_price,
                                       order_type="MARKET", product=config.ORDER_PRODUCT)
                continue


def run_scan_cycle(risk_mgr, trader, broker, cycle_num, prev_signals):
    """
    Run one scan cycle: fetch data → signals → trades.
    Returns current signals dict for comparison with next cycle.
    """
    now = datetime.now()
    logger.info(f"\n{'─'*60}")
    logger.info(f"SCAN #{cycle_num} — {now.strftime('%H:%M:%S')}")
    logger.info(f"{'─'*60}")

    # ── Fetch data and generate signals ─────────────────
    signals = {}
    errors = []

    for ticker in config.WATCHLIST:
        try:
            data = fetch_stock_data(ticker, period="6mo")
            signal = generate_signal(data)
            signals[ticker] = {"signal": signal, "data": data}
        except Exception as e:
            errors.append(f"{ticker}: {e}")
            continue

    # Send error alerts if any
    if errors:
        error_msg = "\n".join(errors[:5])  # Max 5 errors to avoid spam
        logger.error(f"Fetch errors:\n{error_msg}")
        if cycle_num <= 2 or len(errors) > 5:  # Alert on first cycles or many errors
            alert.send(f"⚠️ <b>Fetch Errors (Scan #{cycle_num})</b>\n{error_msg}")

    buy_signals = {t: s for t, s in signals.items() if s["signal"] == "BUY"}
    sell_signals = {t: s for t, s in signals.items() if s["signal"] == "SELL"}
    hold_count = len(signals) - len(buy_signals) - len(sell_signals)

    logger.info(f"Signals: {len(buy_signals)} BUY | {len(sell_signals)} SELL | {hold_count} HOLD")

    # ── Detect NEW signal changes since last scan ───────
    new_buys = []
    new_sells = []
    for ticker, info in signals.items():
        prev = prev_signals.get(ticker, {}).get("signal", "HOLD")
        curr = info["signal"]
        if curr == "BUY" and prev != "BUY":
            new_buys.append(ticker)
        elif curr == "SELL" and prev != "SELL":
            new_sells.append(ticker)

    if new_buys:
        logger.info(f"NEW BUY triggers: {new_buys}")
    if new_sells:
        logger.info(f"NEW SELL triggers: {new_sells}")

    # Send new trigger alerts
    if new_buys and cycle_num > 1:
        symbols = ", ".join([t.replace(".NS", "") for t in new_buys])
        alert.send(f"🔔 <b>New BUY Triggers (Scan #{cycle_num})</b>\n{symbols}")
    if new_sells and cycle_num > 1:
        symbols = ", ".join([t.replace(".NS", "") for t in new_sells])
        alert.send(f"🔔 <b>New SELL Triggers (Scan #{cycle_num})</b>\n{symbols}")

    # ── Process SELL signals ────────────────────────────
    for ticker, info in sell_signals.items():
        # Exit long position if held
        if ticker in trader.positions:
            price = float(info["data"]["Close"].squeeze().iloc[-1])
            position = trader.positions[ticker]
            trade = trader.place_order(ticker, "SELL", position["quantity"], price)
            pnl = trade.get("pnl", 0)
            risk_mgr.record_trade(pnl)
            risk_mgr.update_peak(trader.get_portfolio_value({}))
            logger.info(f"  SOLD {ticker} @ {price:,.2f} | PnL: {pnl:+,.2f}")

            alert.send_trade_alert("SELL", ticker, price, position["quantity"], pnl=pnl)

            if broker:
                symbol = ticker.replace(".NS", "")
                broker.place_order(symbol, "SELL", position["quantity"], price,
                                   product=config.ORDER_PRODUCT)

    # ── Build current prices map for accurate portfolio value ──
    current_prices = {}
    for t, s in signals.items():
        try:
            current_prices[t] = float(s["data"]["Close"].squeeze().iloc[-1])
        except Exception:
            pass

    # ── Score & sort BUY signals by momentum + R:R ──────
    # Priority: best momentum (ADX + RSI) and best R:R ratio first
    scored_buys = []
    for ticker, info in buy_signals.items():
        if ticker in trader.positions:
            continue
        try:
            data = info["data"]
            close = data["Close"].squeeze()
            high = data["High"].squeeze()
            low = data["Low"].squeeze()
            rsi = calculate_rsi(close).iloc[-1]
            adx = calculate_adx(high, low, close).iloc[-1]
            vol_ratio = calculate_volume_ratio(data["Volume"].squeeze()).iloc[-1]
            atr = calculate_atr(high, low, close).iloc[-1]
            price = float(close.iloc[-1])
            # R:R score: higher ATR relative to price = more room for profit
            rr_score = (atr / price * 100) if price > 0 else 0
            # Momentum score: ADX (trend strength) + RSI (momentum) + volume
            momentum_score = (adx * 0.4) + (rsi * 0.3) + (min(vol_ratio, 5) * 20 * 0.3)
            total_score = momentum_score + (rr_score * 10)
            scored_buys.append((ticker, info, total_score))
        except Exception:
            scored_buys.append((ticker, info, 0))

    scored_buys.sort(key=lambda x: x[2], reverse=True)

    # ── Process BUY signals (with Astro Filter) ─────────
    for ticker, info, _score in scored_buys:
        data = info["data"]
        close = data["Close"].squeeze()
        high = data["High"].squeeze()
        low = data["Low"].squeeze()
        price = float(close.iloc[-1])
        atr = float(calculate_atr(high, low, close).iloc[-1])

        # Astro filter
        astro_result = astro.evaluate(signal="BUY", price=price)

        if astro_result["blocked"]:
            reasons = " | ".join(astro_result["block_reasons"])
            logger.warning(f"  ASTRO BLOCKED {ticker}: {reasons}")
            alert.send_blocked_alert(ticker, f"Astro: {reasons}")
            continue

        # Stop loss (Gann vs ATR — use tighter)
        gann_stop = astro_result.get("suggested_stop", 0)
        atr_stop = risk_mgr.calculate_stop_loss(price, atr)
        stop_loss = gann_stop if (gann_stop > 0 and gann_stop > atr_stop) else atr_stop

        # Portfolio value using CURRENT prices (not entry prices)
        portfolio_value = trader.get_portfolio_value(current_prices)

        # Position size (risk-based)
        quantity = risk_mgr.calculate_position_size(portfolio_value, price, stop_loss)
        astro_qty = int(quantity * astro_result["quantity_multiplier"])
        if astro_qty > 0:
            quantity = astro_qty

        # Cap quantity to max position size (5% of portfolio)
        max_position_value = portfolio_value * config.MAX_POSITION_PCT
        max_qty_by_size = int(max_position_value / price) if price > 0 else 0
        if quantity > max_qty_by_size:
            quantity = max_qty_by_size

        # Cap quantity to available cash
        max_qty_by_cash = int(trader.capital / price) if price > 0 else 0
        if quantity > max_qty_by_cash:
            quantity = max_qty_by_cash

        if quantity == 0:
            logger.warning(f"  SKIP {ticker}: position size = 0")
            continue

        proposed_value = quantity * price

        # Risk check (circuit breakers)
        can_trade, reason = risk_mgr.can_open_position(
            portfolio_value,
            list(trader.positions.keys()),
            proposed_value,
        )

        if not can_trade:
            logger.warning(f"  BLOCKED {ticker}: {reason}")
            alert.send_blocked_alert(ticker, reason)
            continue

        # Calculate targets (Risk:Reward ratio)
        risk_per_share = price - stop_loss
        target_1 = price + (risk_per_share * config.TARGET_1_RR)        # 1:1 R:R (half-book)
        target_2 = price + (risk_per_share * config.RISK_REWARD_RATIO)  # 1:2 R:R (full exit)
        target = target_2  # Main target for display

        # Execute trade
        trade = trader.place_order(ticker, "BUY", quantity, price)

        # Store SL, targets, trailing high on position for real-time monitoring
        if ticker in trader.positions:
            trader.positions[ticker]["stop_loss"] = stop_loss
            trader.positions[ticker]["original_sl"] = stop_loss
            trader.positions[ticker]["target"] = target_2
            trader.positions[ticker]["target_1"] = target_1
            trader.positions[ticker]["target_2"] = target_2
            trader.positions[ticker]["trailing_high"] = price
            trader.positions[ticker]["half_booked"] = False
            trader.positions[ticker]["original_qty"] = quantity

        logger.info(
            f"  BOUGHT {ticker} @ {price:,.2f} | Qty: {quantity} | "
            f"SL: {stop_loss:,.2f} | T1: {target_1:,.2f} | T2: {target_2:,.2f} | "
            f"Astro: {astro_result['astro_score']}/100"
        )

        alert.send_trade_alert("BUY", ticker, price, quantity, stop_loss=stop_loss, target=target)

        if broker:
            symbol = ticker.replace(".NS", "")
            broker.place_order(symbol, "BUY", quantity, price,
                               product=config.ORDER_PRODUCT)
            # Place SL order on exchange (instant execution, even gap downs)
            broker.place_sl_order(symbol, quantity, trigger_price=stop_loss,
                                  product=config.ORDER_PRODUCT)

    # ── Score & sort SHORT signals by momentum + R:R ────
    # Priority: strongest bearish momentum (high ADX + low RSI) first
    # No new shorts after 3:00 PM (square-off at 3:15, not worth it)
    square_off_cutoff = time(config.NO_NEW_POSITIONS_AFTER_HOUR, config.NO_NEW_POSITIONS_AFTER_MINUTE)
    if not broker and now.time() < square_off_cutoff:  # Paper mode only + before 3 PM
        scored_shorts = []
        for ticker, info in sell_signals.items():
            short_key = f"{ticker}:SHORT"
            if ticker in trader.positions or short_key in trader.positions:
                continue
            try:
                data = info["data"]
                close = data["Close"].squeeze()
                high = data["High"].squeeze()
                low = data["Low"].squeeze()
                rsi = calculate_rsi(close).iloc[-1]
                adx = calculate_adx(high, low, close).iloc[-1]
                vol_ratio = calculate_volume_ratio(data["Volume"].squeeze()).iloc[-1]
                atr = calculate_atr(high, low, close).iloc[-1]
                price = float(close.iloc[-1])
                rr_score = (atr / price * 100) if price > 0 else 0
                # For shorts: lower RSI = stronger bearish, higher ADX = stronger trend
                bearish_score = (adx * 0.4) + ((100 - rsi) * 0.3) + (min(vol_ratio, 5) * 20 * 0.3)
                total_score = bearish_score + (rr_score * 10)
                scored_shorts.append((ticker, info, total_score))
            except Exception:
                scored_shorts.append((ticker, info, 0))

        scored_shorts.sort(key=lambda x: x[2], reverse=True)

        for ticker, info, _score in scored_shorts:

            data = info["data"]
            close = data["Close"].squeeze()
            high = data["High"].squeeze()
            low = data["Low"].squeeze()
            price = float(close.iloc[-1])
            atr = float(calculate_atr(high, low, close).iloc[-1])

            # Astro filter (same rules apply for shorts)
            astro_result = astro.evaluate(signal="SELL", price=price)
            if astro_result["blocked"]:
                continue

            # Stop loss for short = Entry + (ATR x multiplier) — price goes UP = loss
            stop_loss = price + (atr * config.STOP_LOSS_ATR_MULT)

            # Portfolio value using current prices
            portfolio_value = trader.get_portfolio_value(current_prices)

            # Position size (same risk-based logic)
            risk_per_share = stop_loss - price
            if risk_per_share <= 0:
                continue
            risk_amount = min(
                portfolio_value * config.RISK_PER_TRADE_PCT,
                config.MAX_LOSS_PER_TRADE,
            )
            quantity = int(risk_amount / risk_per_share)

            # Astro quantity adjustment
            astro_qty = int(quantity * astro_result["quantity_multiplier"])
            if astro_qty > 0:
                quantity = astro_qty

            # Cap to max position size
            max_position_value = portfolio_value * config.MAX_POSITION_PCT
            max_qty = int(max_position_value / price) if price > 0 else 0
            if quantity > max_qty:
                quantity = max_qty

            # Cap to available capital (margin)
            max_qty_cash = int(trader.capital / price) if price > 0 else 0
            if quantity > max_qty_cash:
                quantity = max_qty_cash

            if quantity == 0:
                continue

            # Risk check
            proposed_value = quantity * price
            can_trade, reason = risk_mgr.can_open_position(
                portfolio_value,
                list(trader.positions.keys()),
                proposed_value,
            )
            if not can_trade:
                logger.warning(f"  SHORT BLOCKED {ticker}: {reason}")
                alert.send_blocked_alert(ticker, f"Short: {reason}")
                continue

            # Targets for short (price goes DOWN = profit)
            target_1 = price - (risk_per_share * config.TARGET_1_RR)
            target_2 = price - (risk_per_share * config.RISK_REWARD_RATIO)

            # Execute paper short
            trade = trader.place_order(ticker, "SHORT", quantity, price)
            if trade.get("status") != "FILLED":
                continue

            # Store SL/targets on short position
            if short_key in trader.positions:
                trader.positions[short_key]["stop_loss"] = stop_loss
                trader.positions[short_key]["original_sl"] = stop_loss
                trader.positions[short_key]["target"] = target_2
                trader.positions[short_key]["target_1"] = target_1
                trader.positions[short_key]["target_2"] = target_2
                trader.positions[short_key]["trailing_low"] = price
                trader.positions[short_key]["half_booked"] = False
                trader.positions[short_key]["original_qty"] = quantity

            logger.info(
                f"  SHORTED {ticker} @ {price:,.2f} | Qty: {quantity} | "
                f"SL: {stop_loss:,.2f} | T1: {target_1:,.2f} | T2: {target_2:,.2f}"
            )
            alert.send_trade_alert("SHORT", ticker, price, quantity,
                                   stop_loss=stop_loss, target=target_2)

    # ── Scan summary — send to Telegram every scan ──
    if True:
        portfolio_value = trader.get_portfolio_value(current_prices)

        # Build detailed P&L per position
        pnl_lines = []
        total_unrealized = 0
        for sym, pos in trader.positions.items():
            is_short = pos.get("side") == "SHORT"
            base_sym = sym.replace(":SHORT", "").replace(".NS", "")
            price_key = sym.replace(":SHORT", "")
            current = current_prices.get(price_key, pos["entry_price"])
            entry = pos["entry_price"]
            qty = pos["quantity"]

            if is_short:
                unrealized = (entry - current) * qty
                direction = "S"
            else:
                unrealized = (current - entry) * qty
                direction = "L"

            total_unrealized += unrealized
            emoji = "🟢" if unrealized >= 0 else "🔴"
            pnl_lines.append(
                f"  {emoji} {base_sym} [{direction}] ₹{unrealized:+,.0f}"
            )

        # Sort by P&L (best first)
        pnl_lines.sort(key=lambda x: -1 if "🟢" in x else 1)

        pos_detail = "\n".join(pnl_lines) if pnl_lines else "No positions"
        realized_pnl = risk_mgr.daily_pnl
        total_pnl = realized_pnl + total_unrealized

        alert.send(
            f"📊 <b>P&L Report — {now.strftime('%H:%M')}</b>\n"
            f"Scan #{cycle_num}\n\n"
            f"<b>Open Positions ({len(trader.positions)}):</b>\n"
            f"{pos_detail}\n\n"
            f"<b>Unrealized P&L:</b> ₹{total_unrealized:+,.0f}\n"
            f"<b>Realized P&L:</b> ₹{realized_pnl:+,.0f}\n"
            f"<b>Total P&L:</b> {'🟢' if total_pnl >= 0 else '🔴'} ₹{total_pnl:+,.0f}\n"
            f"<b>Portfolio:</b> ₹{portfolio_value:,.0f}\n"
            f"Trades today: {risk_mgr.trades_today}"
        )

    return signals


def run_auto_mode():
    """
    DEFAULT MODE — runs every trading day automatically.

    Each morning:
      1. Wait for market open (skip holidays/weekends)
      2. Ask Paper/Live mode via Telegram
      3. Load previous portfolio state
      4. Scan + trade until market close
      5. Save portfolio state
      6. Sleep until next trading day → repeat
    """
    logger.info("=" * 60)
    logger.info(f"AUTOTRADE BOT — {config.MARKET} MARKET")
    logger.info(f"Scan interval: {config.SCAN_INTERVAL_MINUTES} min")
    logger.info(f"Astro: {'ON' if config.ASTRO_ENABLED else 'OFF'}")
    logger.info("=" * 60)

    # ── Wait for market to open ─────────────────────────
    if not wait_for_market_open():
        return

    # ── Ask trading mode via Telegram ──────────────────
    mode_choice = alert.ask_trading_mode()
    live = (mode_choice == "live")
    mode = "LIVE" if live else "PAPER"

    # ── Load previous portfolio state ──────────────────
    trader, risk_state = PaperTrader.load_state()
    risk_mgr = RiskManager(paper_mode=not live)
    risk_mgr.consecutive_losses = risk_state.get("consecutive_losses", 0)
    risk_mgr.peak_portfolio_value = risk_state.get("peak_portfolio_value", trader.capital)
    risk_mgr.reset_daily(trader.get_portfolio_value({}))

    portfolio_value = trader.get_portfolio_value({})
    pos_count = len(trader.positions)
    pos_list = ", ".join([t.replace(".NS", "") for t in trader.positions.keys()]) or "None"

    logger.info(f"Mode: {mode} | Capital: ₹{trader.capital:,.0f} | Positions: {pos_count}")

    # ── Send startup alert with portfolio status ───────
    alert.send(
        f"🚀 <b>Trading Bot Started — {mode}</b>\n\n"
        f"<b>Portfolio:</b> ₹{portfolio_value:,.0f}\n"
        f"<b>Cash:</b> ₹{trader.capital:,.0f}\n"
        f"<b>Open Positions:</b> {pos_list}\n"
        f"<b>Watchlist:</b> {len(config.WATCHLIST)} stocks (NSE)\n"
        f"<b>Scan interval:</b> {config.SCAN_INTERVAL_MINUTES} min\n"
        f"<b>Astro Filter:</b> {'ON' if config.ASTRO_ENABLED else 'OFF'}\n"
        f"Running until 3:30 PM IST"
    )

    # ── Send Astro daily report ─────────────────────────
    if config.ASTRO_ENABLED:
        report = astro.get_daily_report()
        logger.info(f"\n{report}\n")
        alert.send(f"<pre>{report}</pre>")

    # ── Connect broker if live ──────────────────────────
    broker = None
    if live:
        from execution.broker_api import DhanBroker
        broker = DhanBroker()
        if not broker.connect():
            logger.error("Failed to connect to Dhan. Falling back to paper trading.")
            alert.send("⚠️ <b>Dhan connection failed</b> — falling back to paper trading")
            broker = None
            mode = "PAPER (broker fallback)"

    # ── Main auto loop ──────────────────────────────────
    market_close = time(config.MARKET_CLOSE_HOUR, config.MARKET_CLOSE_MINUTE)
    cycle_num = 0
    prev_signals = {}

    while True:
        now = datetime.now()

        # Check if market is closed
        if now.time() >= market_close:
            logger.info("Market closed. Stopping auto mode.")
            break

        # Check if it's a weekend
        if now.weekday() >= 5:
            logger.info("Weekend — market closed.")
            alert.send("📅 Weekend — market is closed. Bot stopping.")
            break

        # Check if it's a holiday
        is_hol, hol_name = is_market_holiday(now.date())
        if is_hol:
            logger.info(f"Holiday detected: {hol_name}")
            alert.send(f"📅 <b>Holiday Detected — {hol_name}</b>\nStopping scans for today.")
            break

        cycle_num += 1

        try:
            prev_signals = run_scan_cycle(
                risk_mgr, trader, broker, cycle_num, prev_signals
            )
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            tb = traceback.format_exc()
            logger.error(f"Scan #{cycle_num} FAILED:\n{tb}")

            # Send error to Telegram
            alert.send(
                f"🔴 <b>ERROR — Scan #{cycle_num}</b>\n"
                f"<code>{error_msg}</code>\n"
                f"Bot will continue running and retry next scan."
            )

        # Save state after each cycle (crash protection)
        trader.save_state(risk_state={
            "consecutive_losses": risk_mgr.consecutive_losses,
            "peak_portfolio_value": risk_mgr.peak_portfolio_value,
        })

        # ── Wait for next scan — monitor positions every 2 min, heartbeat every 5 min ──
        next_scan = now + timedelta(minutes=config.SCAN_INTERVAL_MINUTES)
        last_heartbeat = datetime.now()
        heartbeat_interval = 300  # 5 minutes

        # Don't scan past market close
        if next_scan.time() >= market_close:
            logger.info(f"Next scan would be after market close. Waiting for 3:30 PM...")
            while datetime.now().time() < market_close:
                monitor_positions(trader, broker, risk_mgr)
                if (datetime.now() - last_heartbeat).total_seconds() >= heartbeat_interval:
                    send_heartbeat(trader, risk_mgr)
                    last_heartbeat = datetime.now()
                time_module.sleep(config.POSITION_CHECK_SECONDS)
            break

        logger.info(f"Next scan at {next_scan.strftime('%H:%M:%S')} | Monitoring positions every {config.POSITION_CHECK_SECONDS}s")
        while datetime.now() < next_scan:
            try:
                monitor_positions(trader, broker, risk_mgr)
            except Exception as e:
                logger.error(f"Position monitor error: {e}")
            if (datetime.now() - last_heartbeat).total_seconds() >= heartbeat_interval:
                send_heartbeat(trader, risk_mgr)
                last_heartbeat = datetime.now()
            remaining = (next_scan - datetime.now()).total_seconds()
            if remaining > config.POSITION_CHECK_SECONDS:
                time_module.sleep(config.POSITION_CHECK_SECONDS)
            elif remaining > 0:
                time_module.sleep(remaining)
                break
            else:
                break

    # ── 3:15 PM — Auto square-off all SHORT positions (intraday rule) ──
    short_positions = {k: v for k, v in trader.positions.items() if v.get("side") == "SHORT"}
    if short_positions:
        logger.info(f"INTRADAY SQUARE-OFF: Covering {len(short_positions)} short positions")
        # Fetch final prices for shorts
        short_tickers = [k.replace(":SHORT", "") for k in short_positions]
        final_prices = fetch_live_prices(short_tickers)

        short_pnl_total = 0
        short_detail = ""
        for short_key, pos in list(short_positions.items()):
            base_ticker = short_key.replace(":SHORT", "")
            name = base_ticker.replace(".NS", "")
            price = final_prices.get(base_ticker, pos["entry_price"])
            qty = pos["quantity"]
            trade = trader.place_order(base_ticker, "COVER", qty, price)
            pnl = trade.get("pnl", 0)
            risk_mgr.record_trade(pnl)
            short_pnl_total += pnl
            emoji = "🟢" if pnl >= 0 else "🔴"
            short_detail += f"  {emoji} {name}: ₹{pnl:+,.0f}\n"
            logger.info(f"  COVERED {name} @ ₹{price:,.2f} | PnL: ₹{pnl:+,.0f}")

        risk_mgr.update_peak(trader.get_portfolio_value({}))
        alert.send(
            f"🔻 <b>INTRADAY SQUARE-OFF — 3:15 PM</b>\n\n"
            f"Covered {len(short_positions)} short positions:\n"
            f"{short_detail}\n"
            f"<b>Short P&L:</b> {'🟢' if short_pnl_total >= 0 else '🔴'} ₹{short_pnl_total:+,.0f}"
        )

    # ── Market Close — Save state + Daily Summary ──────
    portfolio_value = trader.get_portfolio_value({})

    # Save final state (persists for tomorrow)
    trader.save_state(risk_state={
        "consecutive_losses": risk_mgr.consecutive_losses,
        "peak_portfolio_value": risk_mgr.peak_portfolio_value,
    })
    logger.info(f"Portfolio state saved to {config.PORTFOLIO_STATE_FILE}")

    logger.info(f"\n{'='*60}")
    logger.info(f"AUTO MODE COMPLETE — {mode}")
    logger.info(f"Total scans: {cycle_num}")
    logger.info(f"Portfolio: INR {portfolio_value:,.2f}")
    logger.info(f"Trades today: {risk_mgr.trades_today}")
    logger.info(f"Daily PnL: INR {risk_mgr.daily_pnl:+,.2f}")
    logger.info(f"Open positions: {len(trader.positions)}")
    logger.info(f"{'='*60}")

    # Active positions detail (only LONG should remain — shorts already covered)
    long_positions = {k: v for k, v in trader.positions.items() if v.get("side") != "SHORT"}
    pos_detail = ""
    if long_positions:
        pos_detail = "\n<b>Carry Forward (LONG):</b>\n"
        for sym, pos in long_positions.items():
            symbol = sym.replace(".NS", "")
            pos_detail += f"  {symbol}: {pos['quantity']} @ ₹{pos['entry_price']:,.2f}\n"

    # Send detailed closing summary
    alert.send(
        f"🏁 <b>MARKET CLOSED — Daily Summary</b>\n\n"
        f"Mode: {mode}\n"
        f"Total Scans: {cycle_num}\n"
        f"Portfolio: ₹{portfolio_value:,.0f}\n"
        f"Daily PnL: {'🟢' if risk_mgr.daily_pnl >= 0 else '🔴'} ₹{risk_mgr.daily_pnl:+,.0f}\n"
        f"Trades: {risk_mgr.trades_today}\n"
        f"Shorts Covered: All (intraday square-off)\n"
        f"LONG Positions: {len(long_positions)}"
        f"{pos_detail}\n"
        f"See you tomorrow! 👋"
    )

    trader.save_trade_log()
    if trader.trade_log:
        logger.info(f"Trade log saved to {config.TRADE_LOG_FILE}")

    # ── Wait for next market day and run again ─────────
    logger.info("Waiting for next market day...")
    wait_for_market_open()
    return run_auto_mode()


if __name__ == "__main__":
    if "--backtest" in sys.argv:
        from tests.backtest import main as run_backtest
        run_backtest()
    elif "--screener" in sys.argv:
        from screener import run_screener, print_results, save_results
        results = run_screener()
        print_results(results)
        save_results(results)
        alert.send_screener_results(results)
    elif "--astro" in sys.argv:
        print(astro.get_daily_report())
    else:
        # Default: Auto mode — ask paper/live on Telegram, trade all day
        run_auto_mode()
