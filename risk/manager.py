"""
Risk Manager — the layer between you and blowing up your account.
Do not modify without understanding what each rule does.

Circuit Breakers:
    1. Daily loss limit: -2% → stop all new trades for the day
    2. Daily profit target: +3% → stop trading, book profits
    3. Max drawdown: -5% from peak → stop all trading, review system
    4. Consecutive losses: 3 in a row → stop, re-evaluate
    5. Pre-close cutoff: no new positions after 3:00 PM
    6. Friday rule: no new positions after Friday 2:00 PM
    7. Max loss per trade: don't risk more than X per single trade
"""
from datetime import datetime, time
import config


class RiskManager:
    def __init__(self, paper_mode=False):
        self.max_daily_loss_pct = config.MAX_DAILY_LOSS_PCT
        self.max_drawdown_pct = config.MAX_DRAWDOWN_PCT
        self.max_position_pct = config.MAX_POSITION_PCT
        self.max_total_positions = config.MAX_TOTAL_POSITIONS_PAPER if paper_mode else config.MAX_TOTAL_POSITIONS
        self.stop_loss_atr_mult = config.STOP_LOSS_ATR_MULT
        self.paper_mode = paper_mode

        # State
        self.daily_pnl = 0.0
        self.peak_portfolio_value = config.INITIAL_CAPITAL
        self.trades_today = 0
        self.consecutive_losses = 0

    def can_open_position(
        self,
        portfolio_value: float,
        current_positions: list,
        proposed_position_value: float,
        check_time: datetime | None = None,
        intraday: bool = False,
    ) -> tuple[bool, str]:
        """
        Returns (can_trade, reason).

        intraday=True  → SHORT trade: stricter 2:30 PM cutoff, must close same day.
        intraday=False → LONG trade: positional, allowed until 3:00 PM (can hold overnight).
        """
        now = check_time or datetime.now()

        # Check 1: Time cutoff
        # SHORT (intraday): no new positions after 2:30 PM — need time for square-off
        # LONG (positional): no new positions after 3:00 PM — last 1H candle
        if intraday:
            cutoff = time(config.NO_NEW_POSITIONS_AFTER_HOUR, config.NO_NEW_POSITIONS_AFTER_MINUTE)
        else:
            cutoff = time(15, 0)
        if now.time() >= cutoff:
            return False, f"Pre-close cutoff ({'intraday' if intraday else 'positional'}): no new positions after {cutoff}"

        # Check 2: Friday rule
        # SHORT: no new shorts on Friday after 2 PM (can't hold over weekend)
        # LONG:  no new longs on Friday after 3 PM (market closes at 3:30)
        friday_cutoff = time(14, 0) if intraday else time(15, 0)
        if now.weekday() == 4 and now.time() >= friday_cutoff:
            return False, f"Friday rule: no new {'intraday' if intraday else 'positional'} positions after {friday_cutoff}"

        # Check 3: Daily loss limit
        if portfolio_value > 0:
            daily_loss = self.daily_pnl / portfolio_value
            if daily_loss <= -self.max_daily_loss_pct:
                return False, f"Daily loss limit hit: {daily_loss:.2%}"

        # Check 4: Daily profit target — book profits, stop trading
        if portfolio_value > 0:
            daily_gain = self.daily_pnl / portfolio_value
            if daily_gain >= config.DAILY_PROFIT_TARGET_PCT:
                return False, f"Daily profit target hit: {daily_gain:.2%} — booking profits"

        # Check 5: Overall drawdown
        if self.peak_portfolio_value > 0:
            drawdown = (self.peak_portfolio_value - portfolio_value) / self.peak_portfolio_value
            if drawdown >= self.max_drawdown_pct:
                return False, f"Max drawdown hit: {drawdown:.2%}"

        # Check 6: Position count
        if len(current_positions) >= self.max_total_positions:
            return False, f"Max positions reached: {len(current_positions)}"

        # Check 7: Position size
        if portfolio_value > 0 and proposed_position_value / portfolio_value > self.max_position_pct:
            return False, f"Position too large: {proposed_position_value / portfolio_value:.2%}"

        # Check 8: Consecutive losses circuit breaker
        if self.consecutive_losses >= config.CONSECUTIVE_LOSS_LIMIT:
            return False, f"Circuit breaker: {self.consecutive_losses} consecutive losses"

        return True, "OK to trade"

    def calculate_position_size(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> int:
        """
        How many shares to buy. Depends on QUANTITY_MODE in config:
          "auto"    — risk-based: (1% of capital) / (risk per share)
          "fixed"   — always buy FIXED_QUANTITY shares
          "capital" — invest CAPITAL_PER_TRADE amount: qty = amount / price
        """
        mode = config.QUANTITY_MODE

        if mode == "fixed":
            return config.FIXED_QUANTITY

        if mode == "capital":
            if entry_price <= 0:
                return 0
            qty = int(config.CAPITAL_PER_TRADE / entry_price)
            return qty if qty > 0 else 0

        # Default: "auto" — risk-based calculation
        risk_amount = portfolio_value * config.RISK_PER_TRADE_PCT
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share == 0:
            return 0

        # Cap risk_amount by MAX_LOSS_PER_TRADE
        max_loss = config.MAX_LOSS_PER_TRADE
        if risk_amount > max_loss:
            risk_amount = max_loss

        quantity = int(risk_amount / risk_per_share)
        return quantity if quantity > 0 else 0

    def calculate_stop_loss(self, entry_price: float, atr: float) -> float:
        """Stop loss = Entry - (ATR x multiplier)."""
        return entry_price - (atr * self.stop_loss_atr_mult)

    def record_trade(self, pnl: float):
        """Call after every trade to update risk state."""
        self.daily_pnl += pnl
        self.trades_today += 1
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def update_peak(self, portfolio_value: float):
        """Call after each trade to track high-water mark."""
        if portfolio_value > self.peak_portfolio_value:
            self.peak_portfolio_value = portfolio_value

    def reset_daily(self, portfolio_value: float | None = None):
        """Call at the start of each trading day."""
        self.daily_pnl = 0.0
        self.trades_today = 0
        if portfolio_value is not None:
            self.update_peak(portfolio_value)
