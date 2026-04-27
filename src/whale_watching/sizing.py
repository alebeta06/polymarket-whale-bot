"""
Position sizing for whale copy trading.

Pure math, no I/O. The caller is responsible for fetching the whale's notional,
the current market price, and the bot's USDC balance. This module only decides
how big the copy order should be (in USD and in shares) given those inputs.
"""
from dataclasses import dataclass
from typing import Optional


# Polymarket's minimum order size in USD notional (≈5 USDC historically).
# Below this the CLOB rejects the order, so we'd rather skip than thrash.
DEFAULT_MIN_ORDER_USD = 5.0


@dataclass(frozen=True)
class SizingDecision:
    """Outcome of sizing a copy trade.

    skip=True means do not place an order; `reason` explains why (for logs / paper trades).
    skip=False means place a `copy_shares` order at `copy_price`, worth `copy_notional_usd`.
    """
    skip: bool
    reason: str = ""
    copy_notional_usd: float = 0.0
    copy_shares: float = 0.0
    copy_price: float = 0.0


def compute_copy_size(
    whale_notional_usd: float,
    available_balance_usd: float,
    *,
    current_price: float,
    copy_pct: float,
    min_order_usd: float = DEFAULT_MIN_ORDER_USD,
    max_per_trade_usd: Optional[float] = None,
) -> SizingDecision:
    """Decide the size of a copy trade mirroring a whale's bet.

    Args:
        whale_notional_usd: USD notional of the whale's trade (shares * fill_price).
        available_balance_usd: USDC available to the bot's proxy wallet right now.
        current_price: Current price (probability, 0–1) for the same outcome on
            the same market — NOT the whale's fill price. We size in shares using
            this so we don't over- or under-allocate when the market has moved.
        copy_pct: Fraction of the whale's notional to mirror (e.g., 0.15 = 15%).
        min_order_usd: Skip if the resulting order is below this notional.
        max_per_trade_usd: Optional hard cap per single copy trade.

    Returns:
        SizingDecision with skip flag, reason, and (if not skipped) the size to place.
    """
    if copy_pct <= 0 or copy_pct > 1:
        return SizingDecision(skip=True, reason=f"invalid copy_pct={copy_pct}")
    if whale_notional_usd <= 0:
        return SizingDecision(skip=True, reason="whale notional <= 0")
    if current_price <= 0 or current_price >= 1:
        # Polymarket prices are probabilities in (0, 1). 0 or 1 means the outcome
        # is already settled — copying makes no sense.
        return SizingDecision(skip=True, reason=f"degenerate price={current_price}")
    if available_balance_usd <= 0:
        return SizingDecision(skip=True, reason="zero balance")

    target = whale_notional_usd * copy_pct
    target = min(target, available_balance_usd)
    if max_per_trade_usd is not None:
        target = min(target, max_per_trade_usd)

    if target < min_order_usd:
        return SizingDecision(
            skip=True,
            reason=f"target ${target:.2f} below min order ${min_order_usd:.2f}",
        )

    shares = target / current_price
    return SizingDecision(
        skip=False,
        copy_notional_usd=round(target, 4),
        copy_shares=round(shares, 4),
        copy_price=current_price,
    )
