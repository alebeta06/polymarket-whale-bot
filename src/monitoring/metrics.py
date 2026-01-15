"""
Metrics Tracker - Tracks and logs trading metrics
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List
from src.utils import TradeResult, ArbitrageOpportunity, DailyMetrics, log
from src.config import get_settings


class MetricsTracker:
    """Tracks trading metrics and generates reports"""
    
    def __init__(self):
        self.settings = get_settings()
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        self.opportunities_file = self.data_dir / "opportunities.json"
        self.trades_file = self.data_dir / "trades.json"
        self.daily_metrics_file = self.data_dir / "daily_metrics.json"
        
        self.opportunities_detected: List[ArbitrageOpportunity] = []
        self.trades_executed: List[TradeResult] = []
    
    def record_opportunity(self, opportunity: ArbitrageOpportunity):
        """Record a detected arbitrage opportunity"""
        self.opportunities_detected.append(opportunity)
        
        # Save to file
        self._save_opportunity(opportunity)
    
    def record_trade(self, result: TradeResult):
        """Record an executed trade"""
        self.trades_executed.append(result)
        
        # Save to file
        self._save_trade(result)
        
        # Log to console
        if result.success:
            log.info(
                f"✅ Trade executed successfully | "
                f"Profit: ${result.actual_profit:.2f}"
            )
        else:
            log.error(f"❌ Trade failed: {result.error_message}")
    
    def _save_opportunity(self, opportunity: ArbitrageOpportunity):
        """Save opportunity to JSON file"""
        try:
            # Load existing
            existing = []
            if self.opportunities_file.exists():
                with open(self.opportunities_file, 'r') as f:
                    existing = json.load(f)
            
            # Append new
            opp_dict = {
                "id": opportunity.id,
                "market_id": opportunity.market_id,
                "question": opportunity.market_question,
                "type": opportunity.type.value,
                "expected_profit": opportunity.expected_profit,
                "roi": opportunity.roi,
                "required_capital": opportunity.required_capital,
                "detected_at": opportunity.detected_at.isoformat(),
                "yes_price": opportunity.yes_price,
                "no_price": opportunity.no_price,
                "total_probability": opportunity.total_probability
            }
            existing.append(opp_dict)
            
            # Save
            with open(self.opportunities_file, 'w') as f:
                json.dump(existing, f, indent=2)
                
        except Exception as e:
            log.error(f"Error saving opportunity: {e}")
    
    def _save_trade(self, result: TradeResult):
        """Save trade result to JSON file"""
        try:
            # Load existing
            existing = []
            if self.trades_file.exists():
                with open(self.trades_file, 'r') as f:
                    existing = json.load(f)
            
            # Append new
            trade_dict = {
                "opportunity_id": result.opportunity_id,
                "success": result.success,
                "executed_at": result.executed_at.isoformat(),
                "actual_profit": result.actual_profit,
                "error_message": result.error_message,
                "orders_count": len(result.orders)
            }
            existing.append(trade_dict)
            
            # Save
            with open(self.trades_file, 'w') as f:
                json.dump(existing, f, indent=2)
                
        except Exception as e:
            log.error(f"Error saving trade: {e}")
    
    def generate_daily_report(self) -> DailyMetrics:
        """Generate daily metrics report"""
        today = datetime.now().date()
        
        # Filter today's trades
        today_trades = [
            t for t in self.trades_executed
            if t.executed_at.date() == today
        ]
        
        # Calculate metrics
        total_profit = sum(
            t.actual_profit for t in today_trades
            if t.success and t.actual_profit
        )
        
        successful_count = sum(1 for t in today_trades if t.success)
        
        largest_profit = max(
            (t.actual_profit for t in today_trades if t.success and t.actual_profit),
            default=0.0
        )
        
        # Calculate total volume
        total_volume = sum(
            sum(order.size for order in t.orders)
            for t in today_trades
        )
        
        # Today's opportunities
        today_opportunities = [
            o for o in self.opportunities_detected
            if o.detected_at.date() == today
        ]
        
        metrics = DailyMetrics(
            date=datetime.now(),
            opportunities_detected=len(today_opportunities),
            trades_executed=len(today_trades),
            trades_successful=successful_count,
            total_profit=total_profit,
            total_volume=total_volume,
            roi=total_profit / total_volume if total_volume > 0 else 0,
            largest_profit=largest_profit,
            average_slippage=0.0  # TODO: Calculate from fills
        )
        
        log.info(f"\n📊 Daily Report ({today}):")
        log.info(f"  Opportunities: {metrics.opportunities_detected}")
        log.info(f"  Trades: {metrics.trades_executed} ({metrics.trades_successful} successful)")
        log.info(f"  Total Profit: ${metrics.total_profit:.2f}")
        log.info(f"  ROI: {metrics.roi*100:.2f}%")
        
        return metrics
    
    def save_daily_metrics(self, metrics: DailyMetrics):
        """Save daily metrics to file"""
        try:
            # Load existing
            existing = []
            if self.daily_metrics_file.exists():
                with open(self.daily_metrics_file, 'r') as f:
                    existing = json.load(f)
            
            # Append new
            metrics_dict = {
                "date": metrics.date.isoformat(),
                "opportunities_detected": metrics.opportunities_detected,
                "trades_executed": metrics.trades_executed,
                "trades_successful": metrics.trades_successful,
                "total_profit": metrics.total_profit,
                "total_volume": metrics.total_volume,
                "roi": metrics.roi,
                "largest_profit": metrics.largest_profit
            }
            existing.append(metrics_dict)
            
            # Save
            with open(self.daily_metrics_file, 'w') as f:
                json.dump(existing, f, indent=2)
                
        except Exception as e:
            log.error(f"Error saving daily metrics: {e}")
