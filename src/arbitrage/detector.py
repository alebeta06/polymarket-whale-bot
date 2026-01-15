"""
Arbitrage Detector - Identifies arbitrage opportunities in markets
"""
from typing import List
from datetime import datetime
import uuid
from src.utils import Market, ArbitrageOpportunity, ArbitrageType, log
from src.config import get_settings


class ArbitrageDetector:
    """Detects arbitrage opportunities in Polymarket markets"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def find_opportunities(self, markets: List[Market]) -> List[ArbitrageOpportunity]:
        """
        Find all arbitrage opportunities in given markets
        
        Args:
            markets: List of markets to analyze
            
        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        
        # Detect intra-market arbitrage (YES + NO < 1)
        for market in markets:
            opp = self._detect_intra_market(market)
            if opp:
                opportunities.append(opp)
        
        log.info(
            f"Detected {len(opportunities)} arbitrage opportunities "
            f"across {len(markets)} markets"
        )
        
        return opportunities
    
    def _detect_intra_market(self, market: Market) -> ArbitrageOpportunity | None:
        """
        Detect intra-market arbitrage (when YES + NO < 1)
        
        In a fair market: P(YES) + P(NO) = 1
        If the sum is less than 1, we can buy both and profit.
        
        Args:
            market: Market to analyze
            
        Returns:
            ArbitrageOpportunity or None
        """
        # Check if market has arbitrage
        if not market.has_intra_arbitrage:
            return None
        
        yes_price = market.yes_outcome.price
        no_price = market.no_outcome.price
        total_prob = yes_price + no_price
        
        # Calculate profit
        # Cost: Buy $1 of YES + $1 of NO = $(yes_price + no_price)
        # Return: When market resolves, you get $1 back (one will be worth $1, other $0)
        # Gross profit: $1 - total_prob
        
        gross_profit_pct = 1.0 - total_prob
        
        # Subtract fees (2% per trade, so 4% total for YES + NO)
        fees = self.settings.polymarket_fee_percent * 2
        net_profit_pct = gross_profit_pct - fees
        
        # Only create opportunity if profitable after fees
        if net_profit_pct <= self.settings.min_profit_percent:
            return None
        
        # Calculate capital required (based on max position size)
        # We'll scale up to maximum allowed
        max_capital = self.settings.max_position_size_percent * 100  # Assume $100 for now
        required_capital = min(max_capital, market.liquidity / 2)
        
        # Expected profit in USDC
        expected_profit = required_capital * net_profit_pct
        
        opportunity = ArbitrageOpportunity(
            id=str(uuid.uuid4()),
            market_id=market.id,
            market_question=market.question,
            type=ArbitrageType.INTRA_MARKET,
            expected_profit=expected_profit,
            roi=net_profit_pct,
            required_capital=required_capital,
            detected_at=datetime.now(),
            yes_price=yes_price,
            no_price=no_price,
            total_probability=total_prob
        )
        
        log.info(
            f"Found intra-market arbitrage: {market.question[:50]}... | "
            f"YES: {yes_price:.3f}, NO: {no_price:.3f}, Total: {total_prob:.3f} | "
            f"ROI: {net_profit_pct*100:.2f}%, Profit: ${expected_profit:.2f}"
        )
        
        return opportunity
    
    def filter_opportunities(
        self,
        opportunities: List[ArbitrageOpportunity]
    ) -> List[ArbitrageOpportunity]:
        """
        Filter opportunities based on profitability threshold
        
        Args:
            opportunities: List of opportunities
            
        Returns:
            Filtered list of profitable opportunities
        """
        filtered = [
            opp for opp in opportunities
            if opp.is_profitable(
                self.settings.min_profit_percent,
                self.settings.polymarket_fee_percent
            )
        ]
        
        # Sort by ROI (highest first)
        filtered.sort(key=lambda x: x.roi, reverse=True)
        
        log.info(
            f"Filtered to {len(filtered)} profitable opportunities "
            f"(min ROI: {self.settings.min_profit_percent*100}%)"
        )
        
        return filtered
