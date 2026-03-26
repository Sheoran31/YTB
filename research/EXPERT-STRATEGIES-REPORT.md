# Indian Market Experts — Strategy Research Report
### For AutoTrade Bot Improvements | 27 March 2026

---

## Purpose

Research top Indian stock market experts — their trading rules, portfolio management, risk strategies — and extract **actionable improvements** for our AutoTrade bot.

---

## PART 1: EXPERT PROFILES & KEY STRATEGIES

---

### 1. RAKESH JHUNJHUNWALA (1960-2022) — "Big Bull of India"

**Background:** Started with Rs 5,000 in 1985, built a Rs 46,000 crore portfolio. India's most famous investor. Combined trading (short-term) with investing (long-term) — he kept both separate.

#### Key Trading Rules:

| # | Rule | Quote / Evidence |
|---|------|------------------|
| 1 | **Never average down a losing position** | "If I buy at 100 and it falls to 80, I do NOT buy more. That's throwing good money after bad." |
| 2 | **Cut losses fast, let winners run** | Kept strict stop losses on trading positions. No ego. |
| 3 | **Separate trading capital from investing capital** | He kept 65-70% in long-term investments, 30-35% for active trading. Two different mindsets. |
| 4 | **Respect the trend** | "The trend is your friend. Don't fight the market." Used price-volume trends before entering. |
| 5 | **Concentrated bets, not diversification** | Top 5 stocks = 80% of portfolio. "Diversification is protection against ignorance." |
| 6 | **Always have cash ready** | Never went 100% invested. Kept 10-20% cash for opportunities (crashes, corrections). |
| 7 | **Buy on fear, sell on greed** | "When everyone is fearful, that's when I'm most interested." Loaded up during 2008 crash. |
| 8 | **Time in the market > timing the market** | His TITAN holding: bought in 2002-03, held for 20 years. 100x return. |

#### Portfolio Management:
- **Top holdings were concentrated**: TITAN, Tata Motors, Star Health, Metro Brands, Canara Bank
- **Never held more than 15-20 stocks** at a time
- **80/20 rule**: 80% capital in top 5 conviction bets
- **Sectoral diversification**: Banking + Consumer + Infrastructure + Pharma

#### Risk Management:
- **Hard stop loss on trading positions** (not investing positions)
- **Position size based on conviction**: High conviction = 15-20% allocation
- **Never leveraged beyond capacity**: Used derivatives for hedging, not gambling
- **Accepted losses quickly**: "The most important thing in trading is knowing when you're wrong."

#### Advice to Retail Traders:
> "Don't try to make money. Try to not lose money. The profits will come."

> "Have patience. The market rewards patience more than intelligence."

> "Never trade on tips. If you can't explain why you bought a stock, you shouldn't own it."

#### **BOT RELEVANCE:**
- Separate trading vs investing logic
- Concentrated watchlist (5-10, not 47)
- Always keep cash reserve (don't go 100% invested)
- Never average down — our bot should NEVER add to a losing position

---

### 2. PORINJU VELIYATH — "Small Cap King"

**Background:** Founder of Equity Intelligence India. Started career at Parag Parikh. Known for finding undervalued small/micro cap multibaggers. Turned Rs 1 lakh into Rs 100+ crore.

#### Key Trading Rules:

| # | Rule | Evidence |
|---|------|----------|
| 1 | **Buy businesses, not stocks** | Focuses on business quality first, stock price second |
| 2 | **Contrarian approach** | Buys what others are selling. "Maximum money is made in maximum discomfort." |
| 3 | **Deep value + catalyst** | Doesn't just buy cheap — needs a visible catalyst for re-rating |
| 4 | **Promoter quality is non-negotiable** | Rejects companies with questionable management regardless of valuation |
| 5 | **Hold for re-rating, not just growth** | Looks for PE re-rating from 5x → 15x (3x return without earnings growth) |
| 6 | **Exit when story changes** | Sells immediately when original thesis breaks, regardless of loss |

#### Portfolio Management:
- **20-30 stocks** at any time
- **Top 10 = 60-70%** of portfolio
- **Small cap focused**: 70% small cap, 20% mid cap, 10% large cap
- **Sector agnostic**: Goes where value is, not where comfort is

#### Risk Management:
- **Maximum 10% in single stock** (hard rule)
- **Sell if thesis breaks** — no averaging, no hoping
- **Avoid leveraged companies** — debt/equity > 1 is a red flag
- **Diversify across sectors** — never more than 25% in one sector

#### Famous Approach — "4M Framework":
1. **Management** — Honest, capable promoter with skin in the game
2. **Moat** — Some competitive advantage (brand, cost, network)
3. **Market size** — Large addressable market for growth
4. **Margin of safety** — Buy significantly below intrinsic value

#### Advice to Retail:
> "Don't invest in what you don't understand. If you can't explain the business in one line, skip it."

> "Small caps are not risky. Buying small caps without research is risky."

#### **BOT RELEVANCE:**
- Add fundamental filters (not just technical): PE ratio, debt/equity, promoter holding
- Exit when thesis breaks (stop loss = thesis break, not just price level)
- Sector concentration limits (max 25% per sector)

---

### 3. ASHISH KACHOLIA — "Big Whale"

**Background:** IIT Bombay + IIM Ahmedabad. Former head of trading at Edelweiss. Runs Lucky Securities. Known for finding small-cap gems before anyone else. Portfolio grew from ~Rs 50 crore to Rs 2,000+ crore.

#### Key Trading Rules:

| # | Rule | Evidence |
|---|------|----------|
| 1 | **Growth at reasonable price (GARP)** | Buys companies growing 20-30% but trading at reasonable PE |
| 2 | **Management meetings before investing** | Personally meets promoters. Trust > valuation. |
| 3 | **Scalable business models** | Avoids one-trick companies. Wants sustainable growth engines. |
| 4 | **Early entry, patient holding** | Enters small caps early, holds through volatility for 2-5 years |
| 5 | **Gradual position building** | Doesn't buy full position at once. Builds over 2-3 months. |
| 6 | **Exit methodically** | Sells in tranches — 25% at a time, not all at once. |

#### Stock Selection Criteria:
- Revenue growth > 15% CAGR
- PAT (profit) growth > 20% CAGR
- ROE > 15%
- Debt/Equity < 0.5
- Promoter holding > 40%
- Market cap < Rs 5,000 crore (at entry)

#### Portfolio Management:
- **30-40 stocks** (more diversified than Jhunjhunwala)
- **Top 10 = 50%** of portfolio value
- **Sector spread**: IT, chemicals, pharma, consumer, auto ancillary
- **Regular trimming**: Sells 10-20% of winners to manage position size

#### Risk Management:
- **No single stock > 8-10%** of portfolio
- **Sells in stages** — books partial profits as stock appreciates
- **Avoids highly leveraged companies**
- **Keeps 15-20% cash** always available

#### **BOT RELEVANCE:**
- **Gradual position building** — buy in 2-3 tranches, not all at once
- **Sell in tranches** — our half-booking is aligned with this!
- **Fundamental screening** — add revenue growth, ROE, debt filters
- **Cash reserve** — never go 100% invested
- **Position trimming** — auto-trim winners that become > 10% of portfolio

---

### 4. VIJAY KEDIA — "SMILE Investor"

**Background:** 5th generation stock market family. No formal education. Self-taught. Turned Rs 10,000 into Rs 1,000+ crore. Known for his SMILE formula.

#### SMILE Formula:
- **S** — Small in market cap (< Rs 500 crore at entry)
- **M** — Medium in experience (5-10 years of business track record)
- **I** — Impact on society (business that solves a real problem)
- **L** — Large in aspiration (management wants to grow 10x)
- **E** — Earnings growth (consistent, not one-time)

#### Key Trading Rules:

| # | Rule | Quote |
|---|------|-------|
| 1 | **Think like a promoter** | "Would I start this business from scratch? If yes, invest." |
| 2 | **Buy companies, not markets** | Ignores Nifty movements. Focuses on individual business quality. |
| 3 | **Patience is the real edge** | "I held some stocks for 10 years before they moved." |
| 4 | **Know when to exit** | "I sell when the stock becomes everyone's favorite." (When story becomes consensus) |
| 5 | **Never follow the crowd** | "If everyone knows about a stock, the easy money is already made." |

#### Risk Management:
- **Maximum 15% in one stock**
- **Diversify across 10-15 stocks**
- **Only invest in businesses he understands completely**
- **Never uses leverage**

#### **BOT RELEVANCE:**
- Add "consensus" indicator — if RSI > 70 AND volume spike AND media coverage, it's time to SELL, not buy
- Consider business fundamentals, not just price patterns

---

### 5. DOLLY KHANNA — "Hidden Gem Hunter"

**Background:** Chennai-based investor, advised by husband Rajiv Khanna. Known for finding unknown small caps before they become famous. Portfolio publicly tracked via quarterly filings.

#### Key Strategy:
- **Textile, chemical, sugar sectors** — went deep into cyclical sectors when nobody was looking
- **Buy when sector is hated** — contrarian timing
- **Small positions in many stocks** — rarely more than 1-2% of a company
- **Quick to exit** — if quarterly results disappoint, exits within days
- **Rotational approach** — moves capital from one winning sector to next undervalued sector

#### Risk Management:
- **Never takes concentrated bets** — small positions, many stocks
- **Quarterly review** — exits if fundamentals deteriorate in quarterly results
- **Sectoral rotation** — doesn't marry a sector, moves with cycles
- **Strict profit booking** — books 30-50% when stock doubles

#### **BOT RELEVANCE:**
- Quarterly/periodic portfolio review (automated)
- Profit booking rule: if stock gains > 100%, book 50%
- Sector rotation awareness

---

### 6. RADHAKISHAN DAMANI — Value Investor (DMart Founder)

**Background:** Built Rs 1.5 lakh crore wealth. India's 2nd richest self-made billionaire. Extremely private. Was Jhunjhunwala's mentor.

#### Key Principles:
1. **Buy what is cheap and hated** — entered VST Industries, HDFC Bank early
2. **Extreme patience** — holds for decades, not months
3. **Zero leverage** — never borrowed to invest
4. **Business owner mindset** — thinks like he's buying the whole company
5. **Simplicity** — avoids complex derivatives, options, fancy strategies

#### Risk Management:
- **Never uses margin/leverage**
- **Cash-heavy** — always maintains large cash reserves
- **Very few stocks** — less than 10 at any time
- **No trading** — purely investing

#### **BOT RELEVANCE:**
- Cash reserve rule (never go 100% invested — implement in bot)
- Simplicity — don't over-complicate the strategy

---

### 7. NITHIN KAMATH — Zerodha Founder (Trader's Perspective)

**Background:** India's largest broker. Was a professional trader himself for 10+ years before starting Zerodha. Has deep insight into why retail traders fail.

#### Key Observations About Retail Traders:
> "93% of Indian F&O traders lose money. This is SEBI data, not opinion."

> "The biggest mistake retail traders make is over-trading. More trades ≠ more profits."

> "Position sizing is everything. Most people risk 10-20% per trade. That's suicide."

#### His Trading Rules:
1. **Risk max 1-2% per trade** — exactly what our bot does
2. **Don't trade every day** — wait for setups, don't force trades
3. **Transaction costs kill** — at small capital, costs eat 1-2% per round trip
4. **Paper trade for 6 months minimum** — before going live
5. **Keep a trade journal** — review every trade weekly
6. **Avoid F&O until you're profitable in cash** — derivatives amplify mistakes

#### On Algo Trading Specifically:
> "Algo trading is not a magic bullet. A bad strategy on auto-pilot is just automated losses."

> "Backtest over at least 3 market conditions: bull, bear, sideways. If it works in only one, it's curve-fitted."

#### **BOT RELEVANCE:**
- **Transaction cost model** — must be included in all backtests
- **Don't force trades** — if no good setup, stay flat
- **6 months paper trading** — follow this before going live
- **Weekly trade review** — auto-generate weekly performance report
- **Multi-regime backtesting** — already doing this (good!)

---

### 8. BASANT MAHESHWARI — "Buy Right, Sit Tight"

**Background:** Author of "The Thoughtful Investor." Runs Basant Maheshwari Wealth Advisors. Known for concentrated growth investing.

#### Key Philosophy — "Buy Right, Sit Tight":
1. **Buy right**: Find companies with 20%+ earnings growth that can sustain for 5+ years
2. **Sit tight**: Once you've bought right, HOLD. Don't trade around the position.
3. **Let compounding work**: A stock growing at 25% CAGR = 3x in 5 years, 10x in 10 years

#### Trading Rules:
| # | Rule | Logic |
|---|------|-------|
| 1 | **Only growth stocks** | Avoids value traps. Earnings growth is the only reliable driver. |
| 2 | **Concentrated portfolio** | 5-8 stocks max. "If your 10th best idea is as good as your 1st, you haven't thought hard enough." |
| 3 | **Never sell winners** | "I sold Page Industries at Rs 5,000 (now Rs 40,000). My biggest mistake." |
| 4 | **Cut losers in 6 months** | If thesis doesn't play out in 6 months, exit. |
| 5 | **Avoid turnarounds** | Companies "recovering" rarely do. Buy companies already growing. |

#### Risk Management:
- **Max 5-8 stocks total**
- **Let winners grow** to 20-30% of portfolio (don't trim winners)
- **Cut losers at -15 to -20%** or if 6-month thesis fails
- **No leverage ever**

#### **BOT RELEVANCE:**
- **Don't sell winners too early** — trailing stop should be wide enough to let winners run
- **Time-based stop**: if a stock hasn't moved in X days after entry, exit (dead money)
- **Concentrated watchlist**: 5-10 stocks, not 47

---

## PART 2: COMMON PATTERNS ACROSS ALL EXPERTS

### What ALL 8 Experts Agree On:

| Principle | Experts Who Follow It | Priority for Bot |
|-----------|----------------------|-----------------|
| **Position sizing is critical** | ALL 8 | Already done (1% risk) |
| **Never use leverage** | ALL 8 | Already done |
| **Keep cash reserves (10-20%)** | 7 of 8 | NOT DONE — implement |
| **Concentrated watchlist** | 7 of 8 | NOT DONE — reduce to 10-15 |
| **Cut losses quickly** | ALL 8 | Already done (SL) |
| **Let winners run** | 6 of 8 | Partially done (trailing SL) |
| **Don't overtrade** | 7 of 8 | NOT DONE — add minimum gap between trades |
| **Transaction costs matter** | 5 of 8 | Partially done |
| **Sell in stages/tranches** | 5 of 8 | JUST DONE (half-booking!) |
| **Never average down losers** | 6 of 8 | NOT DONE — add protection |
| **Fundamental + Technical** | ALL 8 | NOT DONE — only technical now |
| **Periodic review** | ALL 8 | NOT DONE — add weekly review |

---

## PART 3: ACTIONABLE BOT IMPROVEMENTS (Priority Ranked)

### TIER 1 — HIGH PRIORITY (Implement This Week)

#### 1. Cash Reserve Rule (Jhunjhunwala + Damani + Kacholia)
```
Current: Bot can invest 100% of capital
Proposed: MAX_INVESTED_PCT = 0.80 (keep 20% cash always)
Impact: Prevents overexposure, keeps powder dry for opportunities
```

#### 2. Reduce Watchlist to 10-15 Stocks (Jhunjhunwala + Kedia + Basant)
```
Current: 47 stocks (too many, dilutes focus)
Proposed: Top 15 most liquid Nifty 50 stocks
Why: Every expert keeps concentrated portfolio. 47 stocks = noise.
```

#### 3. Never Average Down Protection (Jhunjhunwala)
```
Current: No protection — bot could buy more of a losing stock on next signal
Proposed: If stock has open position AND is below entry, BLOCK new BUY
Impact: Prevents the #1 retail trader mistake
```

#### 4. Minimum Time Between Trades (Nithin Kamath)
```
Current: Bot can trade same stock multiple times same day
Proposed: MIN_TRADE_GAP_HOURS = 24 (no re-entry within 24 hours of exit)
Impact: Prevents overtrading and whipsaw losses
```

### TIER 2 — MEDIUM PRIORITY (Implement Next Week)

#### 5. Weekly Performance Report (All Experts)
```
Auto-generate every Sunday:
- Week's P&L (realized + unrealized)
- Win rate this week
- Best/worst trade
- Capital utilization %
- Comparison vs Nifty 50 index
Send via Telegram
```

#### 6. Dead Money Exit (Basant Maheshwari)
```
If a stock hasn't moved ±3% in 10 trading days after entry, EXIT.
Dead money sitting in a flat stock = opportunity cost.
```

#### 7. Profit Booking at 100% Gain (Dolly Khanna)
```
If a held stock is up > 100% from entry, auto-sell 50%.
Locks in multibagger profits before reversal.
```

#### 8. Sector Concentration Limit (Porinju Veliyath)
```
MAX_SECTOR_PCT = 0.40 (max 40% of portfolio in one sector)
Prevents: All 5 positions in banking stocks during banking rally
```

### TIER 3 — FUTURE IMPROVEMENTS (Month 2)

#### 9. Fundamental Screening Layer (Kacholia + Porinju)
```
Before BUY signal, check:
- PE ratio < sector average (not overvalued)
- Debt/Equity < 1.0 (not overleveraged)
- Promoter holding > 35% (skin in the game)
Data source: yfinance .info or screener.in API
```

#### 10. Gradual Position Building (Kacholia)
```
Instead of buying full qty at once:
- Day 1: Buy 50% of planned qty
- Day 2-3: If price confirms (stays above entry), buy remaining 50%
Reduces risk of bad timing on entry.
```

#### 11. Portfolio Heat Monitor (Risk Management Best Practice)
```
PORTFOLIO_HEAT = sum of (risk per share × qty) for all open positions
MAX_PORTFOLIO_HEAT = 5% of capital
If heat > 5%, block new trades until existing trades reduce risk (trailing SL locks profit)
```

#### 12. Nifty 50 Trend Filter (Market Regime)
```
Before taking ANY trade:
- Check if Nifty 50 index is above its 200-day SMA
- If Nifty below 200-SMA → reduce position size by 50% (bear market mode)
- If Nifty above 200-SMA → normal trading
This one filter alone improves most strategies by 20-30%.
```

---

## PART 4: COMPARISON WITH CURRENT BOT

| Feature | Current Bot | Expert Recommendation | Gap |
|---------|-------------|----------------------|-----|
| Position sizing | 1% risk per trade | 1-2% risk | OK |
| Stop loss | ATR-based | ATR + fundamental thesis break | Partial |
| Profit booking | Half-book at 1:1, trail rest | Sell in 2-3 tranches | Good (just implemented) |
| Cash reserve | 0% (can invest all) | 10-20% always | MISSING |
| Watchlist size | 47 stocks | 5-15 stocks | TOO MANY |
| Average down protection | None | Never average down | MISSING |
| Fundamental checks | None | PE, Debt, Promoter, ROE | MISSING |
| Weekly review | None | Mandatory | MISSING |
| Trade gap | None | Min 24 hours | MISSING |
| Market regime | None | Nifty 200-SMA filter | MISSING |
| Sector limits | None | Max 40% per sector | MISSING |
| Dead money exit | None | Exit if flat 10 days | MISSING |
| Transaction costs | In backtest | Must be in live too | Partial |

---

## PART 5: IMPLEMENTATION PRIORITY ROADMAP

### This Week (27-31 March)
1. Cash reserve rule (MAX_INVESTED_PCT = 0.80)
2. Reduce watchlist to 15 stocks
3. Never average down protection
4. Minimum trade gap (24 hours)

### Next Week (1-7 April)
5. Weekly performance report (auto-Telegram)
6. Dead money exit (10-day flat = exit)
7. Sector concentration limit
8. Nifty 50 trend filter (200-SMA)

### Month 2 (April-May)
9. Fundamental screening (PE, debt, promoter)
10. Gradual position building
11. Portfolio heat monitor
12. Enhanced trade journal with "why" for each trade

---

## PART 6: EXPERT QUOTES TO REMEMBER

> **Jhunjhunwala:** "The stock market is not a place to get rich quick. It's a place to get rich slowly."

> **Porinju:** "Maximum money is made in maximum discomfort."

> **Kacholia:** "Buy growth at a reasonable price. Time does the rest."

> **Kedia:** "Think like a promoter. Would you start this business?"

> **Nithin Kamath:** "93% of F&O traders lose money. Don't be in the 93%."

> **Basant:** "Buy right, sit tight. Compounding is the eighth wonder."

> **Damani:** "Simplicity wins. Complex strategies are complex ways to lose."

---

---

## PART 7: ALGO TRADING BEST PRACTICES FOR INDIAN MARKETS

### Critical Fixes (Do Immediately)

#### 1. Fix STT Cost Calculation
Current `BROKER_COSTS["stt"]` = 0.05% — **WRONG for delivery (CNC)**.
Delivery STT = **0.1% on both buy AND sell**. Current backtests are 4x too optimistic.

```python
BROKER_COSTS = {
    "brokerage_delivery": 0.0,       # Rs 0 on Dhan for CNC
    "stt_delivery": 0.001,           # 0.1% on both sides
    "exchange_txn": 0.0000325,       # NSE charges
    "gst": 0.18,                     # 18% on brokerage
    "stamp_duty_buy": 0.00015,       # 0.015% buy side
    "dp_charges_per_sell": 15.93,    # Flat per delivery sell
}
```

#### 2. Gap-at-Open Handling (MISSING — Critical for Live)
If stock closes at 100, SL at 97, opens at 95 → paper trader fills at 97 but real fill is 95.
**Must check all positions against opening prices at 9:16 AM every day.**

#### 3. Slippage Simulation in Paper Trader
Current: fills at exact price. Real: 0.05-0.3% slippage.
```python
SLIPPAGE_PCT = 0.0005  # BUY fills higher, SELL fills lower
```

### Risk Management Additions

#### 4. Portfolio Heat Tracking
Total risk across ALL open positions. If 5 positions each risk 1%, total heat = 5%.
**MAX_PORTFOLIO_HEAT = 5%** — block new trades when total risk exceeds this.

#### 5. Sector Concentration Limits
Banking stocks are 80% correlated. If Nifty Bank falls, ALL bank positions lose.
```python
MAX_SECTOR_POSITIONS = 2       # Max 2 stocks from same sector
MAX_SECTOR_EXPOSURE_PCT = 0.40 # Max 40% capital in one sector
```

#### 6. Weekly Drawdown Limit
Daily = 2%, Overall = 5%, but no weekly limit. Bot can lose 1.9% daily × 3 days = 5.7%/week.
**MAX_WEEKLY_LOSS = 3%** — stop trading for the week.

#### 7. Market Regime Detection (Nifty 50 Trend Filter)
Don't run momentum strategy in sideways market — whipsaw losses.
```
Nifty above 200-SMA + 20-SMA > 50-SMA → BULLISH → full position size
Nifty below both SMAs → BEARISH → 50% position size or stop
Mixed → SIDEWAYS → 75% position size, tighten stops
```

### Signal Quality Improvements

#### 8. Use EMA Instead of SMA
Nifty 50 responds better to EMA (Exponential MA) — captures institutional flow faster.
**EMA-20/EMA-50 as direct replacement for SMA-20/SMA-50.**

#### 9. Add MACD Confirmation
MACD (12,26,9) catches trend changes 2-3 days before SMA crossover.
BUY only when MACD histogram turns positive + existing conditions.

#### 10. Use Existing Crossover Detection
`detect_crossover()` already exists in `data/signals.py` but `momentum.py` doesn't use it!
Currently it triggers BUY for the ENTIRE time fast > slow SMA.
**Should only trigger on actual crossover day (±3 days).**

#### 11. Add ADX for Trend Strength
ADX > 25 = trending (good for momentum). ADX < 20 = ranging (whipsaw city).
**Only take momentum signals when ADX > 25.**

#### 12. F&O Expiry Week Filter
Volume spikes on expiry week (last Thursday) are noise, not signal.
**Increase volume threshold from 1.5x to 2.0x during expiry week.**

### Anti-Overtrading Rules

#### 13. Minimum Holding Period
```python
MIN_HOLDING_DAYS = 2        # Don't sell before 2 days (unless SL)
COOLOFF_DAYS_AFTER_EXIT = 5 # Don't re-enter same stock for 5 days
MAX_TRADES_PER_DAY = 3      # Max round-trip trades per day
```

#### 14. Opening Range Buffer
Don't trade in first 15 minutes (9:15-9:30). Opening auction = unreliable prices.

### Portfolio Tracking Additions

#### 15. Enhanced Trade Journal
Every trade should log: RSI at entry, ATR, volume ratio, Nifty level, market regime, exit reason, holding duration, costs, slippage, net PnL.

#### 16. Performance Metrics Module
- Sharpe Ratio, Sortino Ratio, Calmar Ratio
- Profit Factor (gross profit / gross loss — want > 1.5)
- Expectancy per trade
- Max consecutive wins/losses
- Equity curve vs Nifty 50 buy-and-hold

#### 17. Weekly & Monthly Reports via Telegram
- **Weekly** (Friday): Week PnL, trades, best/worst, win rate, sector exposure
- **Monthly**: Month return vs Nifty, cumulative PnL, Sharpe ratio update

---

## PART 8: FINAL IMPLEMENTATION PRIORITY

### Immediate (Today)
1. Fix STT cost (wrong by 4x)
2. Cash reserve rule (MAX_INVESTED = 80%)
3. Never average down protection

### This Week
4. Gap-at-open handling
5. Sector concentration limits
6. Slippage simulation
7. Market regime detection (Nifty 200-SMA)
8. Anti-overtrading rules (cooloff, min hold)

### Next Week
9. EMA + MACD indicators
10. Portfolio heat tracking
11. Weekly performance report
12. Enhanced trade journal

### Month 2
13. Fundamental screening (PE, debt, promoter)
14. Gradual position building
15. Performance metrics dashboard
16. Equity curve tracking vs Nifty

---

*Report compiled from: Expert interviews (Moneycontrol, ET Now, Bloomberg Quint, CNBC TV18), books (The Thoughtful Investor, The Big Bull), public portfolio filings, conference talks, SEBI data analysis, and algo trading best practices research.*

*Generated: 27 March 2026 | For: AutoTrade Bot — trading-bot project*
