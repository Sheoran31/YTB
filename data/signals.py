"""
Technical indicators — all calculated from scratch, no external libraries.
"""
import pandas as pd
import numpy as np


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return prices.rolling(window=period).mean()


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average — reacts faster than SMA to price changes."""
    return prices.ewm(span=period, adjust=False).mean()


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """
    MACD (Moving Average Convergence Divergence).
    Returns (macd_line, signal_line, histogram).
    BUY when histogram turns positive (MACD crosses above signal).
    SELL when histogram turns negative.
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average Directional Index — measures trend STRENGTH (not direction).
    ADX > 25 = strong trend (good for momentum). ADX < 20 = sideways (avoid).
    """
    plus_dm = high.diff()
    minus_dm = -low.diff()

    # +DM: positive when today's high > yesterday's high AND that move > down move
    plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > minus_dm), 0.0)
    # -DM: positive when today's low < yesterday's low AND that move > up move
    minus_dm = minus_dm.where((minus_dm > 0) & (minus_dm > plus_dm), 0.0)

    atr = calculate_atr(high, low, close, period)

    # Smoothed +DI and -DI
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

    # DX and ADX
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1))
    adx = dx.ewm(span=period, adjust=False).mean()

    return adx


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (0-100).

    Uses Wilder's smoothing method (exponential moving average).
    """
    delta = prices.diff()

    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)

    # First average: simple mean of first `period` values
    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()

    # Wilder's smoothing for subsequent values
    for i in range(period, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gains.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + losses.iloc[i]) / period

    # Handle division by zero: if no losses, RSI = 100; if no gains, RSI = 0
    rs = np.where(avg_loss == 0, np.inf, avg_gain / avg_loss)
    rs = pd.Series(rs, index=prices.index)
    rsi = 100 - (100 / (1 + rs))
    # Where both gains and losses are 0 (flat prices), set RSI to 50
    flat = (avg_gain == 0) & (avg_loss == 0)
    rsi[flat] = 50.0

    return rsi


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range — measures volatility."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()

    return atr


def calculate_volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    """Current volume / average volume over `period` days."""
    avg_volume = volume.rolling(window=period).mean()
    return volume / avg_volume


def detect_crossover(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """
    Detect crossovers between two series.
    Returns: 1 for golden cross (fast crosses above slow),
             -1 for death cross (fast crosses below slow),
             0 for no crossover.
    """
    prev_fast = fast.shift(1)
    prev_slow = slow.shift(1)

    golden = (prev_fast <= prev_slow) & (fast > slow)
    death = (prev_fast >= prev_slow) & (fast < slow)

    signal = pd.Series(0, index=fast.index)
    signal[golden] = 1
    signal[death] = -1

    return signal
