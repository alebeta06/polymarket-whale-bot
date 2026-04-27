#!/usr/bin/env python
"""
Whale Watching Bot - Main Entry Point
Monitors specific whale addresses from leaderboard
"""
import asyncio
import signal
from loguru import logger as log

from src.config import get_settings
from src.whale_watching.database import WhaleDatabase
from src.whale_watching.individual_monitor import IndividualWhaleMonitor
from src.whale_watching.risk import RiskLimits


class WhaleWatchingBot:
    """Main bot controller"""

    def __init__(self, poll_interval: int = 60):
        """
        Initialize the Whale Watching bot

        Args:
            poll_interval: Seconds between checks for whale trades
        """
        s = get_settings()
        self.db = WhaleDatabase("data/whales.db")
        self.monitor = IndividualWhaleMonitor(
            self.db,
            poll_interval=poll_interval,
            dry_run=s.dry_run,
            copy_pct=s.max_position_size_percent,
            paper_starting_balance_usd=s.paper_starting_balance_usd,
            max_per_copy_trade_usd=s.max_per_copy_trade_usd,
            risk_limits=RiskLimits(
                min_whale_notional_usd=s.min_whale_trade_usd,
                max_trade_age_seconds=s.max_whale_trade_age_seconds,
                min_market_volume_usd=s.min_market_volume,
                daily_stop_loss_pct=s.daily_stop_loss_percent,
            ),
        )
        self.running = False
    
    async def start(self):
        """Start the bot"""
        log.info("=" * 60)
        log.info("🐋 WHALE WATCHING BOT STARTING")
        log.info("=" * 60)
        log.info("Mode: INDIVIDUAL MONITORING")
        log.info("Strategy: Poll specific whale addresses")
        log.info("=" * 60)
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        
        try:
            # Start monitoring
            await self.monitor.start()
        except Exception as e:
            log.error(f"Error in bot: {e}")
        finally:
            await self.shutdown()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        log.warning(f"\n⚠️  Received signal {signum}, initiating shutdown...")
        self.running = False
        self.monitor.stop()
    
    async def shutdown(self):
        """Clean shutdown"""
        log.info("\n🛑 Shutting down Whale Watching Bot...")
        
        # Show final stats
        following = self.db.get_following_list()
        
        if following:
            log.info(f"\n📊 Monitoring {len(following)} Whales:")
            for whale in following[:10]:  # Show first 10
                log.info(
                    f"  {whale.address[:12]}... - "
                    f"${whale.total_volume:,.2f} ({whale.total_trades} trades)"
                )
        
        # Close database
        self.db.close()
        log.info("✅ Shutdown complete")
        log.info("=" * 60)


async def main():
    """Main entry point"""
    # Create and start the bot
    # Poll every 60 seconds (can be adjusted)
    bot = WhaleWatchingBot(poll_interval=60)
    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 Goodbye!")
