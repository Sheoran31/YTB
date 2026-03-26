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
            action: "BUY" or "SELL"
            quantity: Number of shares
            price: Fill price

        Returns:
            Trade record dict
        """
        if action not in ("BUY", "SELL"):
            raise ValueError(f"Invalid action: {action}. Must be BUY or SELL.")
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

            position = self.positions.pop(symbol)
            pnl = (price - position["entry_price"]) * position["quantity"]
            self.capital += position["quantity"] * price
            trade["pnl"] = pnl
            trade["status"] = "FILLED"

        self.trade_log.append(trade)
        return trade

    def get_portfolio_value(self, current_prices: dict[str, float]) -> float:
        """Total value = cash + sum of position values."""
        position_value = sum(
            pos["quantity"] * current_prices.get(sym, pos["entry_price"])
            for sym, pos in self.positions.items()
        )
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
