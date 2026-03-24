# Strategy from Idea

Use this prompt when you have a new trading idea and want working code + tests.

```
Write a complete trading strategy in strategies/{name}.py:

Requirements:
- [Describe your entry conditions]
- [Describe your exit conditions]
- Log every signal to trade_log.csv with timestamp, symbol, action, price, indicator values
- Include type hints
- Write tests in tests/test_{name}.py covering:
  * Buy signal scenario
  * Sell signal scenario
  * Edge case: insufficient data
  * Edge case: flat/no-movement prices

Use only indicators from data/signals.py. Follow the same pattern as strategies/momentum.py.
```
