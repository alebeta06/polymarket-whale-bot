"""
Market Scanner - Fetches active markets from Polymarket Gamma API
"""
import aiohttp
from typing import List, Optional
from datetime import datetime
from src.utils import Market, Outcome, log
from src.config import get_settings


class MarketScanner:
    """Scans Polymarket for active markets"""
    
    BASE_URL = "https://gamma-api.polymarket.com"
    
    def __init__(self):
        self.settings = get_settings()
        self.cache: List[Market] = []
        self.last_scan: Optional[datetime] = None
    
    async def fetch_active_markets(self) -> List[Market]:
        """
        Fetch all active markets from Gamma API
        
        Returns:
            List of Market objects
        """
        log.info("Fetching active markets from Gamma API...")
        
        try:
            async with aiohttp.ClientSession() as session:
                markets = []
                
                # Fetch markets for each configured category
                for category in self.settings.get_categories_list():
                    category_markets = await self._fetch_markets_by_category(
                        session, category
                    )
                    markets.extend(category_markets)
                
                # Filter by minimum volume
                filtered_markets = [
                    m for m in markets
                    if m.volume >= self.settings.min_market_volume
                ]
                
                log.info(
                    f"Fetched {len(markets)} markets, "
                    f"{len(filtered_markets)} above ${self.settings.min_market_volume} volume"
                )
                
                self.cache = filtered_markets
                self.last_scan = datetime.now()
                
                return filtered_markets
                
        except Exception as e:
            log.error(f"Error fetching markets: {e}")
            return []
    
    async def _fetch_markets_by_category(
        self,
        session: aiohttp.ClientSession,
        category: str
    ) -> List[Market]:
        """Fetch markets for a specific category"""
        
        url = f"{self.BASE_URL}/markets"
        params = {
            "active": "true",
            "closed": "false",
        }
        
        # Add category filter if not empty
        if category and category.lower() != "all":
            params["tag"] = category
        
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    log.error(
                        f"Failed to fetch markets for {category}: "
                        f"Status {response.status}"
                    )
                    return []
                
                data = await response.json()
                markets = []
                
                for market_data in data:
                    market = self._parse_market(market_data, category)
                    if market:
                        markets.append(market)
                
                log.debug(f"Fetched {len(markets)} markets from {category}")
                return markets
                
        except Exception as e:
            log.error(f"Error fetching {category} markets: {e}")
            return []
    
    def _parse_market(self, data: dict, category: str) -> Optional[Market]:
        """
        Parse market data from API response
        
        Args:
            data: Raw market data from API
            category: Market category
            
        Returns:
            Market object or None if parsing fails
        """
        try:
            # Extract market info
            market_id = data.get("condition_id") or data.get("id")
            question = data.get("question", "Unknown")
            volume = float(data.get("volume", 0))
            
            # Extract outcomes (YES/NO)
            outcomes = data.get("outcomes", [])
            if len(outcomes) < 2:
                log.debug(f"Market {market_id} has less than 2 outcomes, skipping")
                return None
            
            # Find YES and NO outcomes
            yes_outcome = None
            no_outcome = None
            
            for outcome_data in outcomes:
                name = outcome_data.get("name", "").upper()
                price = float(outcome_data.get("price", 0))
                token_id = outcome_data.get("token_id", "")
                liquidity = float(outcome_data.get("liquidity", 0))
                
                outcome = Outcome(
                    name=name,
                    price=price,
                    token_id=token_id,
                    liquidity=liquidity
                )
                
                if "YES" in name:
                    yes_outcome = outcome
                elif "NO" in name:
                    no_outcome = outcome
            
            if not yes_outcome or not no_outcome:
                log.debug(f"Market {market_id} missing YES/NO outcomes, skipping")
                return None
            
            # Parse end date if available
            end_date = None
            if "end_date_iso" in data:
                try:
                    end_date = datetime.fromisoformat(
                        data["end_date_iso"].replace("Z", "+00:00")
                    )
                except:
                    pass
            
            market = Market(
                id=market_id,
                question=question,
                category=category,
                volume=volume,
                liquidity=float(data.get("liquidity", 0)),
                yes_outcome=yes_outcome,
                no_outcome=no_outcome,
                active=data.get("active", True),
                end_date=end_date
            )
            
            return market
            
        except Exception as e:
            log.error(f"Error parsing market: {e}")
            return None
    
    def get_cached_markets(self) -> List[Market]:
        """Get cached markets without fetching"""
        return self.cache
    
    def should_refresh(self) -> bool:
        """Check if cache should be refreshed"""
        if not self.last_scan:
            return True
        
        elapsed = (datetime.now() - self.last_scan).total_seconds()
        return elapsed >= self.settings.market_refresh_interval
