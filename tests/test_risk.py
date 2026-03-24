"""
Tests for risk management.
Run with: python -m pytest tests/test_risk.py -v
"""
from risk.manager import RiskManager


def test_daily_loss_limit():
    rm = RiskManager()
    rm.daily_pnl = -2500  # -2.5% on 100k
    can_trade, reason = rm.can_open_position(100_000, [], 5000)
    assert can_trade is False
    assert "Daily loss" in reason


def test_max_positions():
    rm = RiskManager()
    positions = ["A", "B", "C", "D", "E"]  # 5 positions
    can_trade, reason = rm.can_open_position(100_000, positions, 5000)
    assert can_trade is False
    assert "Max positions" in reason


def test_position_too_large():
    rm = RiskManager()
    # Trying to put 10% in one stock (limit is 5%)
    can_trade, reason = rm.can_open_position(100_000, [], 10_000)
    assert can_trade is False
    assert "too large" in reason


def test_consecutive_losses_breaker():
    rm = RiskManager()
    rm.record_trade(-100)
    rm.record_trade(-100)
    rm.record_trade(-100)  # 3 consecutive losses
    can_trade, reason = rm.can_open_position(100_000, [], 5000)
    assert can_trade is False
    assert "Circuit breaker" in reason


def test_winning_trade_resets_losses():
    rm = RiskManager()
    rm.record_trade(-100)
    rm.record_trade(-100)
    rm.record_trade(200)  # Win resets consecutive losses
    assert rm.consecutive_losses == 0


def test_position_sizing():
    rm = RiskManager()
    # Portfolio 100k, entry 1000, stop loss 980 -> risk per share = 20
    # Risk amount = 100k * 0.01 = 1000 -> quantity = 1000/20 = 50
    qty = rm.calculate_position_size(100_000, 1000, 980)
    assert qty == 50


def test_stop_loss_calculation():
    rm = RiskManager()
    # Entry 1000, ATR 25, multiplier 2 -> stop = 1000 - 50 = 950
    stop = rm.calculate_stop_loss(1000, 25)
    assert stop == 950.0


def test_ok_to_trade():
    rm = RiskManager()
    can_trade, reason = rm.can_open_position(100_000, [], 4000)
    assert can_trade is True
    assert "OK" in reason


def test_peak_tracking():
    rm = RiskManager()
    rm.update_peak(110_000)
    assert rm.peak_portfolio_value == 110_000
    rm.update_peak(105_000)  # Lower value shouldn't update peak
    assert rm.peak_portfolio_value == 110_000


def test_zero_quantity_not_forced_to_one():
    rm = RiskManager()
    # Very tight stop: risk_per_share = 0.5, risk_amount = 1000
    # quantity = int(1000 / 0.5) = 2000 — OK
    # But if capital is tiny: risk_amount = 1, risk_per_share = 20
    # quantity = int(1/20) = 0 — should stay 0, not become 1
    qty = rm.calculate_position_size(100, 1000, 980)  # 100 INR capital
    assert qty == 0  # 100 * 0.01 = 1 INR risk / 20 per share = 0
