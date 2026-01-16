"""
Trade Monitor - WebSocket listener for Polymarket CLOB
Observes all trades in real-time and records large ones to build whale database
"""
import asyncio
import websockets
import json
from typing import Optional
from loguru import logger as log
from datetime import datetime

from .database import WhaleDatabase
from .seed_whales import SEED_WHALES


class TradeMonitor:
    """Monitor trades in real-time via WebSocket"""
    
    def __init__(self, db: WhaleDatabase, min_trade_size: float = 1000.0):
        """
        Initialize trade monitor
        
        Args:
            db: WhaleDatabase instance
            min_trade_size: Minimum trade size in USDC to record (default $1,000)
        """
        self.db = db
        self.min_trade_size = min_trade_size
        self.ws_url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        
        log.info(f"🔍 Trade Monitor initialized (min size: ${min_trade_size:,.2f})")
    
    async def connect(self):
        """Connect to Polymarket WebSocket"""
        try:
            self.ws = await websockets.connect(self.ws_url)
            log.info("✅ Connected to Polymarket WebSocket")
            return True
        except Exception as e:
            log.error(f"Failed to connect to WebSocket: {e}")
            return False
    
    async def subscribe_to_trades(self):
        """Subscribe to trade events"""
        if not self.ws:
            log.error("WebSocket not connected")
            return
        
        # Subscribe to all market trades
        subscribe_msg = {
            "type": "subscribe",
            "channel": "trades",
            "markets": ["*"]  # All markets
        }
        
        try:
            await self.ws.send(json.dumps(subscribe_msg))
            log.info("📡 Subscribed to all market trades")
        except Exception as e:
            log.error(f"Failed to subscribe: {e}")
    
    def process_trade(self, trade_data: dict):
        """
        Process a trade event and record if significant
        
        Args:
            trade_data: Trade data from WebSocket
        """
        try:
            # Extract trade details (adjust keys based on actual API response)
            trader_address = trade_data.get('maker') or trade_data.get('taker')
            size = float(trade_data.get('size', 0))
            price = float(trade_data.get('price', 0))
            market_id = trade_data.get('market_id') or trade_data.get('asset_id')
            outcome = trade_data.get('outcome', 'UNKNOWN')
            side = trade_data.get('side', 'UNKNOWN')
            
            if not trader_address or size == 0:
                return
            
            trade_value = size * price
            
            # Only record trades above threshold
            if trade_value >= self.min_trade_size:
                log.info(f"🐋 Large trade detected: {trader_address[:10]}... ${trade_value:,.2f}")
                
                # Record in database
                self.db.record_trade(
                    address=trader_address,
                    market_id=market_id or 'unknown',
                    outcome=outcome,
                    side=side,
                    size=trade_value,
                    price=price
                )
                
                # Check if this trader should be followed
                trader_stats = self.db.get_trader_stats(trader_address)
                if trader_stats and trader_stats.total_volume > 50000 and not trader_stats.is_following:
                    log.warning(f"🎯 Potential whale: {trader_address[:10]}... (${trader_stats.total_volume:,.2f} volume)")
        
        except Exception as e:
            log.error(f"Error processing trade: {e}")
            log.debug(f"Trade data: {trade_data}")
    
    async def listen(self):
        """Main listening loop"""
        self.running = True
        
        while self.running:
            try:
                if not self.ws:
                    await self.connect()
                    await self.subscribe_to_trades()
                
                # Receive messages
                async for message in self.ws:
                    data = json.loads(message)
                    
                    # Check if it's a trade event
                    if data.get('type') == 'trade' or data.get('channel') == 'trades':
                        self.process_trade(data)
                
            except websockets.exceptions.ConnectionClosed:
                log.warning("WebSocket connection closed, reconnecting...")
                await asyncio.sleep(5)
                self.ws = None
            
            except Exception as e:
                log.error(f"Error in listen loop: {e}")
                await asyncio.sleep(5)
    
    async def start(self):
        """Start the trade monitor"""
        log.info("🚀 Starting Trade Monitor...")
        
        # Add seed whales to database if any
        if SEED_WHALES:
            log.info(f"📝 Adding {len(SEED_WHALES)} seed whales to database")
            for address, nickname, reason in SEED_WHALES:
                self.db.add_or_update_trader(address, 0.0)
                self.db.set_following(address, True)
                log.info(f"  ✅ {nickname}: {address[:10]}...")
        
        # Start listening
        await self.listen()
    
    def stop(self):
        """Stop the monitor"""
        self.running = False
        log.info("🛑 Trade Monitor stopped")


# Example usage
async def main():
    db = WhaleDatabase("data/whales.db")
    monitor = TradeMonitor(db, min_trade_size=500.0)  # $500 minimum for testing
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        monitor.stop()
        db.close()
        log.info("👋 Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
