"""WhaleDatabase CRUD on a tmp SQLite — covers the bug-prone paths.

Specifically guards against the regressions we already hit and fixed:
- ensure_trader must NOT inflate total_trades each call (the old
  add_or_update_trader(addr, 0.0) bug from load_whales).
- last_seen_trade_ts must persist and be monotonic.
- Idempotent ALTER TABLE migration must not fail on a fresh DB.
"""
import pytest

from src.whale_watching.database import (
    WhaleDatabase,
    ObservedTrader,
    ObservedTrade,
    PaperTrade,
)

ADDR = "0x" + "ab" * 20  # any valid-shape address


def test_ensure_trader_is_idempotent_and_no_phantom_trades(db):
    db.ensure_trader(ADDR)
    db.ensure_trader(ADDR)
    db.ensure_trader(ADDR)
    t = db.get_trader_stats(ADDR)
    assert t is not None
    assert t.total_trades == 0  # never inflated by ensure_trader
    assert t.total_volume == 0.0


def test_record_trade_increments_counters(db):
    db.ensure_trader(ADDR)
    db.record_trade(ADDR, market_id="m1", outcome="YES", side="BUY", size=1000.0, price=0.4)
    db.record_trade(ADDR, market_id="m2", outcome="NO", side="SELL", size=500.0, price=0.6)
    t = db.get_trader_stats(ADDR)
    assert t.total_trades == 2
    assert t.total_volume == pytest.approx(1500.0)
    assert t.largest_trade == pytest.approx(1000.0)


def test_last_seen_trade_ts_round_trip(db):
    db.ensure_trader(ADDR)
    assert db.get_last_seen_trade_ts(ADDR) is None  # unset → None
    db.set_last_seen_trade_ts(ADDR, 1_700_000_000.0)
    assert db.get_last_seen_trade_ts(ADDR) == 1_700_000_000.0


def test_last_seen_trade_ts_is_monotonic(db):
    db.ensure_trader(ADDR)
    db.set_last_seen_trade_ts(ADDR, 1_700_000_100.0)
    db.set_last_seen_trade_ts(ADDR, 1_700_000_050.0)  # backwards — must be ignored
    assert db.get_last_seen_trade_ts(ADDR) == 1_700_000_100.0


def test_last_seen_trade_ts_unknown_address_is_noop(db):
    # Should not raise, should leave DB untouched.
    db.set_last_seen_trade_ts("0xdoesnotexist", 1.0)
    assert db.get_last_seen_trade_ts("0xdoesnotexist") is None


def test_record_paper_trade_and_committed_sum(db):
    db.ensure_trader(ADDR)
    db.record_paper_trade(
        whale_address=ADDR,
        market_id="m1",
        outcome="YES",
        side="BUY",
        copy_notional_usd=200.0,
        copy_shares=500.0,
        copy_price=0.4,
        whale_size_shares=5000.0,
        whale_price=0.4,
        whale_notional_usd=2000.0,
        whale_tx_hash="0xabc",
    )
    db.record_paper_trade(
        whale_address=ADDR,
        market_id="m2",
        outcome="NO",
        side="BUY",
        copy_notional_usd=50.0,
        copy_shares=100.0,
        copy_price=0.5,
        whale_size_shares=200.0,
        whale_price=0.5,
        whale_notional_usd=100.0,
        whale_tx_hash="0xdef",
    )
    assert db.get_paper_committed_usd() == pytest.approx(250.0)
    assert db.session.query(PaperTrade).count() == 2


def test_committed_excludes_resolved(db):
    db.ensure_trader(ADDR)
    pt = db.record_paper_trade(
        whale_address=ADDR, market_id="m1", outcome="YES", side="BUY",
        copy_notional_usd=100.0, copy_shares=200.0, copy_price=0.5,
        whale_size_shares=1000.0, whale_price=0.5, whale_notional_usd=500.0,
        whale_tx_hash="0xaaa",
    )
    db.record_paper_trade(
        whale_address=ADDR, market_id="m2", outcome="YES", side="BUY",
        copy_notional_usd=75.0, copy_shares=150.0, copy_price=0.5,
        whale_size_shares=1000.0, whale_price=0.5, whale_notional_usd=500.0,
        whale_tx_hash="0xbbb",
    )
    pt.status = "resolved_win"
    db.session.commit()
    assert db.get_paper_committed_usd() == pytest.approx(75.0)


def test_has_paper_trade_for_dedup(db):
    db.ensure_trader(ADDR)
    assert not db.has_paper_trade_for("0xtx1")
    db.record_paper_trade(
        whale_address=ADDR, market_id="m1", outcome="YES", side="BUY",
        copy_notional_usd=10.0, copy_shares=20.0, copy_price=0.5,
        whale_size_shares=100.0, whale_price=0.5, whale_notional_usd=50.0,
        whale_tx_hash="0xtx1",
    )
    assert db.has_paper_trade_for("0xtx1")
    assert not db.has_paper_trade_for("0xtx2")
    assert not db.has_paper_trade_for("")  # empty hash never dedups


def test_set_following_toggles(db):
    db.ensure_trader(ADDR)
    db.set_following(ADDR, True)
    assert any(t.address == ADDR for t in db.get_following_list())
    db.set_following(ADDR, False)
    assert not any(t.address == ADDR for t in db.get_following_list())


def test_migration_is_idempotent_on_repeat_open(tmp_path):
    """Re-opening the same DB file must not fail re-applying ALTER TABLE."""
    p = tmp_path / "repeat.db"
    db1 = WhaleDatabase(str(p))
    db1.ensure_trader(ADDR)
    db1.set_last_seen_trade_ts(ADDR, 42.0)
    db1.close()

    db2 = WhaleDatabase(str(p))
    assert db2.get_last_seen_trade_ts(ADDR) == 42.0
    db2.close()
