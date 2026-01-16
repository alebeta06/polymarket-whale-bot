"""
Database module for Whale Watching
Stores trader statistics and trades using SQLite
"""
from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import List, Optional
from loguru import logger as log

Base = declarative_base()


class ObservedTrader(Base):
    """Track statistics for observed traders"""
    __tablename__ = 'observed_traders'
    
    address = Column(String, primary_key=True)
    total_volume = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_profit = Column(Float, default=0.0)
    largest_trade = Column(Float, default=0.0)
    whale_score = Column(Float, default=0.0)
    is_following = Column(Boolean, default=False)
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now)
    
    # Relationship to trades
    trades = relationship("ObservedTrade", back_populates="trader")
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate"""
        total = self.winning_trades + self.losing_trades
        if total == 0:
            return 0.0
        return self.winning_trades / total
    
    @property
    def avg_trade_size(self) -> float:
        """Calculate average trade size"""
        if self.total_trades == 0:
            return 0.0
        return self.total_volume / self.total_trades


class ObservedTrade(Base):
    """Individual trades from observed traders"""
    __tablename__ = 'observed_trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trader_address = Column(String, ForeignKey('observed_traders.address'))
    market_id = Column(String)
    outcome = Column(String)  # YES or NO
    side = Column(String)  # BUY or SELL
    size = Column(Float)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)
    
    # Relationship
    trader = relationship("ObservedTrader", back_populates="trades")


class WhaleDatabase:
    """Database manager for whale tracking"""
    
    def __init__(self, db_path: str = "data/whales.db"):
        """Initialize database connection"""
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        log.info(f"✅ Database initialized at {db_path}")
    
    def add_or_update_trader(self, address: str, trade_size: float, is_win: Optional[bool] = None) -> ObservedTrader:
        """
        Add new trader or update existing one
        
        Args:
            address: Trader wallet address
            trade_size: Size of the trade in USDC
            is_win: Whether the trade was profitable (None if still open)
        """
        trader = self.session.query(ObservedTrader).filter_by(address=address).first()
        
        if trader is None:
            # New trader
            trader = ObservedTrader(
                address=address,
                total_volume=trade_size,
                total_trades=1,
                largest_trade=trade_size,
                first_seen=datetime.now(),
                last_seen=datetime.now()
            )
            self.session.add(trader)
            log.info(f"📝 New trader discovered: {address[:10]}... (${trade_size:,.2f})")
        else:
            # Update existing
            trader.total_volume += trade_size
            trader.total_trades += 1
            trader.largest_trade = max(trader.largest_trade, trade_size)
            trader.last_seen = datetime.now()
            
            if is_win is True:
                trader.winning_trades += 1
            elif is_win is False:
                trader.losing_trades += 1
        
        self.session.commit()
        return trader
    
    def record_trade(self, address: str, market_id: str, outcome: str, 
                    side: str, size: float, price: float) -> ObservedTrade:
        """Record a trade from a trader"""
        trade = ObservedTrade(
            trader_address=address,
            market_id=market_id,
            outcome=outcome,
            side=side,
            size=size,
            price=price,
            timestamp=datetime.now()
        )
        self.session.add(trade)
        
        # Update trader stats
        self.add_or_update_trader(address, size)
        
        self.session.commit()
        return trade
    
    def get_top_traders(self, limit: int = 50, min_trades: int = 10) -> List[ObservedTrader]:
        """
        Get top traders by volume
        
        Args:
            limit: Number of traders to return
            min_trades: Minimum number of trades required
        """
        traders = self.session.query(ObservedTrader)\
            .filter(ObservedTrader.total_trades >= min_trades)\
            .order_by(ObservedTrader.total_volume.desc())\
            .limit(limit)\
            .all()
        
        return traders
    
    def set_following(self, address: str, following: bool = True):
        """Mark a trader as following/not following"""
        trader = self.session.query(ObservedTrader).filter_by(address=address).first()
        if trader:
            trader.is_following = following
            self.session.commit()
            log.info(f"{'✅ Following' if following else '❌ Unfollowing'}: {address[:10]}...")
    
    def get_following_list(self) -> List[ObservedTrader]:
        """Get all traders we're currently following"""
        return self.session.query(ObservedTrader)\
            .filter_by(is_following=True)\
            .all()
    
    def get_trader_stats(self, address: str) -> Optional[ObservedTrader]:
        """Get stats for a specific trader"""
        return self.session.query(ObservedTrader).filter_by(address=address).first()
    
    def close(self):
        """Close database connection"""
        self.session.close()


# Example usage and testing
if __name__ == "__main__":
    db = WhaleDatabase("data/whales.db")
    
    # Simulate adding some traders
    db.add_or_update_trader("0x1234567890abcdef", 5000.0)
    db.add_or_update_trader("0xabcdef1234567890", 10000.0)
    db.add_or_update_trader("0x1234567890abcdef", 3000.0, is_win=True)
    
    # Get top traders
    top = db.get_top_traders(limit=10, min_trades=1)
    print(f"\n📊 Top Traders:")
    for trader in top:
        print(f"  {trader.address[:10]}... - ${trader.total_volume:,.2f} ({trader.total_trades} trades)")
    
    db.close()
