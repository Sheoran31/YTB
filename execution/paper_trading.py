"""
Paper trading — simulate order fills without real money.
Portfolio state persists across sessions via JSON file.
"""
import csv
import json
import os
from datetime import datetime
import config


class PaperTrader:
    def __init__(self, initial_capital: float = config.INITIAL_CAPITAL):
        self.capital = initial_capital
        self.positions: dict[str, dict] = {}  # symbol -> {quantity, entry_price, entry_date}
        self.trade_log: list[dict] = []

    def place_order(self, symbol: str, action: str, quantity: int, price: float) -> dict:
        """
        Simulate an order fill.

        Args:
            symbol: Stock ticker
            action: "BUY", "SELL", "SHORT", or "COVER"
            quantity: Number of shares
            price: Fill price

        Returns:
            Trade record dict
        """
        if action not in ("BUY", "SELL", "SHORT", "COVER"):
            raise ValueError(f"Invalid action: {action}. Must be BUY, SELL, SHORT, or COVER.")
        if quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}. Must be > 0.")
        if price <= 0:
            raise ValueError(f"Invalid price: {price}. Must be > 0.")

        trade = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "value": quantity * price,
        }

        if action == "BUY":
            cost = quantity * price
            if cost > self.capital:
                trade["status"] = "REJECTED — insufficient capital"
                self.trade_log.append(trade)
                return trade

            self.capital -= cost
            self.positions[symbol] = {
                "quantity": quantity,
                "entry_price": price,
                "entry_date": datetime.now().isoformat(),
            }
            trade["status"] = "FILLED"

        elif action == "SELL":
            if symbol not in self.positions:
                trade["status"] = "REJECTED — no position"
                self.trade_log.append(trade)
                return trade

            position = self.positions[symbol]
            held_qty = position["quantity"]

            if quantity >= held_qty:
                # Full exit — close entire position
                self.positions.pop(symbol)
                pnl = (price - position["entry_price"]) * held_qty
                self.capital += held_qty * price
                trade["quantity"] = held_qty
                trade["value"] = held_qty * price
            else:
                # Partial exit — reduce quantity, keep position open
                pnl = (price - position["entry_price"]) * quantity
                self.capital += quantity * price
                self.positions[symbol]["quantity"] = held_qty - quantity

            trade["pnl"] = pnl
            trade["status"] = "FILLED"

        elif action == "SHORT":
            # Paper short: block margin from capital (equal to position value)
            margin = quantity * price
            if margin > self.capital:
                trade["status"] = "REJECTED — insufficient capital for margin"
                self.trade_log.append(trade)
                return trade

            self.capital -= margin
            short_key = f"{symbol}:SHORT"
            self.positions[short_key] = {
                "quantity": quantity,
                "entry_price": price,
                "entry_date": datetime.now().isoformat(),
                "side": "SHORT",
                "margin_blocked": margin,
            }
            trade["status"] = "FILLED"

        elif action == "COVER":
            short_key = f"{symbol}:SHORT"
            if short_key not in self.positions:
                trade["status"] = "REJECTED — no short position"
                self.trade_log.append(trade)
                return trade

            position = self.positions[short_key]
            held_qty = position["quantity"]

            if quantity >= held_qty:
                # Full cover — close entire short
                self.positions.pop(short_key)
                pnl = (position["entry_price"] - price) * held_qty
                self.capital += position["margin_blocked"] + pnl
                trade["quantity"] = held_qty
                trade["value"] = held_qty * price
            else:
                # Partial cover
                pnl = (position["entry_price"] - price) * quantity
                partial_margin = (quantity / held_qty) * position["margin_blocked"]
                self.capital += partial_margin + pnl
                self.positions[short_key]["quantity"] = held_qty - quantity
                self.positions[short_key]["margin_blocked"] -= partial_margin

            trade["pnl"] = pnl
            trade["status"] = "FILLED"

        self.trade_log.append(trade)
        return trade

    def get_portfolio_value(self, current_prices: dict[str, float]) -> float:
        """Total value = cash + sum of position values (long + short unrealized PnL)."""
        position_value = 0
        for sym, pos in self.positions.items():
            if pos.get("side") == "SHORT":
                # Short: margin + unrealized PnL (entry - current)
                base_sym = sym.replace(":SHORT", "")
                current = current_prices.get(base_sym, pos["entry_price"])
                unrealized_pnl = (pos["entry_price"] - current) * pos["quantity"]
                position_value += pos["margin_blocked"] + unrealized_pnl
            else:
                current = current_prices.get(sym, pos["entry_price"])
                position_value += pos["quantity"] * current
        return self.capital + position_value

    def save_trade_log(self, filepath: str = config.TRADE_LOG_FILE):
        """Save all trades to CSV."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        if not self.trade_log:
            return

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.trade_log[0].keys())
            writer.writeheader()
            writer.writerows(self.trade_log)

    def save_state(self, filepath=None, risk_state=None):
        """Save portfolio state to JSON. Persists capital & positions across sessions."""
        filepath = filepath or config.PORTFOLIO_STATE_FILE
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        state = {
            "capital": self.capital,
            "positions": self.positions,
            "last_saved": datetime.now().isoformat(),
        }
        if risk_state:
            state["risk"] = risk_state
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2, default=str)

    @classmethod
    def load_state(cls, filepath=None):
        """
        Load portfolio state from file.
        Returns (PaperTrader with loaded state, risk_state dict).
        If no file or corrupted, returns fresh PaperTrader.
        """
        filepath = filepath or config.PORTFOLIO_STATE_FILE
        if not os.path.exists(filepath):
            return cls(), {}
        try:
            with open(filepath) as f:
                state = json.load(f)
            trader = cls(state.get("capital", config.INITIAL_CAPITAL))
            trader.positions = state.get("positions", {})
            risk_state = state.get("risk", {})
            return trader, risk_state
        except (json.JSONDecodeError, KeyError, TypeError):
            return cls(), {}
