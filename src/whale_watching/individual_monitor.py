"""
Individual Whale Monitor - Tracks trades from specific whale addresses
Polls Polymarket's public Data API for each followed whale's recent trades.
"""
import asyncio
import time
from typing import List, Dict, Optional
from loguru import logger as log
from datetime import datetime, timedelta

from .database import WhaleDatabase
from .seed_whales import SEED_WHALES, EXCLUDED_WHALES
from .data_api import PolymarketDataAPI
from .markets import MarketsAPI
from .reconcile import reconcile
from .risk import RiskContext, RiskLimits, evaluate as evaluate_risk
from .sizing import compute_copy_size
from py_clob_client.client import ClobClient


# Lookback used the first time we poll a whale (no prior watermark in memory).
INITIAL_LOOKBACK_HOURS = 24
# How many trades to request per whale per poll. Newest first.
TRADES_PER_POLL = 50


class IndividualWhaleMonitor:
    """Monitor specific whale addresses via Polymarket Data API polling"""

    def __init__(
        self,
        db: WhaleDatabase,
        poll_interval: int = 60,
        *,
        dry_run: bool = True,
        copy_pct: float = 0.15,
        paper_starting_balance_usd: float = 1000.0,
        max_per_copy_trade_usd: float = 200.0,
        risk_limits: Optional[RiskLimits] = None,
        reconcile_every_n_polls: int = 10,
    ):
        """
        Initialize the monitor

        Args:
            db: Database instance
            poll_interval: Seconds between checks (default: 60)
            dry_run: When True, copy trades are recorded as paper_trades and no
                CLOB orders are placed. Mirror of Settings.dry_run.
            copy_pct: Fraction of the whale's notional to mirror.
            paper_starting_balance_usd: Notional bankroll for paper-trade sizing.
            max_per_copy_trade_usd: Hard ceiling per single copy.
            risk_limits: Pre-built RiskLimits. Defaults to library defaults.
        """
        self.db = db
        self.poll_interval = poll_interval
        self.dry_run = dry_run
        self.copy_pct = copy_pct
        self.paper_starting_balance_usd = paper_starting_balance_usd
        self.max_per_copy_trade_usd = max_per_copy_trade_usd
        self.risk_limits = risk_limits or RiskLimits()
        self.reconcile_every_n_polls = reconcile_every_n_polls
        self.whale_addresses: List[str] = []
        self.client: Optional[ClobClient] = None
        self.data_api: Optional[PolymarketDataAPI] = None
        self.markets_api: Optional[MarketsAPI] = None
        self.running = False
        self._poll_count: int = 0
        # Watermark per whale: only trades with timestamp > watermark are processed.
        # Stored as unix seconds (float) to match the Data API's `timestamp` field.
        self.last_trade_timestamps: Dict[str, float] = {}

        mode = "PAPER (DRY_RUN)" if dry_run else "LIVE"
        log.info(
            f"🔍 Individual Whale Monitor initialized "
            f"(poll every {poll_interval}s, mode={mode}, copy_pct={copy_pct:.0%})"
        )

    def initialize_client(self):
        """Initialize HTTP clients used for whale tracking"""
        # Public Data API client (read-only, no auth) — primary source of trades.
        self.data_api = PolymarketDataAPI()
        log.info("✅ Polymarket Data API client initialized")

        # Gamma markets client — used by in-loop reconciliation.
        self.markets_api = MarketsAPI()
        log.info("✅ Polymarket Markets API client initialized")

        # CLOB client kept for Fase 2 (order placement); not used for read-only polling.
        try:
            self.client = ClobClient("https://clob.polymarket.com")
            log.info("✅ CLOB client initialized (idle until Fase 2)")
        except Exception as e:
            log.warning(f"CLOB client init failed (non-fatal, only needed in Fase 2): {e}")
    
    def load_whales(self):
        """Load whale addresses from seed list and hydrate watermarks from DB.

        Whales in EXCLUDED_WHALES are skipped (no follow, no polling). The trader
        row is left untouched so any historical observed_trades survive.
        """
        for address, nickname, reason in SEED_WHALES:
            address_lower = address.lower()

            if address_lower in EXCLUDED_WHALES:
                log.info(
                    f"⏭️  Excluded {nickname} ({address_lower[:10]}...): "
                    f"{EXCLUDED_WHALES[address_lower]}"
                )
                # Make sure we are NOT following them, in case a prior run did.
                self.db.set_following(address_lower, False)
                continue

            if address_lower not in self.whale_addresses:
                self.whale_addresses.append(address_lower)

                # Ensure the trader row exists (no fake trade), then mark as following.
                self.db.ensure_trader(address_lower)
                self.db.set_following(address_lower, True)

                # Hydrate the in-memory watermark from DB so restarts don't reprocess.
                persisted_ts = self.db.get_last_seen_trade_ts(address_lower)
                if persisted_ts is not None:
                    self.last_trade_timestamps[address_lower] = persisted_ts

                log.info(f"📝 Loaded: {nickname} ({address_lower[:10]}...)")

        log.info(f"✅ Loaded {len(self.whale_addresses)} whales to monitor")
    
    async def check_whale_trades(self, address: str):
        """
        Check recent trades for a specific whale via the Polymarket Data API.

        Args:
            address: Whale wallet address (lowercase 0x-prefixed)
        """
        if self.data_api is None:
            log.error("Data API client not initialized — call initialize_client() first")
            return

        # Bootstrap watermark: first time we see this whale, look back 24h.
        last_seen = self.last_trade_timestamps.get(address)
        if last_seen is None:
            last_seen = (datetime.now() - timedelta(hours=INITIAL_LOOKBACK_HOURS)).timestamp()

        try:
            trades = await self.data_api.get_user_trades(
                address,
                limit=TRADES_PER_POLL,
                after_timestamp=last_seen,
            )
        except Exception as e:
            log.error(f"Error fetching trades for {address[:10]}...: {e}")
            return

        if not trades:
            self.last_trade_timestamps[address] = last_seen
            return

        max_ts = last_seen
        for trade in trades:
            try:
                ts = float(trade.get("timestamp", 0))
            except (TypeError, ValueError):
                ts = 0.0
            if ts > max_ts:
                max_ts = ts
            self.process_trade(address, trade)

        # Advance watermark in memory and persist so restarts don't reprocess.
        self.last_trade_timestamps[address] = max_ts
        self.db.set_last_seen_trade_ts(address, max_ts)
        log.debug(f"Processed {len(trades)} new trades for {address[:10]}...")

    @staticmethod
    def _normalize_outcome(raw: Optional[str]) -> str:
        """Map Data API's 'Yes'/'No' to the project's 'YES'/'NO' convention."""
        if not raw:
            return "UNKNOWN"
        upper = raw.strip().upper()
        if upper in ("YES", "NO"):
            return upper
        return upper or "UNKNOWN"

    def process_trade(self, whale_address: str, trade: Dict):
        """
        Process a single trade returned by the Data API.

        Pipeline: parse → record observed → risk gate → sizing → paper/live execution.

        Expected fields (see data_api.get_user_trades): proxyWallet, side, asset,
        conditionId, size, price, timestamp, outcome, outcomeIndex, transactionHash.
        """
        try:
            market_id = trade.get("conditionId") or "UNKNOWN"
            asset_id = str(trade.get("asset") or "")
            outcome = self._normalize_outcome(trade.get("outcome"))
            side = (trade.get("side") or "BUY").upper()
            whale_shares = float(trade.get("size", 0) or 0)
            whale_price = float(trade.get("price", 0) or 0)
            tx_hash = str(trade.get("transactionHash") or "")
            try:
                trade_ts = float(trade.get("timestamp", 0))
            except (TypeError, ValueError):
                trade_ts = 0.0

            whale_notional = whale_shares * whale_price
            trade_age = max(0.0, time.time() - trade_ts) if trade_ts > 0 else float("inf")

            # Always record what the whale did, even if we won't copy it. Useful
            # for backfilling stats and for manual review of skipped trades.
            # NOTE: ObservedTrade.size still holds USD notional (legacy schema).
            self.db.record_trade(
                address=whale_address,
                market_id=market_id,
                outcome=outcome,
                side=side,
                size=whale_notional,
                price=whale_price,
            )

            # SELL trades close existing positions and need cost-basis tracking
            # to compute P&L cleanly — out of scope for v1 paper trading.
            if side != "BUY":
                log.debug(f"⏭️  Skip non-BUY trade: {side} {outcome} on {str(market_id)[:12]}...")
                return

            # 1) Risk gate.
            risk_decision = evaluate_risk(
                RiskContext(
                    whale_notional_usd=whale_notional,
                    trade_age_seconds=trade_age,
                    # market_volume_usd / market_seconds_to_expiry: TODO once we
                    # plumb a markets metadata client. Until then they pass freely.
                ),
                self.risk_limits,
            )
            if risk_decision.skip:
                log.debug(
                    f"⏭️  Skip {whale_address[:10]}... {side} {outcome} "
                    f"${whale_notional:,.2f}: {risk_decision.reason}"
                )
                return

            log.info(
                f"🐋 Whale trade: {whale_address[:10]}... {side} {outcome} "
                f"${whale_notional:,.2f} @ {whale_price:.3f} on {str(market_id)[:12]}... "
                f"(age {trade_age:.0f}s)"
            )

            # 2) Sizing. We don't have a live ticker yet, so use the whale's
            # fill price as our entry mark. When a CLOB ticker is wired in
            # (Fase 2.7), replace `current_price` with the live best ask.
            available_balance = max(
                0.0,
                self.paper_starting_balance_usd - self.db.get_paper_committed_usd(),
            )
            sizing = compute_copy_size(
                whale_notional_usd=whale_notional,
                available_balance_usd=available_balance,
                current_price=whale_price,
                copy_pct=self.copy_pct,
                max_per_trade_usd=self.max_per_copy_trade_usd,
            )
            if sizing.skip:
                log.info(f"📐 Size skip: {sizing.reason}")
                return

            # 3) Execute (paper or live).
            if self.dry_run:
                # Idempotency: don't double-record if the same whale trade resurfaces.
                if self.db.has_paper_trade_for(tx_hash):
                    log.debug(f"Already have paper trade for tx {tx_hash[:12]}..., skipping")
                    return
                self.db.record_paper_trade(
                    whale_address=whale_address,
                    market_id=market_id,
                    outcome=outcome,
                    side=side,
                    copy_notional_usd=sizing.copy_notional_usd,
                    copy_shares=sizing.copy_shares,
                    copy_price=sizing.copy_price,
                    whale_size_shares=whale_shares,
                    whale_price=whale_price,
                    whale_notional_usd=whale_notional,
                    whale_tx_hash=tx_hash,
                    asset_id=asset_id,
                )
                log.info(
                    f"📝 Paper copy: {side} {outcome} "
                    f"{sizing.copy_shares:.2f} sh @ {sizing.copy_price:.3f} "
                    f"= ${sizing.copy_notional_usd:.2f}"
                )
            else:
                # TODO (Fase 2.7): plumb in the authenticated ClobClient executor.
                log.warning(
                    f"⚠️  LIVE mode requested but executor not yet implemented "
                    f"— would have placed {side} {sizing.copy_shares:.2f} @ {sizing.copy_price:.3f}"
                )

        except Exception as e:
            log.error(f"Error processing trade for {whale_address[:10]}...: {e}")
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        self.running = True

        log.info("🚀 Starting whale monitoring loop...")

        try:
            while self.running:
                try:
                    # Check all whales
                    for address in self.whale_addresses:
                        if not self.running:
                            break
                        await self.check_whale_trades(address)
                        await asyncio.sleep(1)  # Rate limit between whales

                    self._poll_count += 1

                    # Periodic reconcile so paper P&L stays fresh without a separate cron.
                    if (
                        self.reconcile_every_n_polls > 0
                        and self.markets_api is not None
                        and self._poll_count % self.reconcile_every_n_polls == 0
                    ):
                        try:
                            stats = await reconcile(self.db, self.markets_api)
                            log.info(
                                f"📊 Reconcile: {stats.still_open} open, "
                                f"{stats.resolved_win}W/{stats.resolved_loss}L, "
                                f"realized ${stats.realized_pnl_usd:+,.2f} "
                                f"unrealized ${stats.unrealized_pnl_usd:+,.2f}"
                            )
                        except Exception as e:
                            log.error(f"Reconcile failed (non-fatal): {e}")

                    # Wait for next poll cycle
                    log.info(f"⏳ Checked {len(self.whale_addresses)} whales, waiting {self.poll_interval}s...")
                    await asyncio.sleep(self.poll_interval)

                except Exception as e:
                    log.error(f"Error in monitor loop: {e}")
                    await asyncio.sleep(10)
        finally:
            if self.data_api is not None:
                await self.data_api.close()
                log.info("✅ Data API session closed")
            if self.markets_api is not None:
                await self.markets_api.close()
                log.info("✅ Markets API session closed")
    
    async def start(self):
        """Start the monitor"""
        log.info("=" * 60)
        log.info("🐋 INDIVIDUAL WHALE MONITOR STARTING")
        log.info("=" * 60)
        
        # Initialize
        self.initialize_client()
        self.load_whales()
        
        log.info(f"Monitoring {len(self.whale_addresses)} whales")
        log.info(f"Poll interval: {self.poll_interval}s")
        log.info("=" * 60)
        
        # Start monitoring
        await self.monitor_loop()
    
    def stop(self):
        """Stop the monitor"""
        self.running = False
        log.info("🛑 Monitor stopped")


# Simple test/demo
async def main():
    db = WhaleDatabase("data/whales.db")
    monitor = IndividualWhaleMonitor(db, poll_interval=30)
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        monitor.stop()
        db.close()
        log.info("👋 Shutdown")


if __name__ == "__main__":
    asyncio.run(main())
