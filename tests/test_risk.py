"""
Tests for risk management — every circuit breaker must work.
Run with: python -m pytest tests/test_risk.py -v
"""
from datetime import datetime
from risk.manager import RiskManager


# ============================================================
# CIRCUIT BREAKER TESTS
# ============================================================

def test_daily_loss_limit():
    """Stop trading if down 2% in a day."""
    rm = RiskManager()
    rm.daily_pnl = -2500  # -2.5% on 100k
    can_trade, reason = rm.can_open_position(
        100_000, [], 5000, check_time=datetime(2026, 3, 24, 10, 0)
    )
    assert can_trade is False
    assert "Daily loss" in reason


def test_max_drawdown():
    """Stop all trading if down 5% from peak."""
    rm = RiskManager()
    rm.peak_portfolio_value = 100_000
    # Portfolio dropped to 94,000 = 6% drawdown
    can_trade, reason = rm.can_open_position(
        94_000, [], 4000, check_time=datetime(2026, 3, 24, 10, 0)
    )
    assert can_trade is False
    assert "Max drawdown" in reason


def test_max_positions():
    """Never hold more than 5 positions."""
    rm = RiskManager()
    positions = ["A", "B", "C", "D", "E"]
    can_trade, reason = rm.can_open_position(
        100_000, positions, 5000, check_time=datetime(2026, 3, 24, 10, 0)
    )
    assert can_trade is False
    assert "Max positions" in reason


def test_position_too_large():
    """Never put more than 5% in one stock."""
    rm = RiskManager()
    can_trade, reason = rm.can_open_position(
        100_000, [], 10_000, check_time=datetime(2026, 3, 24, 10, 0)
    )
    assert can_trade is False
    assert "too large" in reason


def test_consecutive_losses_breaker():
    """Stop after 3 consecutive losses."""
    rm = RiskManager()
    rm.record_trade(-100)
    rm.record_trade(-100)
    rm.record_trade(-100)
    can_trade, reason = rm.can_open_position(
        100_000, [], 5000, check_time=datetime(2026, 3, 24, 10, 0)
    )
    assert can_trade is False
    assert "Circuit breaker" in reason


def test_pre_close_cutoff():
    """No new positions after 3:00 PM."""
    rm = RiskManager()
    # 3:15 PM — past cutoff
    can_trade, reason = rm.can_open_position(
        100_000, [], 4000, check_time=datetime(2026, 3, 24, 15, 15)
    )
    assert can_trade is False
    assert "cutoff" in reason.lower()


def test_friday_rule():
    """No new positions after Friday 2:00 PM."""
    rm = RiskManager()
    # Friday March 27, 2026 at 2:30 PM
    friday = datetime(2026, 3, 27, 14, 30)
    assert friday.weekday() == 4  # Verify it's Friday
    can_trade, reason = rm.can_open_position(
        100_000, [], 4000, check_time=friday
    )
    assert can_trade is False
    assert "Friday" in reason


def test_friday_morning_ok():
    """Friday morning should still allow trading."""
    rm = RiskManager()
    friday_morning = datetime(2026, 3, 27, 10, 0)
    can_trade, reason = rm.can_open_position(
        100_000, [], 4000, check_time=friday_morning
    )
    assert can_trade is True


# ============================================================
# STATE TRACKING TESTS
# ============================================================

def test_winning_trade_resets_losses():
    rm = RiskManager()
    rm.record_trade(-100)
    rm.record_trade(-100)
    rm.record_trade(200)  # Win resets consecutive losses
    assert rm.consecutive_losses == 0


def test_peak_tracking():
    rm = RiskManager()
    rm.update_peak(110_000)
    assert rm.peak_portfolio_value == 110_000
    rm.update_peak(105_000)  # Lower value doesn't update peak
    assert rm.peak_portfolio_value == 110_000


def test_daily_reset():
    rm = RiskManager()
    rm.daily_pnl = -500
    rm.trades_today = 3
    rm.reset_daily(portfolio_value=102_000)
    assert rm.daily_pnl == 0.0
    assert rm.trades_today == 0
    assert rm.peak_portfolio_value == 102_000


# ============================================================
# POSITION SIZING TESTS
# ============================================================

def test_position_sizing():
    rm = RiskManager()
    # Portfolio 100k, entry 1000, stop loss 980 -> risk per share = 20
    # Risk amount = 100k * 0.01 = 1000 -> quantity = 1000/20 = 50
    qty = rm.calculate_position_size(100_000, 1000, 980)
    assert qty == 50


def test_zero_quantity_not_forced_to_one():
    rm = RiskManager()
    # 100 INR capital, entry 1000, stop 980 -> risk = 1 INR, per share = 20
    qty = rm.calculate_position_size(100, 1000, 980)
    assert qty == 0


def test_stop_loss_calculation():
    rm = RiskManager()
    # Entry 1000, ATR 25, multiplier 2 -> stop = 1000 - 50 = 950
    stop = rm.calculate_stop_loss(1000, 25)
    assert stop == 950.0


def test_zero_risk_per_share():
    """If entry == stop loss, don't trade."""
    rm = RiskManager()
    qty = rm.calculate_position_size(100_000, 1000, 1000)
    assert qty == 0


# ============================================================
# OK TO TRADE — HAPPY PATH
# ============================================================

def test_ok_to_trade():
    rm = RiskManager()
    can_trade, reason = rm.can_open_position(
        100_000, [], 4000, check_time=datetime(2026, 3, 24, 10, 0)
    )
    assert can_trade is True
    assert "OK" in reason


# ============================================================
# STRESS TEST — simulate a bad trading day
# ============================================================

def test_bad_day_simulation():
    """Simulate losing trades until circuit breaker stops us."""
    rm = RiskManager()
    portfolio = 100_000.0
    blocked_reason = None

    for i in range(10):
        can_trade, reason = rm.can_open_position(
            portfolio, [], 4000, check_time=datetime(2026, 3, 24, 10, 0)
        )
        if not can_trade:
            blocked_reason = reason
            break
        # Simulate a -500 INR loss each trade
        rm.record_trade(-500)
        portfolio -= 500

    assert blocked_reason is not None
    # Should be blocked by consecutive losses (3 in a row) before daily loss limit
    assert "Circuit breaker" in blocked_reason
