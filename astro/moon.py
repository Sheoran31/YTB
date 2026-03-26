"""
Moon Phase calculations for trading.

Academic basis:
  - Dichev & Janes (2003): New Moon returns ~2x Full Moon returns
  - Yuan, Zheng & Zhu (2006): Confirmed across 48 countries
  - Annualized difference: ~3-5%

Rules:
  - NEW_MOON / WAXING: Bullish → full position size
  - FULL_MOON / WANING: Bearish → reduce position size
"""
import ephem
from datetime import datetime


# Moon phase names
NEW_MOON = "NEW_MOON"
WAXING_CRESCENT = "WAXING_CRESCENT"
FIRST_QUARTER = "FIRST_QUARTER"
WAXING_GIBBOUS = "WAXING_GIBBOUS"
FULL_MOON = "FULL_MOON"
WANING_GIBBOUS = "WANING_GIBBOUS"
LAST_QUARTER = "LAST_QUARTER"
WANING_CRESCENT = "WANING_CRESCENT"

# Bullish phases (buy-friendly)
BULLISH_PHASES = {NEW_MOON, WAXING_CRESCENT, FIRST_QUARTER, WAXING_GIBBOUS}
# Bearish phases (sell-friendly / reduce size)
BEARISH_PHASES = {FULL_MOON, WANING_GIBBOUS, LAST_QUARTER, WANING_CRESCENT}


def get_moon_phase(dt: datetime | None = None) -> dict:
    """
    Get current moon phase details.

    Returns:
        {
            "phase_name": "WAXING_CRESCENT",
            "illumination": 23.5,       # 0-100%
            "is_bullish": True,
            "days_to_new": 22,
            "days_to_full": 8,
            "position_multiplier": 1.0,  # 1.0 = full, 0.5 = half
        }
    """
    dt = dt or datetime.now()
    date_str = dt.strftime("%Y/%m/%d %H:%M:%S")

    moon = ephem.Moon()
    moon.compute(date_str)
    illumination = moon.phase  # 0-100

    # Phase name based on illumination + waxing/waning
    phase_name = _classify_phase(dt, illumination)

    # Days to next new/full moon
    next_new = ephem.next_new_moon(date_str)
    next_full = ephem.next_full_moon(date_str)
    days_to_new = float(next_new - ephem.Date(date_str))
    days_to_full = float(next_full - ephem.Date(date_str))

    is_bullish = phase_name in BULLISH_PHASES

    # Position multiplier: 1.0 for bullish phases, reduced for bearish
    if phase_name == NEW_MOON:
        multiplier = 1.0  # Strongest buy signal
    elif phase_name in (WAXING_CRESCENT, WAXING_GIBBOUS):
        multiplier = 1.0
    elif phase_name == FIRST_QUARTER:
        multiplier = 0.9
    elif phase_name == FULL_MOON:
        multiplier = 0.5  # Strongest sell signal
    elif phase_name in (WANING_GIBBOUS, WANING_CRESCENT):
        multiplier = 0.6
    elif phase_name == LAST_QUARTER:
        multiplier = 0.7
    else:
        multiplier = 1.0

    return {
        "phase_name": phase_name,
        "illumination": round(illumination, 1),
        "is_bullish": is_bullish,
        "days_to_new": round(days_to_new, 1),
        "days_to_full": round(days_to_full, 1),
        "position_multiplier": multiplier,
    }


def _classify_phase(dt: datetime, illumination: float) -> str:
    """Classify moon phase name from illumination and waxing/waning state."""
    date_str = dt.strftime("%Y/%m/%d")

    # Determine if waxing or waning by comparing next new vs next full
    next_new = float(ephem.next_new_moon(date_str))
    next_full = float(ephem.next_full_moon(date_str))
    is_waxing = next_full < next_new  # Full comes before New = waxing

    if illumination < 3:
        return NEW_MOON
    elif illumination > 97:
        return FULL_MOON
    elif is_waxing:
        if illumination < 40:
            return WAXING_CRESCENT
        elif illumination < 60:
            return FIRST_QUARTER
        else:
            return WAXING_GIBBOUS
    else:
        if illumination > 60:
            return WANING_GIBBOUS
        elif illumination > 40:
            return LAST_QUARTER
        else:
            return WANING_CRESCENT
