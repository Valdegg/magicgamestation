#!/usr/bin/env python3
"""
Simplified MTG Wishlist Price Checker

Reads a wishlist.json file, scrapes live prices for those cards,
and identifies deals with discounts compared to market prices.

Returns a clean data structure suitable for any UI.

Configuration (edit these values at the top of the file):
    WISHLIST_FILE: Path to wishlist JSON file
    MIN_DISCOUNT: Minimum discount percentage to include in results (0 = show all)
    DELAY_BETWEEN_CARDS: Seconds to wait between scraping cards

Data Structure:
    Each deal is a dictionary with:
    {
        'card': {
            'name': str,
            'expansion': str,
            'card_id': int,
            'historical': {
                'trend': float,    # Market trend price
                'avg30': float,    # 30-day average
                'avg7': float      # 7-day average
            }
        },
        'live_data': {
            'url': str,
            'total_listings': int,
            'cheapest_good_condition': float,
            'cheapest_good_details': {
                'price': float,
                'condition': str,
                'seller': str,
                'quantity': int,
                'country': str
            },
            'top_sellers': [{'seller': str, 'price': float, ...}, ...]
        },
        'discounts': {
            'has_discount': bool,
            'discount_vs_trend': float,    # % discount vs adjusted TREND
            'discount_vs_avg30': float,    # % discount vs AVG30
            'discount_vs_avg7': float       # % discount vs AVG7
        },
        'category': str  # 'excellent', 'good', 'fair', 'expensive', 'no_data'
    }
"""

# ============================================================================
# CONFIGURATION - Edit these values
# ============================================================================
WISHLIST_FILE = "wishlist.json"
MIN_DISCOUNT = 0.0  # Minimum discount percentage (0 = show all deals)
DELAY_BETWEEN_CARDS = 10.0  # Seconds to wait between scraping cards
USE_HISTORICAL_DATA = True  # If False, skips catalogue download and discount calculations
OUTPUT_FILE = None  # Path to save JSON results (None = auto-generate filename based on timestamp)
# ============================================================================

import json
import time
import random
import os
import sys
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from card_lookup import load_cardmarket_data
from mtg_arbitrage.wishlist import load_wishlist, filter_by_wishlist
from mtg_arbitrage.utils import get_cardmarket_url
from mtg_arbitrage.config import get_config

# Import scraper
try:
    from fetch_live_listings_simple import SimpleBrowserScraper
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False
    print("⚠️  Scraper not available. Install dependencies.")


def load_wishlist_cards(wishlist_file: str = "wishlist.json", use_historical: bool = True) -> List[Dict[str, Any]]:
    """
    Load wishlist and optionally match cards from price guide data.
    
    Args:
        wishlist_file: Path to wishlist JSON file
        use_historical: If True, loads price guide to get historical data and match cards.
                       If False, returns wishlist items directly (no historical data).
        
    Returns:
        List of card data dictionaries
    """
    print(f"📋 Loading wishlist from {wishlist_file}...")
    wishlist = load_wishlist(wishlist_file)
    
    if not wishlist:
        print("❌ No wishlist items found")
        return []
    
    if not use_historical:
        # Return wishlist items directly without matching to price guide
        print("⚠️  Historical data disabled - will only show live prices (no discount calculations)")
        cards = []
        for item in wishlist:
            # Create minimal card structure from wishlist
            card = {
                'name': item.get('name', ''),
                'sets': item.get('sets', []),
                'notes': item.get('notes', ''),
                'TREND': 0,
                'AVG30': 0,
                'AVG7': 0,
                'idProduct': None  # Will need to be found via scraping
            }
            cards.append(card)
        print(f"✅ Loaded {len(cards)} wishlist items (no historical data)")
        return cards
    
    # Load Cardmarket data using shared module
    data = load_cardmarket_data()
    
    if data.empty:
        print("❌ No price guide data available")
        return []
    
    print(f"🔍 Matching wishlist items to cards...")
    matched_cards = filter_by_wishlist(data, wishlist)
    
    if matched_cards.empty:
        print("❌ No cards matched from wishlist")
        return []
    
    # Convert to list of dictionaries
    cards = []
    for _, row in matched_cards.iterrows():
        cards.append(row.to_dict())
    
    print(f"✅ Found {len(cards)} matching cards")
    return cards


def scrape_card_prices(card: Dict[str, Any], scraper: SimpleBrowserScraper) -> Optional[Dict[str, Any]]:
    """
    Scrape live prices for a single card.
    
    Args:
        card: Card data dictionary
        scraper: Scraper instance
        
    Returns:
        Live price data or None if failed
    """
    card_id = card.get('idProduct')
    card_name = card.get('name', f"Card ID {card_id}")
    expansion_name = card.get('expansionName')
    
    if not card_id:
        print(f"   ⚠️  No card ID available for {card_name}")
        return None
    
    # Generate Cardmarket URL
    try:
        config = get_config()
        use_german_only = config.get('USE_GERMAN_SELLERS_ONLY', False)
        url = get_cardmarket_url(card_id, card_name, expansion_name, 'direct', include_filters=use_german_only)
        print(f"   🔗 URL: {url}")
    except Exception as e:
        print(f"   ❌ Error generating URL: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Fetch listings
    try:
        print(f"   🌐 Fetching listings from Cardmarket...")
        result = scraper.fetch_listings(url, max_listings=10)
        listings = result.listings
        
        if not listings:
            print(f"   ⚠️  No listings found in response (check debug_html/ for details)")
            # Still try to extract expansion name even if no listings
            scraped_expansion = result.expansion_name
            if not scraped_expansion and '/Singles/' in url:
                try:
                    parts = url.split('/Singles/')
                    if len(parts) > 1:
                        path_part = parts[1].split('?')[0]
                        if '/' in path_part and not path_part.split('/')[0].isdigit():
                            expansion_slug = path_part.split('/')[0]
                            scraped_expansion = expansion_slug.replace('-', ' ').title()
                            print(f"   📦 Extracted expansion from URL: {scraped_expansion}")
                except Exception:
                    pass
            return None
        
        print(f"   ✅ Found {len(listings)} listings")
    except Exception as e:
        print(f"   ❌ Error fetching listings: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Extract expansion from scraped page if available (most reliable)
    scraped_expansion = result.expansion_name
    
    # Fallback: Extract expansion from URL if scraping didn't provide it
    if not scraped_expansion and '/Singles/' in url:
        try:
            # URL format: /Singles/{Expansion}/{CardName} or /Singles/{CardName}-{ID}
            parts = url.split('/Singles/')
            if len(parts) > 1:
                path_part = parts[1].split('?')[0]  # Remove query params
                # Check if it's in format Expansion/CardName (not CardName-ID)
                if '/' in path_part and not path_part.split('/')[0].isdigit():
                    expansion_slug = path_part.split('/')[0]
                    # Convert slug to readable name (e.g., "Revised-Edition" -> "Revised Edition")
                    scraped_expansion = expansion_slug.replace('-', ' ').title()
                    print(f"   📦 Extracted expansion from URL: {scraped_expansion}")
        except Exception as e:
            print(f"   ⚠️  Could not extract expansion from URL: {e}")
    
    if scraped_expansion:
        print(f"   📦 Expansion: {scraped_expansion}")
    
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


def calculate_discounts(live_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate discount percentages compared to other current listings.
    
    Uses the same logic as analyze_sellers.py:
    - Compares cheapest listing against average of positions 2-5
    - This identifies when a listing is significantly cheaper than other current options
    
    Args:
        live_data: Scraped live price data with top_sellers list
        
    Returns:
        Dictionary with discount calculations (no historical data)
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
    # If we have 6+ sellers, use [1:5] (positions 2-5)
    # If we have fewer, use all except the first
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
        'discount_vs_market': discount_vs_market,  # Primary discount metric
        'market_baseline': avg_baseline,  # Average of positions 2-5
        'baseline_count': len(baseline_sellers)  # How many listings used for baseline
    }


def categorize_deal(discounts: Dict[str, Any]) -> str:
    """
    Categorize a deal based on discount vs current market listings.
    
    Uses discount_vs_market (cheapest vs average of positions 2-5).
    
    Args:
        discounts: Discount calculation dictionary
        
    Returns:
        Category string: 'excellent', 'good', 'fair', or 'expensive'
    """
    discount_vs_market = discounts.get('discount_vs_market')
    
    if discount_vs_market is None:
        return 'unknown'
    
    if discount_vs_market >= 7:
        return 'excellent'  # ≥7% below market average (positions 2-5)
    elif discount_vs_market >= 3:
        return 'good'  # 3-7% below market average
    elif discount_vs_market >= 0:
        return 'fair'  # 0-3% below market average (still cheaper)
    else:
        return 'expensive'  # Above market average (not a deal)


def check_wishlist_deals(wishlist_file: str, 
                        delay_between_cards: float = 10.0,
                        use_historical: bool = True) -> List[Dict[str, Any]]:
    """
    Main function: Check wishlist cards for deals.
    
    Args:
        wishlist_file: Path to wishlist JSON file
        delay_between_cards: Seconds to wait between scraping cards
        use_historical: If True, loads price guide for discount calculations.
                       If False, skips catalogue download and only shows live prices.
        
    Returns:
        List of deal dictionaries with card info, live prices, and discounts
    """
    if not SCRAPER_AVAILABLE:
        print("❌ Scraper not available. Cannot check live prices.")
        return []
    
    # Load and match cards
    cards = load_wishlist_cards(wishlist_file, use_historical=use_historical)
    
    if not cards:
        return []
    
    # Initialize scraper (same as main.py)
    scraper = SimpleBrowserScraper(delay_range=(3.0, 5.0), max_retries=3, save_images=True)
    
    print(f"\n💰 Scraping live prices for {len(cards)} cards...")
    print("=" * 60)
    
    deals = []
    
    for i, card in enumerate(cards, 1):
        card_name = card.get('name', 'Unknown')
        expansion = card.get('expansionName') or card.get('sets', ['Unknown'])[0] if card.get('sets') else 'Unknown'
        
        print(f"\n[{i}/{len(cards)}] {card_name} ({expansion})")
        
        # Check if we have card_id (needed for scraping)
        card_id = card.get('idProduct')
        if not card_id and not use_historical:
            print(f"   ⚠️  No card ID available - cannot scrape (need price guide data)")
            deals.append({
                'card': {
                    'name': card_name,
                    'expansion': expansion,
                    'card_id': None,
                    'historical': {
                        'trend': 0,
                        'avg30': 0,
                        'avg7': 0
                    }
                },
                'live_data': None,
                'discounts': None,
                'category': 'no_data'
            })
            continue
        
        # Scrape live prices
        try:
            live_data = scrape_card_prices(card, scraper)
        except Exception as e:
            print(f"   ❌ Exception during scraping: {e}")
            import traceback
            traceback.print_exc()
            live_data = None
        
        if not live_data:
            print(f"   ⚠️  Could not fetch live prices (see details above)")
            deals.append({
                'card': {
                    'name': card_name,
                    'expansion': expansion,
                    'card_id': card.get('idProduct'),
                    'historical': {
                        'trend': card.get('TREND', 0) if use_historical else 0,
                        'avg30': card.get('AVG30', 0) if use_historical else 0,
                        'avg7': card.get('AVG7', 0) if use_historical else 0
                    }
                },
                'live_data': None,
                'discounts': None,
                'category': 'no_data'
            })
            continue
        
        # Calculate discounts based on current market listings (no historical data needed)
        discounts = calculate_discounts(live_data)
        category = categorize_deal(discounts)
        
        # Print summary
        cheapest_good = live_data.get('cheapest_good_condition')
        if cheapest_good:
            print(f"   💶 Best EX+: €{cheapest_good:.2f}")
            
            discount_vs_market = discounts.get('discount_vs_market')
            if discount_vs_market is not None:
                baseline = discounts.get('market_baseline', 0)
                print(f"   📊 Market baseline (avg of positions 2-5): €{baseline:.2f}")
                
                if discount_vs_market >= 7:
                    print(f"   ✅ EXCELLENT: {discount_vs_market:.1f}% below market")
                elif discount_vs_market >= 3:
                    print(f"   🟡 Good: {discount_vs_market:.1f}% below market")
                elif discount_vs_market >= 0:
                    print(f"   🟢 Fair: {discount_vs_market:.1f}% below market")
                else:
                    print(f"   ❌ Expensive: {abs(discount_vs_market):.1f}% above market")
            else:
                print(f"   ⚠️  Not enough listings to calculate discount")
        
        # Use scraped expansion if available, otherwise fall back to price guide data
        final_expansion = live_data.get('expansion_name') or expansion
        if final_expansion == 'Unknown':
            final_expansion = None  # Don't save 'Unknown' as expansion
        
        # Build deal dictionary
        deal = {
            'card': {
                'name': card_name,
                'expansion': final_expansion,
                'card_id': card.get('idProduct'),
                'historical': {
                    'trend': card.get('TREND', 0) if use_historical else 0,
                    'avg30': card.get('AVG30', 0) if use_historical else 0,
                    'avg7': card.get('AVG7', 0) if use_historical else 0
                }
            },
            'live_data': {
                'url': live_data.get('url'),
                'total_listings': live_data.get('total_listings'),
                'available_items_total': live_data.get('available_items_total'),
                'expansion_name': live_data.get('expansion_name'),  # Include scraped expansion
                'cheapest_good_condition': cheapest_good,
                'cheapest_good_details': live_data.get('cheapest_good_details'),
                'top_sellers': live_data.get('top_sellers', [])
            },
            'discounts': discounts,
            'category': category
        }
        
        deals.append(deal)
        
        # Delay between cards (except last one) - same as main.py for consistency
        if i < len(cards):
            delay = random.uniform(10, 15)  # 10-15 seconds between cards (same as main.py)
            print(f"   ⏳ Waiting {delay:.1f}s before next card...")
            time.sleep(delay)
    
    print(f"\n✅ Completed checking {len(cards)} cards")
    return deals


def filter_deals_by_discount(deals: List[Dict[str, Any]], 
                             min_discount: float = 0.0) -> List[Dict[str, Any]]:
    """
    Filter deals to only include those with at least min_discount percentage.
    
    Uses discount_vs_market (cheapest vs average of positions 2-5).
    
    Args:
        deals: List of deal dictionaries
        min_discount: Minimum discount percentage vs market (default: 0 = any discount)
        
    Returns:
        Filtered list of deals
    """
    filtered = []
    
    for deal in deals:
        discounts = deal.get('discounts')
        if not discounts:
            continue
        
        discount_vs_market = discounts.get('discount_vs_market')
        if discount_vs_market is not None and discount_vs_market >= min_discount:
            filtered.append(deal)
    
    return filtered


def print_summary(deals: List[Dict[str, Any]]) -> None:
    """Print a summary of deals."""
    if not deals:
        print("\n❌ No deals found")
        return
    
    # Count by category
    categories = {}
    for deal in deals:
        cat = deal.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total cards checked: {len(deals)}")
    print(f"Excellent deals (≥7% below market): {categories.get('excellent', 0)}")
    print(f"Good deals (3-7% below market): {categories.get('good', 0)}")
    print(f"Fair deals (0-3% below market): {categories.get('fair', 0)}")
    print(f"Expensive (above market): {categories.get('expensive', 0)}")
    print(f"No data: {categories.get('no_data', 0)}")
    
    # Show best deals
    excellent = [d for d in deals if d.get('category') == 'excellent']
    if excellent:
        print(f"\n🎯 Top {min(3, len(excellent))} Excellent Deals:")
        for i, deal in enumerate(excellent[:3], 1):
            card = deal['card']
            live = deal['live_data']
            discounts = deal['discounts']
            
            print(f"\n{i}. {card['name']} ({card['expansion']})")
            if live and live.get('cheapest_good_condition'):
                print(f"   Price: €{live['cheapest_good_condition']:.2f}")
                discount = discounts.get('discount_vs_market', 0)
                baseline = discounts.get('market_baseline', 0)
                if discount is not None:
                    print(f"   Discount: {discount:.1f}% below market (baseline: €{baseline:.2f})")
                details = live.get('cheapest_good_details')
                if details:
                    print(f"   Seller: {details.get('seller')} ({details.get('country')})")


def save_results(deals: List[Dict[str, Any]], output_file: Optional[str] = None) -> str:
    """
    Save deals to JSON file.
    
    Args:
        deals: List of deal dictionaries
        output_file: Path to output file (None = auto-generate)
        
    Returns:
        Path to saved file
    """
    # Create results directory if it doesn't exist
    os.makedirs('results', exist_ok=True)
    
    # Generate filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        wishlist_name = os.path.splitext(os.path.basename(WISHLIST_FILE))[0]
        output_file = f"results/{wishlist_name}_deals_{timestamp}.json"
    
    # Ensure output_file is in results directory if relative path
    if not os.path.isabs(output_file) and not output_file.startswith('results/'):
        output_file = f"results/{output_file}"
    
    # Prepare output data
    output_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'wishlist_file': WISHLIST_FILE,
        'config': {
            'min_discount': MIN_DISCOUNT,
            'delay_between_cards': DELAY_BETWEEN_CARDS,
            'use_historical_data': USE_HISTORICAL_DATA
        },
        'summary': {
            'total_deals': len(deals),
            'excellent': len([d for d in deals if d.get('category') == 'excellent']),
            'good': len([d for d in deals if d.get('category') == 'good']),
            'fair': len([d for d in deals if d.get('category') == 'fair']),
            'expensive': len([d for d in deals if d.get('category') == 'expensive']),
            'no_data': len([d for d in deals if d.get('category') == 'no_data'])
        },
        'deals': deals
    }
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {output_file}")
    return output_file


def main():
    """Main entry point."""
    print("=" * 60)
    print("🃏 MTG Wishlist Deals Checker")
    print("=" * 60)
    print(f"Wishlist file: {WISHLIST_FILE}")
    print(f"Use historical data: {USE_HISTORICAL_DATA}")
    print(f"Min discount: {MIN_DISCOUNT}%")
    print("=" * 60)
    
    try:
        # Check wishlist deals
        print("\n📋 Step 1: Checking wishlist deals...")
        deals = check_wishlist_deals(
            wishlist_file=WISHLIST_FILE,
            delay_between_cards=DELAY_BETWEEN_CARDS,
            use_historical=USE_HISTORICAL_DATA
        )
        
        print(f"\n📊 Step 2: Found {len(deals)} total deals")
        
        # Filter by minimum discount if specified
        if MIN_DISCOUNT > 0:
            original_count = len(deals)
            deals = filter_deals_by_discount(deals, MIN_DISCOUNT)
            print(f"🔍 Step 3: Filtered to deals with ≥{MIN_DISCOUNT}% discount: {len(deals)} deals (from {original_count})")
        else:
            print(f"🔍 Step 3: No filtering applied (showing all deals)")
        
        # Print summary
        print("\n📈 Step 4: Generating summary...")
        print_summary(deals)
        
        # Save results to file (even if empty, so web UI can load it)
        print("\n💾 Step 5: Saving results...")
        try:
            output_file = save_results(deals, OUTPUT_FILE)
            if deals:
                print(f"✅ Results saved successfully to: {output_file}")
            else:
                print(f"⚠️  Saved empty results file (no deals found): {output_file}")
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        print("\n" + "=" * 60)
        print("✅ Analysis complete!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user (Ctrl+C)")
        return []
    except Exception as e:
        print(f"\n\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    return deals


if __name__ == "__main__":
    main()

