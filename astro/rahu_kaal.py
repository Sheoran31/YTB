"""
Rahu Kaal — daily inauspicious time window in Vedic astrology.

Rule: Never initiate new trades during Rahu Kaal.
Each day has a ~1.5 hour window ruled by Rahu (malefic planet).

Rahu Kaal is calculated from sunrise. The timings below are approximate
for Indian Standard Time (IST) based on ~6:00 AM sunrise.
Actual times shift slightly with seasons.
"""
from datetime import datetime, time


# Rahu Kaal periods by weekday (approximate IST, assuming ~6 AM sunrise)
# Each period is ~1.5 hours (1/8th of daylight hours)
RAHU_KAAL = {
    0: {"start": time(7, 30),  "end": time(9, 0),   "day": "Monday"},     # Moon day
    1: {"start": time(15, 0),  "end": time(16, 30),  "day": "Tuesday"},    # Mars day
    2: {"start": time(12, 0),  "end": time(13, 30),  "day": "Wednesday"},  # Mercury day
    3: {"start": time(13, 30), "end": time(15, 0),   "day": "Thursday"},   # Jupiter day
    4: {"start": time(10, 30), "end": time(12, 0),   "day": "Friday"},     # Venus day
    5: {"start": time(9, 0),   "end": time(10, 30),  "day": "Saturday"},   # Saturn day
    6: {"start": time(16, 30), "end": time(18, 0),   "day": "Sunday"},     # Sun day
}

# Yamagandam — another inauspicious period (death-ruled)
YAMAGANDAM = {
    0: {"start": time(10, 30), "end": time(12, 0),  "day": "Monday"},
    1: {"start": time(9, 0),   "end": time(10, 30), "day": "Tuesday"},
    2: {"start": time(7, 30),  "end": time(9, 0),   "day": "Wednesday"},
    3: {"start": time(6, 0),   "end": time(7, 30),  "day": "Thursday"},
    4: {"start": time(15, 0),  "end": time(16, 30), "day": "Friday"},
    5: {"start": time(13, 30), "end": time(15, 0),  "day": "Saturday"},
    6: {"start": time(12, 0),  "end": time(13, 30), "day": "Sunday"},
}


def check_rahu_kaal(dt: datetime | None = None) -> dict:
    """
    Check if current time falls in Rahu Kaal or Yamagandam.

    Returns:
        {
            "in_rahu_kaal": True/False,
            "in_yamagandam": True/False,
            "is_inauspicious": True/False,     # Either one
            "rahu_kaal_start": "15:00",
            "rahu_kaal_end": "16:30",
            "allow_new_trades": True/False,
            "message": "Rahu Kaal active — avoid new trades until 16:30"
        }
    """
    dt = dt or datetime.now()
    weekday = dt.weekday()
    now = dt.time()

    rk = RAHU_KAAL.get(weekday)
    yg = YAMAGANDAM.get(weekday)

    in_rahu = rk and rk["start"] <= now <= rk["end"]
    in_yama = yg and yg["start"] <= now <= yg["end"]
    is_inauspicious = in_rahu or in_yama

    if in_rahu:
        msg = f"RAHU KAAL active ({rk['start'].strftime('%H:%M')}-{rk['end'].strftime('%H:%M')}) — avoid new trades"
    elif in_yama:
        msg = f"YAMAGANDAM active ({yg['start'].strftime('%H:%M')}-{yg['end'].strftime('%H:%M')}) — avoid new trades"
    else:
        next_rk = rk["start"].strftime("%H:%M") if rk else "N/A"
        msg = f"Clear — next Rahu Kaal at {next_rk}"

    return {
        "in_rahu_kaal": in_rahu,
        "in_yamagandam": in_yama,
        "is_inauspicious": is_inauspicious,
        "rahu_kaal_start": rk["start"].strftime("%H:%M") if rk else None,
        "rahu_kaal_end": rk["end"].strftime("%H:%M") if rk else None,
        "allow_new_trades": not is_inauspicious,
        "message": msg,
    }
