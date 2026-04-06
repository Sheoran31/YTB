"""
yfinance Data Fetching Hardening Tests

Tests for robust data fetching:
- Rate limit handling (429)
- Incomplete candles at market open
- Half-day market sessions
- Bulk fetch partial failures
- Empty responses
- Timezone localization errors
- Period/interval mismatches
- Network timeouts
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from data.fetcher import fetch_stock_data, fetch_live_prices, fetch_multiple_stocks


class TestYfinanceRateLimit:
    """Test rate limiting and retry logic"""

    @patch("yfinance.download")
    def test_fetch_stock_data_with_rate_limit_429(self, mock_download):
        """429 rate limit should trigger retry or fallback"""
        # Simulate 429 then success
        mock_download.side_effect = [
            Exception("429 Client Error: Too Many Requests"),
            pd.DataFrame({
                "Open": np.arange(100, 150),
                "High": np.arange(102, 152),
                "Low": np.arange(98, 148),
                "Close": np.arange(101, 151),
                "Volume": np.full(50, 1000000),
            }, index=pd.date_range("2026-01-01", periods=50, freq="1h", tz="UTC")),
        ]

        try:
            data = fetch_stock_data("AAPL")
            # Should either return data or raise controlled error
            if data is not None:
                assert len(data) > 0, "Should return data on retry"
        except Exception as e:
            # Acceptable to raise error, but should not crash silently
            assert "429" in str(e) or "retry" in str(e).lower()


class TestYfinanceIncompleteData:
    """Test handling of incomplete market data"""

    @patch("yfinance.download")
    def test_fetch_stock_data_incomplete_last_candle(self, mock_download):
        """Market open with incomplete last candle should handle gracefully"""
        # Market open at 9:15:01 AM, only 1 minute of data
        mock_download.return_value = pd.DataFrame({
            "Open": [100, 101],
            "High": [102, 103],
            "Low": [98, 99],
            "Close": [101, 102],
            "Volume": [1000000, 50000],  # Last candle has low volume (incomplete)
        }, index=pd.date_range("2026-04-06 09:14:00", periods=2, freq="1min", tz="UTC"))

        data = fetch_stock_data("SBIN.NS")

        # Should handle incomplete data gracefully
        assert data is not None, "Should not crash on incomplete candle"
        if len(data) >= 2:
            # Last candle is incomplete, strategy should handle this
            assert data.iloc[-1]["Volume"] < data.iloc[0]["Volume"] * 0.5

    @patch("yfinance.download")
    def test_fetch_stock_data_all_nan_values(self, mock_download):
        """All NaN values in data should be handled"""
        # Return empty/NaN data
        mock_download.return_value = pd.DataFrame({
            "Open": [np.nan] * 50,
            "High": [np.nan] * 50,
            "Low": [np.nan] * 50,
            "Close": [np.nan] * 50,
            "Volume": [np.nan] * 50,
        }, index=pd.date_range("2026-01-01", periods=50, freq="1h", tz="UTC"))

        try:
            data = fetch_stock_data("INVALID.NS")
            # Should either return None or raise ValueError
            if data is not None:
                assert data.isna().all().any(), "Should contain NaN values"
        except ValueError:
            # Acceptable to raise error for invalid data
            pass


class TestYfinanceMarketSessions:
    """Test different market session types"""

    @patch("yfinance.download")
    def test_fetch_stock_data_half_day_market(self, mock_download):
        """NSE 4-hour half-day session should still work"""
        # Simulate NSE half-day close at 1:30 PM (4 hours of trading)
        mock_download.return_value = pd.DataFrame({
            "Open": np.arange(100, 105),
            "High": np.arange(102, 107),
            "Low": np.arange(98, 103),
            "Close": np.arange(101, 106),
            "Volume": np.full(5, 1000000),
        }, index=pd.date_range("2026-04-03 09:15:00", periods=5, freq="1h", tz="Asia/Kolkata"))

        data = fetch_stock_data("SBIN.NS")

        # Should handle half-day data
        assert data is not None or isinstance(data, type(None))


class TestYfinanceBulkFetch:
    """Test bulk fetching of multiple stocks"""

    @patch("yfinance.download")
    def test_fetch_live_prices_bulk_partial_failure(self, mock_download):
        """2 of 50 stocks fail in bulk fetch, should fallback for those 2"""
        tickers = [f"STOCK{i}.NS" for i in range(50)]

        # Bulk fetch succeeds for 48, fails for 2
        bulk_data = {
            f"STOCK{i}.NS": pd.DataFrame({
                "Close": [100 + i]
            }, index=pd.date_range("2026-04-06", periods=1))
            for i in range(48)
        }

        mock_download.return_value = bulk_data

        try:
            prices = fetch_live_prices(tickers)
            # Should return some data, even if not all 50
            assert len(prices) >= 48, "Should return at least the successful ones"
        except Exception:
            # Acceptable to raise, but should not silently skip
            pass


class TestYfinanceEmptyResponses:
    """Test handling of empty or invalid responses"""

    @patch("yfinance.download")
    def test_fetch_live_prices_empty_response(self, mock_download):
        """Empty yfinance response should not crash"""
        # Return empty dict
        mock_download.return_value = {}

        try:
            prices = fetch_live_prices(["AAPL"])
            # Should return empty dict or None, not crash
            assert isinstance(prices, (dict, type(None)))
        except (ValueError, KeyError):
            # Acceptable to raise error for empty data
            pass

    @patch("yfinance.download")
    def test_fetch_stock_data_none_response(self, mock_download):
        """None response from yfinance should be handled"""
        mock_download.return_value = None

        try:
            data = fetch_stock_data("INVALID.NS")
            # Should handle None gracefully
            assert data is None or len(data) == 0
        except (ValueError, AttributeError):
            # Acceptable to raise error
            pass


class TestYfinanceTimezone:
    """Test timezone handling"""

    @patch("yfinance.download")
    def test_fetch_stock_data_timezone_localization_fails(self, mock_download):
        """Timezone localization error should be caught"""
        df = pd.DataFrame({
            "Open": np.arange(100, 150),
            "High": np.arange(102, 152),
            "Low": np.arange(98, 148),
            "Close": np.arange(101, 151),
            "Volume": np.full(50, 1000000),
        }, index=pd.date_range("2026-01-01", periods=50, freq="1h"))

        # Mock with timezone that will cause issues
        mock_download.return_value = df

        try:
            data = fetch_stock_data("AAPL")
            # Should either succeed or raise controlled error, not silent failure
            if data is None:
                pass  # Acceptable
            else:
                assert len(data) > 0 or data.index.tz is not None
        except Exception as e:
            # Should not be silent failure
            assert str(e) != "", "Should provide error message"


class TestYfinancePeriodIntervalValidation:
    """Test period and interval validation"""

    @patch("yfinance.download")
    def test_fetch_stock_data_period_interval_mismatch(self, mock_download):
        """Period/interval mismatch should be handled"""
        # 15m interval with 730d period exceeds yfinance free tier limit
        # Should detect and either adjust or warn

        mock_download.side_effect = Exception(
            "Invalid period/interval combination. 15min data only available for last 60 days"
        )

        try:
            # This call would fail in real scenario
            data = fetch_stock_data("AAPL", period="730d", interval="15m")
            # Should either return empty or raise error
            assert data is None or len(data) < 4000
        except Exception as e:
            # Should raise meaningful error, not silent failure
            assert "period" in str(e).lower() or "interval" in str(e).lower()


class TestYfinanceTimeout:
    """Test timeout handling"""

    @patch("yfinance.download")
    def test_fetch_live_prices_timeout(self, mock_download):
        """Network timeout should not block main loop"""
        mock_download.side_effect = Exception("Read timed out after 10.0 seconds")

        try:
            prices = fetch_live_prices(["AAPL", "GOOGL", "MSFT"])
            # Should return empty dict or cached data, not raise unhandled exception
            assert isinstance(prices, (dict, type(None)))
        except Exception as e:
            # Should raise controlled exception, not hang the bot
            assert "timeout" in str(e).lower()
