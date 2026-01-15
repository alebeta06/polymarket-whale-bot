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
                
                # Handle cases where API might return a dict or list
                market_list = data
                if isinstance(data, dict):
                    if "markets" in data:
                        market_list = data["markets"]
                    elif "data" in data:
                        market_list = data["data"]
                
                if not isinstance(market_list, list):
                    log.error(f"Expected list of markets, got {type(market_list)}")
                    return []

                for market_data in market_list:
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
            import json
            
            # Extract basic info
            market_id = data.get("conditionId") or data.get("id")
            question = data.get("question", "Unknown")
            volume = float(data.get("volumeNum") or data.get("volume") or 0)
            liquidity = float(data.get("liquidityNum") or data.get("liquidity") or 0)
            
            # Helper to parse string-encoded JSON fields
            def parse_json_field(field_name):
                val = data.get(field_name)
                if isinstance(val, str) and val.strip().startswith("["):
                    try:
                        return json.loads(val)
                    except:
                        return []
                return val if isinstance(val, list) else []

            # Extract outcomes, prices, and token IDs (some come as JSON strings)
            outcomes_names = parse_json_field("outcomes")
            prices = parse_json_field("outcomePrices")
            token_ids = parse_json_field("clobTokenIds")
            
            if len(outcomes_names) < 2:
                # Try fallback for differently structured markets
                return None
            
            # Find YES and NO outcomes
            yes_outcome = None
            no_outcome = None
            
            for i, name in enumerate(outcomes_names):
                upper_name = name.upper()
                price = float(prices[i]) if i < len(prices) else 0.0
                token_id = token_ids[i] if i < len(token_ids) else ""
                
                outcome = Outcome(
                    name=upper_name,
                    price=price,
                    token_id=token_id,
                    liquidity=liquidity # Use market liquidity as proxy
                )
                
                if "YES" in upper_name:
                    yes_outcome = outcome
                elif "NO" in upper_name:
                    no_outcome = outcome
            
            if not yes_outcome or not no_outcome:
                return None
            
            # Parse end date if available
            end_date = None
            for key in ["endDateIso", "end_date_iso", "endDate"]:
                if key in data and data[key]:
                    try:
                        val = data[key]
                        if isinstance(val, str):
                            end_date = datetime.fromisoformat(
                                val.replace("Z", "+00:00")
                            )
                            break
                    except:
                        continue
            
            market = Market(
                id=market_id,
                question=question,
                category=category,
                volume=volume,
                liquidity=liquidity,
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
