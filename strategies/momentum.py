"""
Momentum strategy — supports two signal modes (set in config.SIGNAL_MODE):

OLD mode (SMA only):
  BUY:  SMA-20 > SMA-50 + RSI > 55 + Volume > 1.5x
  SELL: Price < SMA-20 OR RSI < 45

NEW mode (EMA + MACD + ADX + Crossover):
  BUY:  EMA crossover (3-day window) + MACD histogram > 0 + RSI > 55
        + Volume > 1.5x + ADX > 20 (trend strong enough)
  SELL: Price < EMA-20 + (RSI < 45 OR MACD bearish)

NEW mode advantages: fewer false entries (ADX filter), earlier signals (EMA),
  MACD confirmation catches trend changes 2-3 days before SMA.
"""
import pandas as pd
import numpy as np
from data.signals import (
    calculate_sma, calculate_ema, calculate_rsi, calculate_volume_ratio,
    detect_crossover, calculate_macd, calculate_adx,
)
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

    mode = getattr(config, "SIGNAL_MODE", "old")

    if mode == "new":
        return _signal_new(data)
    return _signal_old(data)


def _signal_old(data: pd.DataFrame) -> str:
    """Original SMA-based signal (v1)."""
    try:
        # Ensure data is valid
        if data is None or data.empty or len(data) < config.SMA_SLOW:
            return "HOLD"

        close = data["Close"].squeeze()
        volume = data["Volume"].squeeze()

        # Ensure they're Series, not DataFrames
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        if isinstance(volume, pd.DataFrame):
            volume = volume.iloc[:, 0]

        sma_fast = calculate_sma(close, config.SMA_FAST)
        sma_slow = calculate_sma(close, config.SMA_SLOW)
        rsi = calculate_rsi(close, config.RSI_PERIOD)
        vol_ratio = calculate_volume_ratio(volume)

        latest_rsi = rsi.iloc[-1]
        if pd.isna(latest_rsi) or np.isinf(latest_rsi):
            return "HOLD"

        current_price = close.iloc[-1]
        current_sma_fast = sma_fast.iloc[-1]
        current_sma_slow = sma_slow.iloc[-1]
        latest_vol_ratio = vol_ratio.iloc[-1]

        if (current_sma_fast > current_sma_slow
                and latest_rsi > config.RSI_BUY_THRESHOLD
                and latest_vol_ratio > config.VOLUME_RATIO_MIN):
            return "BUY"

        if current_price < current_sma_fast or latest_rsi < config.RSI_SELL_THRESHOLD:
            return "SELL"

        return "HOLD"
    except Exception as e:
        # Log but don't crash — return HOLD on any error
        return "HOLD"


def _signal_new(data: pd.DataFrame) -> str:
    """Enhanced EMA + MACD + ADX + Crossover signal (v2)."""
    try:
        # Ensure data is valid
        if data is None or data.empty or len(data) < config.SMA_SLOW:
            return "HOLD"

        close = data["Close"].squeeze()
        high = data["High"].squeeze()
        low = data["Low"].squeeze()
        volume = data["Volume"].squeeze()

        # Ensure they're Series, not DataFrames
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        if isinstance(high, pd.DataFrame):
            high = high.iloc[:, 0]
        if isinstance(low, pd.DataFrame):
            low = low.iloc[:, 0]
        if isinstance(volume, pd.DataFrame):
            volume = volume.iloc[:, 0]

        # Indicators
        ema_fast = calculate_ema(close, config.SMA_FAST)
        ema_slow = calculate_ema(close, config.SMA_SLOW)
        rsi = calculate_rsi(close, config.RSI_PERIOD)
        vol_ratio = calculate_volume_ratio(volume)
        macd_line, signal_line, macd_hist = calculate_macd(close)
        adx = calculate_adx(high, low, close)
        crossover = detect_crossover(ema_fast, ema_slow)

        # Latest values
        latest_rsi = rsi.iloc[-1]
        if pd.isna(latest_rsi) or np.isinf(latest_rsi):
            return "HOLD"

        latest_vol_ratio = vol_ratio.iloc[-1]
        latest_macd_hist = macd_hist.iloc[-1]
        latest_adx = adx.iloc[-1]
        current_price = close.iloc[-1]
        current_ema_fast = ema_fast.iloc[-1]
        current_ema_slow = ema_slow.iloc[-1]

        if pd.isna(latest_adx) or pd.isna(latest_macd_hist):
            return "HOLD"

        lookback = getattr(config, "CROSSOVER_LOOKBACK", 3)
        adx_min = getattr(config, "ADX_MIN", 20)

        # ── BUY — uptrend confirmed by all tools ──
        recent_crossover = crossover.iloc[-lookback:].max() >= 1
        uptrend          = current_ema_fast > current_ema_slow
        macd_bullish     = latest_macd_hist > 0
        rsi_ok           = latest_rsi > config.RSI_BUY_THRESHOLD
        volume_ok        = latest_vol_ratio > config.VOLUME_RATIO_MIN
        trend_strong     = latest_adx > adx_min

        if (recent_crossover or uptrend) and macd_bullish and rsi_ok and volume_ok and trend_strong:
            return "BUY"

        # ── SELL — downtrend confirmed by same tools (symmetric with BUY) ──
        recent_death_cross = crossover.iloc[-lookback:].min() <= -1
        downtrend          = current_ema_fast < current_ema_slow
        macd_bearish       = latest_macd_hist < 0
        rsi_weak           = latest_rsi < config.RSI_SELL_THRESHOLD
        trend_strong_down  = latest_adx > adx_min  # trend must be strong for short too

        if (recent_death_cross or downtrend) and macd_bearish and rsi_weak and volume_ok and trend_strong_down:
            return "SELL"

        return "HOLD"
    except Exception as e:
        # Log but don't crash — return HOLD on any error
        return "HOLD"
