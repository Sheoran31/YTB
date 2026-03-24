"""
Momentum strategy — SMA crossover with RSI confirmation.

BUY when:
  - 20-day SMA crosses above 50-day SMA (golden cross)
  - RSI > 55 (momentum confirmed)
  - Volume > 1.5x 20-day average (institutional interest)

SELL when:
  - Price crosses below 20-day SMA
  - OR RSI < 45
"""
import pandas as pd
import numpy as np
from data.signals import calculate_sma, calculate_rsi, calculate_volume_ratio, detect_crossover
import config


def generate_signal(data: pd.DataFrame) -> str:
    """
    Analyze price data and return a trading signal.

    Args:
        data: OHLCV DataFrame (must have at least 50 rows)

    Returns:
        "BUY", "SELL", or "HOLD"
    """
    if len(data) < config.SMA_SLOW:
        return "HOLD"

    close = data["Close"].squeeze()
    volume = data["Volume"].squeeze()

    sma_fast = calculate_sma(close, config.SMA_FAST)
    sma_slow = calculate_sma(close, config.SMA_SLOW)
    rsi = calculate_rsi(close, config.RSI_PERIOD)
    vol_ratio = calculate_volume_ratio(volume)

    latest_rsi = rsi.iloc[-1]
    if pd.isna(latest_rsi) or np.isinf(latest_rsi):
        return "HOLD"

    latest_vol_ratio = vol_ratio.iloc[-1]
    crossover = detect_crossover(sma_fast, sma_slow)
    latest_crossover = crossover.iloc[-1]

    # BUY signal
    if (latest_crossover == 1
            and latest_rsi > config.RSI_BUY_THRESHOLD
            and latest_vol_ratio > config.VOLUME_RATIO_MIN):
        return "BUY"

    # SELL signal
    current_price = close.iloc[-1]
    current_sma_fast = sma_fast.iloc[-1]
    if current_price < current_sma_fast or latest_rsi < config.RSI_SELL_THRESHOLD:
        return "SELL"

    return "HOLD"
