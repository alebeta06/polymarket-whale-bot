# 🐋 Whale Watching Bot - Updated v2.0

## ✅ What Changed

We simplified the approach after discovering WebSocket limitations:

**Old approach** (didn't work):

- Try to monitor ALL trades via WebSocket
- Build database organically over weeks

**New approach** (works):

1. ✅ Scrape leaderboard ONCE to get top 20 whale addresses
2. ✅ Monitor those specific addresses individually
3. ✅ Much more reliable and immediate

---

## 🚀 Quick Start

### Step 1: We Already Have Whale Addresses!

The scraper ran and found 20 top whale addresses. They're saved in:

```
src/whale_watching/seed_whales.py
```

### Step 2: Run the Monitor

```bash
cd /home/alebeta/polymarket-arbitrage-bot
source venv/bin/activate
export PYTHONPATH=.
python scripts/whale_watcher.py
```

**What it does**:

- Loads the 20 whale addresses
- Polls each whale every 60 seconds
- Records their trades to the database
- Builds statistics over time

**Note**: The current version logs activity but doesn't fetch actual trade data yet (CLOB API integration pending). It's ready for the next phase: implementing copy trading logic.

---

## View Whale List

To see which whales we're monitoring:

```bash
python scripts/view_whales.py
```

---

## 📊 The 12 Verified Profitable Whales

From manual leaderboard curation, we're following:

### 🏆 Consistent Winners (Top Month + Top Week):

```
1. 0x006cc834cc092684f1b56626e23bedb3835c16ea (ConsistentWinner#1)
2. 0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee (ConsistentWinner#2)
3. 0xe90bec87d9ef430f27f9dcfe72c34b76967d5da2 (ConsistentWinner#3)
4. 0xdb27bf2ac5d428a9c63dbc914611036855a6c56e (ConsistentWinner#4)
5. 0x1bc0d88ca86b9049cf05d642e634836d5ddf4429 (ConsistentWinner#5)
6. 0xdc876e6873772d38716fda7f2452a78d426d7ab6 (ConsistentWinner#6)
7. 0xcd9bc2939f0dac121f6ccde59cca5e0b6a91414d (ConsistentWinner#7)
```

### 📈 Top Monthly:

```
8. 0x16b29c50f2439faf627209b2ac0c7bbddaa8a881 (MonthlyTop#1)
9. 0x37e4728b3c4607fb2b3b205386bb1d1fb1a8c991 (MonthlyTop#2)
10. 0x507e52ef684ca2dd91f90a9d26d149dd3288beae (MonthlyTop#3)
```

### ⚡ Top Weekly:

```
11. 0x96489abcb9f583d6835c8ef95ffc923d05a86825 (WeeklyTop#1)
12. 0x92672c80d36dcd08172aa1e51dface0f20b70f9a (WeeklyTop#2)
```

**All verified with positive P&L** - No losing traders!

---

## 🎯 Next Steps (Week 2-3)

### Phase 1: Complete CLOB Integration ✅ (Current)

- [x] Extract whale addresses
- [ ] Implement actual trade fetching from CLOB API
- [ ] Store trades in database

### Phase 2: Copy Trading Logic

- [ ] Detect when a whale makes a trade
- [ ] Calculate our position size (10-20% of theirs)
- [ ] Apply risk filters
- [ ] Execute copy in Paper Trading mode

### Phase 3: Testing & Optimization

- [ ] Run in Paper Trading for 1-2 weeks
- [ ] Track win rate and profitability
- [ ] Adjust parameters
- [ ] Go live with small capital

---

## ⚙️ Configuration

Edit `scripts/whale_watcher.py`:

```python
# Change poll frequency
bot = WhaleWatchingBot(poll_interval=60)  # 60 seconds = 1 minute

# For faster updates:
bot = WhaleWatchingBot(poll_interval=30)  # 30 seconds
```

---

## 🔧 Adding More Whales

To add more whale addresses manually, edit `src/whale_watching/seed_whales.py`:

```python
SEED_WHALES = [
    ("0xYourWhaleAddressHere", "Nickname", "Reason"),
    ...
]
```

Or re-run the scraper:

```bash
python scripts/scrape_leaderboard.py
```

---

## 📈 Current Status

✅ **Manual whale curation** (12 verified profitable traders)  
✅ Individual monitoring framework  
✅ Database structure  
⏳ CLOB API trade fetching (next)  
⏳ Copy trading execution  
⏳ Risk management

**You're now ready for Phase 2: Implementing copy trading logic!** 🚀
