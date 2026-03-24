"""
Configuration — all settings in one place.
Modify this file to change trading behavior. Never hardcode values elsewhere.
"""

# ============================================================
# CAPITAL & BROKER
# ============================================================
INITIAL_CAPITAL = 100_000  # INR — start with paper trading
BROKER = "zerodha"  # "zerodha" or "paper"

# Zerodha Kite Connect credentials (set via environment variables, NOT here)
# export KITE_API_KEY="your_key"
# export KITE_API_SECRET="your_secret"

# ============================================================
# STOCKS TO TRACK (Nifty 50 subset)
# ============================================================
WATCHLIST = [
    # Large Cap — Banking & Finance
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "KOTAKBANK.NS",
    "AXISBANK.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "HDFCLIFE.NS",
    "SBILIFE.NS",
    # Large Cap — IT
    "TCS.NS",
    "INFY.NS",
    "WIPRO.NS",
    "HCLTECH.NS",
    "TECHM.NS",
    "LTIM.NS",
    # Large Cap — Consumer & FMCG
    "HINDUNILVR.NS",
    "ITC.NS",
    "NESTLEIND.NS",
    "BRITANNIA.NS",
    "TATACONSUM.NS",
    # Large Cap — Auto
    "MARUTI.NS",
    "SHRIRAMFIN.NS",
    "M&M.NS",
    "BAJAJ-AUTO.NS",
    "HEROMOTOCO.NS",
    # Large Cap — Energy & Metals
    "BHARTIARTL.NS",
    "NTPC.NS",
    "POWERGRID.NS",
    "ONGC.NS",
    "COALINDIA.NS",
    "TATASTEEL.NS",
    "HINDALCO.NS",
    "JSWSTEEL.NS",
    # Large Cap — Pharma & Health
    "SUNPHARMA.NS",
    "DRREDDY.NS",
    "CIPLA.NS",
    "APOLLOHOSP.NS",
    # Large Cap — Others
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "TITAN.NS",
    "ULTRACEMCO.NS",
    "GRASIM.NS",
    "ASIANPAINT.NS",
    "DIVISLAB.NS",
    "EICHERMOT.NS",
    "INDUSINDBK.NS",
]

# ============================================================
# STRATEGY PARAMETERS
# ============================================================
SMA_FAST = 20          # Fast moving average period
SMA_SLOW = 50          # Slow moving average period
RSI_PERIOD = 14        # RSI calculation period
RSI_BUY_THRESHOLD = 55  # Only buy when RSI > this
RSI_SELL_THRESHOLD = 45  # Consider selling when RSI < this
ATR_PERIOD = 14        # ATR calculation period
VOLUME_RATIO_MIN = 1.5  # Minimum volume vs 20-day avg

# ============================================================
# RISK MANAGEMENT (DO NOT CHANGE WITHOUT UNDERSTANDING)
# ============================================================
MAX_DAILY_LOSS_PCT = 0.02       # Stop trading if down 2% in a day
MAX_DRAWDOWN_PCT = 0.05         # Stop trading if down 5% from peak
MAX_POSITION_PCT = 0.05         # Max 5% of capital in one stock
MAX_TOTAL_POSITIONS = 5         # Max 5 open positions at once
RISK_PER_TRADE_PCT = 0.01      # Risk 1% of capital per trade
STOP_LOSS_ATR_MULT = 2.0       # Stop loss = Entry - (2 × ATR)
CONSECUTIVE_LOSS_LIMIT = 3     # Circuit breaker after 3 losses

# ============================================================
# MARKET HOURS (IST)
# ============================================================
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30
NO_NEW_POSITIONS_AFTER_HOUR = 15  # No new trades after 3:00 PM
NO_NEW_POSITIONS_AFTER_MINUTE = 0

# ============================================================
# BROKER COSTS (Zerodha)
# ============================================================
BROKER_COSTS = {
    "brokerage": 0.0003,  # 0.03%
    "stt": 0.0005,        # Securities Transaction Tax
    "gst": 0.18,          # GST on brokerage
}

# ============================================================
# LOGGING
# ============================================================
LOG_DIR = "logs"
TRADE_LOG_FILE = "logs/trade_log.csv"
