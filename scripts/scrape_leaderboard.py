#!/usr/bin/env python
"""Refresh the whale seed list from Polymarket's live profit leaderboard.

Strategy: pull top-N from "30d" and "all" windows. The intersection — whales
profitable both this month AND historically — are the strongest candidates.
Print a ready-to-paste SEED_WHALES Python literal; the user reviews and commits.

We deliberately do NOT overwrite seed_whales.py automatically: per CLAUDE.md the
seed list is curated by the user, and a leaderboard snapshot is one input, not
the source of truth.

Usage:
    PYTHONPATH=. python scripts/scrape_leaderboard.py [--top N]
"""
import argparse
import asyncio
from datetime import datetime
from typing import Dict, List, Tuple

from loguru import logger as log

from src.whale_watching.data_api import PolymarketDataAPI


def merge_windows(
    monthly: List[Dict],
    historic: List[Dict],
    *,
    top_n: int,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Return (consistent, monthly_only, historic_only), each sorted by PnL desc.

    "consistent" = whales that appear in BOTH the 30d and all-time top-N AND have
    positive PnL in both. These are the strongest candidates to copy.
    """
    def by_addr(rows: List[Dict]) -> Dict[str, Dict]:
        return {r["proxyWallet"].lower(): r for r in rows if r.get("proxyWallet")}

    m_map = by_addr(monthly)
    h_map = by_addr(historic)

    consistent: List[Dict] = []
    for addr, m_row in m_map.items():
        h_row = h_map.get(addr)
        if h_row is None:
            continue
        if (m_row.get("amount") or 0) <= 0 or (h_row.get("amount") or 0) <= 0:
            continue
        consistent.append(
            {
                "proxyWallet": addr,
                "name": m_row.get("name") or m_row.get("pseudonym") or "anon",
                "pnl_30d": m_row["amount"],
                "pnl_all": h_row["amount"],
            }
        )
    consistent.sort(key=lambda r: r["pnl_30d"], reverse=True)

    monthly_only = [
        {**r, "address": r["proxyWallet"].lower()}
        for r in monthly
        if r["proxyWallet"].lower() not in {c["proxyWallet"] for c in consistent}
        and (r.get("amount") or 0) > 0
    ][:top_n]

    historic_only = [
        {**r, "address": r["proxyWallet"].lower()}
        for r in historic
        if r["proxyWallet"].lower() not in {c["proxyWallet"] for c in consistent}
        and (r.get("amount") or 0) > 0
    ][:top_n]

    return consistent[:top_n], monthly_only, historic_only


def render_seed(consistent: List[Dict]) -> str:
    """Render a SEED_WHALES Python literal from the consistent winners."""
    today = datetime.now().date().isoformat()
    lines = [
        "# Manual Whale Seed List - REGENERATED from leaderboard",
        f"# Last updated: {today}",
        "# Source: lb-api.polymarket.com /profit (intersection of 30d ∩ all-time, PnL > 0)",
        "",
        "SEED_WHALES = [",
        "    # Format: (address, nickname, reason)",
        "",
    ]
    for i, w in enumerate(consistent, 1):
        nickname = (w["name"] or "anon").replace('"', "'")[:32] or f"Whale#{i}"
        reason = f"30d ${w['pnl_30d']:,.0f} | all-time ${w['pnl_all']:,.0f}"
        lines.append(f'    ("{w["proxyWallet"]}", "{nickname}", "{reason}"),')
    lines.append("]")
    return "\n".join(lines) + "\n"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=15, help="Top N per window (default 15)")
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Overwrite src/whale_watching/seed_whales.py with the suggestion. "
        "Default: just print, let the user review and paste.",
    )
    args = ap.parse_args()

    api = PolymarketDataAPI()
    try:
        log.info("Fetching leaderboards...")
        monthly = await api.get_leaderboard(window="30d", limit=args.top * 3)
        historic = await api.get_leaderboard(window="all", limit=args.top * 3)
    finally:
        await api.close()

    if not monthly or not historic:
        log.error("Could not fetch leaderboards — abort")
        return

    consistent, m_only, h_only = merge_windows(monthly, historic, top_n=args.top)

    log.info("=" * 70)
    log.info(f"📊 LEADERBOARD SNAPSHOT @ {datetime.now():%Y-%m-%d %H:%M}")
    log.info("=" * 70)

    log.info(f"\n✅ Consistent winners (in BOTH 30d & all-time, PnL > 0): {len(consistent)}")
    for i, w in enumerate(consistent, 1):
        log.info(
            f"  {i:2}. {w['proxyWallet'][:12]}... {w['name']:<24} "
            f"30d=${w['pnl_30d']:>+12,.0f}  all=${w['pnl_all']:>+12,.0f}"
        )

    log.info(f"\n🆕 Hot this month only (top {min(5, len(m_only))} for context):")
    for w in m_only[:5]:
        log.info(f"   {w['address'][:12]}... {(w.get('name') or 'anon'):<24} 30d=${w['amount']:>+12,.0f}")

    rendered = render_seed(consistent)

    log.info("\n" + "=" * 70)
    log.info("📋 Suggested seed_whales.py (review before committing):")
    log.info("=" * 70 + "\n")
    print(rendered)

    if args.apply:
        target = "src/whale_watching/seed_whales.py"
        with open(target, "w") as f:
            f.write(rendered)
        log.info(f"✅ Wrote {target} ({len(consistent)} whales). Review with `git diff`.")


if __name__ == "__main__":
    asyncio.run(main())
