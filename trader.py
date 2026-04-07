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
from monitoring.commands import CommandHandler

logger = setup_logger()
alert = TelegramAlert()
astro = AstroFilter()


def fetch_nse_holidays_live() -> dict:
    """
    Fetch NSE trading holidays directly from NSE API.
    Returns dict of {YYYY-MM-DD: holiday_name} or empty dict on failure.
    Falls back silently — hardcoded calendar used if this fails.
    """
    import requests as req
    from datetime import date

    url = "https://www.nseindia.com/api/holiday-master?type=trading"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/",
    }
    try:
        session = req.Session()
        # Need to hit main page first to get cookies
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        resp = session.get(url, headers=headers, timeout=10)
        data = resp.json()

        holidays = {}
        current_year = date.today().year
        for segment, entries in data.items():
            if "CM" not in segment and segment != "CM":  # CM = Capital Market (equity)
                continue
            for entry in entries:
                try:
                    # NSE returns date as "15-Jan-2026" format
                    from datetime import datetime as dt
                    raw = entry.get("tradingDate", "") or entry.get("trade_date", "")
                    if not raw:
                        continue
                    parsed = dt.strptime(raw.strip(), "%d-%b-%Y").date()
                    if parsed.year >= current_year:
                        date_str = parsed.strftime("%Y-%m-%d")
                        name = entry.get("description", entry.get("holidayName", "NSE Holiday"))
                        holidays[date_str] = name
                except Exception:
                    continue
        return holidays
    except Exception as e:
        logger.warning(f"NSE holiday fetch failed: {e} — using hardcoded calendar")
        return {}


HOLIDAY_CACHE_FILE = "logs/nse_holidays_cache.json"
HOLIDAY_CACHE_DAYS = 0  # Always re-fetch from NSE on every startup


def refresh_holidays():
    """
    Update config.NSE_HOLIDAYS with live NSE data.
    Uses a local cache file — re-fetches from NSE API on every startup.
    Falls back to hardcoded calendar if both cache and API fail.
    """
    import json
    from datetime import date, datetime as dt

    os.makedirs("logs", exist_ok=True)
    cache_valid = False
    cached_data = {}

    # ── Try loading from local cache ──────────────────
    if os.path.exists(HOLIDAY_CACHE_FILE):
        try:
            with open(HOLIDAY_CACHE_FILE) as f:
                cache = json.load(f)
            fetched_on = dt.fromisoformat(cache.get("fetched_on", "2000-01-01")).date()
            age_days = (date.today() - fetched_on).days
            if age_days < HOLIDAY_CACHE_DAYS:
                cached_data = cache.get("holidays", {})
                cache_valid = True
                logger.info(f"NSE holidays loaded from cache ({age_days}d old, next refresh in {HOLIDAY_CACHE_DAYS - age_days}d)")
        except Exception:
            pass

    # ── Fetch fresh from NSE API if cache is stale/missing ──
    if not cache_valid:
        logger.info("Fetching NSE holidays from live API...")
        live = fetch_nse_holidays_live()
        if live:
            cached_data = live
            try:
                with open(HOLIDAY_CACHE_FILE, "w") as f:
                    json.dump({"fetched_on": date.today().isoformat(), "holidays": live}, f, indent=2)
                logger.info(f"NSE holidays fetched & cached: {len(live)} holidays")
            except Exception:
                pass
        else:
            logger.info("NSE API failed — using hardcoded calendar as fallback")

    # ── Apply to config (live/cached takes priority over hardcoded) ──
    if cached_data:
        config.NSE_HOLIDAYS.update(cached_data)
        return len(cached_data)
    return 0


def is_market_holiday(check_date=None) -> tuple:
    """
    Check if a given date is an NSE holiday.
    Returns (is_holiday: bool, holiday_name: str or None).

    Detection source: NSE API only (fetched fresh on every startup via refresh_holidays()).
    Falls back to hardcoded NSE_HOLIDAYS in config.py if API is unreachable.
    yfinance is NOT used for holiday detection — it caused false positives at market open.
    """
    if check_date is None:
        check_date = datetime.now().date()

    date_str = check_date.strftime("%Y-%m-%d")

    if date_str in config.NSE_HOLIDAYS:
        return True, config.NSE_HOLIDAYS[date_str]

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
    Handles both LONG and SHORT positions.
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

        # ── SHORT position monitoring ─────────────────────────
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
                if broker and broker.connected:
                    broker.place_order(name, "BUY", qty, current_price, product="INTRADAY")
                logger.info(f"  🔴 SL HIT (SHORT) {name} @ ₹{current_price:,.2f} | PnL: ₹{pnl:+,.0f}")
                alert.send(
                    f"🔴 <b>SHORT SL HIT</b>\n"
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
                    if broker and broker.connected:
                        broker.place_order(name, "BUY", qty, current_price, product="INTRADAY")
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
                if broker and broker.connected:
                    broker.place_order(name, "BUY", half_qty, current_price, product="INTRADAY")
                logger.info(
                    f"  🟡 SHORT T1 HIT {name} @ ₹{current_price:,.2f} | "
                    f"Covered {half_qty} (₹{pnl_half:+,.0f}) | Remaining: {remaining}"
                )
                alert.send(
                    f"🟡 <b>SHORT TARGET-1 HIT — 50% Covered</b>\n"
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
                if broker and broker.connected:
                    broker.place_order(name, "BUY", qty, current_price, product="INTRADAY")
                logger.info(f"  🟢 SHORT TARGET-2 HIT {name} @ ₹{current_price:,.2f} | PnL: ₹{pnl:+,.0f}")
                alert.send(
                    f"🟢 <b>SHORT TARGET-2 — Full Profit!</b>\n"
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


def run_scan_cycle(risk_mgr, trader, broker, cycle_num, prev_signals, cmd_handler=None):
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
            data = fetch_stock_data(ticker, period="730d", interval="1h")
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
        # Skip if already in any position (long or short) — no duplication
        if ticker in trader.positions or f"{ticker}:SHORT" in trader.positions:
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

    # ── Pause check — skip new entries if paused via Telegram ──
    if cmd_handler and cmd_handler.paused:
        logger.info("Trading PAUSED via Telegram — skipping new entries")
        return signals

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

        # Risk check — LONG is positional (hold overnight), intraday=False
        can_trade, reason = risk_mgr.can_open_position(
            portfolio_value,
            list(trader.positions.keys()),
            proposed_value,
            intraday=False,
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
    # SHORT = intraday only. Signal from generate_signal() already confirms:
    # EMA20 < EMA50 + MACD bearish + RSI < 45 + ADX > 20 + Volume > 1.5x
    # Same tools as BUY — symmetric strategy. No external filters needed.
    square_off_cutoff = time(config.NO_NEW_POSITIONS_AFTER_HOUR, config.NO_NEW_POSITIONS_AFTER_MINUTE)

    if now.time() < square_off_cutoff:
        # Count current open SHORT positions
        current_short_count = sum(1 for p in trader.positions.values() if p.get("side") == "SHORT")
        scored_shorts = []
        for ticker, info in sell_signals.items():
            short_key = f"{ticker}:SHORT"
            if ticker in trader.positions or short_key in trader.positions:
                continue
            try:
                data = info["data"]
                close = data["Close"].squeeze()
                high  = data["High"].squeeze()
                low   = data["Low"].squeeze()

                rsi      = calculate_rsi(close).iloc[-1]
                adx      = calculate_adx(high, low, close).iloc[-1]
                vol_ratio = calculate_volume_ratio(data["Volume"].squeeze()).iloc[-1]
                atr      = calculate_atr(high, low, close).iloc[-1]
                price    = float(close.iloc[-1])
                rr_score = (atr / price * 100) if price > 0 else 0
                bearish_score = (adx * 0.4) + ((100 - rsi) * 0.3) + (min(vol_ratio, 5) * 20 * 0.3)
                total_score = bearish_score + (rr_score * 10)
                scored_shorts.append((ticker, info, total_score))
            except Exception:
                scored_shorts.append((ticker, info, 0))

        scored_shorts.sort(key=lambda x: x[2], reverse=True)

        for ticker, info, _score in scored_shorts:

            data = info["data"]
            close = data["Close"].squeeze()
            high  = data["High"].squeeze()
            low   = data["Low"].squeeze()
            price = float(close.iloc[-1])
            atr   = float(calculate_atr(high, low, close).iloc[-1])

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

            # Risk check — SHORT is intraday only, must close same day
            proposed_value = quantity * price
            can_trade, reason = risk_mgr.can_open_position(
                portfolio_value,
                list(trader.positions.keys()),
                proposed_value,
                intraday=True,
            )
            if not can_trade:
                logger.warning(f"  SHORT BLOCKED {ticker}: {reason}")
                alert.send_blocked_alert(ticker, f"Short: {reason}")
                continue

            # Max short positions cap
            if current_short_count >= config.MAX_SHORT_POSITIONS:
                logger.warning(f"  SHORT BLOCKED {ticker}: Max short positions ({config.MAX_SHORT_POSITIONS}) reached")
                break

            # Targets for short (price goes DOWN = profit)
            target_1 = price - (risk_per_share * config.TARGET_1_RR)
            target_2 = price - (risk_per_share * config.RISK_REWARD_RATIO)

            # Execute short (paper tracker + real Dhan order if connected)
            name = ticker.replace(".NS", "")
            trade = trader.place_order(ticker, "SHORT", quantity, price)
            if trade.get("status") != "FILLED":
                continue

            if broker and broker.connected:
                broker.place_order(name, "SELL", quantity, price, product="INTRADAY")
            current_short_count += 1

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

    # ── Fetch live NSE holidays from NSE API ────────────
    n = refresh_holidays()
    if n:
        alert.send(f"📅 NSE holidays refreshed from live API ({n} holidays loaded)")

    # ── Load portfolio state early (needed for pre-market phone commands) ──
    trader, risk_state = PaperTrader.load_state()
    risk_mgr = RiskManager(paper_mode=True)
    risk_mgr.consecutive_losses = risk_state.get("consecutive_losses", 0)
    risk_mgr.peak_portfolio_value = risk_state.get("peak_portfolio_value", trader.capital)

    # ── Wait until 9:00 AM then start phone command handler ──
    now = datetime.now()
    phone_ready = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now < phone_ready:
        wait_sec = (phone_ready - now).total_seconds()
        logger.info(f"Waiting {int(wait_sec/60)}m until 9:00 AM to start phone commands...")
        time_module.sleep(wait_sec)

    cmd_handler = CommandHandler(alert, trader, risk_mgr, broker=None)
    cmd_handler.set_mode("paper")
    cmd_handler.start()
    alert.send("📱 <b>Phone commands active from 9:00 AM</b>\nType /help to control the bot.")

    # ── Wait for market to open ─────────────────────────
    if not wait_for_market_open():
        cmd_handler.stop()
        return

    # ── Ask trading mode via Telegram ──────────────────
    mode_choice = alert.ask_trading_mode()
    live = (mode_choice == "live")
    mode = "LIVE" if live else "PAPER"
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
        else:
            # ── Sync Dhan actual positions → paper tracker (prevents duplicates on restart) ──
            dhan_positions = broker.get_positions()
            if dhan_positions:
                synced = 0
                for dp in dhan_positions:
                    symbol = dp.get("tradingSymbol", "").replace("-EQ", "")
                    net_qty = int(dp.get("netQty", 0))
                    if net_qty == 0:
                        continue
                    is_short = net_qty < 0
                    qty = abs(net_qty)
                    avg_price = float(dp.get("sellAvg", 0) if is_short else dp.get("buyAvg", 0))
                    ticker = f"{symbol}.NS"
                    pos_key = f"{ticker}:SHORT" if is_short else ticker
                    if pos_key in trader.positions or avg_price <= 0:
                        continue

                    # Calculate SL/T1/T2 from ATR so monitoring works after sync
                    sl, t1, t2 = 0.0, 0.0, 0.0
                    try:
                        hist = fetch_stock_data(ticker)
                        if hist is not None and not hist.empty:
                            atr = float(calculate_atr(
                                hist["High"].squeeze(),
                                hist["Low"].squeeze(),
                                hist["Close"].squeeze()
                            ).iloc[-1])
                            risk = atr * config.STOP_LOSS_ATR_MULT
                            sl  = (avg_price + risk) if is_short else (avg_price - risk)
                            t1  = (avg_price - risk * config.TARGET_1_RR) if is_short else (avg_price + risk * config.TARGET_1_RR)
                            t2  = (avg_price - risk * config.RISK_REWARD_RATIO) if is_short else (avg_price + risk * config.RISK_REWARD_RATIO)
                    except Exception:
                        pass

                    trader.positions[pos_key] = {
                        "quantity": qty,
                        "entry_price": avg_price,
                        "entry_date": datetime.now().isoformat(),
                        "side": "SHORT" if is_short else "LONG",
                        "margin_blocked": qty * avg_price,
                        "stop_loss": sl,
                        "original_sl": sl,
                        "target_1": t1,
                        "target_2": t2,
                        "target": t2,
                        "trailing_high": avg_price,
                        "trailing_low": avg_price,
                        "half_booked": False,
                        "original_qty": qty,
                    }
                    if is_short:
                        trader.capital -= qty * avg_price
                    synced += 1
                    logger.info(f"Synced from Dhan: {symbol} {'SHORT' if is_short else 'LONG'} {qty}@{avg_price:.2f} | SL:{sl:.2f} T1:{t1:.2f} T2:{t2:.2f}")

                if synced:
                    alert.send(
                        f"🔄 <b>Synced {synced} positions from Dhan</b>\n"
                        f"Monitoring SL/T1/T2 — no new orders for these stocks."
                    )

    # ── Update command handler with final mode + broker ──
    cmd_handler.set_mode("live" if live else "paper")
    cmd_handler.set_broker(broker)
    risk_mgr.paper_mode = not live

    # ── Main auto loop ──────────────────────────────────
    market_close = time(config.MARKET_CLOSE_HOUR, config.MARKET_CLOSE_MINUTE)
    cycle_num = 0
    prev_signals = {}

    # Setup manual scan callback for Telegram /scan command
    def manual_scan_callback():
        """Allow Telegram /scan command to trigger immediate scan."""
        nonlocal cycle_num, prev_signals
        cycle_num += 1
        try:
            prev_signals = run_scan_cycle(
                risk_mgr, trader, broker, cycle_num, prev_signals, cmd_handler
            )
        except Exception as e:
            logger.error(f"Manual scan failed: {e}")
            raise

    cmd_handler.set_scan_callback(manual_scan_callback)

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
                risk_mgr, trader, broker, cycle_num, prev_signals, cmd_handler
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
                sq_time = time(config.INTRADAY_SQUARE_OFF_HOUR, config.INTRADAY_SQUARE_OFF_MINUTE)
                if datetime.now().time() >= sq_time:
                    break
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
            # ── 3:15 PM intraday square-off check (runs every 2 min loop) ──
            sq_time = time(config.INTRADAY_SQUARE_OFF_HOUR, config.INTRADAY_SQUARE_OFF_MINUTE)
            if datetime.now().time() >= sq_time:
                break
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
            if broker and broker.connected:
                broker.place_order(name, "BUY", qty, price, product="INTRADAY")
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
