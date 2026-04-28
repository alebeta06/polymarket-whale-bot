"""Sizing decisions are pure math — exhaustive happy and edge cases."""
import pytest

from src.whale_watching.sizing import compute_copy_size, SizingDecision


def test_happy_path_15pct_of_whale():
    d = compute_copy_size(
        whale_notional_usd=10_000,
        available_balance_usd=100_000,
        current_price=0.50,
        copy_pct=0.15,
    )
    assert not d.skip
    assert d.copy_notional_usd == pytest.approx(1500.0)
    assert d.copy_shares == pytest.approx(3000.0)
    assert d.copy_price == 0.50


def test_balance_caps_target():
    d = compute_copy_size(
        whale_notional_usd=10_000,
        available_balance_usd=500,  # caps the 1500 target
        current_price=0.50,
        copy_pct=0.15,
    )
    assert not d.skip
    assert d.copy_notional_usd == 500.0
    assert d.copy_shares == 1000.0


def test_max_per_trade_caps_target():
    d = compute_copy_size(
        whale_notional_usd=100_000,
        available_balance_usd=100_000,
        current_price=0.50,
        copy_pct=0.15,
        max_per_trade_usd=200.0,
    )
    assert not d.skip
    assert d.copy_notional_usd == 200.0


def test_skip_below_min_order():
    d = compute_copy_size(
        whale_notional_usd=20,
        available_balance_usd=1000,
        current_price=0.27,
        copy_pct=0.15,
    )
    assert d.skip
    assert "below min order" in d.reason


def test_skip_zero_balance():
    d = compute_copy_size(
        whale_notional_usd=10_000,
        available_balance_usd=0,
        current_price=0.50,
        copy_pct=0.15,
    )
    assert d.skip
    assert "balance" in d.reason


def test_skip_negative_balance():
    d = compute_copy_size(
        whale_notional_usd=10_000,
        available_balance_usd=-5,
        current_price=0.50,
        copy_pct=0.15,
    )
    assert d.skip


@pytest.mark.parametrize("price", [0.0, 1.0, -0.1, 1.5])
def test_skip_degenerate_price(price):
    d = compute_copy_size(
        whale_notional_usd=10_000,
        available_balance_usd=1000,
        current_price=price,
        copy_pct=0.15,
    )
    assert d.skip
    assert "price" in d.reason


@pytest.mark.parametrize("pct", [0, -0.1, 1.5, 2.0])
def test_skip_invalid_copy_pct(pct):
    d = compute_copy_size(
        whale_notional_usd=10_000,
        available_balance_usd=1000,
        current_price=0.5,
        copy_pct=pct,
    )
    assert d.skip
    assert "copy_pct" in d.reason


def test_skip_zero_whale_notional():
    d = compute_copy_size(
        whale_notional_usd=0,
        available_balance_usd=1000,
        current_price=0.5,
        copy_pct=0.15,
    )
    assert d.skip


def test_min_order_threshold_inclusive():
    """At exactly min_order_usd we accept; at min_order_usd - epsilon we skip."""
    accept = compute_copy_size(
        whale_notional_usd=100,
        available_balance_usd=1000,
        current_price=0.5,
        copy_pct=0.05,  # 5 USD target == default min
        min_order_usd=5.0,
    )
    assert not accept.skip

    skip = compute_copy_size(
        whale_notional_usd=100,
        available_balance_usd=1000,
        current_price=0.5,
        copy_pct=0.04,  # 4 USD target
        min_order_usd=5.0,
    )
    assert skip.skip
