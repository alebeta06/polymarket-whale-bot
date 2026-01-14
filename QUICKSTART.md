# 🚀 Quick Start Guide - Polymarket Arbitrage Bot

## ⚡ 5-Minute Setup

### Step 1: Run Setup Script

```bash
cd /home/alebeta/polymarket-arbitrage-bot
./setup.sh
```

This will:

- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Create `.env` from template
- ✅ Create necessary directories

---

### Step 2: Configure Credentials

Edit the `.env` file:

```bash
nano .env
```

**Replace the following values** (DO NOT share these!):

```bash
# From Polymarket Builder Settings
POLYMARKET_API_KEY=019bb5dc-210a-7d56-ba8c-916be4ed9916
POLYMARKET_API_SECRET=your_secret_here
POLYMARKET_API_PASSPHRASE=your_passphrase_here

# From Phantom Wallet
PRIVATE_KEY=0xYOUR_PRIVATE_KEY_FROM_PHANTOM
EOA_ADDRESS=0xcF430a8Fa09A3a2b1CE9Dbd4403102a43e5e8e06
PROXY_WALLET_ADDRESS=0x84c916bb5314515bffa04dd9c714bfa348b98ab8

# Verify these settings match your preferences
DRY_RUN=true  # KEEP true for Paper Trading!
MAX_POSITION_SIZE_PERCENT=0.15  # 15% per trade
DAILY_STOP_LOSS_PERCENT=0.10    # 10% daily stop-loss
MIN_PROFIT_PERCENT=0.02         # 2% minimum profit
```

**Save**: `Ctrl+O`, `Enter`, `Ctrl+X`

---

### Step 3: Run the Bot (Paper Trading)

```bash
source venv/bin/activate
python src/main.py
```

You should see:

```
🤖 POLYMARKET ARBITRAGE BOT STARTING
Mode: 📝 PAPER TRADING (Simulation)
Max Position Size: 15.0%
Daily Stop-Loss: 10.0%
Min Profit: 2.0%
Categories: ['Politics', 'Crypto', 'Sports']
```

---

## 📊 Monitor the Bot

### View logs in real-time:

```bash
# In another terminal
tail -f logs/polymarket_bot.log
```

### Check detected opportunities:

```bash
cat data/opportunities.json | jq '.'
```

### View daily metrics:

```bash
cat data/daily_metrics.json | jq '.[-1]'  # Latest day
```

---

## 🛑 Stop the Bot

Press `Ctrl+C` in the terminal running the bot.

It will gracefully shutdown and generate a final report.

---

## 📈 What to Expect (Paper Trading)

### First Hour:

- Bot scans markets every 5 minutes
- Logs opportunities detected
- Simulates trades (no real money spent)

### After 1 Week:

- Review `data/daily_metrics.json`
- Check average opportunities/day
- Evaluate projected ROI

### Decision Point:

- **If ROI looks good**: Consider adding more capital ($500+) and switching to live trading
- **If ROI is low**: Adjust parameters or wait for better market conditions

---

## ⚙️ Adjust Settings (Optional)

Edit `.env` to change:

```bash
# More aggressive (20% per trade)
MAX_POSITION_SIZE_PERCENT=0.20

# More conservative (5% per trade)
MAX_POSITION_SIZE_PERCENT=0.05

# Higher profit threshold (3%)
MIN_PROFIT_PERCENT=0.03

# Different categories
SCAN_CATEGORIES=Politics,Crypto
```

Then restart the bot.

---

## 🚀 VPS Deployment (After Testing)

Once you're satisfied with Paper Trading results, you can deploy to a VPS for 24/7 operation.

**Guide**: See `VPS_DEPLOYMENT.md` (will be created next)

---

## ⚠️ Common Issues

### Issue: "Failed to load configuration"

**Solution**: Make sure `.env` file exists and is properly formatted

### Issue: "Invalid API credentials"

**Solution**: Double-check your Polymarket API keys in `.env`

### Issue: "No markets found"

**Solution**: Check if Polymarket API is accessible. Try manually visiting https://gamma-api.polymarket.com/markets

### Issue: Bot crashes immediately

**Solution**: Check logs in `logs/errors.log` for details

---

## 📞 Need Help?

Check the full documentation in `README.md`
