"""
Risk Manager — the layer between you and blowing up your account.
Do not modify without understanding what each rule does.
"""
import config


class RiskManager:
    def __init__(self):
        self.max_daily_loss_pct = config.MAX_DAILY_LOSS_PCT
        self.max_drawdown_pct = config.MAX_DRAWDOWN_PCT
        self.max_position_pct = config.MAX_POSITION_PCT
        self.max_total_positions = config.MAX_TOTAL_POSITIONS
        self.stop_loss_atr_mult = config.STOP_LOSS_ATR_MULT

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
    ) -> tuple[bool, str]:
        """Returns (can_trade, reason)."""
        # Check 1: Daily loss limit
        if portfolio_value > 0:
            daily_loss = self.daily_pnl / portfolio_value
            if daily_loss <= -self.max_daily_loss_pct:
                return False, f"Daily loss limit hit: {daily_loss:.2%}"

        # Check 2: Overall drawdown
        if self.peak_portfolio_value > 0:
            drawdown = (self.peak_portfolio_value - portfolio_value) / self.peak_portfolio_value
            if drawdown >= self.max_drawdown_pct:
                return False, f"Max drawdown hit: {drawdown:.2%}"

        # Check 3: Position count
        if len(current_positions) >= self.max_total_positions:
            return False, f"Max positions reached: {len(current_positions)}"

        # Check 4: Position size
        if portfolio_value > 0 and proposed_position_value / portfolio_value > self.max_position_pct:
            return False, f"Position too large: {proposed_position_value / portfolio_value:.2%}"

        # Check 5: Consecutive losses circuit breaker
        if self.consecutive_losses >= config.CONSECUTIVE_LOSS_LIMIT:
            return False, f"Circuit breaker: {self.consecutive_losses} consecutive losses"

        return True, "OK to trade"

    def calculate_position_size(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> int:
        """How many shares to buy based on risk per trade."""
        risk_amount = portfolio_value * config.RISK_PER_TRADE_PCT
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share == 0:
            return 0

        quantity = int(risk_amount / risk_per_share)
        return max(quantity, 1)

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

    def reset_daily(self):
        """Call at the start of each trading day."""
        self.daily_pnl = 0.0
        self.trades_today = 0
