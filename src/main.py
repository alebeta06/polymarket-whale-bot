"""
Polymarket Arbitrage Bot - Main Entry Point
"""
import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional

from src.config import load_settings
from src.utils import log
from src.scanner import MarketScanner
from src.arbitrage import ArbitrageDetector
from src.execution import TradeExecutor
from src.risk import RiskManager
from src.monitoring import MetricsTracker


class PolymarketBot:
    """Main bot orchestrator"""
    
    def __init__(self):
        # Load configuration
        try:
            self.settings = load_settings()
            log.info("✅ Configuration loaded successfully")
        except Exception as e:
            log.error(f"Failed to load configuration: {e}")
            log.error("Make sure .env file exists and is properly configured")
            sys.exit(1)
        
        # Initialize components
        self.scanner = MarketScanner()
        self.detector = ArbitrageDetector()
        self.executor = TradeExecutor()
        self.risk_manager = RiskManager()
        self.metrics = MetricsTracker()
        
        self.running = False
        self.scan_count = 0
    
    async def start(self):
        """Start the bot"""
        log.info("=" * 60)
        log.info("🤖 POLYMARKET ARBITRAGE BOT STARTING")
        log.info("=" * 60)
        log.info(f"Mode: {'📝 PAPER TRADING (Simulation)' if self.settings.dry_run else '💰 LIVE TRADING'}")
        log.info(f"Max Position Size: {self.settings.max_position_size_percent*100}%")
        log.info(f"Daily Stop-Loss: {self.settings.daily_stop_loss_percent*100}%")
        log.info(f"Min Profit: {self.settings.min_profit_percent*100}%")
        log.info(f"Categories: {self.settings.get_categories_list()}")
        log.info("=" * 60)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        
        try:
            await self._main_loop()
        except Exception as e:
            log.error(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def _main_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                self.scan_count += 1
                log.info(f"\n{'='*60}")
                log.info(f"🔄 Scan #{self.scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                log.info(f"{'='*60}")
                
                # Step 1: Scan markets
                markets = await self.scanner.fetch_active_markets()
                if not markets:
                    log.warning("No markets found, waiting before retry...")
                    await asyncio.sleep(60)
                    continue
                
                # Step 2: Detect arbitrage opportunities
                opportunities = self.detector.find_opportunities(markets)
                
                # Record opportunities
                for opp in opportunities:
                    self.metrics.record_opportunity(opp)
                
                if not opportunities:
                    log.info("No arbitrage opportunities found in this scan")
                    await self._wait_for_next_scan()
                    continue
                
                # Step 3: Filter profitable opportunities
                filtered_opps = self.detector.filter_opportunities(opportunities)
                
                if not filtered_opps:
                    log.info("No opportunities meet profitability threshold")
                    await self._wait_for_next_scan()
                    continue
                
                # Step 4: Execute trades
                balance = self.executor.get_balance()
                log.info(f"💰 Current balance: ${balance:.2f}")
                
                for opportunity in filtered_opps[:5]:  # Limit to 5 per batch
                    # Check risk limits
                    can_execute, reason = self.risk_manager.can_execute(
                        opportunity, balance
                    )
                    
                    if not can_execute:
                        log.warning(f"⚠️  Cannot execute: {reason}")
                        continue
                    
                    # Find corresponding market
                    market = next(
                        (m for m in markets if m.id == opportunity.market_id),
                        None
                    )
                    
                    if not market:
                        log.error(f"Market {opportunity.market_id} not found")
                        continue
                    
                    # Execute trade
                    result = await self.executor.execute_arbitrage(opportunity, market)
                    
                    # Record result
                    self.risk_manager.record_trade(result)
                    self.metrics.record_trade(result)
                    
                    # Update balance if successful
                    if result.success and result.actual_profit:
                        balance += result.actual_profit
                
                # Step 5: Wait for next scan
                await self._wait_for_next_scan()
                
            except Exception as e:
                log.error(f"Error in main loop iteration: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute before retry
        
    async def _wait_for_next_scan(self):
        """Wait for next scan interval"""
        interval = self.settings.market_refresh_interval
        log.info(f"⏳ Waiting {interval}s until next scan...")
        log.info(f"\n{'='*60}\n")
        
        # Check risk stats every minute while waiting
        for i in range(interval):
            await asyncio.sleep(1)
            
            # Show stats every minute
            if i > 0 and i % 60 == 0:
                stats = self.risk_manager.get_daily_stats()
                log.info(f"📊 Daily P&L: ${stats['pnl']:.2f} | Trades: {stats['trades_count']}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        log.warning(f"\n⚠️  Received signal {signum}, initiating shutdown...")
        self.running = False
    
    async def shutdown(self):
        """Graceful shutdown"""
        log.info("\n🛑 Shutting down bot...")
        
        # Generate final daily report
        daily_metrics = self.metrics.generate_daily_report()
        self.metrics.save_daily_metrics(daily_metrics)
        
        # Show final stats
        stats = self.risk_manager.get_daily_stats()
        log.info("\n📊 Final Daily Statistics:")
        log.info(f"  Date: {stats['date']}")
        log.info(f"  P&L: ${stats['pnl']:.2f}")
        log.info(f"  Trades: {stats['trades_count']} ({stats['successful_trades']} successful)")
        log.info(f"  Opportunities Detected: {daily_metrics.opportunities_detected}")
        
        log.info("\n✅ Bot shutdown complete")
        log.info("=" * 60)


async def main():
    """Entry point"""
    bot = PolymarketBot()
    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
