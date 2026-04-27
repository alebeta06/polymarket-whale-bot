"""
Polymarket Data API Client
Fetches whale data from Polymarket's public Data API
"""
import aiohttp
import asyncio
from typing import List, Dict, Optional
from loguru import logger as log


class PolymarketDataAPI:
    """Client for Polymarket Data API"""
    
    BASE_URL = "https://data-api.polymarket.com"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_leaderboard(self, period: str = "all", limit: int = 100) -> List[Dict]:
        """
        Fetch leaderboard of top traders
        
        Args:
            period: Time period ('all', '30d', '7d', '24h')
            limit: Number of results (max 100)
        
        Returns:
            List of user dictionaries with address, pnl, volume, etc.
        """
        await self._ensure_session()
        
        url = f"{self.BASE_URL}/leaderboard"
        params = {"period": period, "limit": limit}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    log.info(f"Fetched {len(data)} users from leaderboard")
                    return data
                else:
                    log.error(f"Leaderboard API error: {response.status}")
                    return []
        except Exception as e:
            log.error(f"Error fetching leaderboard: {e}")
            return []
    
    async def get_user_portfolio(self, address: str) -> Optional[Dict]:
        """
        Get portfolio information for a specific user
        
        Args:
            address: Wallet address
        
        Returns:
            Portfolio data or None if error
        """
        await self._ensure_session()
        
        url = f"{self.BASE_URL}/users/{address}/portfolio"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    log.warning(f"Portfolio API error for {address}: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching portfolio for {address}: {e}")
            return None
    
    async def get_user_trades(
        self,
        address: str,
        limit: int = 100,
        after_timestamp: Optional[float] = None,
    ) -> List[Dict]:
        """
        Get recent trades for a specific user.

        Endpoint: GET https://data-api.polymarket.com/trades?user=<address>&limit=N
        Each trade dict contains: proxyWallet, side, asset, conditionId, size, price,
        timestamp (unix seconds), title, slug, outcome, outcomeIndex, transactionHash, ...

        Args:
            address: Wallet address (lowercase 0x-prefixed)
            limit: Max number of trades to fetch from the API
            after_timestamp: If set, only trades with timestamp strictly greater than this
                are returned (client-side filter; the public endpoint has no `since` param).

        Returns:
            List of trade dictionaries, newest first.
        """
        await self._ensure_session()

        url = f"{self.BASE_URL}/trades"
        params = {"user": address, "limit": limit}

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, list):
                        log.warning(f"Unexpected trades payload type for {address[:10]}...: {type(data).__name__}")
                        return []
                    if after_timestamp is not None:
                        data = [t for t in data if float(t.get("timestamp", 0)) > after_timestamp]
                    return data
                else:
                    log.warning(f"Trades API error for {address}: {response.status}")
                    return []
        except Exception as e:
            log.error(f"Error fetching trades for {address}: {e}")
            return []
    
    async def get_user_stats(self, address: str) -> Optional[Dict]:
        """
        Get statistics for a specific user
        
        Args:
            address: Wallet address
        
        Returns:
            User stats or None if error
        """
        await self._ensure_session()
        
        url = f"{self.BASE_URL}/users/{address}/stats"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    log.warning(f"Stats API error for {address}: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching stats for {address}: {e}")
            return None


# Example usage
async def main():
    api = PolymarketDataAPI()
    
    # Fetch top 50 traders
    leaderboard = await api.get_leaderboard(period="all", limit=50)
    print(f"Found {len(leaderboard)} top traders")
    
    if leaderboard:
        # Get details of top trader
        top_trader = leaderboard[0]
        address = top_trader.get('address')
        
        stats = await api.get_user_stats(address)
        print(f"Top trader stats: {stats}")
    
    await api.close()


if __name__ == "__main__":
    asyncio.run(main())
