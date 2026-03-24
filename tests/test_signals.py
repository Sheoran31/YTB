"""
Tests for technical indicator calculations.
Run with: python -m pytest tests/test_signals.py -v
"""
import pandas as pd
import numpy as np
from data.signals import calculate_sma, calculate_rsi, calculate_atr, detect_crossover


def test_sma_basic():
    prices = pd.Series([10, 20, 30, 40, 50])
    sma = calculate_sma(prices, period=3)
    assert sma.iloc[-1] == 40.0  # (30+40+50)/3


def test_rsi_rising_prices():
    """RSI on consistently rising prices should be > 70."""
    prices = pd.Series(range(100, 150))
    rsi = calculate_rsi(prices, period=14)
    assert rsi.iloc[-1] > 70


def test_rsi_falling_prices():
    """RSI on consistently falling prices should be < 30."""
    prices = pd.Series(range(150, 100, -1))
    rsi = calculate_rsi(prices, period=14)
    assert rsi.iloc[-1] < 30


def test_rsi_flat_prices():
    """RSI on flat prices should be 50 (no gains, no losses = neutral)."""
    prices = pd.Series([100.0] * 50)
    rsi = calculate_rsi(prices, period=14)
    last = rsi.iloc[-1]
    assert last == 50.0


def test_rsi_range():
    """RSI should always be between 0 and 100."""
    np.random.seed(42)
    prices = pd.Series(np.random.uniform(90, 110, 100))
    rsi = calculate_rsi(prices, period=14)
    valid = rsi.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_crossover_golden():
    """Detect golden cross (fast crosses above slow)."""
    fast = pd.Series([10, 10, 10, 12])
    slow = pd.Series([11, 11, 11, 11])
    signal = detect_crossover(fast, slow)
    assert signal.iloc[-1] == 1


def test_crossover_death():
    """Detect death cross (fast crosses below slow)."""
    fast = pd.Series([12, 12, 12, 10])
    slow = pd.Series([11, 11, 11, 11])
    signal = detect_crossover(fast, slow)
    assert signal.iloc[-1] == -1
