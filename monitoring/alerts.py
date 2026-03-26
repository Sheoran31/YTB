"""
Telegram Alerts — get notified on your phone when signals trigger.

Setup:
    1. Create bot via @BotFather on Telegram
    2. Get your chat ID from: https://api.telegram.org/bot<TOKEN>/getUpdates
    3. Set environment variables:
        export TELEGRAM_BOT_TOKEN="your_bot_token"
        export TELEGRAM_CHAT_ID="your_chat_id"

Usage:
    from monitoring.alerts import TelegramAlert
    alert = TelegramAlert()
    alert.send("BUY signal: RELIANCE @ 1,411")
"""
import os
import time as time_module
import requests
from datetime import datetime

import config
from monitoring.logger import setup_logger

logger = setup_logger("alerts")


class TelegramAlert:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            logger.warning(
                "Telegram alerts disabled. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID."
            )

    def send(self, message: str) -> bool:
        """Send a message via Telegram. Returns True if successful."""
        if not self.enabled:
            logger.info(f"[ALERT not sent — Telegram not configured] {message}")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"Telegram alert sent: {message[:50]}...")
                return True
            else:
                logger.error(f"Telegram API error {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    def send_screener_results(self, results: list[dict]):
        """Send formatted screener results."""
        if not results:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        buy_stocks = [r for r in results if r["signal"] == "BUY"]
        sell_stocks = [r for r in results if r["signal"] != "BUY"]

        msg = f"<b>📊 SCREENER REPORT — {now}</b>\n"
        msg += f"Scanned: {len(results)} stocks\n\n"

        if buy_stocks:
            msg += "<b>🟢 BUY SIGNALS:</b>\n"
            for r in buy_stocks:
                msg += (
                    f"  <b>{r['symbol']}</b> @ ₹{r['price']:,.2f}\n"
                    f"    RSI: {r['rsi']} | Vol: {r['vol_ratio']}x | ATR: {r['atr']}\n"
                )
            msg += "\n"
        else:
            msg += "🔴 No BUY signals today.\n\n"

        # Top 5 closest to BUY (HOLD stocks sorted by RSI)
        hold_stocks = [r for r in results if r["signal"] == "SKIP" or r["signal"] == "HOLD"]
        # Sort by RSI descending to find closest to buy
        hold_stocks.sort(key=lambda x: x.get("rsi", 0), reverse=True)
        if hold_stocks[:5]:
            msg += "<b>👀 Watch List (closest to BUY):</b>\n"
            for r in hold_stocks[:5]:
                msg += f"  {r['symbol']} — RSI {r['rsi']}, {r['sma_20']}\n"

        msg += f"\n<i>Total: {len(buy_stocks)} BUY | {len(results) - len(buy_stocks)} SKIP</i>"

        self.send(msg)

    def send_trade_alert(self, action: str, ticker: str, price: float, quantity: int,
                         stop_loss: float = 0, target: float = 0, pnl: float = 0):
        """Send alert when a trade is placed."""
        symbol = ticker.replace(".NS", "")
        now = datetime.now().strftime("%H:%M:%S")

        if action == "BUY":
            risk = price - stop_loss if stop_loss else 0
            reward = target - price if target else 0
            rr = f"{reward / risk:.1f}" if risk > 0 else "—"
            msg = (
                f"🟢 <b>BUY ORDER</b> — {now}\n"
                f"<b>{symbol}</b> @ ₹{price:,.2f}\n"
                f"Qty: {quantity} | Value: ₹{quantity * price:,.0f}\n"
                f"Stop Loss: ₹{stop_loss:,.2f}\n"
                f"Target: ₹{target:,.2f}\n"
                f"R:R = 1:{rr}"
            )
        elif action == "SELL":
            emoji = "🟢" if pnl >= 0 else "🔴"
            msg = (
                f"{emoji} <b>SELL ORDER</b> — {now}\n"
                f"<b>{symbol}</b> @ ₹{price:,.2f}\n"
                f"Qty: {quantity} | PnL: ₹{pnl:+,.0f}"
            )
        else:
            msg = f"⚠️ <b>{action}</b> — {symbol} @ ₹{price:,.2f}"

        self.send(msg)

    def send_blocked_alert(self, ticker: str, reason: str):
        """Alert when risk manager blocks a trade."""
        symbol = ticker.replace(".NS", "")
        msg = f"⛔ <b>BLOCKED</b> — {symbol}\nReason: {reason}"
        self.send(msg)

    def send_daily_summary(self, portfolio_value: float, daily_pnl: float,
                           trades_today: int, positions: int):
        """End of day summary."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        emoji = "🟢" if daily_pnl >= 0 else "🔴"
        msg = (
            f"<b>📋 DAILY SUMMARY — {now}</b>\n\n"
            f"Portfolio: ₹{portfolio_value:,.0f}\n"
            f"Daily PnL: {emoji} ₹{daily_pnl:+,.0f}\n"
            f"Trades: {trades_today}\n"
            f"Open Positions: {positions}"
        )
        self.send(msg)

    def ask_trading_mode(self, timeout_seconds=None):
        """
        Ask user via Telegram to select Paper or Live mode.
        Polls getUpdates for a reply. Returns 'paper' or 'live'.
        Defaults to 'paper' if no reply or Telegram not configured.
        """
        timeout = timeout_seconds or config.MODE_REPLY_TIMEOUT

        if not self.enabled:
            logger.info("Telegram not configured — defaulting to PAPER mode")
            return "paper"

        # Get latest update_id to skip old messages
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        offset = 0
        try:
            resp = requests.get(url, params={"offset": -1, "timeout": 1}, timeout=5)
            data = resp.json()
            if data.get("ok") and data.get("result"):
                offset = data["result"][-1]["update_id"] + 1
        except Exception:
            pass

        # Send mode selection message
        self.send(
            "🤖 <b>Good Morning! Trading Bot Ready</b>\n\n"
            "Select mode for today:\n"
            "  Reply <b>paper</b> — Simulated trades\n"
            "  Reply <b>live</b> — Real money (Dhan)\n\n"
            f"⏳ Waiting {timeout // 60} min for reply...\n"
            "Default: <b>PAPER</b> (if no reply)"
        )

        # Poll for response
        start = time_module.time()
        while time_module.time() - start < timeout:
            try:
                resp = requests.get(url, params={
                    "offset": offset,
                    "timeout": 30,
                    "allowed_updates": ["message"],
                }, timeout=35)
                data = resp.json()

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    text = (msg.get("text") or "").strip().lower()

                    if chat_id == self.chat_id and text in ("paper", "live"):
                        self.send(f"✅ Selected: <b>{text.upper()}</b> trading for today")
                        return text
            except Exception:
                time_module.sleep(5)

        # Timeout — default to paper
        self.send("⏰ No reply received. Defaulting to <b>PAPER</b> trading.")
        logger.info("Mode selection timeout — defaulting to PAPER")
        return "paper"
