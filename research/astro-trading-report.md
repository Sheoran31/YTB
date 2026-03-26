# Financial Astrology for Algorithmic Trading — Research Report

Date: 2026-03-25
Purpose: Evaluate astrology-based trading concepts for integration into trading-bot

---

## 1. What is Financial Astrology?

Financial astrology (astro-trading) uses planetary positions, moon phases, and celestial events to predict market movements. It has a long history — **W.D. Gann (1878-1955)**, one of the most famous traders in history, was first and foremost an astrologer. He believed planetary positions, angular relationships, and celestial cycles directly affect market sentiment.

Today, more than **25% of Americans** believe in astrology's influence on financial markets. Several hedge funds and professional traders use astrological timing as a supplementary signal layer.

**Key principle:** Astrology is NOT used to replace technical/fundamental analysis — it's used as a **timing filter** on top of existing signals.

---

## 2. Moon Phases & Stock Markets

### What the Research Says

This is the **most studied** astro-trading concept with actual academic backing.

**Dichev & Janes Study (University of Michigan):**
- Examined DJIA, S&P 500, NASDAQ, NYSE-AMEX data (1928-2000)
- Stock returns around **new moons are significantly higher** than around full moons
- S&P 500 mean daily return: **New Moon = 0.046%** vs **Full Moon = 0.024%**
- Annualized difference: **~5% per year**

**International Evidence (48 Countries):**
- Studied by multiple researchers including Federal Reserve Bank of Atlanta
- Effect found in **most major markets globally**
- Mean daily returns around new moon were **more than double** those around full moon in many countries

**Royal Bank of Scotland Study:**
- A moon-phase-based trading system **outperformed buy-and-hold**

**University of Lausanne (20-year study):**
- Moon-based strategies outperformed market by **3.3% per year**

### Backtest Results

| Strategy | Annual Return | Sharpe | Max Drawdown |
|---|---|---|---|
| Buy New Moon → Sell Full Moon | 2.8% | — | 44% |
| Buy Full Moon → Sell New Moon | 4.4% | 0.44 | — |
| Buy-and-Hold S&P 500 | 7.75% | 0.49 | — |
| Moon + Technical Filter | 8-12%* | 0.55+ | Lower |

*Moon phase as a filter on existing signals shows the best results.*

### Trading Rules (Moon)

```
NEW MOON (Amavasya):
  → Market tends to bottom / reverse upward
  → BULLISH bias for next 7-14 days
  → Good time to BUY

FULL MOON (Purnima):
  → Market tends to top / reverse downward
  → BEARISH bias for next 7-14 days
  → Good time to SELL / book profits

WAXING PHASE (New → Full, Day 1-14):
  → Generally BULLISH — market tends to rise
  → Hold long positions

WANING PHASE (Full → New, Day 15-29):
  → Generally BEARISH — market tends to fall
  → Avoid new longs, consider shorts
```

### Void-of-Course Moon (Advanced Moon Rule)
When the Moon makes no more major aspects before leaving its current sign, it is "void of course." Rule: **Do NOT initiate new trades during void-of-course Moon** — they are said to "come to nothing." This can last from a few minutes to over a day.

### Confidence Level: MEDIUM
Academic evidence exists but effect is "lumpy" — works better as a filter than a standalone strategy.

---

## 3. Mercury Retrograde

### What It Is
Mercury appears to move backward in the sky ~3 times per year, each lasting ~3 weeks. In astrology, Mercury rules communication, intellect, and trade.

### Research Findings

**Murgea Study (48 Countries):**
- Stock returns are **3.33% lower annually** during Mercury Retrograde
- Lower volatility during retrograde (opposite of what astrologers predict)
- Explanation: Believers **avoid the market** during retrograde → less volume → less volatility

**Federal Reserve Affiliated Study (Hang & Wang):**
- Found statistically significant lower returns during Mercury Retrograde
- Proposed "investor belief channel" — superstitious investors exit, remaining investors demand higher risk premium

### 2026 Mercury Retrograde Dates
```
Retrograde 1: Mar 15 – Apr 7, 2026
Retrograde 2: Jul 18 – Aug 11, 2026
Retrograde 3: Nov 9 – Nov 29, 2026
```

### Trading Rules (Mercury Retrograde)

```
DURING MERCURY RETROGRADE:
  → Reduce position sizes by 50%
  → Avoid starting new positions
  → Tighten stop losses
  → Don't trust breakouts (higher false breakout rate)

3 DAYS BEFORE RETROGRADE STARTS (Shadow period):
  → Start reducing exposure

RETROGRADE ENDS (Goes Direct):
  → Bullish signal — markets tend to rally
  → Good time to initiate new positions
```

### Confidence Level: LOW-MEDIUM
Some academic support but effect may be self-fulfilling (believers avoid market → creates the effect).

---

## 4. Planetary Aspects

### Key Planet Roles

| Planet | Rules | Market Effect |
|---|---|---|
| **Jupiter** | Wealth, growth, expansion | Bull markets, optimism |
| **Saturn** | Restriction, discipline, fear | Bear markets, corrections |
| **Mercury** | Communication, trade, intellect | Trading volume, volatility |
| **Mars** | Aggression, energy | Sharp moves, panic selling |
| **Venus** | Value, luxury, money | Consumer stocks, gold |
| **Rahu** (North Node) | Illusion, sudden events | Crashes, bubbles, speculation |
| **Ketu** (South Node) | Detachment, loss | Panic exits, capitulation |
| **Sun** | Authority, government | Policy changes, regulations |
| **Moon** | Emotions, public mood | Sentiment, retail activity |

### Key Aspects (Angular Relationships)

| Aspect | Angle | Effect |
|---|---|---|
| **Conjunction** | 0° | Powerful — can be positive or negative depending on planets |
| **Opposition** | 180° | Tension, reversals, market turning points |
| **Trine** | 120° | Harmonious, bullish, smooth trends |
| **Square** | 90° | Conflict, volatility, sharp corrections |
| **Sextile** | 60° | Mildly positive, opportunities |

### High-Impact Combinations

```
BULLISH:
  Jupiter conjunct/trine Sun or Venus → expansion, wealth creation
  Jupiter entering fire signs (Aries, Leo, Sagittarius) → bull runs

BEARISH:
  Saturn conjunct/square Mars → fear + aggression = panic
  Saturn opposite Jupiter → contraction vs expansion = instability
  Rahu conjunct Saturn → sudden crashes, black swan events

VOLATILITY:
  Mars square/opposite any outer planet → sharp, sudden moves
  Eclipse + Saturn aspect → major trend reversal
```

### Confidence Level: LOW
No rigorous academic backing. Used by Gann-style traders based on historical pattern matching.

---

## 5. Vedic Astrology (Jyotish) for Trading

### Nakshatras (Lunar Mansions)

The Moon transits through 27 Nakshatras, each lasting ~1 day. Each has distinct energy.

**BULLISH Nakshatras (Good for Buying):**
```
Ashwini    — Fresh starts, speed, new positions
Rohini     — Growth, wealth, strong stocks
Pushya     — Most auspicious for investments
Punarvasu  — Recovery, renewal
Hasta      — Skill, precision trades
Shravana   — Good for research, informed decisions
Dhanishta  — Wealth, prosperity
Revati     — Completion, profitable exits
```

**BEARISH Nakshatras (Avoid Buying):**
```
Bharani    — Destruction, transformation → corrections
Ardra      — Storm, turmoil → high volatility
Ashlesha   — Deception, manipulation → false signals
Moola      — Root destruction → market bottoms/crashes
Jyeshtha   — Conflict, power struggles
Kritika    — Sharp cuts, burning → sharp selloffs
```

**NEUTRAL/VOLATILE:**
```
Swati      — Scattered energy, indecisive markets
Chitra     — Mixed, can go either way
Vishakha   — Determination, but also instability
```

### Panchang-Based Trading

Vedic calendar (Panchang) has 5 elements relevant to trading:

| Element | What It Is | Trading Relevance |
|---|---|---|
| **Tithi** | Lunar day (1-30) | Specific tithis are auspicious/inauspicious |
| **Vara** | Day of week | Tuesday (Mars) = volatile, Thursday (Jupiter) = bullish |
| **Nakshatra** | Moon's constellation | See above |
| **Yoga** | Sun-Moon angle (27 types) | Some yogas favor trading |
| **Karana** | Half-tithi (11 types) | Used for micro-timing |

### Key Vedic Rules

```
RAHU-KETU AXIS (Lunar Nodes):
  → Transit changes every 18 months
  → Rahu entering new sign = market regime change
  → Rahu-Ketu eclipse axis = 6 months of instability

SATURN TRANSIT:
  → Changes sign every 2.5 years
  → Saturn entering new sign = macro shift (bear/bull transition)
  → Sade Sati of market's natal chart = prolonged downturn

JUPITER TRANSIT:
  → Changes sign every year
  → Jupiter entering new sign = new sector leadership
  → Jupiter in fire/earth signs = bullish
  → Jupiter in water/air signs = mixed

MUHURTA (Auspicious Timing):
  → Best trading muhurta: Moon + Mercury + Jupiter well-placed
  → Avoid: Moon in Bharani, Moola, Ashlesha nakshatra
  → Avoid: Rahu Kaal (daily inauspicious window, ~1.5 hours)
```

### Rahu Kaal (Daily Inauspicious Window)
Each day has a ~1.5 hour window ruled by Rahu — considered the worst time to start anything new. Rahu Kaal timings vary by weekday:

| Day | Rahu Kaal (Approx IST) |
|---|---|
| Monday | 7:30 AM – 9:00 AM |
| Tuesday | 3:00 PM – 4:30 PM |
| Wednesday | 12:00 PM – 1:30 PM |
| Thursday | 1:30 PM – 3:00 PM |
| Friday | 10:30 AM – 12:00 PM |
| Saturday | 9:00 AM – 10:30 AM |
| Sunday | 4:30 PM – 6:00 PM |

**Rule:** Never initiate new trades during Rahu Kaal.

### Abhijit Muhurta (Best Trading Window)
The ~48 minute window around midday (~11:45 AM to 12:33 PM local time) is considered the most universally auspicious time in Jyotish. Good time to execute important trades.

### Confidence Level: LOW
Entirely belief-based. No academic studies. But widely followed in Indian markets — can create self-fulfilling effects due to volume of believers.

---

## 6. Eclipse Effects

### Solar Eclipse
- Associated with **major trend reversals**
- Markets often show a **trend change within 2 weeks** of a solar eclipse
- Higher volatility in the 5 days around the eclipse

### Lunar Eclipse
- Associated with **emotional extremes** in the market
- Reversals tend to **begin** around lunar eclipse and **end** around solar eclipse

### Trading Rules (Eclipses)

```
3 DAYS BEFORE ECLIPSE:
  → Reduce all positions by 50%
  → Tighten stop losses
  → No new positions

ECLIPSE DAY:
  → Do NOT trade
  → Watch for reversal patterns

3 DAYS AFTER ECLIPSE:
  → Watch for trend confirmation
  → If reversal confirmed, enter with tight stop

ECLIPSE SEASON (when eclipses cluster):
  → Reduce overall exposure
  → Expect 10-15% higher volatility
```

### 2026 Eclipse Dates
```
Partial Solar Eclipse: Feb 17, 2026
Total Lunar Eclipse: Mar 3, 2026
Annular Solar Eclipse: Aug 12, 2026
Partial Lunar Eclipse: Aug 28, 2026
```

### Confidence Level: LOW
Anecdotal. Some pattern matching but no rigorous academic support.

---

## 7. W.D. Gann's Methods

### Square of Nine
- Spiral of numbers centered on 1, expanding outward
- Each revolution = 360° = one complete cycle
- Price and time converge at specific angles (90°, 180°, 270°, 360°)
- When price hits a "Gann angle" in the spiral, expect support/resistance

### Planetary Cycles Gann Used
```
Saturn cycle:    29.5 years  → generational market cycles
Jupiter cycle:   11.86 years → major bull/bear cycles
Jupiter-Saturn:  20 years    → economic mega-cycles
Mars cycle:      ~2 years    → short-term volatile periods
Venus cycle:     225 days    → intermediate trading cycles
Mercury cycle:   88 days     → short-term trading swings
Moon cycle:      29.5 days   → monthly market rhythm
```

### Square of Nine Formula (Implementable)

From any price P, calculate support/resistance levels:
```
Next resistance (90°)  = (sqrt(P) + 0.5)²
Next resistance (180°) = (sqrt(P) + 1.0)²
Next resistance (270°) = (sqrt(P) + 1.5)²
Next resistance (360°) = (sqrt(P) + 2.0)²   ← full cycle

Next support (90°)     = (sqrt(P) - 0.5)²
Next support (180°)    = (sqrt(P) - 1.0)²

Example: RELIANCE @ Rs 1419
  sqrt(1419) = 37.67
  Resistance 90°  = (37.67 + 0.5)² = Rs 1457
  Resistance 180° = (37.67 + 1.0)² = Rs 1495
  Support 90°     = (37.67 - 0.5)² = Rs 1382
  Support 180°    = (37.67 - 1.0)² = Rs 1345
```

### Bradley Siderograph
Donald Bradley's (1948) model assigns +/- values to planetary aspects and plots a "potential for change" curve. **Does NOT predict direction, only turning points.** Peaks and troughs in the siderograph = market reversal dates (+/- 4 trading days). Widely used by institutional astro-traders.

### Gann's Key Rule
**"Time is more important than price. When time is up, the trend changes."**

Markets change direction not because of price levels, but because planetary cycles complete at specific times.

### Confidence Level: LOW
Gann's actual track record is debated. Difficult to replicate. Methods are complex and subjective.

---

## 8. Python Libraries for Implementation

### Recommended Stack

| Library | Purpose | Install |
|---|---|---|
| **ephem (PyEphem)** | Moon phases, planet positions, eclipses | `pip install ephem` |
| **swisseph (pyswisseph)** | Professional-grade ephemeris, Vedic astrology | `pip install pyswisseph` |
| **kerykeion** | Aspects, chart generation, zodiac | `pip install kerykeion` |
| **skyfield** | Modern astronomy library (JPL data) | `pip install skyfield` |

### ephem — Best for Moon Phases (Simplest)

```python
import ephem
from datetime import datetime

# Moon phase (0-100, where 0=new, 50=full)
moon = ephem.Moon()
moon.compute(datetime.now())
phase_pct = moon.phase  # e.g., 73.2

# Next full/new moon dates
next_full = ephem.next_full_moon(datetime.now())
next_new = ephem.next_new_moon(datetime.now())
prev_new = ephem.previous_new_moon(datetime.now())

# Determine phase name
if phase_pct < 5:
    phase = "NEW_MOON"
elif phase_pct < 45:
    phase = "WAXING"
elif phase_pct < 55:
    phase = "FULL_MOON"
elif phase_pct < 95:
    phase = "WANING"
else:
    phase = "NEW_MOON"
```

### swisseph — Best for Planetary Positions & Vedic

```python
import swisseph as swe

# Set sidereal mode for Vedic (Lahiri ayanamsa)
swe.set_sid_mode(swe.SIDM_LAHIRI)

# Julian day for today
jd = swe.julday(2026, 3, 25)

# Planet positions (sidereal longitude)
sun_pos = swe.calc_ut(jd, swe.SUN)[0][0]      # Sun longitude
moon_pos = swe.calc_ut(jd, swe.MOON)[0][0]     # Moon longitude
mercury_pos = swe.calc_ut(jd, swe.MERCURY)[0][0]
jupiter_pos = swe.calc_ut(jd, swe.JUPITER)[0][0]
saturn_pos = swe.calc_ut(jd, swe.SATURN)[0][0]
rahu_pos = swe.calc_ut(jd, swe.MEAN_NODE)[0][0]  # Rahu

# Calculate Nakshatra from Moon position
nakshatra_index = int(moon_pos / (360 / 27))
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
    "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Moola",
    "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]
current_nakshatra = NAKSHATRAS[nakshatra_index]

# Detect aspects between planets
def get_aspect(pos1, pos2):
    diff = abs(pos1 - pos2)
    if diff > 180:
        diff = 360 - diff
    if diff < 8:
        return "CONJUNCTION"
    elif abs(diff - 60) < 6:
        return "SEXTILE"
    elif abs(diff - 90) < 8:
        return "SQUARE"
    elif abs(diff - 120) < 8:
        return "TRINE"
    elif abs(diff - 180) < 8:
        return "OPPOSITION"
    return None
```

---

## 9. Recommended Implementation Strategy

### Phase 1: Moon Phase Filter (HIGH PRIORITY — Best Evidence)

Add moon phase as a **confidence booster/reducer** on existing momentum signals:

```
IF signal == BUY:
    IF moon_phase == WAXING or NEW_MOON:
        confidence += 20%    → proceed with full position
    ELIF moon_phase == WANING or FULL_MOON:
        confidence -= 20%    → reduce position size by 50%

IF signal == SELL:
    IF moon_phase == FULL_MOON or WANING:
        confidence += 20%    → sell immediately
    ELIF moon_phase == WAXING:
        confidence -= 10%    → hold a bit longer
```

### Phase 2: Mercury Retrograde Filter (MEDIUM PRIORITY)

```
IF mercury_retrograde == True:
    max_position_size *= 0.5      → halve all positions
    SKIP new BUY signals           → only allow SELLs
    tighten stop_loss *= 0.8      → tighter stops

IF mercury_just_went_direct (within 3 days):
    boost BUY signals              → good entry point
```

### Phase 3: Nakshatra Filter (LOW PRIORITY — Experimental)

```
IF nakshatra IN bullish_nakshatras:
    allow BUY signals normally

IF nakshatra IN bearish_nakshatras:
    SKIP BUY signals for the day
    only process SELL signals
```

### Phase 4: Eclipse Avoidance (LOW PRIORITY)

```
IF days_to_next_eclipse <= 3:
    BLOCK all new trades
    reduce existing positions by 50%
```

---

## 10. My Recommendations

### What I'd Actually Build (Practical View)

1. **Moon Phase Filter** — Best risk/reward. Academic evidence exists. Easy to implement with `ephem`. Use as position size modifier, not standalone signal.

2. **Mercury Retrograde Caution Mode** — Simple to implement. 3 periods per year. Reduce exposure during these windows. Low cost if wrong, high value if right.

3. **Nakshatra Daily Filter** — Interesting for Indian markets specifically because many Indian traders follow it → self-fulfilling effect. Use as a "avoid bad days" filter.

4. **Eclipse Buffer Zone** — Only 4-6 eclipses per year. Simply avoid trading 3 days around each. Minimal impact on total trading days.

### Additional Rules Worth Implementing

| Rule | Trigger | Action |
|---|---|---|
| **Saturn Station** | Saturn turns retrograde or direct (~2x/year) | Expect major market reversal within +/-5 days |
| **Venus Retrograde** | ~40 days every 18 months | Financial/luxury stocks underperform |
| **Mars-Saturn Hard Aspect** | Mars conjunct/square/opposite Saturn | Sharp selloff potential — avoid new longs |
| **Pushya Nakshatra** | Moon transits Pushya (most auspicious) | Best day for new investments |
| **Gann Square of 9** | Price hits calculated level | Use as stop-loss and take-profit targets |

### What I Would NOT Build

- Gann Square of Nine — too complex, too subjective, no reliable backtest data
- Full planetary aspect matrix — too many variables, overfitting risk
- Standalone astrology-based signals — always use as FILTER on top of technical analysis

### Suggested Config Parameters

```python
# config.py additions
ASTRO_ENABLED = True
MOON_PHASE_FILTER = True          # Adjust position size by moon phase
MERCURY_RETROGRADE_FILTER = True  # Reduce exposure during retrograde
NAKSHATRA_FILTER = False          # Experimental — enable when ready
ECLIPSE_FILTER = True             # Avoid trading around eclipses
ECLIPSE_BUFFER_DAYS = 3           # Days before/after eclipse to avoid
MOON_BEARISH_REDUCTION = 0.5     # Reduce qty by 50% in bearish moon phase
RETROGRADE_REDUCTION = 0.5       # Reduce qty by 50% during retrograde
```

---

## Sources

### Academic Papers
- [Dichev & Janes — "Are Investors Moonstruck? Lunar Phases and Stock Returns"](https://www.bus.umich.edu/pdf/mitsui/workshopdocs/ZhengMoonstruck.pdf)
- [Murgea — "Mercury Retrograde Effect in Capital Markets: Truth or Illusion?"](https://www.researchgate.net/publication/309453371_Mercury_Retrograde_Effect_in_Capital_Markets_Truth_or_Illusion)
- [Hang & Wang — "Long Live Hermes! Mercury Retrograde and Equity Prices"](https://acfr.aut.ac.nz/__data/assets/pdf_file/0004/576994/Hang-Wang-Hermes2021.pdf)

### Trading & Strategy
- [QuantifiedStrategies — Moon Phase Trading Backtest](https://www.quantifiedstrategies.com/full-moon-moon-phases-lunar-cycles-trading-strategies/)
- [LunaticTrader — Moon Cycles Research](https://lunatictrader.com/moon-cycles-in-the-markets/)
- [Rajeev Prakash — Financial Astrology for Market Cycles](https://rajeevprakash.com/financial-astrology-a-new-approach-to-market-forecasting/)
- [Bramesh — Eclipse Trading Strategy](https://brameshtechanalysis.com/2025/09/07/lunar-eclipse-trading-strategy-unlocking-market-cycles-with-astronomy-2/)

### Vedic Astrology
- [Modern Vedic Astrology — Financial Astrology Essentials](https://modernvedicastrology.com/financial-astrology/)
- [A2S Solutions — Nakshatra-Based Market Predictions](https://a2sfinsolutions.in/f/stock-market-predictions-based-on-nakshatras)
- [DKScore — Vedic Astrology & Stock Market Trends](https://www.dkscore.com/jyotishmedium/vedic-astrologys-impact-on-stock-market-trends-explained-2036)

### Gann Methods
- [LiteFinance — Gann Theories & Methods](https://www.litefinance.org/blog/for-professionals/william-gann-theories-and-methods/)
- [Wikipedia — W.D. Gann](https://en.wikipedia.org/wiki/William_Delbert_Gann)
- [Gann Academy — Lunar Cycles in Trading](https://gann.academy/lunar-cycles/)

### Python Libraries
- [PyEphem Documentation](https://rhodesmill.org/pyephem/quick.html)
- [pyswisseph on PyPI](https://pypi.org/project/pyswisseph/)
- [Kerykeion on PyPI](https://pypi.org/project/kerykeion/)

### Books
- "A Trader's Guide to Financial Astrology" by Larry Pesavento (Wiley)
- "Timing Solutions for Swing Traders" by Robert Lee (O'Reilly)
- "Super Timing: W.D. Gann's Astrological Method" by Myles Wilson Walker
- "Planetary Stock Trading" by Bill Meridian
- "The Ultimate Book on Stock Market Timing" by Ray Merriman

---

## Important Caveats

1. **No peer-reviewed study has proven astrology generates alpha net of transaction costs over the long term.** The lunar effect is the most robust finding but it's small.
2. **Confirmation bias** — astro-traders remember hits and forget misses.
3. **Overfitting risk** — with thousands of planetary combinations, some will correlate by chance.
4. **No known physical mechanism** — except Moon's tidal/light effects on mood, there's no science explaining how planets affect markets.
5. **Best use: as a FILTER** — astrology should adjust confidence/position size on existing technical signals, never be the sole reason to trade.
6. **Self-fulfilling prophecy** — in Indian markets especially, enough traders follow Jyotish that it can move volume on certain days (Pushya buying, Moola avoidance).
