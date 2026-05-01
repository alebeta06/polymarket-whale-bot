#!/usr/bin/env python
"""Throwaway probe: how much historical data do Polymarket's public APIs give us?

Answers two questions before we invest in a real backtest:
  1. How far back does data-api `/trades` go for a typical whale?
  2. What fraction of historical conditionIds are still queryable via Gamma
     (and how many of those are already resolved)?

Usage:
    PYTHONPATH=. python scripts/probe_data_coverage.py
"""
import asyncio
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List

import aiohttp

from src.whale_watching.data_api import PolymarketDataAPI
from src.whale_watching.markets import is_resolved
from src.whale_watching.seed_whales import SEED_WHALES


# Gamma's default /markets response excludes closed markets — we have to
# explicitly ask for them. Querying twice (open + closed) and merging gives
# full coverage for our backtest.
GAMMA_BASE = "https://gamma-api.polymarket.com"
GAMMA_BATCH = 25


async def fetch_markets_full(session: aiohttp.ClientSession, condition_ids: List[str]) -> Dict[str, dict]:
    """Fetch markets covering both open and closed states."""
    seen, uniq = set(), []
    for c in condition_ids:
        if c and c not in seen:
            seen.add(c)
            uniq.append(c)

    result: Dict[str, dict] = {}
    for closed_flag in (None, "true"):
        for i in range(0, len(uniq), GAMMA_BATCH):
            batch = uniq[i : i + GAMMA_BATCH]
            params = [("condition_ids", c) for c in batch]
            if closed_flag:
                params.append(("closed", closed_flag))
            try:
                async with session.get(f"{GAMMA_BASE}/markets", params=params) as r:
                    if r.status != 200:
                        continue
                    data = await r.json()
                    if isinstance(data, list):
                        for m in data:
                            cid = m.get("conditionId")
                            if cid and cid not in result:
                                result[cid] = m
            except Exception as e:
                print(f"  WARN: gamma batch error: {e}")
    return result


# Pick a small spread of whales: top all-time, top 30d, and a mid one.
PROBE_WHALES = [
    ("0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee", "kch123"),
    ("0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2", "reachingthesky"),
    ("0x2005d16a84ceefa912d4e380cd32e7ff827875ea", "RN1"),
]
TRADES_LIMIT = 1000


def fmt_ts(ts: float) -> str:
    if not ts:
        return "n/a"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def month_key(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m")


async def probe_whale_trades(api: PolymarketDataAPI, address: str, nickname: str):
    print(f"\n{'='*70}")
    print(f"Whale: {nickname} ({address[:12]}...)")
    print(f"{'='*70}")

    trades = await api.get_user_trades(address, limit=TRADES_LIMIT)
    if not trades:
        print(f"  No trades returned (limit={TRADES_LIMIT}).")
        return [], set()

    timestamps = [float(t.get("timestamp", 0) or 0) for t in trades]
    timestamps = [t for t in timestamps if t > 0]
    oldest = min(timestamps) if timestamps else 0
    newest = max(timestamps) if timestamps else 0
    span_days = (newest - oldest) / 86400 if timestamps else 0

    print(f"  Trades returned : {len(trades)} (asked for {TRADES_LIMIT})")
    print(f"  Oldest trade    : {fmt_ts(oldest)}")
    print(f"  Newest trade    : {fmt_ts(newest)}")
    print(f"  Span            : {span_days:.1f} days")

    # Monthly histogram
    months = Counter(month_key(t) for t in timestamps)
    print(f"  Trades per month:")
    for m in sorted(months):
        bar = "#" * min(40, months[m])
        print(f"    {m}  {months[m]:4d}  {bar}")

    # Side breakdown (BUY vs SELL) — relevant for hold-to-resolution model
    sides = Counter((t.get("side") or "").upper() for t in trades)
    print(f"  Side breakdown  : {dict(sides)}")

    condition_ids = {t.get("conditionId") for t in trades if t.get("conditionId")}
    print(f"  Unique markets  : {len(condition_ids)}")

    return trades, condition_ids


async def probe_markets(session: aiohttp.ClientSession, condition_ids: set):
    print(f"\n{'='*70}")
    print(f"Gamma coverage for {len(condition_ids)} unique markets")
    print(f"{'='*70}")

    if not condition_ids:
        print("  No markets to query.")
        return

    found = await fetch_markets_full(session, list(condition_ids))

    resolved = 0
    open_markets = 0
    closed_unresolved = 0  # closed=true but outcome prices not 0/1 (UMA dispute, etc.)
    for cid, m in found.items():
        if is_resolved(m):
            resolved += 1
        elif m.get("closed"):
            closed_unresolved += 1
        else:
            open_markets += 1

    not_found = len(condition_ids) - len(found)
    total = len(condition_ids)

    def pct(n):
        return f"{100*n/total:.1f}%" if total else "0%"

    print(f"  Resolved (clean settlement) : {resolved:4d}  ({pct(resolved)})")
    print(f"  Open (still trading)        : {open_markets:4d}  ({pct(open_markets)})")
    print(f"  Closed but unresolved       : {closed_unresolved:4d}  ({pct(closed_unresolved)})")
    print(f"  Not found in Gamma          : {not_found:4d}  ({pct(not_found)})")
    print(f"  ---")
    print(f"  Total                       : {total:4d}")


async def main():
    print("Polymarket data coverage probe")
    print(f"Probing {len(PROBE_WHALES)} whales, limit={TRADES_LIMIT} trades each")

    data_api = PolymarketDataAPI()
    session = aiohttp.ClientSession()

    all_condition_ids: set = set()
    try:
        for address, nickname in PROBE_WHALES:
            _trades, cids = await probe_whale_trades(data_api, address, nickname)
            all_condition_ids |= cids

        await probe_markets(session, all_condition_ids)
    finally:
        await data_api.close()
        await session.close()

    print(f"\nDone. Use these numbers to decide whether the full backtest is viable.")


if __name__ == "__main__":
    asyncio.run(main())
