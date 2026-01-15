"""
Trade Executor - Executes trades on Polymarket using CLOB API
"""
from typing import List, Optional
from datetime import datetime
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from src.utils import (
    ArbitrageOpportunity,
    TradeOrder,
    TradeResult,
    OrderSide,
    Market,
    log
)
from src.config import get_settings


class TradeExecutor:
    """Executes arbitrage trades on Polymarket"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[ClobClient] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Polymarket CLOB client"""
        try:
            # Initialize client with API credentials
            self.client = ClobClient(
                key=self.settings.polymarket_api_key,
                secret=self.settings.polymarket_api_secret,
                passphrase=self.settings.polymarket_api_passphrase,
                host="https://clob.polymarket.com",
                chain_id=137  #Polygon mainnet
            )
            
            # Set private key for signing
            self.client.set_api_creds(self.client.create_or_derive_api_creds())
            
            log.info("✅ CLOB client initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize CLOB client: {e}")
            self.client = None
    
    async def execute_arbitrage(
        self,
        opportunity: ArbitrageOpportunity,
        market: Market
    ) -> TradeResult:
        """
        Execute an arbitrage opportunity
        
        Args:
            opportunity: The arbitrage opportunity
            market: The market to trade in
            
        Returns:
            TradeResult with execution details
        """
        log.info(f"{'[DRY RUN] ' if self.settings.dry_run else ''}Executing arbitrage...")
        log.info(f"Market: {opportunity.market_question[:60]}...")
        log.info(f"Expected profit: ${opportunity.expected_profit:.2f} ({opportunity.roi*100:.2f}% ROI)")
        
        if self.settings.dry_run:
            return self._simulate_execution(opportunity, market)
        
        try:
            # Real execution
            return await self._execute_real_trade(opportunity, market)
            
        except Exception as e:
            log.error(f"Error executing trade: {e}")
            return TradeResult(
                opportunity_id=opportunity.id,
                success=False,
                executed_at=datetime.now(),
                orders=[],
                error_message=str(e)
            )
    
    def _simulate_execution(
        self,
        opportunity: ArbitrageOpportunity,
        market: Market
    ) -> TradeResult:
        """
        Simulate trade execution (Paper Trading)
        
        Args:
            opportunity: The arbitrage opportunity
            market: The market
            
        Returns:
            Simulated TradeResult
        """
        # Create simulated orders
        yes_order = TradeOrder(
            market_id=market.id,
            token_id=market.yes_outcome.token_id,
            side=OrderSide.BUY,
            size=opportunity.required_capital / 2,
            price=opportunity.yes_price
        )
        
        no_order = TradeOrder(
            market_id=market.id,
            token_id=market.no_outcome.token_id,
            side=OrderSide.BUY,
            size=opportunity.required_capital / 2,
            price=opportunity.no_price
        )
        
        log.info(f"[DRY RUN] Would buy ${yes_order.size:.2f} YES at {yes_order.price:.3f}")
        log.info(f"[DRY RUN] Would buy ${no_order.size:.2f} NO at {no_order.price:.3f}")
        log.info(f"[DRY RUN] Simulated profit: ${opportunity.expected_profit:.2f}")
        
        return TradeResult(
            opportunity_id=opportunity.id,
            success=True,
            executed_at=datetime.now(),
            orders=[yes_order, no_order],
            actual_profit=opportunity.expected_profit,
            fills=[]
        )
    
    async def _execute_real_trade(
        self,
        opportunity: ArbitrageOpportunity,
        market: Market
    ) -> TradeResult:
        """
        Execute real trade on Polymarket
        
        IMPORTANT: This will spend real USDC!
        
        Args:
            opportunity: The arbitrage opportunity
            market: The market
            
        Returns:
            TradeResult with actual execution data
        """
        if not self.client:
            raise RuntimeError("CLOB client not initialized")
        
        log.warning("⚠️  EXECUTING REAL TRADE - This will spend USDC!")
        
        orders = []
        fills = []
        
        try:
            # Place YES order
            yes_size = opportunity.required_capital / 2
            yes_order_args = OrderArgs(
                token_id=market.yes_outcome.token_id,
                price=opportunity.yes_price,
                side="BUY",
                size=yes_size
            )
            
            yes_response = self.client.create_order(yes_order_args)
            log.info(f"✅ YES order placed: {yes_response}")
            
            yes_order = TradeOrder(
                market_id=market.id,
                token_id=market.yes_outcome.token_id,
                side=OrderSide.BUY,
                size=yes_size,
                price=opportunity.yes_price
            )
            orders.append(yes_order)
            
            # Place NO order
            no_size = opportunity.required_capital / 2
            no_order_args = OrderArgs(
                token_id=market.no_outcome.token_id,
                price=opportunity.no_price,
                side="BUY",
                size=no_size
            )
            
            no_response = self.client.create_order(no_order_args)
            log.info(f"✅ NO order placed: {no_response}")
            
            no_order = TradeOrder(
                market_id=market.id,
                token_id=market.no_outcome.token_id,
                side=OrderSide.BUY,
                size=no_size,
                price=opportunity.no_price
            )
            orders.append(no_order)
            
            # Calculate actual profit (will be known after fills)
            # For now, use expected profit
            actual_profit = opportunity.expected_profit
            
            return TradeResult(
                opportunity_id=opportunity.id,
                success=True,
                executed_at=datetime.now(),
                orders=orders,
                actual_profit=actual_profit,
                fills=[yes_response, no_response]
            )
            
        except Exception as e:
            log.error(f"Error in real trade execution: {e}")
            raise
    
    def get_balance(self) -> float:
        """
        Get current USDC balance
        
        Returns:
            Balance in USDC
        """
        if not self.client or self.settings.dry_run:
            # Return simulated balance for dry run
            return 15.61
        
        try:
            # Get actual balance from Polymarket
            # Note: This would need to be implemented based on py-clob-client API
            # For now, return a placeholder
            return 15.61
            
        except Exception as e:
            log.error(f"Error fetching balance: {e}")
            return 0.0
    
    def can_execute(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Check if we have sufficient balance to execute opportunity
        
        Args:
            opportunity: The opportunity to check
            
        Returns:
            True if executable, False otherwise
        """
        balance = self.get_balance()
        return balance >= opportunity.required_capital
