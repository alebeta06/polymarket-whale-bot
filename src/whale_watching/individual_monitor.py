"""
Individual Whale Monitor - Tracks trades from specific whale addresses
Uses Polymarket CLOB API to poll their recent activity
"""
import asyncio
from typing import List, Dict
from loguru import logger as log
from datetime import datetime, timedelta
import time

from .database import WhaleDatabase
from .seed_whales import SEED_WHALES
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds


class IndividualWhaleMonitor:
    """Monitor specific whale addresses via CLOB API polling"""
    
    def __init__(self, db: WhaleDatabase, poll_interval: int = 60):
        """
        Initialize the monitor
        
        Args:
            db: Database instance
            poll_interval: Seconds between checks (default: 60)
        """
        self.db = db
        self.poll_interval = poll_interval
        self.whale_addresses: List[str] = []
        self.client: ClobClient = None
        self.running = False
        self.last_trade_timestamps: Dict[str, datetime] = {}
        
        log.info(f"🔍 Individual Whale Monitor initialized (poll every {poll_interval}s)")
    
    def initialize_client(self):
        """Initialize CLOB client (read-only, no auth needed for public data)"""
        try:
            # Create client without authentication for public read operations
            self.client = ClobClient("https://clob.polymarket.com")
            log.info("✅ CLOB client initialized")
        except Exception as e:
            log.error(f"Failed to initialize CLOB client: {e}")
    
    def load_whales(self):
        """Load whale addresses from seed list and database"""
        # Load from seed list
        for address, nickname, reason in SEED_WHALES:
            address_lower = address.lower()
            if address_lower not in self.whale_addresses:
                self.whale_addresses.append(address_lower)
                
                # Add to database
                self.db.add_or_update_trader(address_lower, 0.0)
                self.db.set_following(address_lower, True)
                
                log.info(f"📝 Loaded: {nickname} ({address_lower[:10]}...)")
        
        log.info(f"✅ Loaded {len(self.whale_addresses)} whales to monitor")
    
    async def check_whale_trades(self, address: str):
        """
        Check recent trades for a specific whale
        
        Args:
            address: Whale wallet address
        """
        try:
            # Get last check timestamp
            last_check = self.last_trade_timestamps.get(address, 
                                                        datetime.now() - timedelta(hours=24))
            
            # Note: This is simplified - actual implementation would use
            # the CLOB API's order history endpoint
            # For now, we'll just log that we're checking
            
            # In real implementation:
            # trades = await self.client.get_user_trades(address, since=last_check)
            # for trade in trades:
            #     self.process_trade(address, trade)
            
            # Update last check time
            self.last_trade_timestamps[address] = datetime.now()
            
        except Exception as e:
            log.error(f"Error checking trades for {address[:10]}...: {e}")
    
    def process_trade(self, whale_address: str, trade: Dict):
        """
        Process a whale trade (to be called when we detect a trade)
        
        Args:
            whale_address: Address of the whale
            trade: Trade data
        """
        try:
            market_id = trade.get('market') or trade.get('asset_id')
            outcome = trade.get('outcome', 'UNKNOWN')
            side = trade.get('side', 'BUY')
            size = float(trade.get('size', 0))
            price = float(trade.get('price', 0))
            
            value = size * price
            
            if value > 500:  # Only track significant trades
                log.info(f"🐋 Whale trade: {whale_address[:10]}... ${value:,.2f} on {market_id[:10]}...")
                
                # Record in database
                self.db.record_trade(
                    address=whale_address,
                    market_id=market_id,
                    outcome=outcome,
                    side=side,
                    size=value,
                    price=price
                )
                
                # TODO: Trigger copy trading logic here
                # copy_trading.execute_copy(whale_address, trade)
        
        except Exception as e:
            log.error(f"Error processing trade: {e}")
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        self.running = True
        
        log.info("🚀 Starting whale monitoring loop...")
        
        while self.running:
            try:
                # Check all whales
                for address in self.whale_addresses:
                    await self.check_whale_trades(address)
                    await asyncio.sleep(1)  # Rate limit between whales
                
                # Wait for next poll cycle
                log.info(f"⏳ Checked {len(self.whale_addresses)} whales, waiting {self.poll_interval}s...")
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                log.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(10)
    
    async def start(self):
        """Start the monitor"""
        log.info("=" * 60)
        log.info("🐋 INDIVIDUAL WHALE MONITOR STARTING")
        log.info("=" * 60)
        
        # Initialize
        self.initialize_client()
        self.load_whales()
        
        log.info(f"Monitoring {len(self.whale_addresses)} whales")
        log.info(f"Poll interval: {self.poll_interval}s")
        log.info("=" * 60)
        
        # Start monitoring
        await self.monitor_loop()
    
    def stop(self):
        """Stop the monitor"""
        self.running = False
        log.info("🛑 Monitor stopped")


# Simple test/demo
async def main():
    db = WhaleDatabase("data/whales.db")
    monitor = IndividualWhaleMonitor(db, poll_interval=30)
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        monitor.stop()
        db.close()
        log.info("👋 Shutdown")


if __name__ == "__main__":
    asyncio.run(main())
