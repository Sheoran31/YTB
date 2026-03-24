"""
Main Trading Pipeline — connects all layers together.

Usage:
    python trader.py              # Run once (paper trading mode)
    python trader.py --backtest   # Run backtest instead

Flow:
    1. Fetch data for all watchlist stocks
    2. Generate signals (momentum strategy)
    3. Check risk rules (can we trade?)
    4. Place paper trades for qualified signals
    5. Log everything
"""
import sys
from datetime import datetime, time

import config
from data.fetcher import fetch_stock_data
from data.signals import calculate_atr
from strategies.momentum import generate_signal
from risk.manager import RiskManager
from execution.paper_trading import PaperTrader
from monitoring.logger import setup_logger

logger = setup_logger()


def is_market_open() -> bool:
    """Check if Indian stock market is currently open (IST)."""
    now = datetime.now().time()
    market_open = time(config.MARKET_OPEN_HOUR, config.MARKET_OPEN_MINUTE)
    market_close = time(config.MARKET_CLOSE_HOUR, config.MARKET_CLOSE_MINUTE)
    return market_open <= now <= market_close


def is_new_positions_allowed() -> bool:
    """Check if we're still in the window for new positions."""
    now = datetime.now().time()
    cutoff = time(config.NO_NEW_POSITIONS_AFTER_HOUR, config.NO_NEW_POSITIONS_AFTER_MINUTE)
    return now < cutoff


def run_trading_pipeline():
    """Execute one full cycle of the trading pipeline."""
    logger.info("=" * 60)
    logger.info("TRADING PIPELINE STARTED")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Mode: PAPER TRADING")
    logger.info("=" * 60)

    # Initialize components
    risk_mgr = RiskManager()
    trader = PaperTrader(config.INITIAL_CAPITAL)

    # Check market hours (log warning but continue for paper trading)
    if not is_market_open():
        logger.warning("Market is CLOSED. Running in simulation mode with latest available data.")

    if not is_new_positions_allowed():
        logger.warning("Past new-positions cutoff time. No new trades will be placed.")

    # Step 1: Fetch data and generate signals
    signals = {}
    for ticker in config.WATCHLIST:
        logger.info(f"Fetching data for {ticker}...")
        try:
            data = fetch_stock_data(ticker, period="6mo")
        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {e}")
            continue

        signal = generate_signal(data)
        signals[ticker] = {"signal": signal, "data": data}
        logger.info(f"  {ticker}: {signal}")

    # Step 2: Execute on BUY signals
    buy_signals = {t: s for t, s in signals.items() if s["signal"] == "BUY"}
    sell_signals = {t: s for t, s in signals.items() if s["signal"] == "SELL"}

    logger.info(f"\nSignal summary: {len(buy_signals)} BUY, {len(sell_signals)} SELL, "
                f"{len(signals) - len(buy_signals) - len(sell_signals)} HOLD")

    # Process SELL signals first (free up capital)
    for ticker, info in sell_signals.items():
        if ticker in trader.positions:
            price = float(info["data"]["Close"].squeeze().iloc[-1])
            position = trader.positions[ticker]
            trade = trader.place_order(ticker, "SELL", position["quantity"], price)
            pnl = trade.get("pnl", 0)
            risk_mgr.record_trade(pnl)
            risk_mgr.update_peak(trader.get_portfolio_value({}))
            logger.info(f"  SOLD {ticker} @ {price:,.2f} | PnL: {pnl:+,.2f} | Status: {trade['status']}")

    # Process BUY signals
    for ticker, info in buy_signals.items():
        data = info["data"]
        close = data["Close"].squeeze()
        high = data["High"].squeeze()
        low = data["Low"].squeeze()
        price = float(close.iloc[-1])
        atr = float(calculate_atr(high, low, close).iloc[-1])

        # Calculate stop loss and position size
        stop_loss = risk_mgr.calculate_stop_loss(price, atr)
        quantity = risk_mgr.calculate_position_size(
            trader.get_portfolio_value({}), price, stop_loss
        )

        if quantity == 0:
            logger.warning(f"  SKIP {ticker}: position size = 0 (stop too tight or capital too low)")
            continue

        proposed_value = quantity * price

        # Check risk rules
        can_trade, reason = risk_mgr.can_open_position(
            trader.get_portfolio_value({}),
            list(trader.positions.keys()),
            proposed_value,
        )

        if not can_trade:
            logger.warning(f"  BLOCKED {ticker}: {reason}")
            continue

        # Place the order
        trade = trader.place_order(ticker, "BUY", quantity, price)
        logger.info(
            f"  BOUGHT {ticker} @ {price:,.2f} | Qty: {quantity} | "
            f"Stop: {stop_loss:,.2f} | Status: {trade['status']}"
        )

    # Step 3: Summary
    portfolio_value = trader.get_portfolio_value({})
    logger.info(f"\n{'='*60}")
    logger.info(f"PIPELINE COMPLETE")
    logger.info(f"Portfolio value: INR {portfolio_value:,.2f}")
    logger.info(f"Cash: INR {trader.capital:,.2f}")
    logger.info(f"Open positions: {len(trader.positions)}")
    logger.info(f"Trades today: {risk_mgr.trades_today}")
    logger.info(f"Daily PnL: INR {risk_mgr.daily_pnl:+,.2f}")
    logger.info(f"{'='*60}")

    # Save trade log
    trader.save_trade_log()
    if trader.trade_log:
        logger.info(f"Trade log saved to {config.TRADE_LOG_FILE}")

    return trader, risk_mgr


if __name__ == "__main__":
    if "--backtest" in sys.argv:
        from tests.backtest import main as run_backtest
        run_backtest()
    else:
        run_trading_pipeline()
