#!/bin/bash
#
# Setup script for Polymarket Arbitrage Bot
# This script will guide you through the initial setup
#

set -e  # Exit on error

echo "========================================"
echo "🤖 Polymarket Arbitrage Bot - Setup"
echo "========================================"
echo ""

# Check Python version
echo "📋 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Found Python $PYTHON_VERSION"

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found. Are you in the project directory?"
    exit 1
fi

# Create virtual environment
echo ""
echo "📦 Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "⚠️  Virtual environment already exists, skipping..."
fi

# Activate virtual environment
echo ""
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "📥 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Dependencies installed successfully"

# Check for .env file
echo ""
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: You MUST edit the .env file with your credentials:"
    echo "   1. Open .env in a text editor: nano .env"
    echo "   2. Add your Polymarket API credentials"
    echo "   3. Add your Phantom wallet private key"
    echo "   4. Add your addresses (EOA and Proxy Wallet)"
    echo ""
    echo "   DO NOT SKIP THIS STEP - The bot will not work without proper configuration!"
else
    echo "⚠️  .env file already exists, not overwriting"
fi

# Create log and data directories
echo ""
echo "📁 Creating directories..."
mkdir -p logs data

echo ""
echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Edit your .env file with credentials:"
echo "   nano .env"
echo ""
echo "2. Configure your settings (optional):"
echo "   - MAX_POSITION_SIZE_PERCENT (default: 0.15)"
echo "   - DAILY_STOP_LOSS_PERCENT (default: 0.10)"
echo "   - MIN_PROFIT_PERCENT (default: 0.02)"
echo ""
echo "3. Run the bot in PAPER TRADING mode:"
echo "   source venv/bin/activate"
echo "   python src/main.py"
echo ""
echo "4. Monitor logs:"
echo "   tail -f logs/polymarket_bot.log"
echo ""
echo "⚠️  REMINDER: Keep DRY_RUN=true for testing!"
echo ""
echo "========================================"
