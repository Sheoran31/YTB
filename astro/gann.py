"""
W.D. Gann Square of Nine — price level calculator.

The Square of Nine maps price to a spiral where each full revolution = 360°.
Support and resistance occur at specific angular intervals (90°, 180°, 270°, 360°).

Used for:
  - Setting stop-loss levels (support below entry)
  - Setting take-profit targets (resistance above entry)
  - Identifying key price levels for any stock

Formula:
  Next level up (N degrees) = (sqrt(price) + N/360)²
  Next level down (N degrees) = (sqrt(price) - N/360)²
"""
import math


def gann_levels(price: float) -> dict:
    """
    Calculate Gann Square of 9 support and resistance levels.

    Args:
        price: Current stock price

    Returns:
        {
            "price": 1419.0,
            "resistance": {
                "R1_90":  1456.8,  # 90° up
                "R2_180": 1495.1,  # 180° up
                "R3_270": 1533.9,  # 270° up
                "R4_360": 1573.2,  # 360° up (full cycle)
            },
            "support": {
                "S1_90":  1381.7,  # 90° down
                "S2_180": 1345.0,  # 180° down
                "S3_270": 1308.7,  # 270° down
                "S4_360": 1273.0,  # 360° down (full cycle)
            },
            "suggested_stop": 1381.7,   # S1 (nearest support)
            "suggested_target": 1456.8, # R1 (nearest resistance)
        }
    """
    if price <= 0:
        return {"price": price, "resistance": {}, "support": {},
                "suggested_stop": 0, "suggested_target": 0}

    sqrt_p = math.sqrt(price)

    resistance = {}
    support = {}

    for degrees, label in [(90, "R1_90"), (180, "R2_180"), (270, "R3_270"), (360, "R4_360")]:
        increment = degrees / 360.0
        level = (sqrt_p + increment) ** 2
        resistance[label] = round(level, 2)

    for degrees, label in [(90, "S1_90"), (180, "S2_180"), (270, "S3_270"), (360, "S4_360")]:
        increment = degrees / 360.0
        level = (sqrt_p - increment) ** 2
        if level > 0:
            support[label] = round(level, 2)
        else:
            support[label] = 0.0

    return {
        "price": price,
        "resistance": resistance,
        "support": support,
        "suggested_stop": support.get("S1_90", 0),
        "suggested_target": resistance.get("R1_90", 0),
    }


def gann_time_cycles(price: float) -> dict:
    """
    Gann planetary time cycles — natural market rhythms.

    These are common cycle lengths (in trading days) based on
    planetary orbital periods. Watch for trend changes at these intervals.
    """
    return {
        "moon_cycle": 21,        # ~29.5 calendar days = ~21 trading days
        "mercury_cycle": 63,     # ~88 calendar days = ~63 trading days
        "venus_cycle": 161,      # ~225 calendar days
        "mars_cycle": 487,       # ~687 calendar days (~2 years)
        "jupiter_cycle": 3000,   # ~11.86 years
        "saturn_cycle": 7500,    # ~29.5 years
        "gann_45_days": 45,      # Gann's 45-day cycle
        "gann_90_days": 90,      # Quarter year
        "gann_180_days": 180,    # Half year
        "gann_360_days": 360,    # Full year cycle
        "note": "Watch for trend reversals at these day intervals from major highs/lows",
    }
