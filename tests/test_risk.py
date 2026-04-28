"""Risk gating — first failure short-circuits, in priority order."""
import pytest

from src.whale_watching.risk import (
    RiskContext,
    RiskLimits,
    FilterDecision,
    evaluate,
)


@pytest.fixture
def limits():
    return RiskLimits(
        min_whale_notional_usd=500.0,
        max_whale_notional_usd=None,
        max_trade_age_seconds=600.0,
        min_market_volume_usd=10_000.0,
        min_seconds_to_expiry=3600.0,
        daily_stop_loss_pct=0.10,
    )


def test_happy_path(limits):
    ctx = RiskContext(
        whale_notional_usd=2500,
        trade_age_seconds=30,
        market_volume_usd=50_000,
        market_seconds_to_expiry=86_400,
    )
    assert evaluate(ctx, limits) == FilterDecision(skip=False)


def test_dust_blocked(limits):
    ctx = RiskContext(whale_notional_usd=100, trade_age_seconds=10)
    d = evaluate(ctx, limits)
    assert d.skip and "below min" in d.reason


def test_max_whale_notional_blocked():
    limits = RiskLimits(max_whale_notional_usd=10_000)
    ctx = RiskContext(whale_notional_usd=20_000, trade_age_seconds=10)
    d = evaluate(ctx, limits)
    assert d.skip and "above max" in d.reason


def test_stale_trade_blocked(limits):
    ctx = RiskContext(whale_notional_usd=2500, trade_age_seconds=900)
    d = evaluate(ctx, limits)
    assert d.skip and "old" in d.reason


def test_thin_market_blocked(limits):
    ctx = RiskContext(
        whale_notional_usd=2500, trade_age_seconds=10, market_volume_usd=500
    )
    d = evaluate(ctx, limits)
    assert d.skip and "volume" in d.reason


def test_market_expiring_blocked(limits):
    ctx = RiskContext(
        whale_notional_usd=2500,
        trade_age_seconds=10,
        market_volume_usd=50_000,
        market_seconds_to_expiry=300,
    )
    d = evaluate(ctx, limits)
    assert d.skip and "expires" in d.reason


def test_daily_stop_loss_short_circuits(limits):
    """Stop-loss must take precedence even over an otherwise-perfect trade."""
    ctx = RiskContext(
        whale_notional_usd=2500,
        trade_age_seconds=10,
        market_volume_usd=50_000,
        market_seconds_to_expiry=86_400,
        daily_pnl_pct=-0.12,
    )
    d = evaluate(ctx, limits)
    assert d.skip and "stop-loss" in d.reason


def test_optional_market_fields_pass_when_none(limits):
    """Missing market metadata = no opinion, not auto-block."""
    ctx = RiskContext(
        whale_notional_usd=2500,
        trade_age_seconds=10,
        market_volume_usd=None,
        market_seconds_to_expiry=None,
    )
    assert not evaluate(ctx, limits).skip


def test_stop_loss_uses_abs_value(limits):
    """Caller may set daily_stop_loss_pct as positive 0.10; -0.10 should also trigger."""
    limits = RiskLimits(daily_stop_loss_pct=-0.10)
    ctx = RiskContext(whale_notional_usd=2500, trade_age_seconds=10, daily_pnl_pct=-0.10)
    assert evaluate(ctx, limits).skip
