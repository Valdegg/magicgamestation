#!/usr/bin/env python3
"""
MTG Card Discovery - Find new cards to add to wishlist

Discovers cards that are:
- NOT already in wishlist
- Historically discounted (AVG30 vs TREND) - initial filter
- ACTUALLY being offered below market RIGHT NOW (scrapes live prices)
- Compares live prices vs other current listings (positions 2-5)

This helps discover cards you might want but don't already know about.
"""

import json
import time
import random
import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from card_lookup import (
    load_cardmarket_data,
    exclude_wishlist_cards,
    find_cards_by_price_discount
)
from mtg_arbitrage.utils import get_cardmarket_url
from mtg_arbitrage.config import get_config

# Import scraper
try:
    from fetch_live_listings_simple import SimpleBrowserScraper
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False
    print("⚠️  Scraper not available. Install dependencies.")

# ============================================================================
# CONFIGURATION - Edit these values
# ============================================================================
WISHLIST_FILE = "wishlist.json"  # Cards to exclude from discovery
MIN_AVG30 = 10.0  # Minimum AVG30 price (€)
MAX_AVG30 = 500.0  # Maximum AVG30 price (€)
HISTORICAL_DISCOUNT_THRESHOLD = 0.05  # Initial filter: 5% under TREND (AVG30 vs TREND) - matches main.py, live EX+ check filters further
LIVE_DISCOUNT_THRESHOLD = 7.0  # Minimum live discount: 7% below market for EX+ cards (positions 2-5)
MIN_LIQUIDITY = 0.01  # Minimum AVG7 for liquidity check
MAX_CANDIDATES_TO_SCRAPE = 1  # Maximum candidates to scrape live prices for (TESTING: set to 1)
DELAY_BETWEEN_CARDS = 10.0  # Seconds to wait between scraping cards
OUTPUT_FILE = None  # Optional: Save results to JSON file (None = don't save)
# ============================================================================


def scrape_card_prices(card: Dict[str, Any], scraper: SimpleBrowserScraper) -> Optional[Dict[str, Any]]:
    """
    Scrape live prices for a single card.
    
    Args:
        card: Card data dictionary
        scraper: Scraper instance
        
    Returns:
        Live price data or None if failed
    """
    card_id = card.get('card_id') or card.get('idProduct')
    card_name = card.get('name', f"Card ID {card_id}")
    expansion_name = card.get('expansion') or card.get('expansionName')
    
    if not card_id:
        return None
    
    # Generate Cardmarket URL
    config = get_config()
    use_german_only = config.get('USE_GERMAN_SELLERS_ONLY', False)
    url = get_cardmarket_url(card_id, card_name, expansion_name, 'direct', include_filters=use_german_only)
    
    # Fetch listings
    result = scraper.fetch_listings(url, max_listings=10)
    listings = result.listings
    
    # Extract expansion from scraped page if available
    scraped_expansion = result.expansion_name
    
    if not listings:
        return None
    
    # Extract prices and find best EX+ listing
    prices = [l.price for l in listings if l.price > 0]
    if not prices:
        return None
    
    # Find EX+ condition listings (EX, NM, MT)
    good_condition_listings = [
        l for l in listings 
        if l.condition.upper() in ['EX', 'NM', 'MT']
    ]
    
    cheapest_good = None
    top_sellers = []
    
    if good_condition_listings:
        sorted_good = sorted(good_condition_listings, key=lambda x: x.price)
        cheapest_good = sorted_good[0]
        
        # Get top 6 sellers for comparison
        top_sellers = [
            {
                'seller': l.seller,
                'price': l.price,
                'condition': l.condition,
                'quantity': l.quantity,
                'country': l.seller_country
            }
            for l in sorted_good[:6]
        ]
    
    return {
        'url': url,
        'total_listings': len(listings),
        'available_items_total': result.available_items_total,
        'expansion_name': scraped_expansion,  # Add scraped expansion name
        'cheapest_current': min(prices),
        'average_current': sum(prices) / len(prices),
        'cheapest_good_condition': cheapest_good.price if cheapest_good else None,
        'cheapest_good_details': {
            'price': cheapest_good.price,
            'condition': cheapest_good.condition,
            'seller': cheapest_good.seller,
            'quantity': cheapest_good.quantity,
            'country': cheapest_good.seller_country
        } if cheapest_good else None,
        'top_sellers': top_sellers
    }


def calculate_live_discount(live_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate discount based on live prices vs other current listings.
    
    Compares cheapest listing against average of positions 2-5.
    
    Args:
        live_data: Scraped live price data with top_sellers list
        
    Returns:
        Dictionary with discount calculations
    """
    cheapest_good = live_data.get('cheapest_good_condition')
    top_sellers = live_data.get('top_sellers', [])
    
    if not cheapest_good or not top_sellers or len(top_sellers) < 2:
        return {
            'has_discount': False,
            'discount_vs_market': None,
            'market_baseline': None,
            'baseline_count': None
        }
    
    # Calculate average using positions 2-5 (exclude cheapest to avoid self-comparison)
    baseline_sellers = top_sellers[1:5] if len(top_sellers) >= 5 else top_sellers[1:]
    
    if not baseline_sellers:
        return {
            'has_discount': False,
            'discount_vs_market': None,
            'market_baseline': None,
            'baseline_count': None
        }
    
    # Calculate average price of positions 2-5
    avg_baseline = sum(s['price'] for s in baseline_sellers) / len(baseline_sellers)
    
    # Calculate discount: how much cheaper is the cheapest vs the baseline average
    discount_vs_market = ((avg_baseline - cheapest_good) / avg_baseline) * 100
    
    return {
        'has_discount': discount_vs_market > 0,
        'discount_vs_market': discount_vs_market,
        'market_baseline': avg_baseline,
        'baseline_count': len(baseline_sellers)
    }


def format_card_summary(card: Dict[str, Any]) -> str:
    """Format a card for display."""
    name = card.get('name', 'Unknown')
    expansion = card.get('expansion', 'Unknown')
    live_discount = card.get('live_discount', {}).get('discount_vs_market')
    
    if live_discount is not None:
        cheapest = card.get('live_data', {}).get('cheapest_good_condition', 0)
        baseline = card.get('live_discount', {}).get('market_baseline', 0)
        return f"{name} ({expansion}) - Live: €{cheapest:.2f} ({live_discount:.1f}% below €{baseline:.2f})"
    else:
        avg30 = card.get('historical', {}).get('avg30', 0)
        trend = card.get('historical', {}).get('trend', 0)
        discount_pct = card.get('historical_discount_pct', 0)
        return f"{name} ({expansion}) - AVG30: €{avg30:.2f}, TREND: €{trend:.2f}, Historical: {discount_pct:.1f}%"


def discover_cards(
    wishlist_file: str = WISHLIST_FILE,
    min_avg30: float = MIN_AVG30,
    max_avg30: float = MAX_AVG30,
    historical_discount_threshold: float = HISTORICAL_DISCOUNT_THRESHOLD,
    live_discount_threshold: float = LIVE_DISCOUNT_THRESHOLD,
    min_liquidity: float = MIN_LIQUIDITY,
    max_candidates_to_scrape: int = MAX_CANDIDATES_TO_SCRAPE,
    delay_between_cards: float = DELAY_BETWEEN_CARDS
) -> List[Dict[str, Any]]:
    """
    Discover cards that are not in wishlist and are actually being offered below market.
    
    Process:
    1. Use historical data (AVG30 vs TREND) to find initial candidates
    2. Scrape live prices for those candidates
    3. Compare live prices vs other current listings (positions 2-5)
    4. Only return cards that are actually being offered at discounts RIGHT NOW
    
    Args:
        wishlist_file: Path to wishlist JSON file (cards to exclude)
        min_avg30: Minimum AVG30 price
        max_avg30: Maximum AVG30 price
        historical_discount_threshold: Initial filter: minimum historical discount (0.25 = 25%)
        live_discount_threshold: Minimum live discount vs market (7.0 = 7%)
        min_liquidity: Minimum AVG7 for liquidity
        max_candidates_to_scrape: Maximum candidates to scrape live prices for
        delay_between_cards: Seconds to wait between scraping cards
        
    Returns:
        List of discovery candidate dictionaries with live price data
    """
    if not SCRAPER_AVAILABLE:
        print("❌ Scraper not available. Cannot check live prices.")
        return []
    
    print("🔍 MTG CARD DISCOVERY")
    print("=" * 60)
    print(f"Step 1: Finding candidates (≥{historical_discount_threshold*100:.0f}% AVG30<TREND) - initial filter")
    print(f"Step 2: Scraping EX+ live prices to verify actual discounts (≥{live_discount_threshold:.0f}% below EX+ market)")
    print(f"Note: Historical filter uses all-condition data; we verify with EX+ live prices vs EX+ listings")
    print()
    
    # Step 1: Load Cardmarket data and find historical candidates
    data = load_cardmarket_data()
    
    if data.empty:
        print("❌ No data available")
        return []
    
    # Exclude cards already in wishlist
    data = exclude_wishlist_cards(data, wishlist_file)
    
    if data.empty:
        print("❌ No cards remaining after excluding wishlist")
        return []
    
    # Find cards with significant historical discounts (initial filter)
    historical_candidates = find_cards_by_price_discount(
        data,
        min_avg30=min_avg30,
        max_avg30=max_avg30,
        discount_threshold=historical_discount_threshold,
        min_liquidity=min_liquidity
    )
    
    if historical_candidates.empty:
        print("❌ No historical candidates found")
        return []
    
    # Limit candidates to scrape
    if max_candidates_to_scrape:
        historical_candidates = historical_candidates.head(max_candidates_to_scrape)
    
    print(f"\n💰 Step 2: Scraping live prices for {len(historical_candidates)} candidates...")
    print("=" * 60)
    
    # Step 2: Scrape live prices and verify actual discounts
    scraper = SimpleBrowserScraper(delay_range=(3.0, 5.0), max_retries=3, save_images=False)
    discovery_cards = []
    
    for i, (_, row) in enumerate(historical_candidates.iterrows(), 1):
        card = {
            'card_id': int(row.get('idProduct', 0)),
            'name': row.get('name', 'Unknown'),
            'expansion': row.get('expansionName', 'Unknown'),
            'historical': {
                'trend': float(row.get('TREND', 0)),
                'avg30': float(row.get('AVG30', 0)),
                'avg7': float(row.get('AVG7', 0))
            },
            'historical_discount_pct': float(row.get('discount_pct', 0))
        }
        
        card_name = card['name']
        expansion = card['expansion']
        
        print(f"\n[{i}/{len(historical_candidates)}] {card_name} ({expansion})")
        
        # Scrape live prices
        live_data = scrape_card_prices(card, scraper)
        
        if not live_data:
            print(f"   ⚠️  Could not fetch live prices")
            continue
        
        # Calculate live discount vs market
        live_discount = calculate_live_discount(live_data)
        discount_vs_market = live_discount.get('discount_vs_market')
        
        # Only include if meets live discount threshold
        if discount_vs_market is None or discount_vs_market < live_discount_threshold:
            if discount_vs_market is not None:
                print(f"   ❌ Live discount {discount_vs_market:.1f}% below threshold ({live_discount_threshold:.0f}%)")
            continue
        
        cheapest_good = live_data.get('cheapest_good_condition')
        baseline = live_discount.get('market_baseline', 0)
        
        print(f"   💶 Best EX+: €{cheapest_good:.2f}")
        print(f"   📊 Market baseline: €{baseline:.2f}")
        print(f"   ✅ DISCOVERY: {discount_vs_market:.1f}% below market")
        
        # Calculate category based on discount
        if discount_vs_market >= 7:
            category = 'excellent'
        elif discount_vs_market >= 3:
            category = 'good'
        elif discount_vs_market >= 0:
            category = 'fair'
        else:
            category = 'expensive'
        
        # Standardize structure to match wishlist_deals.py
        deal = {
            'card': {
                'name': card['name'],
                'expansion': card['expansion'],
                'card_id': card['card_id'],
                'historical': card['historical']
            },
            'live_data': live_data,
            'discounts': live_discount,  # Use 'discounts' to match wishlist_deals.py
            'category': category,
            'historical_discount_pct': card.get('historical_discount_pct', 0)  # Keep for reference
        }
        
        discovery_cards.append(deal)
        
        # Delay between cards
        if i < len(historical_candidates):
            delay = random.uniform(delay_between_cards * 0.8, delay_between_cards * 1.2)
            print(f"   ⏳ Waiting {delay:.1f}s...")
            time.sleep(delay)
    
    print(f"\n✅ Found {len(discovery_cards)} cards actually being offered below market")
    return discovery_cards


def print_discovery_summary(cards: List[Dict[str, Any]]) -> None:
    """Print a summary of discovery candidates."""
    if not cards:
        print("\n❌ No discovery candidates found")
        return
    
    print("\n" + "=" * 60)
    print(f"🎯 DISCOVERY RESULTS: {len(cards)} candidates")
    print("=" * 60)
    
    print(f"\nTop {min(10, len(cards))} Discovery Candidates:")
    print("-" * 60)
    
    for i, deal in enumerate(cards[:10], 1):
        print(f"{i:2d}. {format_card_summary(deal)}")
    
    if len(cards) > 10:
        print(f"\n... and {len(cards) - 10} more candidates")
    
    # Statistics
    live_discounts = [c.get('discounts', {}).get('discount_vs_market', 0) for c in cards if c.get('discounts', {}).get('discount_vs_market') is not None]
    avg30s = [c['card']['historical']['avg30'] for c in cards]
    
    print(f"\n📊 Statistics:")
    if live_discounts:
        print(f"   Average live discount: {sum(live_discounts)/len(live_discounts):.1f}%")
        print(f"   Live discount range: {min(live_discounts):.1f}% - {max(live_discounts):.1f}%")
    print(f"   Average AVG30: €{sum(avg30s)/len(avg30s):.2f}")
    print(f"   AVG30 range: €{min(avg30s):.2f} - €{max(avg30s):.2f}")
    
    print(f"\n💡 These cards are actually being offered below market RIGHT NOW and not in your wishlist.")
    print(f"   Consider adding interesting ones to your wishlist for price monitoring.")


def save_discovery_results(cards: List[Dict[str, Any]], output_file: str) -> None:
    """Save discovery results to JSON file."""
    output_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'wishlist_file': WISHLIST_FILE,
        'config': {
            'min_avg30': MIN_AVG30,
            'max_avg30': MAX_AVG30,
            'historical_discount_threshold': HISTORICAL_DISCOUNT_THRESHOLD,
            'live_discount_threshold': LIVE_DISCOUNT_THRESHOLD,
            'min_liquidity': MIN_LIQUIDITY
        },
        'total_candidates': len(cards),
        'candidates': cards
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {output_file}")


def main():
    """Main entry point."""
    # Discover cards
    cards = discover_cards(
        wishlist_file=WISHLIST_FILE,
        min_avg30=MIN_AVG30,
        max_avg30=MAX_AVG30,
        historical_discount_threshold=HISTORICAL_DISCOUNT_THRESHOLD,
        live_discount_threshold=LIVE_DISCOUNT_THRESHOLD,
        min_liquidity=MIN_LIQUIDITY,
        max_candidates_to_scrape=MAX_CANDIDATES_TO_SCRAPE,
        delay_between_cards=DELAY_BETWEEN_CARDS
    )
    
    # Print summary
    print_discovery_summary(cards)
    
    # Save to file if requested
    if OUTPUT_FILE:
        save_discovery_results(cards, OUTPUT_FILE)
    
    return cards


if __name__ == "__main__":
    main()

