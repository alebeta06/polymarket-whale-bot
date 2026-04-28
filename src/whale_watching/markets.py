"""
Polymarket Gamma API client.

Used for market metadata: resolution state, current prices, expiry.
Read-only, no auth required. Separate from data_api.py (which is for traders/trades).
"""
import asyncio
import json
import aiohttp
from typing import Dict, List, Optional
from loguru import logger as log


class MarketsAPI:
    """Async client for Polymarket Gamma markets endpoint."""

    BASE_URL = "https://gamma-api.polymarket.com"
    # Gamma's `condition_ids` query param tolerates many ids per request, but to
    # stay polite (and within URL length) we batch.
    BATCH_SIZE = 25

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_markets(self, condition_ids: List[str]) -> Dict[str, dict]:
        """Fetch market metadata for the given condition ids.

        Returns a {condition_id: market_dict} mapping. Missing ids simply do not
        appear in the result (no exception).
        """
        await self._ensure_session()

        # Dedup while preserving order, then batch.
        seen = set()
        uniq = [c for c in condition_ids if c and not (c in seen or seen.add(c))]

        result: Dict[str, dict] = {}
        for i in range(0, len(uniq), self.BATCH_SIZE):
            batch = uniq[i : i + self.BATCH_SIZE]
            try:
                async with self.session.get(
                    f"{self.BASE_URL}/markets",
                    params=[("condition_ids", c) for c in batch],
                ) as r:
                    if r.status != 200:
                        log.warning(f"Gamma /markets HTTP {r.status} for batch of {len(batch)}")
                        continue
                    data = await r.json()
                    if not isinstance(data, list):
                        log.warning(f"Gamma /markets unexpected payload: {type(data).__name__}")
                        continue
                    for m in data:
                        cid = m.get("conditionId")
                        if cid:
                            result[cid] = m
            except Exception as e:
                log.error(f"Gamma /markets error for batch starting {batch[0][:10]}...: {e}")

        return result


# --- Pure helpers (no network) used by reconcile.py and tests. -----------------

def parse_outcome_prices(market: dict) -> Optional[List[float]]:
    """Gamma encodes outcomePrices as a JSON string. Return parsed floats or None."""
    raw = market.get("outcomePrices")
    if raw is None:
        return None
    try:
        if isinstance(raw, str):
            parsed = json.loads(raw)
        else:
            parsed = raw
        return [float(p) for p in parsed]
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def parse_outcomes(market: dict) -> Optional[List[str]]:
    """Gamma encodes outcomes as a JSON string of strings (e.g. ["Yes","No"])."""
    raw = market.get("outcomes")
    if raw is None:
        return None
    try:
        if isinstance(raw, str):
            parsed = json.loads(raw)
        else:
            parsed = raw
        return [str(o) for o in parsed]
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def outcome_index(market: dict, outcome_label: str) -> Optional[int]:
    """Find the index of `outcome_label` (case-insensitive) in market['outcomes']."""
    outcomes = parse_outcomes(market)
    if not outcomes:
        return None
    target = outcome_label.strip().lower()
    for i, o in enumerate(outcomes):
        if o.strip().lower() == target:
            return i
    return None


def is_resolved(market: dict) -> bool:
    """A market is resolved when Gamma marks it closed AND outcome prices are 0/1.

    Sometimes a market is `closed=true` while `outcomePrices` is still mid-range
    (during UMA dispute windows). We require a clean settlement before computing P&L.
    """
    if not market.get("closed"):
        return False
    prices = parse_outcome_prices(market)
    if not prices or len(prices) < 2:
        return False
    # Settled state: one price ≈ 1, the other ≈ 0.
    return any(abs(p - 1.0) < 1e-3 for p in prices) and any(abs(p) < 1e-3 for p in prices)
