# Backtest and Compare

Use this prompt to test a strategy against historical data.

```
Run a backtest of [strategy name] on [ticker] for the following periods:
1. COVID crash: Jan 2020 - Mar 2020
2. Bull run: Apr 2021 - Dec 2021
3. Sideways/Bear: Jan 2022 - Dec 2023

For each period, report:
- Total return (%)
- Sharpe ratio
- Max drawdown (%)
- Win rate (%)
- Number of trades
- Largest single win and loss

Compare against buy-and-hold for the same period.
Strategy must be profitable in at least 2 of 3 regimes.
```
