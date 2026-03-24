# 30-Day Trading Bot Plan — Daily Checklist

Start Date: 2026-03-25 (Day 1)
Rule: NO REAL MONEY until Day 21 at the earliest.

---

## WEEK 1: Paper Trading Only (Days 1-7)

### Day 1 (Tue Mar 25)
- [ ] Run `python trader.py --screener` at 9:30 AM
- [ ] Screenshot the screener output
- [ ] Write down which stocks got BUY signals and why
- [ ] Run `python trader.py` (paper mode) — note what trades it would make
- [ ] Review the log file: `logs/trading_bot.log`
- [ ] Push any changes to GitHub

### Day 2 (Wed Mar 26)
- [ ] Run screener at 9:30 AM
- [ ] Compare today's signals with yesterday — what changed?
- [ ] Run `python -m tests.backtest` on any new BUY signal stock
- [ ] Open `screener_results.csv` — is data accumulating correctly?
- [ ] Run all tests: `python -m pytest tests/ -v`

### Day 3 (Thu Mar 27)
- [ ] Run screener at 9:30 AM
- [ ] Manually track: if you had followed yesterday's signals, what would PnL be?
- [ ] Add 5 more stocks to `config.py` WATCHLIST (pick from Nifty 50)
- [ ] Run screener again with 15 stocks — does it still work?
- [ ] Commit and push changes

### Day 4 (Fri Mar 28)
- [ ] Run screener at 9:30 AM
- [ ] Note: Friday rule should block new positions after 2 PM — verify in logs
- [ ] Review the full week's screener_results.csv
- [ ] Count: how many BUY signals this week? How many would have been profitable?
- [ ] Write a 3-line summary of Week 1 observations in a file `logs/weekly_notes.md`

### Day 5 (Sat Mar 29) — Study Day
- [ ] Read Claude Code docs: https://docs.anthropic.com/en/docs/claude-code (1 hour)
- [ ] Practice: ask Claude Code to explain every line of `risk/manager.py`
- [ ] Practice: ask Claude Code to find bugs in `strategies/momentum.py`
- [ ] Try writing a new prompt: "Add MACD indicator to data/signals.py"

### Day 6 (Sun Mar 30) — Study Day
- [ ] Read about RSI divergence — can you code it?
- [ ] Ask Claude Code: "Write a mean reversion strategy in strategies/mean_reversion.py"
- [ ] Review the code Claude generates — do you understand every line?
- [ ] Run backtest on the new strategy
- [ ] Commit and push

### Day 7 (Mon Mar 31)
- [ ] Run screener at 9:30 AM
- [ ] Run BOTH strategies (momentum + mean reversion) — compare signals
- [ ] Start a trade journal: `logs/trade_journal.md` — write why you agree/disagree with each signal
- [ ] Week 1 complete. Review: did you run the screener every day?

---

## WEEK 2: Build Execution Layer (Days 8-14)

### Day 8 (Tue Apr 1)
- [ ] Run screener at 9:30 AM (this is now a daily habit)
- [ ] Set up Zerodha Kite Connect developer account: https://developers.kite.trade
- [ ] Apply for API access (takes 1-2 days to approve)
- [ ] While waiting: add Telegram alerts (ask Claude Code to help)
- [ ] `pip install python-telegram-bot` and create a bot via @BotFather

### Day 9 (Wed Apr 2)
- [ ] Run screener at 9:30 AM
- [ ] Build Telegram alert: send screener results to your phone every morning
- [ ] Test: run screener → get Telegram message with results
- [ ] Commit alert code to `monitoring/alerts.py`
- [ ] Push to GitHub

### Day 10 (Thu Apr 3)
- [ ] Run screener at 9:30 AM
- [ ] Check if Kite Connect API is approved
- [ ] If approved: set environment variables (KITE_API_KEY, KITE_API_SECRET)
- [ ] Run: `python -c "from execution.broker_api import ZerodhaBroker; b = ZerodhaBroker(); print(b.connect())"`
- [ ] If not approved yet: continue with paper trading

### Day 11 (Fri Apr 4)
- [ ] Run screener at 9:30 AM
- [ ] If Kite connected: fetch LTP for 5 stocks and compare with screener data
- [ ] DO NOT place any real orders yet
- [ ] Review Week 2 paper trade results
- [ ] Update `logs/weekly_notes.md`

### Day 12 (Sat Apr 5) — Study Day
- [ ] Read: "Algorithmic Trading" by Ernest Chan — Chapters 1-3
- [ ] Key concept: What is "alpha" vs "beta"?
- [ ] Ask Claude Code: "Explain the difference between alpha and beta in trading"
- [ ] Think about: does your momentum strategy capture alpha or just beta?

### Day 13 (Sun Apr 6) — Study Day
- [ ] Continue reading Ernest Chan — Chapter 4 (Mean Reversion)
- [ ] Compare your mean_reversion.py strategy with what the book describes
- [ ] Ask Claude Code to improve mean_reversion.py based on book concepts
- [ ] Run backtest on improved version
- [ ] Commit and push

### Day 14 (Mon Apr 7)
- [ ] Run screener at 9:30 AM
- [ ] Week 2 review: are Telegram alerts working daily?
- [ ] Count total paper trades this week — win rate?
- [ ] Ask Claude Code: "Analyze screener_results.csv — what patterns do you see?"

---

## WEEK 3: Strategy Refinement (Days 15-21)

### Day 15 (Tue Apr 8)
- [ ] Run screener at 9:30 AM
- [ ] Ask Claude Code: "Add MACD and Bollinger Bands to data/signals.py with tests"
- [ ] Run new tests
- [ ] Commit and push

### Day 16 (Wed Apr 9)
- [ ] Run screener at 9:30 AM
- [ ] Build a combined signal generator: `strategies/signal_generator.py`
- [ ] It should combine momentum + mean reversion signals
- [ ] Rule: only BUY when BOTH strategies agree
- [ ] Backtest the combined strategy

### Day 17 (Thu Apr 10)
- [ ] Run screener at 9:30 AM
- [ ] Add ATR-based trailing stop loss (not just fixed stop)
- [ ] Ask Claude Code: "Implement trailing stop loss in risk/stop_loss.py"
- [ ] Test with backtest — does trailing stop improve results?

### Day 18 (Fri Apr 11)
- [ ] Run screener at 9:30 AM
- [ ] Review 3 weeks of paper trading data
- [ ] Ask Claude Code: "Read logs/trade_journal.md and screener_results.csv. What are my biggest mistakes?"
- [ ] Update `logs/weekly_notes.md`

### Day 19 (Sat Apr 12) — Study Day
- [ ] Read Ernest Chan — Chapters 5-6
- [ ] Topic: Position sizing and Kelly Criterion
- [ ] Ask Claude Code: "Add Kelly Criterion position sizing as an option in risk/manager.py"
- [ ] Backtest: Kelly sizing vs fixed 1% risk — which is better?

### Day 20 (Sun Apr 13) — Study Day
- [ ] Review ALL your code. Can you explain every function?
- [ ] Ask Claude Code for a full audit: use `prompts/audit-trading-system.md`
- [ ] Fix any issues found
- [ ] Commit and push

### Day 21 (Mon Apr 14)
- [ ] Run screener at 9:30 AM
- [ ] DECISION POINT: review 3 weeks of paper results
- [ ] If win rate > 40% AND positive total PnL: consider moving to live (Week 4)
- [ ] If not: continue paper trading another week, adjust strategy
- [ ] Write honest assessment in `logs/weekly_notes.md`

---

## WEEK 4: Go Live (Carefully) (Days 22-30)

### Day 22 (Tue Apr 15)
- [ ] Run screener at 9:30 AM
- [ ] If approved for live: start with ONLY 1 STOCK, ONLY ₹10,000 capital
- [ ] Set config: `INITIAL_CAPITAL = 10_000` and `WATCHLIST = ["RELIANCE.NS"]`
- [ ] Run `python trader.py --live` — place ONE trade only
- [ ] Monitor all day. Do NOT walk away.

### Day 23 (Wed Apr 16)
- [ ] Check yesterday's live trade result
- [ ] Run screener at 9:30 AM
- [ ] If yesterday was profitable: continue with 1 stock
- [ ] If loss: review why. Was it strategy or market? Don't panic.
- [ ] Log everything in trade journal

### Day 24 (Thu Apr 17)
- [ ] Run screener at 9:30 AM
- [ ] If 2 profitable days: add 1 more stock to live watchlist (total: 2)
- [ ] Keep capital at ₹10,000 — don't increase yet
- [ ] Compare paper vs live results — any difference?

### Day 25 (Fri Apr 18)
- [ ] Run screener at 9:30 AM
- [ ] Friday: let system respect the Friday rule (no new positions after 2 PM)
- [ ] Weekly review: live trading PnL this week
- [ ] Update `logs/weekly_notes.md`

### Day 26 (Sat Apr 19) — Study Day
- [ ] Analyze your live trade log
- [ ] Ask Claude Code: "Compare my live trades vs what backtest predicted"
- [ ] Identify: where does reality differ from backtest?
- [ ] Common issues: slippage, timing, API delays

### Day 27 (Sun Apr 20) — Study Day
- [ ] Read about risk of ruin: what % of capital can you lose before recovery is impossible?
- [ ] Review your circuit breakers — are they tight enough?
- [ ] Plan: what would you do if you lost 5% in one day?
- [ ] Write your trading rules in `TRADING_RULES.md` — these are YOUR rules, not the bot's

### Day 28 (Mon Apr 21)
- [ ] Run screener at 9:30 AM
- [ ] If Week 4 profitable: consider increasing to 3 stocks
- [ ] Still keep capital at ₹10,000-₹20,000
- [ ] DO NOT go all-in. Ever.

### Day 29 (Tue Apr 22)
- [ ] Run screener at 9:30 AM
- [ ] Normal trading day
- [ ] Start preparing presentation for Vinay (Day 30 review)

### Day 30 (Wed Apr 23) — REVIEW DAY
- [ ] Run screener one last time
- [ ] Prepare presentation for Vinay:
  - [ ] Show git history (`git log --oneline`)
  - [ ] Show backtest results
  - [ ] Show live trading PnL
  - [ ] Explain your risk management rules
  - [ ] Explain what worked and what didn't
  - [ ] What's your plan for Month 2?
- [ ] Push final state to GitHub
- [ ] Celebrate. You built a trading system from scratch in 30 days.

---

## Quick Reference — Daily Routine

Every trading day at 9:15 AM:
```bash
cd ~/YTB/trading-bot
source venv/bin/activate
python trader.py --screener      # Check signals
python trader.py                 # Paper trade
# OR
python trader.py --live          # Live trade (Week 4+)
```

Every evening:
```bash
cat logs/trading_bot.log | tail -50   # Review today's decisions
git add -A && git commit -m "Daily log: $(date +%Y-%m-%d)"
git push
```

Every weekend:
```bash
python -m tests.backtest --multi     # Re-run backtests
python -m pytest tests/ -v           # Verify nothing is broken
```
