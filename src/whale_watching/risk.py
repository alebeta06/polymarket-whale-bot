"""
Risk filters for whale copy trading.

Pure-function gating: given a candidate whale trade and the bot's current state,
decide whether we should consider copying it. No I/O — the caller resolves any
market metadata or PnL inputs and feeds them in as RiskContext.
"""
from dataclasses import dataclass
from typing import Optional


# Trades older than this when we observe them are stale: the price has likely
# moved and copying ceases to mirror the whale's actual entry. Tunable per call.
DEFAULT_MAX_TRADE_AGE_SECONDS = 600.0  # 10 minutes


@dataclass(frozen=True)
class RiskContext:
    """Resolved inputs for a single candidate trade.

    Optional fields are skipped (treated as "no opinion") when None — that lets
    callers add gating progressively without rewriting every call site.
    """
    whale_notional_usd: float
    trade_age_seconds: float
    market_volume_usd: Optional[float] = None
    market_seconds_to_expiry: Optional[float] = None
    daily_pnl_pct: float = 0.0  # signed, e.g. -0.04 means down 4% today


@dataclass(frozen=True)
class RiskLimits:
    """Static limits, normally sourced from Settings / env."""
    min_whale_notional_usd: float = 500.0
    max_whale_notional_usd: Optional[float] = None
    max_trade_age_seconds: float = DEFAULT_MAX_TRADE_AGE_SECONDS
    min_market_volume_usd: Optional[float] = None
    min_seconds_to_expiry: Optional[float] = None
    # Positive value, e.g. 0.10 means halt copying after a 10% drawdown today.
    daily_stop_loss_pct: float = 0.10


@dataclass(frozen=True)
class FilterDecision:
    skip: bool
    reason: str = ""


def evaluate(ctx: RiskContext, limits: RiskLimits) -> FilterDecision:
    """Run all gates in priority order. First failure short-circuits."""

    # Daily stop-loss takes precedence: if we're bleeding today, skip everything.
    if ctx.daily_pnl_pct <= -abs(limits.daily_stop_loss_pct):
        return FilterDecision(
            skip=True,
            reason=f"daily stop-loss hit ({ctx.daily_pnl_pct:.1%} <= -{limits.daily_stop_loss_pct:.1%})",
        )

    if ctx.whale_notional_usd < limits.min_whale_notional_usd:
        return FilterDecision(
            skip=True,
            reason=f"whale notional ${ctx.whale_notional_usd:,.2f} below min ${limits.min_whale_notional_usd:,.2f}",
        )

    if (
        limits.max_whale_notional_usd is not None
        and ctx.whale_notional_usd > limits.max_whale_notional_usd
    ):
        return FilterDecision(
            skip=True,
            reason=f"whale notional ${ctx.whale_notional_usd:,.2f} above max ${limits.max_whale_notional_usd:,.2f}",
        )

    if ctx.trade_age_seconds > limits.max_trade_age_seconds:
        return FilterDecision(
            skip=True,
            reason=f"trade {ctx.trade_age_seconds:.0f}s old (> {limits.max_trade_age_seconds:.0f}s)",
        )

    if (
        limits.min_market_volume_usd is not None
        and ctx.market_volume_usd is not None
        and ctx.market_volume_usd < limits.min_market_volume_usd
    ):
        return FilterDecision(
            skip=True,
            reason=f"market volume ${ctx.market_volume_usd:,.0f} below min ${limits.min_market_volume_usd:,.0f}",
        )

    if (
        limits.min_seconds_to_expiry is not None
        and ctx.market_seconds_to_expiry is not None
        and ctx.market_seconds_to_expiry < limits.min_seconds_to_expiry
    ):
        return FilterDecision(
            skip=True,
            reason=f"market expires in {ctx.market_seconds_to_expiry:.0f}s (< {limits.min_seconds_to_expiry:.0f}s)",
        )

    return FilterDecision(skip=False)
