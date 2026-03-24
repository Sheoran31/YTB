"""
Main Trading Pipeline — connects all layers together.

Usage:
    python trader.py                # Paper trading (default, safe)
    python trader.py --live         # Live trading via Zerodha (requires API keys)
    python trader.py --backtest     # Run backtest
    python trader.py --screener     # Run screener only

Flow:
    9:15 AM  → Fetch live data for all tracked stocks
    9:20 AM  → Run screener → generate signals
    9:25 AM  → Apply risk rules (can we trade?)
    9:30 AM  → Place trades for qualified signals
    All day  → Monitor positions, update stop losses
    3:15 PM  → Square off all intraday positions
    3:20 PM  → Log full trade day to trade_log.csv
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


def run_trading_pipeline(live: bool = False):
    """Execute one full cycle of the trading pipeline."""
    mode = "LIVE" if live else "PAPER"

    logger.info("=" * 60)
    logger.info("TRADING PIPELINE STARTED")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Mode: {mode} TRADING")
    logger.info(f"Capital: INR {config.INITIAL_CAPITAL:,.0f}")
    logger.info("=" * 60)

    # Initialize components
    risk_mgr = RiskManager()
    trader = PaperTrader(config.INITIAL_CAPITAL)

    # If live mode, also init broker
    broker = None
    if live:
        from execution.broker_api import ZerodhaBroker
        broker = ZerodhaBroker()
        if not broker.connect():
            logger.error("Failed to connect to Zerodha. Falling back to paper trading.")
            broker = None
            mode = "PAPER (broker fallback)"

    # Market hours check
    if not is_market_open():
        logger.warning("Market is CLOSED. Running with latest available data.")

    # ── Step 1: Fetch data and generate signals ─────────────
    signals = {}
    for ticker in config.WATCHLIST:
        logger.info(f"Fetching {ticker}...")
        try:
            data = fetch_stock_data(ticker, period="6mo")
        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {e}")
            continue

        signal = generate_signal(data)
        signals[ticker] = {"signal": signal, "data": data}
        logger.info(f"  {ticker}: {signal}")

    buy_signals = {t: s for t, s in signals.items() if s["signal"] == "BUY"}
    sell_signals = {t: s for t, s in signals.items() if s["signal"] == "SELL"}
    hold_count = len(signals) - len(buy_signals) - len(sell_signals)

    logger.info(f"\nSignals: {len(buy_signals)} BUY | {len(sell_signals)} SELL | {hold_count} HOLD")

    # ── Step 2: Process SELL signals first (free up capital) ─
    for ticker, info in sell_signals.items():
        if ticker in trader.positions:
            price = float(info["data"]["Close"].squeeze().iloc[-1])
            position = trader.positions[ticker]
            trade = trader.place_order(ticker, "SELL", position["quantity"], price)
            pnl = trade.get("pnl", 0)
            risk_mgr.record_trade(pnl)
            risk_mgr.update_peak(trader.get_portfolio_value({}))
            logger.info(f"  SOLD {ticker} @ {price:,.2f} | PnL: {pnl:+,.2f}")

            # Mirror to live broker if connected
            if broker:
                symbol = ticker.replace(".NS", "")
                broker.place_order(symbol, "SELL", position["quantity"], price)

    # ── Step 3: Process BUY signals ─────────────────────────
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
            logger.warning(f"  SKIP {ticker}: position size = 0")
            continue

        proposed_value = quantity * price

        # Risk check (includes market hours, Friday rule, all circuit breakers)
        can_trade, reason = risk_mgr.can_open_position(
            trader.get_portfolio_value({}),
            list(trader.positions.keys()),
            proposed_value,
        )

        if not can_trade:
            logger.warning(f"  BLOCKED {ticker}: {reason}")
            continue

        # Place paper trade
        trade = trader.place_order(ticker, "BUY", quantity, price)
        logger.info(
            f"  BOUGHT {ticker} @ {price:,.2f} | Qty: {quantity} | "
            f"Stop: {stop_loss:,.2f} | Status: {trade['status']}"
        )

        # Mirror to live broker if connected
        if broker:
            symbol = ticker.replace(".NS", "")
            broker.place_order(symbol, "BUY", quantity, price)

    # ── Step 4: Summary ─────────────────────────────────────
    portfolio_value = trader.get_portfolio_value({})
    logger.info(f"\n{'='*60}")
    logger.info(f"PIPELINE COMPLETE — {mode}")
    logger.info(f"Portfolio: INR {portfolio_value:,.2f}")
    logger.info(f"Cash: INR {trader.capital:,.2f}")
    logger.info(f"Positions: {len(trader.positions)}")
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
    elif "--screener" in sys.argv:
        from screener import run_screener, print_results, save_results
        results = run_screener()
        print_results(results)
        save_results(results)
    elif "--live" in sys.argv:
        print("WARNING: Live trading mode. Real money will be used.")
        confirm = input("Type 'YES' to confirm: ")
        if confirm == "YES":
            run_trading_pipeline(live=True)
        else:
            print("Cancelled.")
    else:
        run_trading_pipeline(live=False)
