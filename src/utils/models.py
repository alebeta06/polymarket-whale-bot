"""
Data models for Polymarket markets and arbitrage opportunities.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ArbitrageType(Enum):
    """Type of arbitrage opportunity"""
    INTRA_MARKET = "intra_market"  # YES + NO != 1 in same market
    INTER_MARKET = "inter_market"  # Price inconsistency between related markets


class OrderSide(Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Outcome:
    """Market outcome (YES or NO)"""
    name: str  # "YES" or "NO"
    price: float  # Current price (0-1)
    token_id: str  # Outcome token ID
    liquidity: float  # Available liquidity


@dataclass
class Market:
    """Polymarket market"""
    id: str
    question: str
    category: str
    volume: float
    liquidity: float
    yes_outcome: Outcome
    no_outcome: Outcome
    active: bool = True
    end_date: Optional[datetime] = None
    
    @property
    def total_probability(self) -> float:
        """Sum of YES + NO prices"""
        return self.yes_outcome.price + self.no_outcome.price
    
    @property
    def has_intra_arbitrage(self) -> bool:
        """Check if sum of probabilities is < 1"""
        return self.total_probability < 0.98  # Account for 2% fees


@dataclass
class ArbitrageOpportunity:
    """Arbitrage opportunity"""
    id: str
    market_id: str
    market_question: str
    type: ArbitrageType
    expected_profit: float  # In USDC
    roi: float  # Return on investment (percentage)
    required_capital: float  # In USDC
    detected_at: datetime
    
    # Intra-market specific
    yes_price: Optional[float] = None
    no_price: Optional[float] = None
    total_probability: Optional[float] = None
    
    # Inter-market specific
    related_market_ids: Optional[List[str]] = None
    
    def is_profitable(self, min_profit_percent: float, fees: float = 0.02) -> bool:
        """Check if opportunity meets minimum profit threshold"""
        net_profit = self.expected_profit - (self.required_capital * fees * 2)  # 2 trades
        net_roi = net_profit / self.required_capital if self.required_capital > 0 else 0
        return net_roi >= min_profit_percent


@dataclass
class TradeOrder:
    """Order to be placed"""
    market_id: str
    token_id: str
    side: OrderSide
    size: float  # In USDC
    price: float  # Limit price (0-1)
    order_type: str = "LIMIT"  # LIMIT or MARKET


@dataclass
class TradeResult:
    """Result of a trade execution"""
    opportunity_id: str
    success: bool
    executed_at: datetime
    orders: List[TradeOrder]
    actual_profit: Optional[float] = None
    error_message: Optional[str] = None
    fills: Optional[List[dict]] = None


@dataclass
class DailyMetrics:
    """Daily trading metrics"""
    date: datetime
    opportunities_detected: int
    trades_executed: int
    trades_successful: int
    total_profit: float
    total_volume: float
    roi: float
    largest_profit: float
    average_slippage: float
