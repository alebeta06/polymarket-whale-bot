"""
Quick script to view current whale database stats
"""
from src.whale_watching.database import WhaleDatabase


def main():
    db = WhaleDatabase("data/whales.db")
    
    print("\n" + "=" * 70)
    print("🐋 WHALE DATABASE STATISTICS")
    print("=" * 70)
    
    # Get all traders
    all_traders = db.session.query(db.session.query(db.session.bind.execute("SELECT COUNT(*) FROM observed_traders").scalar())).scalar()
    
    # Get top traders
    top_traders = db.get_top_traders(limit=20, min_trades=1)
    
    print(f"\nTotal Traders Observed: {len(top_traders)}")
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
    
    print("=" * 70 + "\n")
    
    db.close()


if __name__ == "__main__":
    main()
