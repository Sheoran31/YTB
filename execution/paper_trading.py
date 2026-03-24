"""
Paper trading — simulate order fills without real money.
"""
import csv
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
