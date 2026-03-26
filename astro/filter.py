"""
Astro Filter — combines all astrological signals into one trading decision.

This is the MAIN entry point for astro-trading integration.
It takes the existing technical signal (BUY/SELL/HOLD) and adjusts it
based on celestial conditions.

Usage:
    from astro.filter import AstroFilter
    astro = AstroFilter()
    result = astro.evaluate(signal="BUY", price=1419.0)
    # result["final_signal"] → "BUY" or "HOLD" (blocked)
    # result["quantity_multiplier"] → 0.5 to 1.3 (adjust position size)
    # result["suggested_stop"] → Gann S1 level
    # result["suggested_target"] → Gann R1 level
"""
from datetime import datetime

import config
from astro.moon import get_moon_phase, BULLISH_PHASES
from astro.mercury import is_mercury_retrograde
from astro.nakshatra import get_moon_nakshatra, get_vara
from astro.eclipse import check_eclipse
from astro.rahu_kaal import check_rahu_kaal
from astro.gann import gann_levels
from monitoring.logger import setup_logger

logger = setup_logger("astro")


class AstroFilter:
    """
    Combines all astro signals into a single filter decision.

    Flow:
        Technical Signal (BUY/SELL)
            → Moon Phase (adjust size)
            → Mercury Retrograde (block/reduce)
            → Nakshatra (allow/block)
            → Rahu Kaal (block if active)
            → Eclipse (block if in window)
            → Gann Levels (stop/target)
            → Final Decision
    """

    def __init__(self):
        self.enabled = config.ASTRO_ENABLED

    def evaluate(
        self,
        signal: str,
        price: float = 0.0,
        dt: datetime | None = None,
    ) -> dict:
        """
        Evaluate a trading signal through all astro filters.

        Args:
            signal: "BUY", "SELL", or "HOLD" from technical analysis
            price: Current stock price (for Gann levels)
            dt: Optional datetime override (for backtesting)

        Returns:
            {
                "original_signal": "BUY",
                "final_signal": "BUY" or "HOLD",
                "quantity_multiplier": 0.65,    # combined multiplier
                "blocked": False,
                "block_reasons": [],
                "astro_score": 72,              # 0-100 (higher = more favorable)
                "suggested_stop": 1381.7,       # Gann S1
                "suggested_target": 1456.8,     # Gann R1
                "details": { ... all sub-filter results ... }
            }
        """
        if not self.enabled:
            return self._pass_through(signal, price)

        dt = dt or datetime.now()

        # ── Run all filters ────────────────────────────────
        moon = get_moon_phase(dt)
        mercury = is_mercury_retrograde(dt)
        nakshatra = get_moon_nakshatra(dt)
        eclipse = check_eclipse(dt)
        rahu = check_rahu_kaal(dt)
        vara = get_vara(dt)
        gann = gann_levels(price) if price > 0 else {}

        # ── Calculate combined multiplier ──────────────────
        multipliers = []
        block_reasons = []

        # Moon Phase filter
        if config.MOON_PHASE_FILTER:
            multipliers.append(moon["position_multiplier"])
            if signal == "BUY" and not moon["is_bullish"]:
                logger.info(f"  ASTRO Moon: {moon['phase_name']} (bearish) — reducing size")

        # Mercury Retrograde filter
        if config.MERCURY_RETROGRADE_FILTER:
            multipliers.append(mercury["position_multiplier"])
            if mercury["is_retrograde"] and signal == "BUY":
                block_reasons.append(f"Mercury Retrograde (day {mercury['days_in_retrograde']})")
                logger.info(f"  ASTRO Mercury: RETROGRADE — blocking new BUY")
            elif mercury["is_shadow"] and mercury["status"] == "SHADOW_PRE":
                logger.info(f"  ASTRO Mercury: Shadow period — caution")

        # Nakshatra filter
        if config.NAKSHATRA_FILTER:
            multipliers.append(nakshatra["position_multiplier"])
            if signal == "BUY" and not nakshatra["allow_buy"]:
                block_reasons.append(f"Bearish Nakshatra: {nakshatra['nakshatra']} ({nakshatra['note']})")
                logger.info(f"  ASTRO Nakshatra: {nakshatra['nakshatra']} (bearish) — blocking BUY")

        # Eclipse filter
        if config.ECLIPSE_FILTER:
            multipliers.append(eclipse["position_multiplier"])
            if not eclipse["allow_new_trades"]:
                block_reasons.append(f"Eclipse window: {eclipse['eclipse_type']} on {eclipse['nearest_eclipse']}")
                logger.info(f"  ASTRO Eclipse: {eclipse['message']}")

        # Rahu Kaal filter
        if config.RAHU_KAAL_FILTER:
            if not rahu["allow_new_trades"] and signal == "BUY":
                block_reasons.append(f"Rahu Kaal active ({rahu['rahu_kaal_start']}-{rahu['rahu_kaal_end']})")
                logger.info(f"  ASTRO Rahu Kaal: {rahu['message']}")

        # ── Combine multipliers ────────────────────────────
        combined_multiplier = 1.0
        for m in multipliers:
            combined_multiplier *= m

        # Clamp between 0.0 and 1.5
        combined_multiplier = max(0.0, min(1.5, combined_multiplier))

        # ── Final decision ─────────────────────────────────
        blocked = False
        final_signal = signal

        if signal == "BUY" and block_reasons:
            blocked = True
            final_signal = "HOLD"  # Block the buy
            combined_multiplier = 0.0

        # SELL signals are never blocked by astro (safety first)
        if signal == "SELL":
            final_signal = "SELL"
            blocked = False
            # But if moon is bearish, that confirms the sell
            if not moon.get("is_bullish", True):
                combined_multiplier = 1.0  # Full sell

        # ── Astro Score (0-100) ────────────────────────────
        astro_score = self._calculate_score(moon, mercury, nakshatra, eclipse, rahu, vara)

        # ── Gann levels ────────────────────────────────────
        suggested_stop = gann.get("suggested_stop", 0) if gann else 0
        suggested_target = gann.get("suggested_target", 0) if gann else 0

        result = {
            "original_signal": signal,
            "final_signal": final_signal,
            "quantity_multiplier": round(combined_multiplier, 2),
            "blocked": blocked,
            "block_reasons": block_reasons,
            "astro_score": astro_score,
            "suggested_stop": suggested_stop,
            "suggested_target": suggested_target,
            "details": {
                "moon": moon,
                "mercury": mercury,
                "nakshatra": nakshatra,
                "eclipse": eclipse,
                "rahu_kaal": rahu,
                "vara": vara,
                "gann": gann,
            },
        }

        # Log summary
        self._log_summary(result)
        return result

    def get_daily_report(self, dt: datetime | None = None) -> str:
        """Generate a human-readable daily astro report for logging/Telegram."""
        dt = dt or datetime.now()

        moon = get_moon_phase(dt)
        mercury = is_mercury_retrograde(dt)
        nakshatra = get_moon_nakshatra(dt)
        eclipse = check_eclipse(dt)
        rahu = check_rahu_kaal(dt)
        vara = get_vara(dt)

        lines = [
            f"{'='*50}",
            f"ASTRO DAILY REPORT — {dt.strftime('%Y-%m-%d %H:%M')}",
            f"{'='*50}",
            f"Moon Phase  : {moon['phase_name']} ({moon['illumination']}% lit)",
            f"  Bias      : {'BULLISH' if moon['is_bullish'] else 'BEARISH'}",
            f"  Next New  : {moon['days_to_new']:.0f} days",
            f"  Next Full : {moon['days_to_full']:.0f} days",
            f"",
            f"Mercury     : {mercury['status']}",
            f"  {mercury['message']}",
            f"",
            f"Nakshatra   : {nakshatra['nakshatra']} (ruled by {nakshatra['ruler']})",
            f"  Sentiment : {nakshatra['sentiment']}",
            f"  {nakshatra['note']}",
            f"",
            f"Vara (Day)  : {vara['vara']} (ruled by {vara['ruler']})",
            f"  Sentiment : {vara['sentiment']}",
            f"",
            f"Eclipse     : {eclipse['message']}",
            f"",
            f"Rahu Kaal   : {rahu['message']}",
            f"{'='*50}",
        ]

        return "\n".join(lines)

    def _calculate_score(self, moon, mercury, nakshatra, eclipse, rahu, vara) -> int:
        """Calculate overall astro favorability score (0-100)."""
        score = 50  # Start neutral

        # Moon phase: +/- 15 points
        if moon["is_bullish"]:
            score += 15
        else:
            score -= 15

        # Mercury: +/- 15 points
        if mercury["is_retrograde"]:
            score -= 15
        elif mercury["status"] == "SHADOW_POST":
            score += 10  # Just went direct = bullish
        elif mercury["status"] == "SHADOW_PRE":
            score -= 5

        # Nakshatra: +/- 15 points
        if nakshatra["sentiment"] == "BULLISH":
            score += 15
            if nakshatra["nakshatra"] == "Pushya":
                score += 5  # Bonus for most auspicious
        elif nakshatra["sentiment"] == "BEARISH":
            score -= 15

        # Eclipse: -20 points if in window
        if eclipse["in_eclipse_window"]:
            score -= 20
            if eclipse["is_eclipse_day"]:
                score -= 10  # Extra penalty

        # Rahu Kaal: -10 if active
        if rahu["is_inauspicious"]:
            score -= 10

        # Vara: +/- 5 points
        if vara["sentiment"] == "BULLISH":
            score += 5
        elif vara["sentiment"] == "BEARISH":
            score -= 5

        return max(0, min(100, score))

    def _log_summary(self, result: dict):
        """Log a one-line astro summary."""
        details = result["details"]
        moon_name = details["moon"]["phase_name"]
        mercury_status = details["mercury"]["status"]
        nakshatra_name = details["nakshatra"]["nakshatra"]
        score = result["astro_score"]

        if result["blocked"]:
            reasons = " | ".join(result["block_reasons"])
            logger.warning(
                f"ASTRO BLOCKED: {result['original_signal']} → HOLD | "
                f"Score: {score}/100 | Reasons: {reasons}"
            )
        else:
            logger.info(
                f"ASTRO: {result['original_signal']} → {result['final_signal']} | "
                f"Qty x{result['quantity_multiplier']} | Score: {score}/100 | "
                f"Moon: {moon_name} | Mercury: {mercury_status} | Nakshatra: {nakshatra_name}"
            )

    def _pass_through(self, signal: str, price: float) -> dict:
        """When astro is disabled, pass signal through unchanged."""
        gann = gann_levels(price) if price > 0 else {}
        return {
            "original_signal": signal,
            "final_signal": signal,
            "quantity_multiplier": 1.0,
            "blocked": False,
            "block_reasons": [],
            "astro_score": 50,
            "suggested_stop": gann.get("suggested_stop", 0) if gann else 0,
            "suggested_target": gann.get("suggested_target", 0) if gann else 0,
            "details": {},
        }
