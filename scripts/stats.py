#!/usr/bin/env python
"""Paper-trading stats — what to look at before flipping DRY_RUN to false.

Reports:
  - Overall: total trades, resolved win-rate, realized + unrealized P&L, ROI.
  - Equity curve: max drawdown computed over chronological resolved trades.
  - Per whale: trades / win-rate / realized P&L.

Usage:
    PYTHONPATH=. python scripts/stats.py
"""
from collections import defaultdict
from typing import List

from src.config import get_settings
from src.whale_watching.database import WhaleDatabase, PaperTrade


RESOLVED_STATUSES = {"resolved_win", "resolved_loss"}


def max_drawdown(equity_curve: List[float]) -> float:
    """Largest peak-to-trough drop in the equity curve, as a positive USD figure."""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    worst = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        worst = max(worst, peak - v)
    return worst


def main():
    s = get_settings()
    starting = s.paper_starting_balance_usd
    db = WhaleDatabase("data/whales.db")

    all_trades = db.session.query(PaperTrade).order_by(PaperTrade.timestamp.asc()).all()
    if not all_trades:
        print("No paper trades yet. Run scripts/whale_watcher.py first.")
        db.close()
        return

    open_trades = [t for t in all_trades if t.status == "open"]
    resolved = [t for t in all_trades if t.status in RESOLVED_STATUSES]
    invalidated = [t for t in all_trades if t.status == "invalidated"]

    wins = [t for t in resolved if t.status == "resolved_win"]
    realized = sum(t.realized_pnl_usd for t in resolved)
    unrealized = sum(t.unrealized_pnl_usd for t in open_trades)
    win_rate = (len(wins) / len(resolved)) if resolved else 0.0
    roi = ((realized + unrealized) / starting) if starting > 0 else 0.0

    # Equity curve = starting balance + cumulative realized P&L over time.
    equity = [starting]
    for t in resolved:
        equity.append(equity[-1] + t.realized_pnl_usd)
    dd = max_drawdown(equity)
    dd_pct = (dd / starting) if starting > 0 else 0.0

    print("\n" + "=" * 70)
    print("📊 PAPER TRADING REPORT")
    print("=" * 70)
    print(f"Starting balance:      ${starting:>12,.2f}")
    print(f"Realized P&L:          ${realized:>+12,.2f}")
    print(f"Unrealized P&L:        ${unrealized:>+12,.2f}")
    print(f"Total equity (paper):  ${starting + realized + unrealized:>12,.2f}")
    print(f"ROI:                   {roi:>+12.2%}")
    print(f"Max drawdown:          ${dd:>12,.2f}  ({dd_pct:.2%})")
    print()
    print(f"Trades total:    {len(all_trades)}")
    print(f"  open:          {len(open_trades)}")
    print(f"  resolved:      {len(resolved)} (win-rate {win_rate:.1%}, target ≥60%)")
    print(f"    wins:        {len(wins)}")
    print(f"    losses:      {len(resolved) - len(wins)}")
    print(f"  invalidated:   {len(invalidated)}")

    # Per-whale breakdown.
    by_whale = defaultdict(lambda: {"n": 0, "wins": 0, "losses": 0, "realized": 0.0, "open": 0})
    for t in all_trades:
        b = by_whale[t.whale_address]
        b["n"] += 1
        if t.status == "resolved_win":
            b["wins"] += 1
            b["realized"] += t.realized_pnl_usd
        elif t.status == "resolved_loss":
            b["losses"] += 1
            b["realized"] += t.realized_pnl_usd
        elif t.status == "open":
            b["open"] += 1

    print("\n" + "-" * 70)
    print("Per-whale breakdown:")
    print("-" * 70)
    print(f"  {'address':<14} {'trades':>6} {'open':>5} {'W':>3} {'L':>3} {'win%':>6} {'realized':>12}")
    rows = sorted(by_whale.items(), key=lambda kv: kv[1]["realized"], reverse=True)
    for addr, b in rows:
        decided = b["wins"] + b["losses"]
        wr = (b["wins"] / decided) if decided else 0.0
        print(
            f"  {addr[:12]}.. {b['n']:>6} {b['open']:>5} "
            f"{b['wins']:>3} {b['losses']:>3} {wr:>5.0%} "
            f"${b['realized']:>+11,.2f}"
        )

    print("=" * 70 + "\n")
    db.close()


if __name__ == "__main__":
    main()
