"""
Leaderboard Scraper - One-time script to extract top whale addresses
from Polymarket's public leaderboard
"""
import requests
from bs4 import BeautifulSoup
import json
from loguru import logger as log
from typing import List, Dict


def scrape_leaderboard() -> List[Dict]:
    """
    Scrape Polymarket leaderboard for top trader addresses
    
    Returns:
        List of dictionaries with trader info (address, volume, pnl, etc.)
    """
    url = "https://polymarket.com/leaderboard"
    
    try:
        # Make request
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            log.error(f"Failed to fetch leaderboard: HTTP {response.status_code}")
            return []
        
        # Try to find JSON data in page (Polymarket likely uses Next.js with data in script tags)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for Next.js data
        scripts = soup.find_all('script', {'id': '__NEXT_DATA__'})
        
        if scripts:
            try:
                data = json.loads(scripts[0].string)
                log.info("Found Next.js data in page")
                
                # Navigate the JSON to find leaderboard data
                # This structure may vary, needs inspection
                props = data.get('props', {})
                page_props = props.get('pageProps', {})
                
                # Look for leaderboard array
                leaderboard = (
                    page_props.get('leaderboard') or
                    page_props.get('traders') or
                    page_props.get('users') or
                    []
                )
                
                if leaderboard:
                    log.info(f"✅ Found {len(leaderboard)} traders in leaderboard")
                    return leaderboard
                else:
                    log.warning("Leaderboard data not found in expected location")
                    # Save the JSON for manual inspection
                    with open('debug_leaderboard.json', 'w') as f:
                        json.dump(page_props, f, indent=2)
                    log.info("Saved page data to debug_leaderboard.json for inspection")
                    
            except json.JSONDecodeError as e:
                log.error(f"Failed to parse JSON: {e}")
        
        # Fallback: try to parse HTML directly
        log.info("Attempting HTML parsing...")
        traders = []
        
        # Look for addresses in the HTML (they typically start with 0x)
        import re
        addresses = re.findall(r'0x[a-fA-F0-9]{40}', response.text)
        
        if addresses:
            # Remove duplicates
            unique_addresses = list(set(addresses))
            log.info(f"Found {len(unique_addresses)} unique addresses in HTML")
            
            traders = [{'address': addr} for addr in unique_addresses[:20]]
            return traders
        
        return []
        
    except Exception as e:
        log.error(f"Error scraping leaderboard: {e}")
        return []


def save_to_seed_file(traders: List[Dict], output_file: str = "src/whale_watching/seed_whales.py"):
    """
    Save extracted traders to seed_whales.py file
    
    Args:
        traders: List of trader dictionaries
        output_file: Path to output file
    """
    if not traders:
        log.warning("No traders to save")
        return
    
    # Generate Python code for seed list
    code = "# Manual Whale Seed List (Auto-generated from leaderboard)\n"
    code += "# Generated: " + str(__import__('datetime').datetime.now()) + "\n\n"
    code += "SEED_WHALES = [\n"
    code += "    # Format: (address, nickname, reason)\n\n"
    
    for i, trader in enumerate(traders[:20], 1):  # Top 20
        address = trader.get('address') or trader.get('walletAddress') or trader.get('user')
        if address:
            pnl = trader.get('pnl', 'unknown')
            volume = trader.get('volume', 'unknown')
            nickname = f"Leaderboard#{i}"
            reason = f"PnL: ${pnl}, Volume: ${volume}" if pnl != 'unknown' else "Top trader"
            
            code += f'    ("{address}", "{nickname}", "{reason}"),\n'
    
    code += "]\n"
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(code)
    
    log.info(f"✅ Saved {len(traders[:20])} whales to {output_file}")


def main():
    log.info("🔍 Scraping Polymarket Leaderboard...")
    log.info("=" * 60)
    
    traders = scrape_leaderboard()
    
    if traders:
        log.info(f"\n📊 Found {len(traders)} traders")
        
        # Show first 5
        log.info("\nTop 5 Traders:")
        for i, trader in enumerate(traders[:5], 1):
            address = trader.get('address') or trader.get('walletAddress', 'N/A')
            log.info(f"  {i}. {address}")
        
        # Save to seed file
        save_to_seed_file(traders)
        
        log.info("\n✅ Scraping complete!")
        log.info("Next step: Update trade_monitor.py to use these addresses")
    else:
        log.error("\n❌ Failed to extract traders")
        log.info("Manual action required:")
        log.info("1. Visit https://polymarket.com/leaderboard in your browser")
        log.info("2. Open DevTools (F12) -> Network tab")
        log.info("3. Look for API calls that load leaderboard data")
        log.info("4. Copy the addresses manually")
    
    log.info("=" * 60)


if __name__ == "__main__":
    main()
