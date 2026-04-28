#!/usr/bin/env python
"""Reconcile paper_trades against current Polymarket market state.

Run periodically (cron / loop) while the bot is in DRY_RUN mode:
    PYTHONPATH=. python scripts/reconcile.py
"""
import asyncio
from loguru import logger as log

from src.whale_watching.database import WhaleDatabase
from src.whale_watching.markets import MarketsAPI
from src.whale_watching.reconcile import reconcile


async def main():
    db = WhaleDatabase("data/whales.db")
    markets = MarketsAPI()
    try:
        stats = await reconcile(db, markets)
        log.info("=" * 60)
        log.info("📊 RECONCILIATION SUMMARY")
        log.info("=" * 60)
        log.info(f"  Open before:    {stats.open_before}")
        log.info(f"  Resolved (win): {stats.resolved_win}")
        log.info(f"  Resolved (loss):{stats.resolved_loss}")
        log.info(f"  Invalidated:    {stats.invalidated}")
        log.info(f"  Still open:     {stats.still_open}")
        log.info(f"  Realized P&L:   ${stats.realized_pnl_usd:+,.2f}")
        log.info(f"  Unrealized P&L: ${stats.unrealized_pnl_usd:+,.2f}")
        if stats.errors:
            log.warning(f"  Errors ({len(stats.errors)}):")
            for e in stats.errors[:5]:
                log.warning(f"    - {e}")
        log.info("=" * 60)
    finally:
        await markets.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
