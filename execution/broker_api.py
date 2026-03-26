"""
Dhan broker integration.

Setup:
    1. pip install dhanhq
    2. Create account at dhan.co, open Demat
    3. Go to web.dhan.co → Profile → "Access DhanHQ APIs" → Generate token
    4. Set environment variables:
        export DHAN_CLIENT_ID="your_client_id"
        export DHAN_ACCESS_TOKEN="your_token"

    Token validity: up to 30 days (set when generating).
    No daily login like Zerodha — much simpler.

Usage:
    broker = DhanBroker()
    broker.connect()
    ltp = broker.get_ltp("RELIANCE")
    broker.place_order("RELIANCE", "BUY", 1, ltp)
"""
import os
from datetime import datetime, time

import config
from monitoring.logger import setup_logger

logger = setup_logger("broker")


# ── Ticker → Dhan Security ID mapping (NSE Equity) ──────────
# Dhan uses numeric security_id, not trading symbols.
# These are NSE scrip codes. Download full list:
#   https://images.dhan.co/api-data/api-scrip-master.csv
# Or via SDK: dhan.fetch_security_list(mode='compact')
SECURITY_IDS = {
    # Banking & Finance
    "RELIANCE":    2885,
    "HDFCBANK":    1333,
    "ICICIBANK":   4963,
    "SBIN":       3045,
    "KOTAKBANK":   1922,
    "AXISBANK":    5900,
    "BAJFINANCE":  317,
    "BAJAJFINSV":  16675,
    "HDFCLIFE":    467,
    "SBILIFE":     21808,
    # IT
    "TCS":         11536,
    "INFY":        1594,
    "WIPRO":       3787,
    "HCLTECH":     7229,
    "TECHM":       13538,
    "LTIM":        17818,
    # Consumer & FMCG
    "HINDUNILVR":  1394,
    "ITC":         1660,
    "NESTLEIND":   17963,
    "BRITANNIA":   547,
    "TATACONSUM":  3432,
    # Auto
    "MARUTI":      10999,
    "SHRIRAMFIN":  3002,
    "M&M":         2031,
    "BAJAJ-AUTO":  16669,
    "HEROMOTOCO":  1348,
    # Energy & Metals
    "BHARTIARTL":  10604,
    "NTPC":        11630,
    "POWERGRID":   14977,
    "ONGC":        2475,
    "COALINDIA":   20374,
    "TATASTEEL":   3499,
    "HINDALCO":    1363,
    "JSWSTEEL":    11723,
    # Pharma & Health
    "SUNPHARMA":   3351,
    "DRREDDY":     881,
    "CIPLA":       694,
    "APOLLOHOSP":  157,
    # Others
    "ADANIENT":    25,
    "ADANIPORTS":  15083,
    "TITAN":       3506,
    "ULTRACEMCO":  11532,
    "GRASIM":      1232,
    "ASIANPAINT":  236,
    "DIVISLAB":    10940,
    "EICHERMOT":   910,
    "INDUSINDBK":  5258,
}


def get_security_id(symbol: str) -> str | None:
    """Convert trading symbol to Dhan security_id string.

    Accepts either 'RELIANCE' or 'RELIANCE.NS' format.
    """
    clean = symbol.replace(".NS", "").replace(".BO", "")
    sec_id = SECURITY_IDS.get(clean)
    if sec_id is None:
        logger.error(f"Security ID not found for {symbol}. Add it to SECURITY_IDS in broker_api.py")
        return None
    return str(sec_id)


class DhanBroker:
    def __init__(self):
        self.client_id = os.getenv("DHAN_CLIENT_ID")
        self.access_token = os.getenv("DHAN_ACCESS_TOKEN")
        self.dhan = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to Dhan API. Returns True if successful."""
        if not self.client_id:
            logger.error("DHAN_CLIENT_ID not set. Run: export DHAN_CLIENT_ID='your_id'")
            return False
        if not self.access_token:
            logger.error("DHAN_ACCESS_TOKEN not set. Run: export DHAN_ACCESS_TOKEN='your_token'")
            return False

        try:
            from dhanhq import dhanhq
        except ImportError:
            logger.error("dhanhq not installed. Run: pip install dhanhq")
            return False

        try:
            self.dhan = dhanhq(client_id=self.client_id, access_token=self.access_token)
            self.connected = True
            logger.info(f"Connected to Dhan (client: {self.client_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Dhan: {e}")
            return False

    def get_ltp(self, symbol: str) -> float | None:
        """Get Last Traded Price for a symbol (e.g., 'RELIANCE' or 'RELIANCE.NS')."""
        if not self.connected:
            logger.error("Not connected. Call connect() first.")
            return None

        sec_id = get_security_id(symbol)
        if not sec_id:
            return None

        try:
            data = self.dhan.ticker_data(securities={"NSE_EQ": [int(sec_id)]})
            if data.get("status") == "success":
                # ticker_data returns nested data by security ID
                tick_data = data.get("data", {})
                if tick_data:
                    for entry in tick_data.values() if isinstance(tick_data, dict) else [tick_data]:
                        if isinstance(entry, dict) and "last_price" in entry:
                            return float(entry["last_price"])
                    # Fallback: try first value
                    first = next(iter(tick_data.values())) if isinstance(tick_data, dict) else tick_data
                    if isinstance(first, dict):
                        return float(first.get("last_price", first.get("LTP", 0)))
            logger.error(f"Unexpected LTP response for {symbol}: {data}")
            return None
        except Exception as e:
            logger.error(f"Failed to get LTP for {symbol}: {e}")
            return None

    def get_multiple_ltp(self, symbols: list[str]) -> dict[str, float]:
        """Get LTP for multiple symbols."""
        if not self.connected:
            return {}

        sec_ids = []
        id_to_symbol = {}
        for sym in symbols:
            sec_id = get_security_id(sym)
            if sec_id:
                sec_ids.append(int(sec_id))
                id_to_symbol[sec_id] = sym

        if not sec_ids:
            return {}

        try:
            data = self.dhan.ticker_data(securities={"NSE_EQ": sec_ids})
            result = {}
            if data.get("status") == "success":
                for sec_id_str, info in data.get("data", {}).items():
                    sym = id_to_symbol.get(str(sec_id_str), sec_id_str)
                    if isinstance(info, dict):
                        price = info.get("last_price", info.get("LTP", 0))
                        result[sym] = float(price)
            return result
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
        product: str = "CNC",  # CNC = delivery (default), INTRADAY = intraday
    ) -> str | None:
        """
        Place an order on Dhan.

        Args:
            symbol: Trading symbol (e.g., "RELIANCE" or "RELIANCE.NS")
            action: "BUY" or "SELL"
            quantity: Number of shares
            price: Limit price (0 for MARKET orders)
            order_type: "LIMIT" or "MARKET"
            product: "INTRADAY" or "CNC" (delivery)

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
        if price <= 0 and order_type == "LIMIT":
            logger.error(f"Invalid price for LIMIT order: {price}")
            return None

        sec_id = get_security_id(symbol)
        if not sec_id:
            return None

        # Market hours check
        now = datetime.now().time()
        market_open = time(config.MARKET_OPEN_HOUR, config.MARKET_OPEN_MINUTE)
        market_close = time(config.MARKET_CLOSE_HOUR, config.MARKET_CLOSE_MINUTE)
        if not (market_open <= now <= market_close):
            logger.warning(f"Market closed. Order for {symbol} not placed.")
            return None

        try:
            response = self.dhan.place_order(
                security_id=sec_id,
                exchange_segment=self.dhan.NSE,
                transaction_type=self.dhan.BUY if action == "BUY" else self.dhan.SELL,
                quantity=quantity,
                order_type=self.dhan.LIMIT if order_type == "LIMIT" else self.dhan.MARKET,
                product_type=self.dhan.INTRA if product == "INTRADAY" else self.dhan.CNC,
                price=price if order_type == "LIMIT" else 0,
            )

            if response.get("status") == "success":
                order_id = response["data"]["orderId"]
                logger.info(f"Order placed: {action} {quantity} {symbol} @ {price} | ID: {order_id}")
                return order_id
            else:
                logger.error(f"Order rejected: {action} {quantity} {symbol} @ {price} | {response.get('remarks', response)}")
                return None
        except Exception as e:
            logger.error(f"Order failed: {action} {quantity} {symbol} @ {price} | Error: {e}")
            return None

    def place_sl_order(
        self,
        symbol: str,
        quantity: int,
        trigger_price: float,
        limit_price: float = 0,
        product: str = "CNC",
    ) -> str | None:
        """
        Place a Stop Loss SELL order on Dhan.
        Exchange handles execution — instant, even on gap downs.

        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            quantity: Number of shares to sell
            trigger_price: Price at which SL activates
            limit_price: Sell price after activation (0 = market)
            product: "CNC" or "INTRADAY"

        Returns:
            Order ID if successful, None on failure
        """
        if not self.connected:
            logger.error("Not connected. Call connect() first.")
            return None

        sec_id = get_security_id(symbol)
        if not sec_id:
            return None

        try:
            # SL-M (Stop Loss Market) if no limit price, else SL-L (Stop Loss Limit)
            order_type = self.dhan.SL if limit_price > 0 else self.dhan.SLM
            price = limit_price if limit_price > 0 else 0

            response = self.dhan.place_order(
                security_id=sec_id,
                exchange_segment=self.dhan.NSE,
                transaction_type=self.dhan.SELL,
                quantity=quantity,
                order_type=order_type,
                product_type=self.dhan.INTRA if product == "INTRADAY" else self.dhan.CNC,
                price=price,
                trigger_price=trigger_price,
            )

            if response.get("status") == "success":
                order_id = response["data"]["orderId"]
                logger.info(f"SL order placed: SELL {quantity} {symbol} trigger@{trigger_price} | ID: {order_id}")
                return order_id
            else:
                logger.error(f"SL order rejected: {symbol} | {response.get('remarks', response)}")
                return None
        except Exception as e:
            logger.error(f"SL order failed: {symbol} | {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if not self.connected:
            return False

        try:
            response = self.dhan.cancel_order(order_id=order_id)
            if response.get("status") == "success":
                logger.info(f"Order cancelled: {order_id}")
                return True
            else:
                logger.error(f"Cancel failed for {order_id}: {response.get('remarks', response)}")
                return False
        except Exception as e:
            logger.error(f"Cancel failed for {order_id}: {e}")
            return False

    def get_positions(self) -> list[dict]:
        """Get current open positions."""
        if not self.connected:
            return []

        try:
            response = self.dhan.get_positions()
            if response.get("status") == "success":
                return response.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    def get_order_list(self) -> list[dict]:
        """Get all orders for today."""
        if not self.connected:
            return []

        try:
            response = self.dhan.get_order_list()
            if response.get("status") == "success":
                return response.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []

    def get_holdings(self) -> list[dict]:
        """Get delivery holdings."""
        if not self.connected:
            return []

        try:
            response = self.dhan.get_holdings()
            if response.get("status") == "success":
                return response.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get holdings: {e}")
            return []
