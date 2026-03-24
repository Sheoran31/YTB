"""
Zerodha Kite Connect broker integration.

Setup:
    1. pip install kiteconnect
    2. Get API key from developer.zerodha.com
    3. Set environment variables:
        export KITE_API_KEY="your_key"
        export KITE_API_SECRET="your_secret"
    4. Run get_access_token() once to authorize via browser

Usage:
    broker = ZerodhaBroker()
    broker.connect()
    ltp = broker.get_ltp("NSE:RELIANCE")
    broker.place_order("RELIANCE", "BUY", 1, ltp)
"""
import os
from datetime import datetime, time

import config
from monitoring.logger import setup_logger

logger = setup_logger("broker")


class ZerodhaBroker:
    def __init__(self):
        self.api_key = os.getenv("KITE_API_KEY")
        self.api_secret = os.getenv("KITE_API_SECRET")
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")
        self.kite = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to Kite API. Returns True if successful."""
        if not self.api_key:
            logger.error("KITE_API_KEY not set. Run: export KITE_API_KEY='your_key'")
            return False

        try:
            from kiteconnect import KiteConnect
        except ImportError:
            logger.error("kiteconnect not installed. Run: pip install kiteconnect")
            return False

        self.kite = KiteConnect(api_key=self.api_key)

        if self.access_token:
            self.kite.set_access_token(self.access_token)
            self.connected = True
            logger.info("Connected to Zerodha Kite (using saved access token)")
            return True

        # Need to generate access token via browser login
        login_url = self.kite.login_url()
        logger.info(f"Open this URL in your browser to authorize:\n{login_url}")
        logger.info("After login, you'll get a request_token in the redirect URL.")
        logger.info("Run: broker.set_access_token(request_token) to complete setup.")
        return False

    def set_access_token(self, request_token: str):
        """Exchange request_token for access_token (one-time setup)."""
        if not self.kite or not self.api_secret:
            logger.error("Call connect() first and set KITE_API_SECRET")
            return

        data = self.kite.generate_session(request_token, api_secret=self.api_secret)
        self.access_token = data["access_token"]
        self.kite.set_access_token(self.access_token)
        self.connected = True
        logger.info(f"Access token generated. Save it:")
        logger.info(f"export KITE_ACCESS_TOKEN='{self.access_token}'")

    def get_ltp(self, symbol: str) -> float | None:
        """Get Last Traded Price for a symbol (e.g., 'NSE:RELIANCE')."""
        if not self.connected:
            logger.error("Not connected. Call connect() first.")
            return None

        try:
            data = self.kite.ltp(symbol)
            return data[symbol]["last_price"]
        except Exception as e:
            logger.error(f"Failed to get LTP for {symbol}: {e}")
            return None

    def get_multiple_ltp(self, symbols: list[str]) -> dict[str, float]:
        """Get LTP for multiple symbols."""
        if not self.connected:
            return {}

        try:
            data = self.kite.ltp(symbols)
            return {sym: info["last_price"] for sym, info in data.items()}
        except Exception as e:
            logger.error(f"Failed to get LTP: {e}")
            return {}

    def place_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        order_type: str = "LIMIT",
        product: str = "MIS",  # MIS = intraday, CNC = delivery
    ) -> str | None:
        """
        Place an order on Zerodha.

        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            action: "BUY" or "SELL"
            quantity: Number of shares
            price: Limit price
            order_type: "LIMIT" or "MARKET"
            product: "MIS" (intraday) or "CNC" (delivery)

        Returns:
            Order ID if successful, None on failure
        """
        if not self.connected:
            logger.error("Not connected. Call connect() first.")
            return None

        # Safety checks
        if action not in ("BUY", "SELL"):
            logger.error(f"Invalid action: {action}")
            return None
        if quantity <= 0:
            logger.error(f"Invalid quantity: {quantity}")
            return None
        if price <= 0:
            logger.error(f"Invalid price: {price}")
            return None

        # Market hours check
        now = datetime.now().time()
        market_open = time(config.MARKET_OPEN_HOUR, config.MARKET_OPEN_MINUTE)
        market_close = time(config.MARKET_CLOSE_HOUR, config.MARKET_CLOSE_MINUTE)
        if not (market_open <= now <= market_close):
            logger.warning(f"Market closed. Order for {symbol} queued for next open.")
            return None

        transaction_type = (
            self.kite.TRANSACTION_TYPE_BUY if action == "BUY"
            else self.kite.TRANSACTION_TYPE_SELL
        )

        try:
            order_id = self.kite.place_order(
                exchange="NSE",
                tradingsymbol=symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                product=product,
                variety="regular",
                order_type=order_type,
                price=price if order_type == "LIMIT" else None,
            )
            logger.info(f"Order placed: {action} {quantity} {symbol} @ {price} | ID: {order_id}")
            return order_id
        except Exception as e:
            logger.error(f"Order failed: {action} {quantity} {symbol} @ {price} | Error: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if not self.connected:
            return False

        try:
            self.kite.cancel_order(variety="regular", order_id=order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Cancel failed for {order_id}: {e}")
            return False

    def get_positions(self) -> list[dict]:
        """Get current open positions."""
        if not self.connected:
            return []

        try:
            positions = self.kite.positions()
            return positions.get("net", [])
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
