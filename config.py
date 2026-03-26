"""
Configuration — all settings in one place.
Modify this file to change trading behavior. Never hardcode values elsewhere.
"""

# ============================================================
# MARKET (Indian stock market only — do not change without
# updating watchlist, holidays, and broker integration)
# ============================================================
MARKET = "INDIA"  # NSE/BSE only

# ============================================================
# CAPITAL & BROKER
# ============================================================
INITIAL_CAPITAL = 100_000  # INR — start with paper trading
BROKER = "dhan"  # "dhan" or "paper"
ORDER_PRODUCT = "CNC"  # "CNC" = delivery, "INTRADAY" = intraday

# Dhan credentials (set via environment variables, NOT here)
# export DHAN_CLIENT_ID="your_client_id"
# export DHAN_ACCESS_TOKEN="your_token"
# Token validity: up to 30 days (set when generating at web.dhan.co)

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
# QUANTITY MODE
# ============================================================
# "auto"  = bot calculates qty based on risk per trade & stop loss (ATR-based)
# "fixed" = use FIXED_QUANTITY for every trade
# "capital" = invest CAPITAL_PER_TRADE amount per trade (qty = amount / price)
QUANTITY_MODE = "auto"
FIXED_QUANTITY = 1              # Used when QUANTITY_MODE = "fixed"
CAPITAL_PER_TRADE = 10_000     # Used when QUANTITY_MODE = "capital" (INR per trade)

# ============================================================
# RISK MANAGEMENT (DO NOT CHANGE WITHOUT UNDERSTANDING)
# ============================================================
MAX_DAILY_LOSS_PCT = 0.02       # Stop trading if down 2% in a day
MAX_DRAWDOWN_PCT = 0.05         # Stop trading if down 5% from peak
MAX_POSITION_PCT = 0.20         # Max 20% of capital in one stock
MAX_TOTAL_POSITIONS = 5         # Max 5 open positions at once
RISK_PER_TRADE_PCT = 0.01      # Risk 1% of capital per trade
STOP_LOSS_ATR_MULT = 2.0       # Stop loss = Entry - (2 × ATR)
CONSECUTIVE_LOSS_LIMIT = 3     # Circuit breaker after 3 losses
DAILY_PROFIT_TARGET_PCT = 0.03  # Stop trading if up 3% in a day (book profits)
MAX_LOSS_PER_TRADE = 1_000     # Max loss allowed per single trade (INR)

# ============================================================
# TARGET & TRAILING STOP
# ============================================================
RISK_REWARD_RATIO = 2.0           # Target = Entry + (risk × 2). 1:2 R:R minimum
TRAILING_STOP_ENABLED = True      # Move stop loss up as price rises
POSITION_CHECK_SECONDS = 60       # Check held positions every 60 sec (real-time SL/target)

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
# AUTO MODE
# ============================================================
SCAN_INTERVAL_MINUTES = 15        # Scan every 15 minutes in auto mode
MODE_REPLY_TIMEOUT = 300          # Seconds to wait for Telegram paper/live reply (5 min)

# ============================================================
# PORTFOLIO PERSISTENCE (balance carries across sessions)
# ============================================================
PORTFOLIO_STATE_FILE = "logs/portfolio_state.json"

# ============================================================
# BROKER COSTS (Dhan)
# ============================================================
BROKER_COSTS = {
    "brokerage": 0.0003,  # 0.03% (Dhan intraday) — delivery is Rs 0
    "stt": 0.0005,        # Securities Transaction Tax
    "gst": 0.18,          # GST on brokerage
}

# ============================================================
# ASTRO TRADING FILTERS
# ============================================================
ASTRO_ENABLED = True              # Master switch for all astro filters
MOON_PHASE_FILTER = True          # Adjust position size by moon phase
MERCURY_RETROGRADE_FILTER = True  # Reduce/block trades during retrograde
NAKSHATRA_FILTER = True           # Vedic nakshatra daily filter
ECLIPSE_FILTER = True             # Avoid trading around eclipses
RAHU_KAAL_FILTER = True           # Block trades during Rahu Kaal
ECLIPSE_BUFFER_DAYS = 3           # Days before/after eclipse to avoid

# ============================================================
# NSE HOLIDAYS (update yearly — source: nseindia.com)
# ============================================================
NSE_HOLIDAYS = {
    # ── 2026 ──
    "2026-01-26": "Republic Day",
    "2026-02-17": "Maha Shivaratri",
    "2026-03-10": "Holi",
    "2026-03-26": "Jamat Ul-Vida",
    "2026-03-31": "Id-Ul-Fitr (Eid)",
    "2026-04-02": "Ram Navami",
    "2026-04-03": "Good Friday",
    "2026-04-14": "Dr. Ambedkar Jayanti",
    "2026-05-01": "Maharashtra Day",
    "2026-05-25": "Buddha Purnima",
    "2026-07-17": "Muharram",
    "2026-08-15": "Independence Day",
    "2026-08-28": "Janmashtami",
    "2026-10-02": "Mahatma Gandhi Jayanti",
    "2026-10-20": "Dussehra",
    "2026-11-09": "Diwali (Laxmi Puja)",
    "2026-11-10": "Diwali (Balipratipada)",
    "2026-11-27": "Guru Nanak Jayanti",
    "2026-12-25": "Christmas",
    # ── 2027 (add when NSE publishes) ──
}

# ============================================================
# LOGGING
# ============================================================
LOG_DIR = "logs"
TRADE_LOG_FILE = "logs/trade_log.csv"
