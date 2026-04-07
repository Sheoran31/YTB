# DECISIONS.md — Autonomous Bot Hardening

## Scope & Approach

**Goal:** Harden 5 fragile areas (Telegram, yfinance, state management, signals, Docker) with comprehensive tests and fixes.

**Execution Strategy:**
1. Write pytest tests for each area covering identified edge cases
2. Run tests (expected to fail initially on unfixed code)
3. Fix code to make tests pass
4. Commit after each area reaches 100% pass rate
5. Use parallel agents for independent areas (test writing, code fixing)

---

## Design Decisions (Justified Below)

### 1. TELEGRAM ALERTS Hardening

**Decision: Implement exponential backoff retry + credential validation**

- **Assumption:** Telegram API 429 (rate limit) is transient; retrying after 2^n seconds helps
- **Assumption:** Missing bot token is a startup error; should fail loud, not silent
- **Why:** Trades have executed while notifications lost (user discovers at EOD) — unacceptable
- **Changes:**
  - Validate `bot_token` and `chat_id` non-empty at init, raise if missing
  - Wrap `send_alert()` in retry loop: max 3 attempts, backoff 1s, 2s, 4s
  - Handle 429 → sleep + retry; 401 → log and disable; timeout → increase to 30s
  - Escape HTML special chars in user data (price, symbol, RSI)
  - Add `.get()` calls for missing fields in screener results, default to "N/A"
  - Unit tests: 7 test cases (credentials, rate limit, timeout, HTML escape, missing fields, mode timeout, mode mismatch)

### 2. YFINANCE DATA FETCHING Hardening

**Decision: Implement request queuing with rate-limit awareness + data validation**

- **Assumption:** Yfinance free tier allows ~300 calls/hour; we need ~600/hour → implement 200ms delay between calls
- **Assumption:** Incomplete last candle at market open (9:15 AM) → validate min 50 rows for SMA_SLOW
- **Assumption:** NSE half-day sessions (4-hour close) → fetch full previous day's data if today is incomplete
- **Why:** False signals from incomplete/corrupted data lead to bad trades
- **Changes:**
  - Add `time.sleep(0.2)` between yfinance calls in `fetch_multiple_stocks()`
  - Validate returned data: min 50 rows, no all-NaN columns
  - If market hours filter returns < 50 rows, fetch previous day too
  - Implement 3-attempt retry with exponential backoff for 429, 403, timeout
  - Add logging for each failed fetch (not just generic error)
  - Unit tests: 8 test cases (rate limit, incomplete candle, half-day session, partial failure, empty response, timezone error, period mismatch, timeout)

### 3. CSV STATE MANAGEMENT Hardening

**Decision: Implement atomic writes + state validation + backup**

- **Assumption:** Power loss during JSON write can corrupt state → use temp file + atomic rename
- **Assumption:** State format can change (e.g., add new fields) → validate all keys exist, provide defaults
- **Assumption:** Position keys (symbol) can become orphaned → validate ticker still in watchlist
- **Why:** State corruption loses all position data; no way to recover (no backup)
- **Changes:**
  - Write to `portfolio_state.json.tmp`, then `os.rename()` → atomic
  - Keep backup: `portfolio_state.json.bak` (previous state)
  - Validate on load: position quantity > 0, entry_price > 0, all required keys present
  - Remove orphaned positions (ticker not in yfinance data)
  - Add to CSV: position ID, save timestamp, bot version
  - Unit tests: 10 test cases (corrupted JSON, wrong types, missing keys, race conditions, atomic failure, PnL consistency, empty fields, delisted ticker, capital 0, negative quantity)

### 4. SIGNAL LOGIC & INDICATORS Hardening

**Decision: Explicit NaN/Inf/edge-case validation in every indicator**

- **Assumption:** No indicator output should be NaN, Inf, or < 0 (invalid)
- **Assumption:** Data length varies (market open vs EOD) → validate before calculation
- **Assumption:** Flat market (0 gains, 0 losses) is valid → RSI should be 50, not Inf
- **Why:** Silent NaN/Inf propagates through strategy, triggers false HOLD signals
- **Changes:**
  - RSI: cap at 100 if all gains; cap at 0 if all losses; return 50 if flat
  - ADX: smooth twice (correct formula); cap to [0, 100]; return 0 if flat
  - EMA/SMA: return NaN explicitly if not enough data; check before crossover
  - Volume ratio: cap at [0.1, 100] (clamp outliers); return 1.0 if 0 volume
  - MACD: return NaN if not 26 periods of data
  - Add assertion: all signal outputs (BUY/SELL/HOLD) are valid strings, no Inf/NaN in intermediate values
  - Unit tests: 10 test cases (RSI infinity, flat ADX, NaN data, insufficient rows, all-NaN, volume outliers, mode switch, boundary rows, gap handling, MACD startup)

### 5. DOCKER STARTUP & NSE HOLIDAYS Hardening

**Decision: Add startup validation + timezone enforcement + health check**

- **Assumption:** System timezone doesn't guarantee Python sees it → explicit validation in code
- **Assumption:** Bot runs forever (day trading mode) → needs health check for container orchestration
- **Assumption:** NSE API failure is temporary → retry up to 5 times before falling back to cache
- **Why:** Bot trading at wrong times (UTC vs IST) is silent; container silent crashes go undetected
- **Changes:**
  - Validate `datetime.now()` is in IST; if UTC, warn and override
  - Add health file: `logs/bot_health.json` updated every scan cycle
  - Docker HEALTHCHECK: check if health file updated in last 30 min
  - NSE holiday fetch: retry 5 times with exponential backoff (1s, 2s, 4s, 8s, 16s)
  - Startup validation: capital > 1000 INR, watchlist not empty, required configs set
  - Validate corrupted state: capital=0 → reset to INITIAL_CAPITAL
  - Unit tests: 10 test cases (API timeout, format change, stale cache, UTC timezone, corrupted capital, empty watchlist, missing dependencies, Telegram disabled, market open check, silent crash detection)

---

## Test Framework & Mocking Strategy

**Framework:** pytest (already in `tests/` directory)

**Mocking:**
- `unittest.mock.patch` for external APIs (yfinance.download, requests.post, NSE API)
- Hardcoded test data for valid/invalid scenarios
- Temporary files for state JSON tests (use `tempfile.NamedTemporaryFile`)

**Assertion Style:**
```python
assert signal == "BUY", f"Expected BUY, got {signal}"
pytest.raises(ValueError, func, *args)
```

**Test Organization:**
- `tests/test_telegram_hardening.py` — 7 tests
- `tests/test_yfinance_hardening.py` — 8 tests
- `tests/test_state_management_hardening.py` — 10 tests
- `tests/test_signal_logic_hardening.py` — 10 tests
- `tests/test_docker_startup_hardening.py` — 10 tests

---

## Risk & Mitigation

| Risk | Mitigation |
|------|-----------|
| Changing core trading logic breaks existing strategy | Tests ONLY validate edge cases, not strategy behavior. No changes to momentum thresholds. |
| Backoff delays slow down trading | Delays are 200ms between yfinance calls; 15-min scan interval can absorb this. |
| State backup takes disk space | Keep only 1 backup (portfolio_state.json.bak); archive old logs weekly. |
| Health check adds overhead | Health file write is 1KB JSON, negligible; read from Dockerfile is async. |
| Timezone validation at startup adds latency | < 10ms; only runs once at bot startup. |

---

## Success Criteria

✅ **All 45 tests pass** (7 + 8 + 10 + 10 + 10)
✅ **Code coverage:** 80%+ for modified modules
✅ **No changes to strategy (momentum, RSI thresholds, BUY/SELL rules)**
✅ **Backward compatible:** Old state files load without errors
✅ **Performance:** Scan cycle time unchanged (< 5 seconds)
✅ **Commits:** One commit per hardened area (5 commits total)

---

## Execution Plan

**Phase 1:** Write all tests (parallel)
- Agent 1: Telegram tests + yfinance tests
- Agent 2: State management tests + signal tests
- Agent 3: Docker startup tests

**Phase 2:** Fix code area-by-area until tests pass (sequential, one area per commit)
1. Telegram Alerts (run tests → fix → rerun until pass → commit)
2. yfinance Fetching (run tests → fix → rerun until pass → commit)
3. State Management (run tests → fix → rerun until pass → commit)
4. Signal Logic (run tests → fix → rerun until pass → commit)
5. Docker Startup (run tests → fix → rerun until pass → commit)

---

## Assumptions Made

1. **Python 3.12 available** → tests run with current venv
2. **yfinance will accept mock responses** → use `unittest.mock.patch("yfinance.download")`
3. **Dhan API not mocked** → tests only cover paper trading + state, not live Dhan trades
4. **Market hours are fixed** → 9:15-15:30 IST; no holiday changes during test run
5. **Existing strategy is correct** → tests validate edge cases, not signal rules
6. **No external system changes** → tests assume current NSE API format (may change)

---

## Success Definition

**Fragility → Robustness:**

| Before | After |
|--------|-------|
| Telegram fails silently, no retry | 3-attempt retry with exponential backoff |
| yfinance rate limit crashes | Detect 429, sleep, retry |
| Corrupted state = lost positions | Atomic write + backup + validation |
| RSI = Inf on flat market | Explicit 50.0 return |
| Bot trades at wrong time if UTC | Timezone validation at startup |
| Container dies, Kubernetes doesn't know | Health check every scan cycle |
| **Zero tests** for critical modules | **45 new tests**, 80%+ coverage |

---

**Timestamp:** 2026-04-06 12:50 PM IST  
**Bot Status:** Running (PID 13287)  
**Target Completion:** All 5 areas hardened, all 45 tests passing, 5 commits
