"""
Data storage — save and load market data locally.
"""
import pandas as pd
import os


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")


def save_to_csv(data: pd.DataFrame, ticker: str, directory: str = DATA_DIR):
    """Save stock data to CSV."""
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, f"{ticker.replace('.', '_')}.csv")
    data.to_csv(filepath)
    return filepath


def load_from_csv(ticker: str, directory: str = DATA_DIR) -> pd.DataFrame:
    """Load stock data from CSV."""
    filepath = os.path.join(directory, f"{ticker.replace('.', '_')}.csv")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No saved data for {ticker}")
    return pd.read_csv(filepath, index_col=0, parse_dates=True)
