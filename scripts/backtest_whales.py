#!/usr/bin/env python
"""Whale copy-trading backtest.

Decision model (validated with the user 2026-04-29):
  - Sizing : min(15% * whale_notional, 5% * $1000 = $50)
  - Exit   : hold-to-resolution (ignore the whale's SELLs)
  - Fill   : optimistic — assume we fill at the whale's price (no slippage)
            Slippage levels 0/1/2/5% are explored as sensitivity analysis below.

Pipeline:
  1. For each whale, pull up to TRADES_LIMIT recent trades.
  2. Keep only BUYs. Compute a sized "copy" per trade.
  3. Batch-fetch market metadata from Gamma.
  4. Reuse `reconcile_one` for the realized / unrealized P&L math.
  5. Aggregate per-whale and globally + show sensitivity to slippage.

Usage:
    PYTHONPATH=. python scripts/backtest_whales.py
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from src.whale_watching.data_api import PolymarketDataAPI
from src.whale_watching.markets import MarketsAPI
from src.whale_watching.reconcile import reconcile_one
from src.whale_watching.seed_whales import SEED_WHALES
from src.whale_watching.sizing import compute_copy_size


# Backtest parameters (per the validated decision model).
STARTING_BALANCE_USD = 1000.0
COPY_PCT = 0.15
MAX_PER_TRADE_USD = STARTING_BALANCE_USD * 0.05  # $50 cap → "5% of own capital"
TRADES_LIMIT = 1000

# Whales excluded from the post-filter run because their first-pass ROI was
# negative. Kept here (not removed from SEED_WHALES) so we can still see them
# in the unfiltered run if we want to re-evaluate later.
EXCLUDED_WHALES = {
    "0x507e52ef684ca2dd91f90a9d26d149dd3288beae",  # GamblingIsAllYouNeed: -5.5% ROI
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf",  # sovereign2013:        -7.6% ROI
}

# Slippage levels (decimal) to test. 0 = optimistic baseline.
# Buying at price p with slippage s means we actually paid p*(1+s).
SLIPPAGE_LEVELS = [0.0, 0.01, 0.02, 0.05]


@dataclass
class FakePaperTrade:
    """Stand-in for the SQLAlchemy PaperTrade. `reconcile_one` only reads attrs."""
    side: str
    outcome: str
    copy_price: float
    copy_shares: float


@dataclass
class WhaleResult:
    address: str
    nickname: str
    trades_total: int = 0
    trades_buy: int = 0
    trades_sized_in: int = 0
    trades_resolved: int = 0
    trades_open: int = 0
    trades_invalidated: int = 0
    wins: int = 0
    losses: int = 0
    invested_usd: float = 0.0
    realized_pnl_usd: float = 0.0
    unrealized_pnl_usd: float = 0.0
    skip_reasons: Dict[str, int] = field(default_factory=dict)
    oldest_trade_ts: float = 0.0
    newest_trade_ts: float = 0.0
    # Per-trade resolved P&Ls — used for avg win/loss, profit factor, concentration.
    resolved_pnls: List[float] = field(default_factory=list)


def fmt_usd(x: float) -> str:
    sign = "-" if x < 0 else " "
    return f"{sign}${abs(x):>9,.2f}"


def fmt_pct(num: float, den: float) -> str:
    return f"{100*num/den:5.1f}%" if den else "  n/a"


def fmt_date(ts: float) -> str:
    if not ts:
        return "n/a"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


async def collect_whale_trades(api: PolymarketDataAPI, exclude: set) -> List[tuple]:
    """Fetch trades for every seed whale not in the exclusion set."""
    out = []
    for address, nickname, _reason in SEED_WHALES:
        addr = address.lower()
        if addr in exclude:
            continue
        trades = await api.get_user_trades(addr, limit=TRADES_LIMIT)
        out.append((addr, nickname, trades))
    return out


def backtest_whale(
    address: str,
    nickname: str,
    trades: List[dict],
    market_data: Dict[str, dict],
    slippage: float,
) -> WhaleResult:
    r = WhaleResult(address=address, nickname=nickname)
    r.trades_total = len(trades)

    timestamps = [float(t.get("timestamp", 0) or 0) for t in trades if float(t.get("timestamp", 0) or 0) > 0]
    if timestamps:
        r.oldest_trade_ts = min(timestamps)
        r.newest_trade_ts = max(timestamps)

    for t in trades:
        side = (t.get("side") or "").upper()
        if side != "BUY":
            continue
        r.trades_buy += 1

        try:
            whale_shares = float(t.get("size") or 0)
            whale_price = float(t.get("price") or 0)
        except (TypeError, ValueError):
            continue
        whale_notional = whale_shares * whale_price
        outcome = (t.get("outcome") or "").strip().upper() or "UNKNOWN"
        market_id = t.get("conditionId")
        if not market_id:
            continue

        # Apply slippage: we actually pay a worse price than the whale.
        # Cap at <1.0 because Polymarket prices are probabilities.
        effective_price = min(0.999, whale_price * (1.0 + slippage))

        sizing = compute_copy_size(
            whale_notional_usd=whale_notional,
            available_balance_usd=STARTING_BALANCE_USD,
            current_price=effective_price,
            copy_pct=COPY_PCT,
            max_per_trade_usd=MAX_PER_TRADE_USD,
        )
        if sizing.skip:
            r.skip_reasons[sizing.reason] = r.skip_reasons.get(sizing.reason, 0) + 1
            continue
        r.trades_sized_in += 1
        r.invested_usd += sizing.copy_notional_usd

        fake = FakePaperTrade(
            side="BUY",
            outcome=outcome,
            copy_price=sizing.copy_price,
            copy_shares=sizing.copy_shares,
        )
        market = market_data.get(market_id)
        new_status, realized, unrealized, _reason = reconcile_one(fake, market)

        if new_status == "resolved_win":
            r.trades_resolved += 1
            r.wins += 1
            r.realized_pnl_usd += realized
            r.resolved_pnls.append(realized)
        elif new_status == "resolved_loss":
            r.trades_resolved += 1
            r.losses += 1
            r.realized_pnl_usd += realized
            r.resolved_pnls.append(realized)
        elif new_status == "invalidated":
            r.trades_invalidated += 1
        else:  # "open"
            r.trades_open += 1
            r.unrealized_pnl_usd += unrealized

    return r


def quality_metrics(r: WhaleResult) -> dict:
    """Per-whale derived metrics: avg win, avg loss, profit factor, concentration."""
    wins = [p for p in r.resolved_pnls if p > 0]
    losses = [p for p in r.resolved_pnls if p < 0]
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0  # negative
    sum_wins = sum(wins)
    sum_losses = abs(sum(losses))
    profit_factor = (sum_wins / sum_losses) if sum_losses > 0 else float("inf") if sum_wins > 0 else 0.0
    # Concentration: of all positive P&L, what fraction came from the top 5 wins?
    if wins:
        top5 = sum(sorted(wins, reverse=True)[:5])
        concentration = top5 / sum_wins
    else:
        concentration = 0.0
    return {
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "top5_concentration": concentration,
    }


def print_per_whale(results: List[WhaleResult], slippage: float):
    print(f"\n{'='*120}")
    print(f"PER-WHALE RESULTS (slippage={slippage:.1%})")
    print(f"{'='*120}")
    header = (
        f"{'Whale':<22} {'Span':<24} {'Sized':>5} {'Resv':>5} "
        f"{'WR%':>6} {'Avg Win':>9} {'Avg Loss':>9} {'PF':>5} "
        f"{'Top5%':>6} {'Realized':>11} {'ROI%':>7}"
    )
    print(header)
    print("-" * 120)

    for r in sorted(results, key=lambda x: x.realized_pnl_usd, reverse=True):
        m = quality_metrics(r)
        span = f"{fmt_date(r.oldest_trade_ts)}→{fmt_date(r.newest_trade_ts)}"
        wr = fmt_pct(r.wins, r.trades_resolved)
        roi = fmt_pct(r.realized_pnl_usd, r.invested_usd) if r.invested_usd else "  n/a"
        pf_str = "  inf" if m["profit_factor"] == float("inf") else f"{m['profit_factor']:5.2f}"
        print(
            f"{r.nickname[:22]:<22} {span:<24} "
            f"{r.trades_sized_in:>5} {r.trades_resolved:>5} "
            f"{wr:>6} {fmt_usd(m['avg_win']):>9} {fmt_usd(m['avg_loss']):>9} "
            f"{pf_str:>5} {100*m['top5_concentration']:5.1f}% "
            f"{fmt_usd(r.realized_pnl_usd)} {roi:>7}"
        )


def global_aggregate(results: List[WhaleResult]) -> dict:
    return {
        "buys": sum(r.trades_buy for r in results),
        "sized": sum(r.trades_sized_in for r in results),
        "resolved": sum(r.trades_resolved for r in results),
        "open": sum(r.trades_open for r in results),
        "invalid": sum(r.trades_invalidated for r in results),
        "wins": sum(r.wins for r in results),
        "losses": sum(r.losses for r in results),
        "invested": sum(r.invested_usd for r in results),
        "realized": sum(r.realized_pnl_usd for r in results),
        "unrealized": sum(r.unrealized_pnl_usd for r in results),
    }


def print_global(agg: dict, slippage: float):
    print(f"\n  GLOBAL @ slippage={slippage:.1%}:")
    wr = fmt_pct(agg["wins"], agg["resolved"])
    roi = fmt_pct(agg["realized"], agg["invested"])
    print(f"    Resolved        : {agg['resolved']}  (W {agg['wins']} / L {agg['losses']})  WR={wr}")
    print(f"    Invested        : ${agg['invested']:,.2f}")
    print(f"    Realized P&L    : ${agg['realized']:,.2f}  (ROI {roi})")
    print(f"    Unrealized      : ${agg['unrealized']:,.2f}")
    print(f"    Combined        : ${agg['realized'] + agg['unrealized']:,.2f}")


def print_skip_summary(results: List[WhaleResult]):
    """Bucket the per-amount 'below min order' messages so the output is readable."""
    buckets: Dict[str, int] = {}
    for r in results:
        for reason, n in r.skip_reasons.items():
            if "below min order" in reason:
                bucket = "target below min order ($5)"
            elif "degenerate price" in reason:
                bucket = "degenerate price (=0 or =1)"
            else:
                bucket = reason
            buckets[bucket] = buckets.get(bucket, 0) + n
    if not buckets:
        return
    print(f"\nSizing skip reasons (aggregate):")
    for reason, n in sorted(buckets.items(), key=lambda x: -x[1]):
        print(f"  {n:>5}  {reason}")


def print_slippage_sensitivity(rows: List[Tuple[float, dict]]):
    """How does the global ROI hold up as slippage rises?"""
    print(f"\n{'='*120}")
    print("SLIPPAGE SENSITIVITY (global aggregate, post-filter)")
    print(f"{'='*120}")
    print(f"  {'Slip':>6}  {'Sized':>6}  {'Resolved':>9}  {'WR%':>6}  {'Invested':>12}  {'Realized':>11}  {'ROI%':>7}")
    print("  " + "-" * 70)
    for slip, agg in rows:
        wr = fmt_pct(agg["wins"], agg["resolved"])
        roi = fmt_pct(agg["realized"], agg["invested"])
        print(
            f"  {slip:>5.1%}  {agg['sized']:>6}  {agg['resolved']:>9}  "
            f"{wr:>6}  ${agg['invested']:>11,.2f}  {fmt_usd(agg['realized']):>11}  {roi:>7}"
        )


async def main():
    print(f"Backtest config: capital=${STARTING_BALANCE_USD:.0f}, copy_pct={COPY_PCT:.0%}, "
          f"per_trade_cap=${MAX_PER_TRADE_USD:.0f}, trades_limit={TRADES_LIMIT}")
    print(f"Whales in seed: {len(SEED_WHALES)}, excluded: {len(EXCLUDED_WHALES)} (negative ROI in pass 1)")

    data_api = PolymarketDataAPI()
    markets_api = MarketsAPI()
    try:
        whale_trades = await collect_whale_trades(data_api, EXCLUDED_WHALES)
        print(f"Running on {len(whale_trades)} whales (post-filter).")

        all_cids = {
            t.get("conditionId")
            for _addr, _nick, trades in whale_trades
            for t in trades
            if t.get("conditionId")
        }
        print(f"Unique markets: {len(all_cids)}. Fetching from Gamma...")
        market_data = await markets_api.get_markets(list(all_cids))
        print(f"Gamma returned {len(market_data)} / {len(all_cids)} markets.")
    finally:
        await data_api.close()
        await markets_api.close()

    # Run the backtest at each slippage level. Whale data is reused across runs.
    sensitivity: List[Tuple[float, dict]] = []
    headline_results: Optional[List[WhaleResult]] = None
    for slip in SLIPPAGE_LEVELS:
        results = [
            backtest_whale(addr, nick, trades, market_data, slip)
            for addr, nick, trades in whale_trades
        ]
        agg = global_aggregate(results)
        sensitivity.append((slip, agg))
        if slip == 0.0:
            headline_results = results

    # Detailed per-whale view at slippage=0 (cleanest picture, headline).
    assert headline_results is not None
    print_per_whale(headline_results, slippage=0.0)
    print_skip_summary(headline_results)
    print_slippage_sensitivity(sensitivity)


if __name__ == "__main__":
    asyncio.run(main())
