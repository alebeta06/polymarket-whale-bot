"""
Pydantic models for Whale Watching
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WhaleStats(BaseModel):
    """Statistics for a whale trader"""
    address: str
    total_roi: float = 0.0
    win_rate: float = 0.0
    total_volume: float = 0.0
    total_trades: int = 0
    last_30d_roi: float = 0.0
    whale_score: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.now)
    is_following: bool = False


class WhaleTrade(BaseModel):
    """Individual trade by a whale"""
    id: Optional[int] = None
    whale_address: str
    market_id: str
    outcome: str  # YES or NO
    size: float
    price: float
    timestamp: datetime = Field(default_factory=datetime.now)


class LeaderboardUser(BaseModel):
    """User from Polymarket leaderboard"""
    address: str
    pnl: float  # Profit and Loss
    volume: float
    trades: int
    win_rate: Optional[float] = None
