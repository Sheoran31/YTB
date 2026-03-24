# Trading Bot — Algorithmic Trading System for NSE/BSE

An AI-augmented algorithmic trading system for Indian stock markets (NSE/BSE).

## What This Bot Does
- Screens Nifty 50 stocks daily using technical indicators (RSI, SMA, ATR, Volume)
- Generates BUY/SELL signals based on momentum and mean reversion strategies
- Manages risk with position sizing, stop losses, and circuit breakers
- Backtests strategies on historical data before risking real money
- Integrates with Zerodha Kite Connect for paper and live trading
- Logs every decision for review and improvement

## Architecture
- **Data Layer**: Fetch and store market data (yfinance + Kite Connect)
- **Strategy Layer**: Momentum, mean reversion, signal combination
- **Execution Layer**: Order placement, paper trading simulation
- **Risk Layer**: Position sizing, stop losses, drawdown guards
- **Monitoring Layer**: Logging, alerts, dashboard

## Status
🚧 Under development — Paper trading only. No real money.
