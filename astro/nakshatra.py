"""
Vedic Nakshatra (Lunar Mansion) calculations for trading.

The Moon transits through 27 Nakshatras, each spanning 13°20' of the zodiac.
Each Nakshatra has distinct energy affecting market sentiment.

Uses sidereal zodiac (Lahiri Ayanamsa) for Vedic accuracy.

Widely followed in Indian markets — can create self-fulfilling effects.
"""
import ephem
import math
from datetime import datetime


# Lahiri Ayanamsa for 2026 (approximate: 24.2 degrees)
# Ayanamsa increases ~50.3 arcseconds per year from the J2000 epoch
# J2000 Lahiri Ayanamsa ≈ 23.85°, so for 2026: ~24.22°
AYANAMSA_2026 = 24.22

# All 27 Nakshatras with trading sentiment
NAKSHATRAS = [
    {"name": "Ashwini",            "ruler": "Ketu",    "sentiment": "BULLISH",  "note": "Fresh starts, speed — good for new positions"},
    {"name": "Bharani",            "ruler": "Venus",   "sentiment": "BEARISH",  "note": "Destruction, transformation — expect corrections"},
    {"name": "Krittika",           "ruler": "Sun",     "sentiment": "BEARISH",  "note": "Sharp cuts, burning — sharp selloffs"},
    {"name": "Rohini",             "ruler": "Moon",    "sentiment": "BULLISH",  "note": "Growth, wealth — strong stocks rally"},
    {"name": "Mrigashira",         "ruler": "Mars",    "sentiment": "NEUTRAL",  "note": "Searching, indecisive markets"},
    {"name": "Ardra",              "ruler": "Rahu",    "sentiment": "BEARISH",  "note": "Storm, turmoil — high volatility"},
    {"name": "Punarvasu",          "ruler": "Jupiter", "sentiment": "BULLISH",  "note": "Recovery, renewal — bounce-back days"},
    {"name": "Pushya",             "ruler": "Saturn",  "sentiment": "BULLISH",  "note": "MOST AUSPICIOUS — best day for investments"},
    {"name": "Ashlesha",           "ruler": "Mercury", "sentiment": "BEARISH",  "note": "Deception, manipulation — false signals"},
    {"name": "Magha",              "ruler": "Ketu",    "sentiment": "NEUTRAL",  "note": "Power shifts, authority sectors"},
    {"name": "Purva Phalguni",     "ruler": "Venus",   "sentiment": "BULLISH",  "note": "Pleasure, luxury stocks favored"},
    {"name": "Uttara Phalguni",    "ruler": "Sun",     "sentiment": "BULLISH",  "note": "Stable gains, blue-chip stocks"},
    {"name": "Hasta",              "ruler": "Moon",    "sentiment": "BULLISH",  "note": "Skill, precision — good for calculated trades"},
    {"name": "Chitra",             "ruler": "Mars",    "sentiment": "NEUTRAL",  "note": "Mixed energy, can go either way"},
    {"name": "Swati",              "ruler": "Rahu",    "sentiment": "NEUTRAL",  "note": "Scattered energy, volatile but tradeable"},
    {"name": "Vishakha",           "ruler": "Jupiter", "sentiment": "NEUTRAL",  "note": "Determination but also instability"},
    {"name": "Anuradha",           "ruler": "Saturn",  "sentiment": "BULLISH",  "note": "Research-based trading, long-term investments"},
    {"name": "Jyeshtha",           "ruler": "Mercury", "sentiment": "BEARISH",  "note": "Conflict, power struggles"},
    {"name": "Moola",              "ruler": "Ketu",    "sentiment": "BEARISH",  "note": "Root destruction — market bottoms/crashes"},
    {"name": "Purva Ashadha",      "ruler": "Venus",   "sentiment": "NEUTRAL",  "note": "Early victory, partial success"},
    {"name": "Uttara Ashadha",     "ruler": "Sun",     "sentiment": "BULLISH",  "note": "Final victory, strong completions"},
    {"name": "Shravana",           "ruler": "Moon",    "sentiment": "BULLISH",  "note": "Listening, learning — good research day"},
    {"name": "Dhanishta",          "ruler": "Mars",    "sentiment": "BULLISH",  "note": "Wealth, prosperity — strong buy days"},
    {"name": "Shatabhisha",        "ruler": "Rahu",    "sentiment": "NEUTRAL",  "note": "Healing, secretive — hidden moves"},
    {"name": "Purva Bhadrapada",   "ruler": "Jupiter", "sentiment": "NEUTRAL",  "note": "Intense energy, risky trades"},
    {"name": "Uttara Bhadrapada",  "ruler": "Saturn",  "sentiment": "NEUTRAL",  "note": "Deep, slow — patience needed"},
    {"name": "Revati",             "ruler": "Mercury", "sentiment": "BULLISH",  "note": "Completion, profitable exits"},
]

BULLISH_NAKSHATRAS = {n["name"] for n in NAKSHATRAS if n["sentiment"] == "BULLISH"}
BEARISH_NAKSHATRAS = {n["name"] for n in NAKSHATRAS if n["sentiment"] == "BEARISH"}
NEUTRAL_NAKSHATRAS = {n["name"] for n in NAKSHATRAS if n["sentiment"] == "NEUTRAL"}


def get_moon_nakshatra(dt: datetime | None = None) -> dict:
    """
    Calculate which Nakshatra the Moon is currently in (Vedic/Sidereal).

    Returns:
        {
            "nakshatra": "Pushya",
            "index": 7,
            "ruler": "Saturn",
            "sentiment": "BULLISH",
            "note": "MOST AUSPICIOUS — best day for investments",
            "moon_longitude_sidereal": 103.5,
            "position_multiplier": 1.2,   # boost for bullish, reduce for bearish
            "allow_buy": True,
        }
    """
    dt = dt or datetime.now()
    date_str = dt.strftime("%Y/%m/%d %H:%M:%S")

    # Get Moon's ecliptic longitude (tropical)
    moon = ephem.Moon()
    moon.compute(date_str)

    # Convert to degrees (ephem gives radians for ecliptic longitude)
    # Use moon.hlong for heliocentric, but we need geocentric ecliptic
    # ephem.Ecliptic gives us ecliptic coordinates
    ecliptic = ephem.Ecliptic(moon)
    tropical_lon = math.degrees(float(ecliptic.lon))

    # Convert tropical to sidereal (subtract ayanamsa)
    # Adjust ayanamsa for current year
    year = dt.year
    ayanamsa = AYANAMSA_2026 + (year - 2026) * (50.3 / 3600)  # ~50.3"/year
    sidereal_lon = (tropical_lon - ayanamsa) % 360

    # Each Nakshatra spans 13°20' = 13.3333°
    nakshatra_span = 360 / 27  # 13.3333°
    index = int(sidereal_lon / nakshatra_span)
    index = min(index, 26)  # safety clamp

    nakshatra = NAKSHATRAS[index]

    # Position multiplier based on sentiment
    if nakshatra["sentiment"] == "BULLISH":
        multiplier = 1.2  # 20% boost
        if nakshatra["name"] == "Pushya":
            multiplier = 1.3  # Extra boost for most auspicious
    elif nakshatra["sentiment"] == "BEARISH":
        multiplier = 0.5  # 50% reduction
    else:
        multiplier = 1.0  # Neutral

    return {
        "nakshatra": nakshatra["name"],
        "index": index,
        "ruler": nakshatra["ruler"],
        "sentiment": nakshatra["sentiment"],
        "note": nakshatra["note"],
        "moon_longitude_sidereal": round(sidereal_lon, 2),
        "position_multiplier": multiplier,
        "allow_buy": nakshatra["sentiment"] != "BEARISH",
    }


def get_vara(dt: datetime | None = None) -> dict:
    """
    Get Vara (day of week) with Vedic trading significance.

    Returns:
        {"vara": "Thursday", "ruler": "Jupiter", "sentiment": "BULLISH", "note": "..."}
    """
    dt = dt or datetime.now()
    weekday = dt.weekday()  # 0=Monday

    VARAS = [
        {"vara": "Monday",    "ruler": "Moon",    "sentiment": "NEUTRAL",  "note": "Emotional trading, watch sentiment shifts"},
        {"vara": "Tuesday",   "ruler": "Mars",    "sentiment": "VOLATILE", "note": "Aggressive moves, high volatility"},
        {"vara": "Wednesday", "ruler": "Mercury", "sentiment": "NEUTRAL",  "note": "Good for analysis, IT/communication stocks"},
        {"vara": "Thursday",  "ruler": "Jupiter", "sentiment": "BULLISH",  "note": "Most auspicious — banking/finance favored"},
        {"vara": "Friday",    "ruler": "Venus",   "sentiment": "BULLISH",  "note": "Luxury/consumer stocks, tend to be positive"},
        {"vara": "Saturday",  "ruler": "Saturn",  "sentiment": "BEARISH",  "note": "Market closed — but plan cautiously for Monday"},
        {"vara": "Sunday",    "ruler": "Sun",     "sentiment": "NEUTRAL",  "note": "Market closed"},
    ]

    return VARAS[weekday]
