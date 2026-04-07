"""
Data fetcher module — pulls stock data from yfinance or broker API.
"""
import yfinance as yf
import pandas as pd


def fetch_stock_data(ticker: str, period: str = "2y", interval: str = "1h") -> pd.DataFrame:
    """
    Fetch OHLCV data for a single stock.

    Args:
        ticker:   Stock symbol (e.g., "RELIANCE.NS" for NSE)
        period:   How far back to fetch ("730d", "1y", "2y", etc.)
        interval: Candle size — "1h" (default), "1d", "15m", etc.
                  yfinance limits: 1h → max 730d | 15m → max 60d | 1d → any range

    Returns:
        DataFrame with Open, High, Low, Close, Volume columns (market hours only)
    """
    data = yf.download(ticker, period=period, interval=interval, progress=False)
    if data is None or data.empty:
        raise ValueError(f"No data returned for {ticker}")

    # Flatten MultiIndex columns if present (happens with some yfinance responses)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Ensure data is a DataFrame with required columns
    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    if not required_cols.issubset(set(data.columns)):
        raise ValueError(f"Missing OHLCV columns for {ticker}. Got: {list(data.columns)}")

    # Filter to NSE market hours (9:15–15:30 IST) for intraday intervals
    if interval not in ("1d", "1wk", "1mo") and hasattr(data.index, "hour"):
        try:
            # yfinance returns UTC timestamps for NSE — convert to IST before filtering
            if data.index.tz is None:
                # Assume UTC if no timezone info
                data.index = data.index.tz_localize("UTC")
            # Convert to IST
            data.index = data.index.tz_convert("Asia/Kolkata")
            # Filter market hours
            data = data.between_time("09:15", "15:30")
            # Remove timezone for clean downstream use
            data.index = data.index.tz_localize(None)
        except Exception as e:
            # If timezone conversion fails, continue with unfiltered data
            pass

    result = data.dropna()
    if result.empty:
        raise ValueError(f"No valid data after processing for {ticker}")

    return result


def fetch_multiple_stocks(tickers: list[str], period: str = "730d",
                          interval: str = "1h") -> dict[str, pd.DataFrame]:
    """
    Fetch data for multiple stocks.

    Returns:
        Dict mapping ticker -> DataFrame
    """
    results = {}
    for ticker in tickers:
        try:
            results[ticker] = fetch_stock_data(ticker, period, interval)
        except Exception as e:
            print(f"Failed to fetch {ticker}: {e}")
    return results


def fetch_live_prices(tickers: list[str]) -> dict[str, float]:
    """
    Fetch latest prices for a list of tickers (lightweight, for position monitoring).
    Uses single bulk yf.download call for speed — 1 API call instead of N.
    Falls back to individual ticker fetch if bulk download fails.
    """
    if not tickers:
        return {}

    prices = {}

    # Try bulk download first
    try:
        data = yf.download(tickers, period="1d", progress=False, threads=True)
        if data is not None and not data.empty:
            if len(tickers) == 1:
                # Single ticker — Close is a Series
                try:
                    close = data["Close"].squeeze()
                    if isinstance(close, pd.Series) and len(close) > 0:
                        last = float(close.iloc[-1])
                        if last > 0:
                            prices[tickers[0]] = last
                except:
                    pass
            else:
                # Multiple tickers — Close is a DataFrame with ticker columns
                try:
                    close = data.get("Close", None) if isinstance(data, dict) else (data["Close"] if "Close" in data.columns else None)
                    if close is not None:
                        for ticker in tickers:
                            try:
                                if ticker in close.columns:
                                    val = close[ticker].dropna()
                                    if len(val) > 0:
                                        last = float(val.iloc[-1])
                                        if last > 0:
                                            prices[ticker] = last
                            except:
                                pass
                except:
                    pass
    except:
        pass

    # Fallback: fetch missing tickers one-by-one
    missing = [t for t in tickers if t not in prices]
    if missing:
        for ticker in missing:
            try:
                single_data = yf.download(ticker, period="1d", progress=False)
                if single_data is not None and not single_data.empty and "Close" in single_data.columns:
                    close = single_data["Close"].squeeze()
                    if isinstance(close, pd.Series) and len(close) > 0:
                        last = float(close.iloc[-1])
                        if last > 0:
                            prices[ticker] = last
            except:
                pass

    return prices
