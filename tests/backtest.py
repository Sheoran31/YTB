"""
Backtester — prove your strategy works before risking real money.

Usage:
    python -m tests.backtest

Tests strategy on 3 market regimes:
    1. COVID crash (Jan 2020 - Mar 2020)
    2. Bull run (Apr 2021 - Dec 2021)
    3. Sideways/Bear (Jan 2022 - Dec 2023)

Rule: Strategy must be profitable in at least 2 of 3 regimes.
"""
import pandas as pd
import numpy as np
from datetime import datetime

import config
from data.fetcher import fetch_stock_data
from data.signals import calculate_sma, calculate_rsi, calculate_atr
from strategies.momentum import generate_signal as momentum_strategy


# ============================================================
# BACKTEST ENGINE
# ============================================================

def calculate_max_drawdown(portfolio_values: list[float]) -> float:
    """Max drawdown as a percentage (0 to 1)."""
    if not portfolio_values:
        return 0.0

    peak = portfolio_values[0]
    max_dd = 0.0

    for value in portfolio_values:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    return max_dd


def backtest(
    strategy,
    data: pd.DataFrame,
    initial_capital: float = config.INITIAL_CAPITAL,
    broker_costs: dict = config.BROKER_COSTS,
) -> dict:
    """
    Run a strategy on historical data and return performance metrics.

    Args:
        strategy: Function(DataFrame) -> "BUY"/"SELL"/"HOLD"
        data: OHLCV DataFrame
        initial_capital: Starting capital in INR
        broker_costs: Dict with brokerage, stt, gst rates

    Returns:
        Dict with total_return, sharpe_ratio, max_drawdown,
        win_rate, total_trades, trade_log
    """
    portfolio = initial_capital
    position = None  # {entry_price, quantity, entry_date}
    trades = []
    daily_values = []

    close = data["Close"].squeeze()

    for i in range(config.SMA_SLOW, len(data)):
        # CRITICAL: only pass data up to current day (no lookahead)
        historical = data.iloc[:i + 1]
        signal = strategy(historical)
        current_price = float(close.iloc[i])
        current_date = data.index[i]

        daily_values.append(portfolio if position is None
                           else portfolio + position["quantity"] * (current_price - position["entry_price"]))

        if signal == "BUY" and position is None and current_price > 0:
            # Calculate costs
            brokerage_cost = current_price * broker_costs["brokerage"]
            total_cost_per_share = current_price + brokerage_cost

            quantity = int((portfolio * 0.9) / total_cost_per_share)
            if quantity <= 0:
                continue

            cost = quantity * total_cost_per_share
            portfolio -= cost
            position = {
                "entry_price": current_price,
                "quantity": quantity,
                "entry_date": current_date,
            }
            trades.append({
                "action": "BUY",
                "price": current_price,
                "quantity": quantity,
                "date": str(current_date),
            })

        elif signal == "SELL" and position is not None:
            sell_value = position["quantity"] * current_price
            brokerage_cost = sell_value * broker_costs["brokerage"]
            stt_cost = sell_value * broker_costs["stt"]
            net_sell = sell_value - brokerage_cost - stt_cost

            pnl = net_sell - (position["quantity"] * position["entry_price"])
            portfolio += net_sell

            trades.append({
                "action": "SELL",
                "price": current_price,
                "quantity": position["quantity"],
                "pnl": round(pnl, 2),
                "date": str(current_date),
                "holding_days": (current_date - position["entry_date"]).days
                if hasattr(current_date, "days") or hasattr(position["entry_date"], "days")
                else "N/A",
            })
            position = None

    # Close any open position at last price
    if position is not None:
        last_price = float(close.iloc[-1])
        pnl = (last_price - position["entry_price"]) * position["quantity"]
        portfolio += position["quantity"] * last_price
        trades.append({
            "action": "SELL (forced close)",
            "price": last_price,
            "quantity": position["quantity"],
            "pnl": round(pnl, 2),
            "date": str(data.index[-1]),
        })

    # Calculate metrics
    sell_trades = [t for t in trades if "pnl" in t]
    pnls = [t["pnl"] for t in sell_trades]
    wins = [p for p in pnls if p > 0]

    total_return = (portfolio - initial_capital) / initial_capital

    # Sharpe ratio from daily portfolio values
    if len(daily_values) > 1:
        daily_returns = pd.Series(daily_values).pct_change().dropna()
        if daily_returns.std() > 0:
            sharpe = daily_returns.mean() / daily_returns.std() * (252 ** 0.5)
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0

    return {
        "total_return": round(total_return * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(calculate_max_drawdown(daily_values) * 100, 2),
        "win_rate": round(len(wins) / max(len(sell_trades), 1) * 100, 1),
        "total_trades": len(sell_trades),
        "final_portfolio": round(portfolio, 2),
        "total_pnl": round(sum(pnls), 2),
        "trade_log": trades,
    }


# ============================================================
# MARKET REGIME TESTS
# ============================================================

REGIMES = {
    "COVID Crash (Jan-Mar 2020)": ("2019-07-01", "2020-04-01"),
    "Bull Run (Apr-Dec 2021)": ("2020-10-01", "2022-01-01"),
    "Sideways/Bear (Jan 2022-Dec 2023)": ("2021-07-01", "2024-01-01"),
}


def run_regime_test(ticker: str, regime_name: str, start: str, end: str) -> dict:
    """Run backtest on a specific market regime."""
    import yfinance as yf

    data = yf.download(ticker, start=start, end=end, progress=False)
    if data.empty or len(data) < config.SMA_SLOW + 10:
        return {"regime": regime_name, "error": "Not enough data"}

    result = backtest(momentum_strategy, data)
    result["regime"] = regime_name
    return result


def print_regime_results(results: list[dict]):
    """Print backtest results across regimes."""
    print(f"\n{'='*70}")
    print(f"{'Regime':<35} {'Return':>8} {'Sharpe':>8} {'MaxDD':>8} {'WinRate':>8} {'Trades':>7}")
    print(f"{'='*70}")

    profitable = 0
    for r in results:
        if "error" in r:
            print(f"{r['regime']:<35} {'ERROR':>8}")
            continue

        ret = f"{r['total_return']:>+7.1f}%"
        sharpe = f"{r['sharpe_ratio']:>7.2f}"
        maxdd = f"{r['max_drawdown']:>7.1f}%"
        wr = f"{r['win_rate']:>7.1f}%"
        trades = f"{r['total_trades']:>6}"
        print(f"{r['regime']:<35} {ret} {sharpe} {maxdd} {wr} {trades}")

        if r["total_return"] > 0:
            profitable += 1

    print(f"{'='*70}")
    print(f"\nProfitable regimes: {profitable}/{len(results)}")
    if profitable >= 2:
        print("PASS — Strategy works in 2+ regimes")
    else:
        print("FAIL — Strategy only works in bull markets. Not robust enough.")


def run_multi_stock_backtest(tickers: list[str] | None = None):
    """Run backtest across multiple stocks and all regimes."""
    tickers = tickers or config.WATCHLIST[:5]  # Top 5 from watchlist

    print(f"\n{'='*80}")
    print(f"MULTI-STOCK BACKTEST REPORT")
    print(f"Strategy: Momentum (SMA crossover + RSI)")
    print(f"Initial capital: INR {config.INITIAL_CAPITAL:,.0f} per stock")
    print(f"{'='*80}")

    all_results = {}
    for ticker in tickers:
        print(f"\n--- {ticker} ---")
        results = []
        for regime_name, (start, end) in REGIMES.items():
            result = run_regime_test(ticker, regime_name, start, end)
            results.append(result)
        all_results[ticker] = results
        print_regime_results(results)

    # Summary table across all stocks
    print(f"\n{'='*80}")
    print(f"SUMMARY: Average performance across all stocks")
    print(f"{'='*80}")
    print(f"{'Ticker':<15} {'COVID':>10} {'Bull':>10} {'Sideways':>10} {'Avg':>10} {'Pass?':>8}")
    print("-" * 65)

    for ticker, results in all_results.items():
        returns = []
        for r in results:
            ret = r.get("total_return", 0)
            returns.append(ret)

        avg = sum(returns) / len(returns) if returns else 0
        profitable = sum(1 for r in returns if r > 0)
        passed = "PASS" if profitable >= 2 else "FAIL"

        ret_strs = [f"{r:>+9.1f}%" for r in returns]
        print(f"{ticker.replace('.NS',''):<15} {ret_strs[0]} {ret_strs[1]} {ret_strs[2]} {avg:>+9.1f}% {passed:>8}")


def main():
    import sys
    if "--multi" in sys.argv:
        run_multi_stock_backtest()
    else:
        ticker = "RELIANCE.NS"
        print(f"\nBacktesting momentum strategy on {ticker}")
        print(f"Initial capital: INR {config.INITIAL_CAPITAL:,.0f}")

        results = []
        for regime_name, (start, end) in REGIMES.items():
            print(f"\nRunning: {regime_name}...")
            result = run_regime_test(ticker, regime_name, start, end)
            results.append(result)

        print_regime_results(results)

        # Print detailed trade log for the most recent regime
        last = results[-1]
        if "trade_log" in last and last["trade_log"]:
            print(f"\nDetailed trades for {last['regime']}:")
            print(f"{'Action':<18} {'Price':>10} {'Qty':>6} {'PnL':>10} {'Date'}")
            print("-" * 65)
            for t in last["trade_log"]:
                pnl_str = f"{t.get('pnl', 0):>+10,.0f}" if "pnl" in t else "          "
                print(f"{t['action']:<18} {t['price']:>10,.2f} {t['quantity']:>6} {pnl_str} {t['date'][:10]}")


if __name__ == "__main__":
    main()
