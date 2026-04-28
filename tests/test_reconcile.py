"""Reconciliation logic — pure functions exercised with synthetic market dicts."""
import json
import pytest

from src.whale_watching.database import PaperTrade
from src.whale_watching.reconcile import (
    reconcile_one,
    compute_realized_pnl_buy,
    compute_unrealized_pnl_buy,
)
from src.whale_watching.markets import (
    parse_outcome_prices,
    parse_outcomes,
    outcome_index,
    is_resolved,
)


# ---------- markets helpers --------------------------------------------------

def test_parse_outcome_prices_handles_json_string():
    assert parse_outcome_prices({"outcomePrices": '["0.7", "0.3"]'}) == [0.7, 0.3]


def test_parse_outcome_prices_handles_already_parsed_list():
    assert parse_outcome_prices({"outcomePrices": [0.7, 0.3]}) == [0.7, 0.3]


def test_parse_outcome_prices_returns_none_on_garbage():
    assert parse_outcome_prices({"outcomePrices": "not json"}) is None
    assert parse_outcome_prices({}) is None


def test_outcome_index_case_insensitive():
    m = {"outcomes": '["Yes", "No"]'}
    assert outcome_index(m, "YES") == 0
    assert outcome_index(m, "no") == 1
    assert outcome_index(m, "Maybe") is None


def test_is_resolved_requires_clean_settlement():
    # Settled YES.
    assert is_resolved({"closed": True, "outcomePrices": '["1", "0"]'})
    # Settled NO.
    assert is_resolved({"closed": True, "outcomePrices": '["0", "1"]'})
    # Closed but mid-range (UMA dispute) → not yet settled.
    assert not is_resolved({"closed": True, "outcomePrices": '["0.5", "0.5"]'})
    # Live market.
    assert not is_resolved({"closed": False, "outcomePrices": '["0.7", "0.3"]'})
    # Closed without outcome prices yet.
    assert not is_resolved({"closed": True})


# ---------- reconcile_one ---------------------------------------------------

def _trade(side="BUY", outcome="YES", price=0.4, shares=500.0, market_id="m1"):
    """Lightweight PaperTrade-shaped object — uses the real model so attributes match."""
    return PaperTrade(
        whale_address="0x" + "ab" * 20,
        market_id=market_id,
        outcome=outcome,
        side=side,
        copy_notional_usd=price * shares,
        copy_shares=shares,
        copy_price=price,
        whale_size_shares=shares * 10,
        whale_price=price,
        whale_notional_usd=price * shares * 10,
        whale_tx_hash="0xtest",
        status="open",
        realized_pnl_usd=0.0,
        unrealized_pnl_usd=0.0,
        asset_id="",
    )


def test_reconcile_one_resolved_win():
    """BUY YES @ 0.4, market resolved YES → P&L = (1 - 0.4) * 500 = 300."""
    market = {"closed": True, "outcomes": '["Yes","No"]', "outcomePrices": '["1","0"]'}
    status, realized, unreal, _ = reconcile_one(_trade(outcome="YES"), market)
    assert status == "resolved_win"
    assert realized == pytest.approx(300.0)
    assert unreal == 0.0


def test_reconcile_one_resolved_loss():
    """BUY YES @ 0.4, market resolved NO → P&L = (0 - 0.4) * 500 = -200."""
    market = {"closed": True, "outcomes": '["Yes","No"]', "outcomePrices": '["0","1"]'}
    status, realized, unreal, _ = reconcile_one(_trade(outcome="YES"), market)
    assert status == "resolved_loss"
    assert realized == pytest.approx(-200.0)
    assert unreal == 0.0


def test_reconcile_one_open_uses_best_bid_for_unrealized():
    """Live market → mark-to-market with bestBid."""
    market = {
        "closed": False,
        "outcomes": '["Yes","No"]',
        "outcomePrices": '["0.55","0.45"]',
        "bestBid": "0.50",
    }
    status, realized, unreal, _ = reconcile_one(_trade(price=0.4, shares=500), market)
    assert status == "open"
    assert realized == 0.0
    # (0.50 - 0.40) * 500 = 50
    assert unreal == pytest.approx(50.0)


def test_reconcile_one_open_falls_back_to_outcome_price_without_bid():
    market = {
        "closed": False,
        "outcomes": '["Yes","No"]',
        "outcomePrices": '["0.55","0.45"]',
    }
    _, _, unreal, _ = reconcile_one(_trade(price=0.4, shares=500), market)
    # (0.55 - 0.40) * 500 = 75
    assert unreal == pytest.approx(75.0)


def test_reconcile_one_missing_market_invalidates():
    status, realized, unreal, reason = reconcile_one(_trade(), market=None)
    assert status == "invalidated"
    assert realized == 0.0 and unreal == 0.0
    assert "not found" in reason


def test_reconcile_one_outcome_mismatch_invalidates():
    market = {"closed": True, "outcomes": '["A","B"]', "outcomePrices": '["1","0"]'}
    status, *_ = reconcile_one(_trade(outcome="YES"), market)
    assert status == "invalidated"


def test_reconcile_one_non_buy_invalidates():
    market = {"closed": True, "outcomes": '["Yes","No"]', "outcomePrices": '["1","0"]'}
    status, *_ = reconcile_one(_trade(side="SELL", outcome="YES"), market)
    assert status == "invalidated"


# ---------- pnl helpers (sanity) --------------------------------------------

def test_pnl_helpers():
    assert compute_realized_pnl_buy(0.4, 500, 1.0) == pytest.approx(300.0)
    assert compute_realized_pnl_buy(0.4, 500, 0.0) == pytest.approx(-200.0)
    assert compute_unrealized_pnl_buy(0.4, 500, 0.5) == pytest.approx(50.0)
    assert compute_unrealized_pnl_buy(0.4, 500, 0.3) == pytest.approx(-50.0)
