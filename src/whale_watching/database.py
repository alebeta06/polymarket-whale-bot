"""
Database module for Whale Watching
Stores trader statistics and trades using SQLite
"""
import os
from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
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
    # Watermark of the newest trade timestamp (unix seconds) we have already
    # processed for this whale. Survives restarts so we don't re-emit old trades.
    last_seen_trade_ts = Column(Float, default=0.0)
    
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


class PaperTrade(Base):
    """Simulated copy trades while DRY_RUN=true.

    Mirrors what we *would* have placed on the CLOB so we can compute paper P&L
    without putting real capital at risk. Includes both the whale's original trade
    and our copy parameters so reconciliation can compare slippage, fill price, etc.
    """
    __tablename__ = 'paper_trades'

    id = Column(Integer, primary_key=True, autoincrement=True)
    whale_address = Column(String, ForeignKey('observed_traders.address'))
    market_id = Column(String)
    outcome = Column(String)
    side = Column(String)
    # What we would have placed (USD notional, shares, fill price assumption).
    copy_notional_usd = Column(Float)
    copy_shares = Column(Float)
    copy_price = Column(Float)
    # The whale's original trade for reference / slippage analysis.
    whale_size_shares = Column(Float)
    whale_price = Column(Float)
    whale_notional_usd = Column(Float)
    # Lifecycle: open → resolved_win | resolved_loss | invalidated
    status = Column(String, default="open")
    realized_pnl_usd = Column(Float, default=0.0)
    # Mark-to-market for still-open positions; refreshed by reconcile.py.
    unrealized_pnl_usd = Column(Float, default=0.0)
    # CLOB token id for the outcome we bought — useful for direct CLOB queries
    # and to disambiguate when a market has more than two outcomes.
    asset_id = Column(String, default="")
    timestamp = Column(DateTime, default=datetime.now)
    # When reconcile.py last updated this row.
    last_reconciled_at = Column(DateTime, default=None)
    # Whale trade hash for traceability / dedup if we ever re-poll the same trade.
    whale_tx_hash = Column(String, default="")


class WhaleDatabase:
    """Database manager for whale tracking"""

    def __init__(self, db_path: str = "data/whales.db"):
        """Initialize database connection"""
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self._migrate_schema()
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        log.info(f"✅ Database initialized at {db_path}")

    def _migrate_schema(self):
        """Apply idempotent ALTER TABLE statements for columns added after first release.

        SQLAlchemy's create_all only creates missing tables; it does not add new
        columns to an existing table. SQLite ignores ADD COLUMN if the column
        already exists only via try/except, so we swallow the duplicate-column
        OperationalError.
        """
        migrations = [
            "ALTER TABLE observed_traders ADD COLUMN last_seen_trade_ts REAL DEFAULT 0",
            "ALTER TABLE paper_trades ADD COLUMN unrealized_pnl_usd REAL DEFAULT 0",
            "ALTER TABLE paper_trades ADD COLUMN asset_id TEXT DEFAULT ''",
            "ALTER TABLE paper_trades ADD COLUMN last_reconciled_at DATETIME",
        ]
        with self.engine.begin() as conn:
            for stmt in migrations:
                try:
                    conn.execute(text(stmt))
                except OperationalError:
                    # Column already exists — fine.
                    pass
    
    def ensure_trader(self, address: str) -> ObservedTrader:
        """Insert the trader row if missing, without touching trade counters.

        Use this from seed/loader code so each restart does not phantom-increment
        total_trades. Use add_or_update_trader only when there is a real trade.
        """
        trader = self.session.query(ObservedTrader).filter_by(address=address).first()
        if trader is None:
            trader = ObservedTrader(
                address=address,
                total_volume=0.0,
                total_trades=0,
                largest_trade=0.0,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
            )
            self.session.add(trader)
            self.session.commit()
        return trader

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

    def get_last_seen_trade_ts(self, address: str) -> Optional[float]:
        """Return the persisted trade-timestamp watermark for a whale, or None if unset."""
        trader = self.session.query(ObservedTrader).filter_by(address=address).first()
        if trader is None:
            return None
        ts = trader.last_seen_trade_ts or 0.0
        return ts if ts > 0 else None

    def set_last_seen_trade_ts(self, address: str, ts: float) -> None:
        """Persist the trade-timestamp watermark, monotonically (never moves backward)."""
        trader = self.session.query(ObservedTrader).filter_by(address=address).first()
        if trader is None:
            return
        current = trader.last_seen_trade_ts or 0.0
        if ts > current:
            trader.last_seen_trade_ts = ts
            self.session.commit()

    def record_paper_trade(
        self,
        *,
        whale_address: str,
        market_id: str,
        outcome: str,
        side: str,
        copy_notional_usd: float,
        copy_shares: float,
        copy_price: float,
        whale_size_shares: float,
        whale_price: float,
        whale_notional_usd: float,
        whale_tx_hash: str = "",
        asset_id: str = "",
    ) -> PaperTrade:
        """Persist a simulated copy trade (DRY_RUN mode). Returns the row."""
        pt = PaperTrade(
            whale_address=whale_address,
            market_id=market_id,
            outcome=outcome,
            side=side,
            copy_notional_usd=copy_notional_usd,
            copy_shares=copy_shares,
            copy_price=copy_price,
            whale_size_shares=whale_size_shares,
            whale_price=whale_price,
            whale_notional_usd=whale_notional_usd,
            whale_tx_hash=whale_tx_hash,
            asset_id=asset_id,
            status="open",
            realized_pnl_usd=0.0,
            unrealized_pnl_usd=0.0,
            timestamp=datetime.now(),
        )
        self.session.add(pt)
        self.session.commit()
        return pt

    def get_open_paper_trades(self) -> List["PaperTrade"]:
        """All paper trades whose lifecycle has not yet terminated."""
        return (
            self.session.query(PaperTrade)
            .filter(PaperTrade.status == "open")
            .all()
        )

    def get_paper_committed_usd(self) -> float:
        """Sum of notional locked in still-open paper trades."""
        from sqlalchemy import func
        total = (
            self.session.query(func.coalesce(func.sum(PaperTrade.copy_notional_usd), 0.0))
            .filter(PaperTrade.status == "open")
            .scalar()
        )
        return float(total or 0.0)

    def has_paper_trade_for(self, whale_tx_hash: str) -> bool:
        """Idempotency guard: avoid recording the same whale trade twice if a poll cycle re-emits it."""
        if not whale_tx_hash:
            return False
        return (
            self.session.query(PaperTrade.id)
            .filter(PaperTrade.whale_tx_hash == whale_tx_hash)
            .first()
            is not None
        )

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
