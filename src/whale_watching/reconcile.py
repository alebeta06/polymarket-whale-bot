"""
Paper-trade reconciliation.

For each open paper_trade:
- If the underlying market has resolved cleanly (closed + outcomePrices in {0,1}):
  set status to resolved_win/resolved_loss and write realized_pnl_usd.
- Otherwise: refresh unrealized_pnl_usd using the current bestBid (what we'd net
  by selling the position right now).
- If gamma returns no data for the conditionId: mark status='invalidated'.

Pure functions live alongside the I/O entry point so tests can hit them with
fixture market dicts (no network).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from loguru import logger as log

from .database import WhaleDatabase, PaperTrade
from .markets import (
    MarketsAPI,
    parse_outcome_prices,
    outcome_index,
    is_resolved,
)


@dataclass
class ReconciliationStats:
    open_before: int = 0
    resolved_win: int = 0
    resolved_loss: int = 0
    invalidated: int = 0
    still_open: int = 0
    realized_pnl_usd: float = 0.0
    unrealized_pnl_usd: float = 0.0
    errors: List[str] = field(default_factory=list)


def compute_realized_pnl_buy(copy_price: float, copy_shares: float, final_price: float) -> float:
    """For a BUY position: each share is now worth `final_price`. P&L = (final - entry) * shares."""
    return (final_price - copy_price) * copy_shares


def compute_unrealized_pnl_buy(copy_price: float, copy_shares: float, current_bid: float) -> float:
    """Mark-to-bid: what we'd net if we hit the best bid right now."""
    return (current_bid - copy_price) * copy_shares


def reconcile_one(trade: PaperTrade, market: Optional[dict]) -> Tuple[str, float, float, str]:
    """Pure: given a paper trade and (optional) market dict, return (new_status, realized, unrealized, reason).

    Does NOT touch the DB. Caller applies the result.
    """
    # The monitor only ever paper-trades BUY orders today. Belt-and-suspenders here.
    if trade.side != "BUY":
        return ("invalidated", 0.0, 0.0, f"non-BUY side {trade.side} not reconcilable")

    if market is None:
        return ("invalidated", 0.0, 0.0, "market not found in gamma")

    idx = outcome_index(market, trade.outcome)
    prices = parse_outcome_prices(market)
    if idx is None or prices is None or idx >= len(prices):
        return ("invalidated", 0.0, 0.0, "could not align outcome with market")

    if is_resolved(market):
        final_price = prices[idx]
        realized = compute_realized_pnl_buy(trade.copy_price, trade.copy_shares, final_price)
        # Outcome won iff its final price is ~1.
        won = abs(final_price - 1.0) < 1e-3
        return ("resolved_win" if won else "resolved_loss", realized, 0.0, "")

    # Mark-to-market with the best bid we'd get right now.
    raw_bid = market.get("bestBid")
    try:
        bid = float(raw_bid) if raw_bid is not None else prices[idx]
    except (TypeError, ValueError):
        bid = prices[idx]

    unreal = compute_unrealized_pnl_buy(trade.copy_price, trade.copy_shares, bid)
    return ("open", 0.0, unreal, "")


async def reconcile(db: WhaleDatabase, markets: MarketsAPI) -> ReconciliationStats:
    """Reconcile every open paper trade. One Gamma batch per ~25 distinct markets."""
    stats = ReconciliationStats()

    open_trades = db.get_open_paper_trades()
    stats.open_before = len(open_trades)
    if not open_trades:
        return stats

    cids = list({t.market_id for t in open_trades if t.market_id})
    market_data = await markets.get_markets(cids)

    now = datetime.now()
    for t in open_trades:
        try:
            new_status, realized, unrealized, reason = reconcile_one(t, market_data.get(t.market_id))
        except Exception as e:
            stats.errors.append(f"{t.id}: {e}")
            continue

        t.status = new_status
        t.realized_pnl_usd = realized
        t.unrealized_pnl_usd = unrealized
        t.last_reconciled_at = now

        if new_status == "resolved_win":
            stats.resolved_win += 1
            stats.realized_pnl_usd += realized
        elif new_status == "resolved_loss":
            stats.resolved_loss += 1
            stats.realized_pnl_usd += realized
        elif new_status == "invalidated":
            stats.invalidated += 1
            if reason:
                log.debug(f"Paper trade #{t.id} invalidated: {reason}")
        else:  # still open
            stats.still_open += 1
            stats.unrealized_pnl_usd += unrealized

    db.session.commit()
    return stats
