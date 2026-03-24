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
