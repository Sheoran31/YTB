"""
Data fetcher module — pulls stock data from yfinance or broker API.
"""
import yfinance as yf
import pandas as pd


def fetch_stock_data(ticker: str, period: str = "2y") -> pd.DataFrame:
    """
    Fetch OHLCV data for a single stock.

    Args:
        ticker: Stock symbol (e.g., "RELIANCE.NS" for NSE)
        period: How far back to fetch ("1y", "2y", "5y", etc.)

    Returns:
        DataFrame with Open, High, Low, Close, Volume columns
    """
    data = yf.download(ticker, period=period, progress=False)
    if data.empty:
        raise ValueError(f"No data returned for {ticker}")
    return data


def fetch_multiple_stocks(tickers: list[str], period: str = "2y") -> dict[str, pd.DataFrame]:
    """
    Fetch data for multiple stocks.

    Returns:
        Dict mapping ticker -> DataFrame
    """
    results = {}
    for ticker in tickers:
        try:
            results[ticker] = fetch_stock_data(ticker, period)
        except Exception as e:
            print(f"Failed to fetch {ticker}: {e}")
    return results


def fetch_live_prices(tickers: list[str]) -> dict[str, float]:
    """
    Fetch latest prices for a list of tickers (lightweight, for position monitoring).
    Uses single bulk yf.download call for speed — 1 API call instead of N.
    """
    if not tickers:
        return {}

    prices = {}
    try:
        # Bulk download 1-day data for all tickers at once
        data = yf.download(tickers, period="1d", progress=False, threads=True)
        if data.empty:
            return prices

        if len(tickers) == 1:
            # Single ticker — Close is a Series
            close = data["Close"].squeeze()
            last = float(close.iloc[-1]) if len(close) > 0 else 0
            if last > 0:
                prices[tickers[0]] = last
        else:
            # Multiple tickers — Close is a DataFrame with ticker columns
            close = data["Close"]
            for ticker in tickers:
                try:
                    val = close[ticker].dropna()
                    if len(val) > 0:
                        last = float(val.iloc[-1])
                        if last > 0:
                            prices[ticker] = last
                except Exception:
                    pass
    except Exception:
        # Fallback: one by one if bulk fails
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                price = t.fast_info.get("last_price", 0)
                if price and price > 0:
                    prices[ticker] = float(price)
            except Exception:
                pass
    return prices
