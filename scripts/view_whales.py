"""
Quick script to view current whale database stats
"""
from src.whale_watching.database import WhaleDatabase, ObservedTrader, ObservedTrade, PaperTrade


def main():
    db = WhaleDatabase("data/whales.db")

    print("\n" + "=" * 70)
    print("🐋 WHALE DATABASE STATISTICS")
    print("=" * 70)

    total_traders = db.session.query(ObservedTrader).count()
    total_trades = db.session.query(ObservedTrade).count()
    total_paper = db.session.query(PaperTrade).count()
    paper_committed = db.get_paper_committed_usd()

    # Get top traders
    top_traders = db.get_top_traders(limit=20, min_trades=1)

    print(f"\nTotal Traders Observed: {total_traders}")
    print(f"Total Trades Recorded:  {total_trades}")
    print(f"Paper Trades Recorded:  {total_paper}  (committed: ${paper_committed:,.2f})")
    print(f"\nTop 20 Traders by Volume:")
    print("-" * 70)
    
    for i, trader in enumerate(top_traders, 1):
        following = "⭐" if trader.is_following else "  "
        print(
            f"{following} {i:2}. {trader.address[:12]}... │ "
            f"${trader.total_volume:>10,.2f} │ "
            f"{trader.total_trades:>3} trades │ "
            f"{trader.win_rate*100:>5.1f}% win"
        )
    
    # Get following list
    following = db.get_following_list()
    if following:
        print(f"\n✅ Currently Following: {len(following)} whales")
        for whale in following:
            print(f"   - {whale.address[:12]}... (${whale.total_volume:,.2f})")
    else:
        print("\n📝 Not following any whales yet")

    # Recent paper trades
    recent_paper = (
        db.session.query(PaperTrade)
        .order_by(PaperTrade.id.desc())
        .limit(10)
        .all()
    )
    if recent_paper:
        print(f"\n📝 Recent Paper Trades (last {len(recent_paper)}):")
        print("-" * 70)
        for pt in recent_paper:
            print(
                f"  {pt.timestamp:%Y-%m-%d %H:%M} │ "
                f"{pt.whale_address[:10]}... │ "
                f"{pt.side:<4} {pt.outcome:<3} │ "
                f"{pt.copy_shares:>8.2f} sh @ {pt.copy_price:.3f} = "
                f"${pt.copy_notional_usd:>7.2f} │ {pt.status}"
            )

    print("=" * 70 + "\n")

    db.close()


if __name__ == "__main__":
    main()
