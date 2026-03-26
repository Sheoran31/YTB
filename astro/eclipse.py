"""
Eclipse detection and avoidance for trading.

Rules:
  - No new trades 3 days before/after any eclipse
  - Eclipses mark major trend reversals (within 2 weeks)
  - Reduce existing positions by 50% in eclipse window

2026-2027 eclipse dates (pre-calculated from NASA data).
"""
from datetime import datetime, date, timedelta

import config

# Eclipse dates for 2026-2027
ECLIPSE_DATES = [
    # 2026
    {"date": "2026-02-17", "type": "Partial Solar",  "sign": "Aquarius"},
    {"date": "2026-03-03", "type": "Total Lunar",    "sign": "Virgo"},
    {"date": "2026-08-12", "type": "Annular Solar",  "sign": "Leo"},
    {"date": "2026-08-28", "type": "Partial Lunar",  "sign": "Pisces"},
    # 2027
    {"date": "2027-02-06", "type": "Annular Solar",  "sign": "Aquarius"},
    {"date": "2027-02-20", "type": "Penumbral Lunar", "sign": "Leo"},
    {"date": "2027-07-18", "type": "Penumbral Lunar", "sign": "Capricorn"},
    {"date": "2027-08-02", "type": "Total Solar",    "sign": "Leo"},
]


def check_eclipse(dt: datetime | None = None) -> dict:
    """
    Check if we're in an eclipse avoidance window.

    Returns:
        {
            "in_eclipse_window": True/False,
            "nearest_eclipse": "2026-03-03",
            "eclipse_type": "Total Lunar",
            "eclipse_sign": "Virgo",
            "days_to_eclipse": -2,         # negative = past, positive = future
            "is_eclipse_day": False,
            "position_multiplier": 0.5,    # reduce positions
            "allow_new_trades": False,
            "message": "Eclipse window — Total Lunar in 2 days"
        }
    """
    dt = dt or datetime.now()
    today = dt.date()
    buffer_days = config.ECLIPSE_BUFFER_DAYS

    nearest = None
    nearest_days = 999

    for eclipse in ECLIPSE_DATES:
        eclipse_date = datetime.strptime(eclipse["date"], "%Y-%m-%d").date()
        days_diff = (eclipse_date - today).days

        if abs(days_diff) < abs(nearest_days):
            nearest_days = days_diff
            nearest = eclipse

    if nearest is None:
        return _no_eclipse()

    eclipse_date = datetime.strptime(nearest["date"], "%Y-%m-%d").date()
    in_window = abs(nearest_days) <= buffer_days
    is_eclipse_day = nearest_days == 0

    if in_window:
        if is_eclipse_day:
            msg = f"ECLIPSE TODAY — {nearest['type']} in {nearest['sign']}. DO NOT TRADE."
            multiplier = 0.0  # Block all
        elif nearest_days > 0:
            msg = f"Eclipse in {nearest_days} days ({nearest['type']}) — reduce exposure"
            multiplier = 0.5
        else:
            msg = f"Eclipse was {abs(nearest_days)} days ago — watch for trend reversal"
            multiplier = 0.7
    else:
        msg = f"No eclipse nearby. Next: {nearest['date']} ({nearest['type']})"
        multiplier = 1.0

    return {
        "in_eclipse_window": in_window,
        "nearest_eclipse": nearest["date"],
        "eclipse_type": nearest["type"],
        "eclipse_sign": nearest["sign"],
        "days_to_eclipse": nearest_days,
        "is_eclipse_day": is_eclipse_day,
        "position_multiplier": multiplier,
        "allow_new_trades": not in_window,
        "message": msg,
    }


def _no_eclipse():
    return {
        "in_eclipse_window": False,
        "nearest_eclipse": None,
        "eclipse_type": None,
        "eclipse_sign": None,
        "days_to_eclipse": 999,
        "is_eclipse_day": False,
        "position_multiplier": 1.0,
        "allow_new_trades": True,
        "message": "No eclipse data available for this period",
    }
