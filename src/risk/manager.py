"""
Risk Manager - Manages trading risk and circuit breakers
"""
from datetime import datetime, timedelta
from typing import List
from src.utils import ArbitrageOpportunity, TradeResult, log
from src.config import get_settings


class RiskManager:
    """Manages risk and enforces trading limits"""
    
    def __init__(self):
        self.settings = get_settings()
        self.daily_pnl: float = 0.0
        self.daily_trades: List[TradeResult] = []
        self.last_reset: datetime = datetime.now()
        self.circuit_breaker_active: bool = False
    
    def can_execute(
        self,
        opportunity: ArbitrageOpportunity,
        current_balance: float
    ) -> tuple[bool, str]:
        """
        Check if trade can be executed based on risk limits
        
        Args:
            opportunity: The opportunity to evaluate
            current_balance: Current USDC balance
            
        Returns:
            Tuple of (can_execute: bool, reason: str)
        """
        # Check if circuit breaker is active
        if self.circuit_breaker_active:
            return False, "Circuit breaker is active - daily stop-loss hit"
        
        # Reset daily stats if new day
        self._reset_if_new_day()
        
        # Check max position size
        max_position = current_balance * self.settings.max_position_size_percent
        if opportunity.required_capital > max_position:
            return False, (
                f"Position size ${opportunity.required_capital:.2f} exceeds "
                f"max allowed ${max_position:.2f} "
                f"({self.settings.max_position_size_percent*100}% of balance)"
            )
        
        # Check sufficient balance
        if opportunity.required_capital > current_balance:
            return False, (
                f"Insufficient balance: need ${opportunity.required_capital:.2f}, "
                f"have ${current_balance:.2f}"
            )
        
        # Check daily stop-loss
        if not self._check_daily_stop_loss(current_balance):
            return False, f"Daily stop-loss limit reached: {self.daily_pnl:.2f}"
        
        # Check minimum profit
        if not opportunity.is_profitable(
            self.settings.min_profit_percent,
            self.settings.polymarket_fee_percent
        ):
            return False, (
                f"Profit {opportunity.roi*100:.2f}% below minimum "
                f"{self.settings.min_profit_percent*100}%"
            )
        
        return True, "All risk checks passed"
    
    def record_trade(self, result: TradeResult):
        """
        Record trade result and update daily P&L
        
        Args:
            result: The trade result
        """
        self.daily_trades.append(result)
        
        if result.success and result.actual_profit:
            self.daily_pnl += result.actual_profit
            log.info(f"Daily P&L updated: ${self.daily_pnl:.2f}")
        
        # Check if circuit breaker should activate
        self._check_circuit_breaker()
    
    def _check_daily_stop_loss(self, current_balance: float) -> bool:
        """
        Check if daily stop-loss limit has been hit
        
        Args:
            current_balance: Current balance
            
        Returns:
            True if within limits, False if stop-loss hit
        """
        stop_loss_threshold = current_balance * self.settings.daily_stop_loss_percent
        
        if self.daily_pnl < -stop_loss_threshold:
            log.error(
                f"⛔ DAILY STOP-LOSS HIT: ${self.daily_pnl:.2f} "
                f"exceeds ${-stop_loss_threshold:.2f}"
            )
            return False
        
        return True
    
    def _check_circuit_breaker(self):
        """Activate circuit breaker if daily loss exceeds limit"""
        # This will be checked on next can_execute() call
        # For now, just log
        if self.daily_pnl < 0:
            loss_percent = abs(self.daily_pnl) / 15.61  # Use starting balance
            if loss_percent >= self.settings.daily_stop_loss_percent:
                self.circuit_breaker_active = True
                log.error(
                    f"🚨 CIRCUIT BREAKER ACTIVATED! "
                    f"Daily loss: ${self.daily_pnl:.2f} "
                    f"({loss_percent*100:.1f}%)"
                )
    
    def _reset_if_new_day(self):
        """Reset daily counters if it's a new day"""
        now = datetime.now()
        if now.date() > self.last_reset.date():
            log.info(
                f"New day - resetting counters. "
                f"Yesterday's P&L: ${self.daily_pnl:.2f}, "
                f"Trades: {len(self.daily_trades)}"
            )
            self.daily_pnl = 0.0
            self.daily_trades = []
            self.circuit_breaker_active = False
            self.last_reset = now
    
    def get_daily_stats(self) -> dict:
        """Get current daily statistics"""
        return {
            "date": self.last_reset.date().isoformat(),
            "pnl": self.daily_pnl,
            "trades_count": len(self.daily_trades),
            "successful_trades": sum(1 for t in self.daily_trades if t.success),
            "circuit_breaker_active": self.circuit_breaker_active
        }
    
    def reset_circuit_breaker(self):
        """Manually reset circuit breaker (use with caution!)"""
        log.warning("⚠️  Circuit breaker manually reset")
        self.circuit_breaker_active = False
