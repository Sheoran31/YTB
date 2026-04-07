"""
Telegram Command Handler — control the bot from your phone.

Commands:
    /status      — Bot status + portfolio summary
    /positions   — Open positions with live P&L and R:R
    /pnl         — Today's P&L
    /scan        — Trigger immediate stock scan (don't wait 15 min)
    /close SYMBOL — Manually close a position (e.g. /close HDFCBANK)
    /pause       — Pause new trades (existing positions still monitored)
    /resume      — Resume new trades
    /squareoff   — Emergency: close ALL open positions immediately
    /help        — List all commands
"""
import threading
import time as time_module
import requests
from datetime import datetime

import config
from data.fetcher import fetch_live_prices
from monitoring.logger import setup_logger

logger = setup_logger("commands")


class CommandHandler:
    def __init__(self, alert, trader, risk_mgr, broker=None, scan_callback=None):
        self.alert = alert
        self.trader = trader
        self.risk_mgr = risk_mgr
        self.broker = broker
        self.scan_callback = scan_callback
        self.paused = False
        self.running = True
        self._offset = 0
        self._mode = "paper"
        self._last_command_time = {}  # Track last execution time per command
        self._command_cooldown_sec = 3  # Prevent same command twice in 3 seconds

    def set_mode(self, mode: str):
        self._mode = mode

    def set_broker(self, broker):
        self.broker = broker

    def set_scan_callback(self, callback):
        self.scan_callback = callback

    def start(self):
        """Start command polling in background daemon thread."""
        self._init_offset()
        thread = threading.Thread(target=self._poll_loop, daemon=True, name="TelegramCommands")
        thread.start()
        logger.info("Telegram command handler started — type /help in Telegram")
        return thread

    def stop(self):
        self.running = False

    def _init_offset(self):
        """Skip all old/pending messages on startup."""
        if not self.alert.enabled:
            return
        try:
            url = f"https://api.telegram.org/bot{self.alert.bot_token}/getUpdates"
            resp = requests.get(url, params={"offset": -1, "timeout": 1}, timeout=5)
            data = resp.json()
            if data.get("ok") and data.get("result"):
                self._offset = data["result"][-1]["update_id"] + 1
                logger.info(f"Offset initialized to {self._offset} — old messages will be skipped")
        except Exception as e:
            logger.warning(f"Could not initialize offset: {e}")
            pass

    def _poll_loop(self):
        while self.running:
            try:
                self._check_commands()
            except Exception as e:
                logger.error(f"Command poll error: {e}")
                time_module.sleep(5)

    def _check_commands(self):
        if not self.alert.enabled:
            time_module.sleep(10)
            return
        url = f"https://api.telegram.org/bot{self.alert.bot_token}/getUpdates"
        try:
            resp = requests.get(url, params={
                "offset": self._offset,
                "timeout": 10,
                "allowed_updates": ["message"],
            }, timeout=15)
            data = resp.json()
            updates = data.get("result", [])
            if updates:
                logger.info(f"DEBUG: Received {len(updates)} updates, expected chat: {self.alert.chat_id}")
            for update in updates:
                self._offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = (msg.get("text") or "").strip()
                if chat_id == self.alert.chat_id and text.startswith("/"):
                    logger.info(f"Command detected: {text}")
                    self._handle_command(text)
        except Exception as e:
            logger.error(f"Telegram poll error: {e}")
            time_module.sleep(5)

    def _handle_command(self, text: str):
        parts = text.split()
        cmd = parts[0].lower().split("@")[0]
        args = parts[1:] if len(parts) > 1 else []
        logger.info(f"Command received: {text}")

        # Check cooldown — prevent duplicate commands within 3 seconds
        now = time_module.time()
        last_time = self._last_command_time.get(cmd, 0)
        if now - last_time < self._command_cooldown_sec:
            logger.warning(f"Command {cmd} ignored — cooldown active (last executed {now - last_time:.1f}s ago)")
            return

        self._last_command_time[cmd] = now

        dispatch = {
            "/status":    self._cmd_status,
            "/positions": self._cmd_positions,
            "/pnl":       self._cmd_pnl,
            "/scan":      self._cmd_scan,
            "/pause":     self._cmd_pause,
            "/resume":    self._cmd_resume,
            "/squareoff": self._cmd_squareoff,
            "/help":      self._cmd_help,
        }

        if cmd == "/close":
            try:
                self._cmd_close(args[0].upper() if args else "")
            except Exception as e:
                logger.error(f"Close error: {e}")
                self.alert.send(f"⚠️ /close failed: {e}")
        elif cmd in dispatch:
            try:
                logger.info(f"Executing command: {cmd}")
                dispatch[cmd]()
                logger.info(f"Command {cmd} executed successfully")
            except Exception as e:
                logger.error(f"Command {cmd} failed: {e}")
                self.alert.send(f"⚠️ Command failed: {e}")
        else:
            self.alert.send(f"Unknown command: <b>{cmd}</b>\nType /help for all commands.")

    # ── Commands ────────────────────────────────────────────────

    def _cmd_status(self):
        positions = self.trader.positions
        capital = self.trader.capital
        short_count = sum(1 for p in positions.values() if p.get("side") == "SHORT")
        long_count = len(positions) - short_count
        mode_emoji = "💰" if self._mode == "live" else "📝"
        pause_status = "⏸ PAUSED" if self.paused else "▶️ RUNNING"
        now = datetime.now().strftime("%H:%M")

        self.alert.send(
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>📊 Bot Status — {now}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Mode: {mode_emoji} {self._mode.upper()}\n"
            f"Status: {pause_status}\n"
            f"Capital: ₹{capital:,.0f}\n"
            f"Positions: {len(positions)} ({long_count} LONG / {short_count} SHORT)\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    def _cmd_positions(self):
        positions = self.trader.positions
        if not positions:
            self.alert.send("📭 No open positions.")
            return

        tickers = [t.replace(":SHORT", "") for t in positions]
        prices = fetch_live_prices(tickers)

        now = datetime.now().strftime("%H:%M")
        msg = f"━━━━━━━━━━━━━━━━━━━━\n<b>📊 Positions — {now}</b>\n━━━━━━━━━━━━━━━━━━━━\n"

        total_unreal = 0
        for ticker, pos in positions.items():
            base = ticker.replace(":SHORT", "")
            name = base.replace(".NS", "")
            is_short = pos.get("side") == "SHORT"
            entry = pos["entry_price"]
            qty = pos["quantity"]
            sl = pos.get("stop_loss", 0)
            target = pos.get("target_2", pos.get("target", 0))
            current = prices.get(base, entry)

            unreal = ((entry - current) if is_short else (current - entry)) * qty
            total_unreal += unreal
            u_emoji = "🟢" if unreal >= 0 else "🔴"
            side = "🔻 SHORT" if is_short else "🟢 LONG"

            risk = abs(sl - entry) if sl else 1
            reward = abs(target - current) if target else 0
            rr = f"1:{reward/risk:.1f}" if risk > 0 else "—"

            msg += (
                f"\n<b>{name}</b> [{side}]\n"
                f"Entry: ₹{entry:,.2f} → Now: ₹{current:,.2f}\n"
                f"Qty: {qty} | {u_emoji} ₹{unreal:+,.0f}\n"
                f"SL: ₹{sl:,.2f} | T2: ₹{target:,.2f}\n"
                f"R:R remaining: {rr}\n"
            )

        t_emoji = "🟢" if total_unreal >= 0 else "🔴"
        msg += f"\n━━━━━━━━━━━━━━━━━━━━\n{t_emoji} <b>Unrealized: ₹{total_unreal:+,.0f}</b>"
        self.alert.send(msg)

    def _cmd_pnl(self):
        capital = self.trader.capital
        initial = config.INITIAL_CAPITAL
        pnl = capital - initial
        pnl_pct = (pnl / initial) * 100
        emoji = "🟢" if pnl >= 0 else "🔴"
        now = datetime.now().strftime("%H:%M")

        self.alert.send(
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>💰 P&L — {now}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Capital: ₹{capital:,.0f}\n"
            f"Started: ₹{initial:,.0f}\n"
            f"{emoji} P&L: ₹{pnl:+,.0f} ({pnl_pct:+.2f}%)\n"
            f"Open Positions: {len(self.trader.positions)}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    def _cmd_scan(self):
        """Trigger immediate stock scan (don't wait for next 15-min scan)."""
        if not self.scan_callback:
            self.alert.send("⚠️ Scan callback not configured")
            return

        self.alert.send("🔍 <b>Scanning all 46 stocks...</b> (this takes ~60 sec)")
        try:
            self.scan_callback()
            logger.info("Manual scan completed via Telegram command")
        except Exception as e:
            logger.error(f"Manual scan failed: {e}")
            self.alert.send(f"❌ Scan failed: {e}")

    def _cmd_close(self, symbol: str):
        if not symbol:
            self.alert.send("Usage: /close SYMBOL\nExample: <code>/close HDFCBANK</code>")
            return

        positions = self.trader.positions
        ticker = f"{symbol}.NS"
        short_key = f"{ticker}:SHORT"

        if ticker in positions:
            pos_key, is_short = ticker, False
        elif short_key in positions:
            pos_key, is_short = short_key, True
        else:
            self.alert.send(f"⚠️ No open position for <b>{symbol}</b>")
            return

        pos = positions[pos_key]
        qty = pos["quantity"]
        prices = fetch_live_prices([ticker])
        current = prices.get(ticker, pos["entry_price"])

        action = "COVER" if is_short else "SELL"
        trade = self.trader.place_order(pos_key if is_short else ticker, action, qty, current)
        pnl = trade.get("pnl", 0)
        self.risk_mgr.record_trade(pnl)

        if self.broker and self.broker.connected:
            dhan_action = "BUY" if is_short else "SELL"
            product = "INTRADAY" if is_short else config.ORDER_PRODUCT
            self.broker.place_order(symbol, dhan_action, qty, current, product=product)

        emoji = "🟢" if pnl >= 0 else "🔴"
        self.alert.send(
            f"{emoji} <b>MANUAL CLOSE — {symbol}</b>\n"
            f"{'SHORT COVERED' if is_short else 'SOLD'} @ ₹{current:,.2f}\n"
            f"Qty: {qty} | PnL: ₹{pnl:+,.0f}"
        )
        logger.info(f"Manual close: {symbol} {action} @ {current:.2f} | PnL: {pnl:+.0f}")

    def _cmd_pause(self):
        self.paused = True
        self.alert.send(
            "⏸ <b>Trading PAUSED</b>\n"
            "No new positions will be opened.\n"
            "Existing positions are still monitored.\n"
            "Use /resume to continue."
        )

    def _cmd_resume(self):
        self.paused = False
        self.alert.send("▶️ <b>Trading RESUMED</b>\nBot will open new positions again.")

    def _cmd_squareoff(self):
        positions = self.trader.positions
        if not positions:
            self.alert.send("📭 No positions to square off.")
            return

        self.alert.send(f"🚨 <b>EMERGENCY SQUARE-OFF</b>\nClosing all {len(positions)} positions...")
        tickers = [t.replace(":SHORT", "") for t in positions]
        prices = fetch_live_prices(tickers)

        total_pnl = 0
        detail = ""
        for pos_key, pos in list(positions.items()):
            base = pos_key.replace(":SHORT", "")
            name = base.replace(".NS", "")
            is_short = pos.get("side") == "SHORT"
            qty = pos["quantity"]
            current = prices.get(base, pos["entry_price"])

            action = "COVER" if is_short else "SELL"
            trade = self.trader.place_order(pos_key if is_short else base, action, qty, current)
            pnl = trade.get("pnl", 0)
            total_pnl += pnl
            self.risk_mgr.record_trade(pnl)

            if self.broker and self.broker.connected:
                dhan_action = "BUY" if is_short else "SELL"
                product = "INTRADAY" if is_short else config.ORDER_PRODUCT
                self.broker.place_order(name, dhan_action, qty, current, product=product)

            e = "🟢" if pnl >= 0 else "🔴"
            detail += f"  {e} {name}: ₹{pnl:+,.0f}\n"

        t_emoji = "🟢" if total_pnl >= 0 else "🔴"
        self.alert.send(
            f"✅ <b>SQUARE-OFF COMPLETE</b>\n\n"
            f"{detail}\n"
            f"{t_emoji} <b>Total PnL: ₹{total_pnl:+,.0f}</b>"
        )

    def _cmd_help(self):
        self.alert.send(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>📱 Bot Commands</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "/status — Bot status &amp; capital\n"
            "/positions — Open positions + P&amp;L\n"
            "/pnl — Total P&amp;L\n"
            "/scan — Scan all 46 stocks NOW (~60 sec)\n"
            "/close SYMBOL — Close one position\n"
            "  e.g. <code>/close HDFCBANK</code>\n"
            "/pause — Stop new trades\n"
            "/resume — Resume trading\n"
            "/squareoff — Close ALL positions 🚨\n"
            "/help — This message\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
