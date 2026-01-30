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
DELAY_BETWEEN_CARDS = 15.0  # Minimum seconds to wait between scraping cards (actual: 15-25s random)
USE_HISTORICAL_DATA = True  # If False, skips catalogue download and discount calculations
OUTPUT_FILE = None  # Path to save JSON results (None = auto-generate filename based on timestamp)
# ============================================================================

import json
import time
import random
import os
import sys
import math
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from card_lookup import load_cardmarket_data
from mtg_arbitrage.wishlist import load_wishlist, filter_by_wishlist
from mtg_arbitrage.utils import get_cardmarket_url, map_condition_to_cardmarket_code
from mtg_arbitrage.config import get_config

# Import database module for per-user wishlist support
try:
    import database
    DATABASE_AVAILABLE = True
    # Initialize database to ensure schema is up to date (including migrations)
    database.init_db()
except ImportError:
    DATABASE_AVAILABLE = False
    print("⚠️  Database module not available. Per-user wishlists will not work.")

# Import scraper
try:
    from fetch_live_listings_simple import SimpleBrowserScraper
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False
    print("⚠️  Scraper not available. Install dependencies.")


def load_all_wishlists(source: str = "json") -> List[Dict[str, Any]]:
    """
    Load wishlists from different sources based on the source parameter.
    
    Args:
        source: Where to load wishlists from:
            - "json": Load from wishlist.json only (original behavior)
            - "db": Load union of all users' wishlists from database (non-archived)
            - "all": Load both JSON + all database wishlists combined
            
    Returns:
        List of wishlist item dictionaries, deduplicated by (card name, expansion)
    """
    print(f"📋 Loading wishlists from source: {source}")
    
    all_items = []
    seen_keys = set()  # Track (card_name_lower, expansion) to deduplicate
    
    def add_item(item: Dict[str, Any], source_label: str = ""):
        """Add item to list if not a duplicate."""
        name = item.get('name', '').lower().strip()
        if not name:
            return False
            
        # Create key from name and sets (first set if available)
        sets = item.get('sets', [])
        expansion = sets[0].lower().strip() if sets else ''
        key = (name, expansion)
        
        if key not in seen_keys:
            seen_keys.add(key)
            all_items.append(item)
            return True
        return False
    
    # Load from JSON file if source is "json" or "all"
    if source in ("json", "all"):
        if os.path.exists(WISHLIST_FILE):
            try:
                json_wishlist = load_wishlist(WISHLIST_FILE)
                added_count = 0
                for item in json_wishlist:
                    if add_item(item, "json"):
                        added_count += 1
                print(f"   📄 Loaded {added_count} items from {WISHLIST_FILE}")
            except Exception as e:
                print(f"   ⚠️  Error loading {WISHLIST_FILE}: {e}")
        else:
            print(f"   ⚠️  JSON file {WISHLIST_FILE} not found")
    
    # Load from database if source is "db" or "all"
    if source in ("db", "all"):
        if not DATABASE_AVAILABLE:
            print(f"   ⚠️  Database not available, skipping database wishlists")
        else:
            try:
                # Get all users from database
                conn = database.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id, username FROM users")
                users = cursor.fetchall()
                conn.close()
                
                total_db_items = 0
                for user in users:
                    user_id = user["id"]
                    username = user["username"]
                    
                    # Get non-archived wishlist items for this user
                    user_wishlist = database.get_user_wishlist(user_id, include_archived=False)
                    
                    added_count = 0
                    for item in user_wishlist:
                        if add_item(item, f"db:{username}"):
                            added_count += 1
                    
                    if added_count > 0:
                        print(f"   👤 User '{username}': added {added_count} unique items")
                    total_db_items += added_count
                
                print(f"   🗄️  Total from database: {total_db_items} unique items from {len(users)} users")
                
            except Exception as e:
                print(f"   ⚠️  Error loading from database: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"   ✅ Total unique wishlist items: {len(all_items)}")
    return all_items


def load_wishlist_cards(wishlist_file: str = "wishlist.json", use_historical: bool = True, source: str = "json") -> List[Dict[str, Any]]:
    """
    Load wishlist and optionally match cards from price guide data.
    
    Args:
        wishlist_file: Path to wishlist JSON file (used when source="json")
        use_historical: If True, loads price guide to get historical data and match cards.
                       If False, returns wishlist items directly (no historical data).
        source: Where to load wishlists from:
            - "json": Load from wishlist_file only (original behavior)
            - "db": Load union of all users' wishlists from database
            - "all": Load both JSON + all database wishlists combined
        
    Returns:
        List of card data dictionaries
    """
    # Use configurable loading based on source
    if source in ("db", "all"):
        print(f"📋 Loading wishlists from source: {source}...")
        wishlist = load_all_wishlists(source)
    else:
        print(f"📋 Loading wishlist from {wishlist_file}...")
        wishlist = load_wishlist(wishlist_file)
    
    if not wishlist:
        print("❌ No wishlist items found")
        return []
    
    print(f"📊 Collection has {len(wishlist)} items")
    
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
                'idProduct': None,  # Will need to be found via scraping
                'collection_condition': item.get('condition'),  # Preserve condition from collection
                'alternative_name': item.get('alternative_name'),
                'language': item.get('language'),
                'foil': item.get('foil', False),
                'old_school_legal': item.get('old_school_legal', False),
                'premodern_legal': item.get('premodern_legal', False)
            }
            cards.append(card)
        print(f"✅ Loaded {len(cards)} wishlist items (no historical data)")
        return cards
    
    # Load Cardmarket data using shared module
    data = load_cardmarket_data()
    
    if data.empty:
        print("❌ No price guide data available")
        return []
    
    print(f"🔍 Matching wishlist items to cards in price guide...")
    matched_cards = filter_by_wishlist(data, wishlist)
    
    if matched_cards.empty:
        print("❌ No cards matched from wishlist")
        print(f"💡 This could mean:")
        print(f"   - Cards not in price guide data")
        print(f"   - Set names don't match exactly")
        print(f"   - Cards have no sales data")
        return []
    
    # Convert to list of dictionaries and preserve condition from wishlist/collection
    cards = []
    matched_wishlist_items = set()  # Track which wishlist items were matched
    
    for _, row in matched_cards.iterrows():
        card_dict = row.to_dict()
        card_name = card_dict.get('name', '').lower()
        card_expansion_raw = card_dict.get('expansionName', '')
        # Convert to string, handling None/NaN/float cases
        if card_expansion_raw is None or (isinstance(card_expansion_raw, float) and math.isnan(card_expansion_raw)):
            card_expansion = ''
        else:
            card_expansion = str(card_expansion_raw)
        
        # Try to find matching wishlist item to preserve condition and alternative_name
        # Match by name first, then by expansion if available
        matching_item = None
        for item in wishlist:
            item_name = item.get('name', '').lower()
            item_alt_name = item.get('alternative_name', '').lower()
            # Match if main name matches OR alternative name matches
            if item_name == card_name or (item_alt_name and item_alt_name == card_name):
                # If expansion matches or item has no sets specified, use this item
                item_sets = item.get('sets', [])
                if not item_sets or card_expansion in item_sets or any(card_expansion in str(s) for s in item_sets):
                    matching_item = item
                    matched_wishlist_items.add(item.get('name'))
                    break
        
        # Preserve condition, alternative_name, foil, and format fields if found in wishlist/collection item
        if matching_item:
            if 'condition' in matching_item:
                card_dict['collection_condition'] = matching_item['condition']
            if 'alternative_name' in matching_item:
                card_dict['alternative_name'] = matching_item['alternative_name']
            if 'language' in matching_item:
                card_dict['collection_language'] = matching_item['language']
            if 'foil' in matching_item:
                card_dict['foil'] = matching_item['foil']
            if 'old_school_legal' in matching_item:
                card_dict['old_school_legal'] = matching_item['old_school_legal']
            if 'premodern_legal' in matching_item:
                card_dict['premodern_legal'] = matching_item['premodern_legal']
        
        cards.append(card_dict)
    
    matched_count = len(cards)
    total_items = len(wishlist)
    unmatched = total_items - matched_count
    
    print(f"\n✅ Found {matched_count} matching cards (out of {total_items} collection items)")
    
    # Add fallback cards for unmatched items (will scrape without card_id)
    if unmatched > 0:
        print(f"\n⚠️  {unmatched} collection items couldn't be matched to price guide (will use fallback):")
        # Show which items failed and add fallback entries
        for item in wishlist:
            item_name = item.get('name', 'Unknown')
            if item_name not in matched_wishlist_items:
                sets = item.get('sets', [])
                alt_name = item.get('alternative_name', '')
                language = item.get('language', '')
                print(f"   ⚠️  {item_name}", end="")
                if sets:
                    print(f" ({', '.join(sets)})", end="")
                if alt_name:
                    print(f" [alt: {alt_name}]", end="")
                if language:
                    print(f" [lang: {language}]", end="")
                print(" → Will scrape without card ID")
                
                # Create fallback card entry
                # Use first set as expansion, or map set names if needed
                expansion = sets[0] if sets else None
                if expansion and language:
                    # Map set names (e.g., Revised + Italian → Foreign White Bordered)
                    from mtg_arbitrage.wishlist import get_cardmarket_set_name
                    expansion = get_cardmarket_set_name(expansion, language)
                
                fallback_card = {
                    'name': item_name,
                    'expansionName': expansion,
                    'sets': sets,
                    'alternative_name': alt_name,
                    'language': language,
                    'foil': item.get('foil', False),
                    'collection_condition': item.get('condition'),
                    'old_school_legal': item.get('old_school_legal', False),
                    'premodern_legal': item.get('premodern_legal', False),
                    'TREND': 0,
                    'AVG30': 0,
                    'AVG7': 0,
                    'idProduct': None  # No card ID - will use fallback URL building
                }
                cards.append(fallback_card)
        
        print(f"\n   💡 Fallback mode: Will scrape using expansion + card name (no historical data)")
    
    return cards


def scrape_card_prices(card: Dict[str, Any], scraper: SimpleBrowserScraper) -> Optional[Dict[str, Any]]:
    """
    Scrape live prices for a single card.
    
    Args:
        card: Card data dictionary (may contain 'collection_condition' for collection items)
        scraper: Scraper instance
        
    Returns:
        Live price data or None if failed
    """
    card_id = card.get('idProduct')
    card_name = card.get('name', f"Card ID {card_id}")
    expansion_name = card.get('expansionName')
    sets = card.get('sets', [])
    
    # Prefer sets array over expansionName for mapping (sets array has the original collection set name)
    # This ensures we catch patterns like "Fourth Edition (Foreign Black Bordered)"
    set_to_map = sets[0] if sets else expansion_name
    
    # Fallback: if no expansionName, use sets array
    if not expansion_name:
        if sets:
            expansion_name = sets[0]
    
    # Always map set name (handles language-based mappings and set name patterns)
    language = card.get('language') or card.get('collection_language')
    if set_to_map:
        from mtg_arbitrage.wishlist import get_cardmarket_set_name
        original_expansion = expansion_name or set_to_map
        mapped_expansion = get_cardmarket_set_name(set_to_map, language)
        if mapped_expansion != set_to_map:
            print(f"   🔄 Mapped expansion: '{set_to_map}' -> '{mapped_expansion}'")
            expansion_name = mapped_expansion
        elif expansion_name != mapped_expansion:
            expansion_name = mapped_expansion
    
    collection_condition = card.get('collection_condition')  # Condition from collection item
    
    # If no card_id, we'll use fallback URL building (expansion + card name)
    if not card_id:
        if not expansion_name:
            print(f"   ❌ No card ID and no expansion name available for {card_name}")
            print(f"      Cannot build Cardmarket URL - need either card_id or expansion name")
            return None
        print(f"   ⚠️  No card ID available for {card_name} - using fallback URL (expansion + name)")
    
    # Determine minimum condition for URL
    # If collection_condition exists, use it; otherwise default to Excellent+ (3)
    if collection_condition:
        min_condition_code = map_condition_to_cardmarket_code(collection_condition)
        print(f"   📋 Using collection condition: {collection_condition} (code: {min_condition_code})")
    else:
        min_condition_code = 3  # Default to Excellent+ for wishlist
        print(f"   📋 No condition specified, using Excellent+ (code: 3)")
    
    # Generate Cardmarket URL
    try:
        config = get_config()
        use_german_only = config.get('USE_GERMAN_SELLERS_ONLY', False)
        alternative_name = card.get('alternative_name')  # Use alternative_name if available (e.g., for foreign card names)
        is_foil = card.get('foil', False)  # Check if card is foil
        card_language = language  # Use language from card (already extracted above)
        
        # If no card_id, pass None and URL builder will use expansion + card name
        url = get_cardmarket_url(card_id, card_name, expansion_name, 'direct', include_filters=use_german_only, min_condition=min_condition_code, alternative_name=alternative_name, is_foil=is_foil, language=card_language)
        print(f"   🔗 URL: {url}")
        if alternative_name:
            print(f"   📝 Using alternative_name: {alternative_name}")
        if is_foil:
            print(f"   ✨ Filtering for foil versions only")
        if card_language:
            print(f"   🌍 Filtering for language: {card_language}")
        if not card_id:
            print(f"   📝 Fallback mode: URL built from expansion '{expansion_name}' + card name")
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
    
    # Extract prices and find best listing matching the condition
    prices = [l.price for l in listings if l.price > 0]
    if not prices:
        return None
    
    # Determine which conditions to accept based on collection_condition
    # Cardmarket condition codes: 1=MT, 2=NM, 3=EX, 4=GD, 5=LP, 6=PL, 7=PO
    collection_condition = card.get('collection_condition')
    if collection_condition:
        min_condition_code = map_condition_to_cardmarket_code(collection_condition)
        # Map condition codes to accepted condition strings
        condition_map = {
            1: ['MT'],  # Mint only
            2: ['NM', 'MT'],  # Near Mint or better
            3: ['EX', 'NM', 'MT'],  # Excellent or better
            4: ['GD', 'EX', 'NM', 'MT'],  # Good or better
            5: ['LP', 'GD', 'EX', 'NM', 'MT'],  # Lightly Played or better
            6: ['PL', 'LP', 'GD', 'EX', 'NM', 'MT'],  # Played or better
            7: ['PO', 'PL', 'LP', 'GD', 'EX', 'NM', 'MT']  # Poor or better (all)
        }
        accepted_conditions = condition_map.get(min_condition_code, ['EX', 'NM', 'MT'])
        print(f"   🔍 Filtering for conditions: {', '.join(accepted_conditions)}")
    else:
        # Default to EX+ for wishlist (no condition specified)
        accepted_conditions = ['EX', 'NM', 'MT']
        print(f"   🔍 Filtering for EX+ conditions: {', '.join(accepted_conditions)}")
    
    # Find listings matching the condition requirement
    good_condition_listings = [
        l for l in listings 
        if l.condition.upper() in [c.upper() for c in accepted_conditions]
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


def scan_single_collection_card(collection_item: Dict[str, Any],
                                use_historical: bool = True) -> List[Dict[str, Any]]:
    """
    Scan a single collection card for market deals.
    
    This function creates a temporary wishlist file with a single card and runs
    the scan on it. Useful for auto-scanning newly added collection cards.
    
    Args:
        collection_item: Collection item dictionary with 'name', 'sets', etc.
        use_historical: If True, loads price guide for discount calculations.
        
    Returns:
        List of deal dictionaries (usually one per set, or empty if scan fails)
    """
    import tempfile
    
    if not SCRAPER_AVAILABLE:
        print("❌ Scraper not available. Cannot check live prices.", flush=True)
        return []
    
    # Create temporary wishlist file with single card (wishlist format is an array)
    temp_wishlist = [collection_item]
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(temp_wishlist, f, indent=2, ensure_ascii=False)
        temp_file = f.name
    
    try:
        # Run scan on temporary file
        deals = check_wishlist_deals(
            wishlist_file=temp_file,
            delay_between_cards=0.0,  # No delay needed for single card
            use_historical=use_historical
        )
        return deals
    except Exception as e:
        print(f"❌ Error scanning single card: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return []
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file)
        except Exception:
            pass


def check_wishlist_deals(wishlist_file: str, 
                        delay_between_cards: float = 10.0,
                        use_historical: bool = True,
                        source: str = "json") -> List[Dict[str, Any]]:
    """
    Main function: Check wishlist cards for deals.
    
    Args:
        wishlist_file: Path to wishlist JSON file (used when source="json")
        delay_between_cards: Seconds to wait between scraping cards
        use_historical: If True, loads price guide for discount calculations.
                       If False, skips catalogue download and only shows live prices.
        source: Where to load wishlists from:
            - "json": Load from wishlist_file only (original behavior)
            - "db": Load union of all users' wishlists from database
            - "all": Load both JSON + all database wishlists combined
        
    Returns:
        List of deal dictionaries with card info, live prices, and discounts
    """
    if not SCRAPER_AVAILABLE:
        print("❌ Scraper not available. Cannot check live prices.")
        return []
    
    # Load and match cards
    cards = load_wishlist_cards(wishlist_file, use_historical=use_historical, source=source)
    
    if not cards:
        return []
    
    # Initialize scraper with safer, more human-like delays
    scraper = SimpleBrowserScraper(delay_range=(5.0, 8.0), max_retries=3, save_images=True)
    
    print(f"\n💰 Scraping live prices for {len(cards)} cards...")
    print("=" * 60)
    
    deals = []
    
    # Track if we've been rate limited to save partial results
    rate_limited = False
    
    # Check which cards already have today's scan data (if using database)
    already_scanned = set()
    if source in ("db", "all") and DATABASE_AVAILABLE:
        try:
            already_scanned = database.get_cards_with_scan_date()
            if already_scanned:
                print(f"📊 Found {len(already_scanned)} cards already scanned today - will skip them")
        except Exception as e:
            print(f"⚠️  Could not check existing scan data: {e}")
    
    for i, card in enumerate(cards, 1):
        card_name = card.get('name', 'Unknown')
        expansion = card.get('expansionName') or card.get('sets', ['Unknown'])[0] if card.get('sets') else 'Unknown'
        
        # Check if this card already has today's scan data
        card_key = (card_name, expansion)
        if card_key in already_scanned:
            print(f"\n[{i}/{len(cards)}] {card_name} ({expansion}) - ⏭️  Already scanned today, skipping...")
            # Still add to deals list with existing data (we'll load it from DB later if needed)
            # For now, skip scraping but add placeholder
            deals.append({
                'card': {
                    'name': card_name,
                    'expansion': expansion,
                    'card_id': card.get('idProduct'),
                    'old_school_legal': card.get('old_school_legal', False),
                    'premodern_legal': card.get('premodern_legal', False),
                    'historical': {
                        'trend': card.get('TREND', 0) if use_historical else 0,
                        'avg30': card.get('AVG30', 0) if use_historical else 0,
                        'avg7': card.get('AVG7', 0) if use_historical else 0
                    }
                },
                'live_data': None,
                'discounts': None,
                'category': 'skipped'  # Mark as skipped
            })
            continue
        
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
                    'old_school_legal': card.get('old_school_legal', False),
                    'premodern_legal': card.get('premodern_legal', False),
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
            error_msg = str(e)
            print(f"   ❌ Exception during scraping: {e}")
            import traceback
            traceback.print_exc()
            
            # Check if this is a rate limit exception
            if 'RATE LIMITED' in error_msg.upper() or '429' in error_msg:
                rate_limited = True
                print(f"\n⚠️  Rate limiting detected! Saving partial results ({len(deals)} cards processed so far)...")
                # Save partial results before stopping
                try:
                    partial_output = save_results(deals, OUTPUT_FILE, wishlist_file, source)
                    print(f"💾 Partial results saved to: {partial_output}")
                    print(f"⚠️  Script stopped due to rate limiting. {len(deals)}/{len(cards)} cards processed.")
                except Exception as save_error:
                    print(f"❌ Failed to save partial results: {save_error}")
            
            live_data = None
        
        if not live_data:
            print(f"   ⚠️  Could not fetch live prices (see details above)")
            deals.append({
                'card': {
                    'name': card_name,
                    'expansion': expansion,
                    'card_id': card.get('idProduct'),
                    'old_school_legal': card.get('old_school_legal', False),
                    'premodern_legal': card.get('premodern_legal', False),
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
        card_condition = card.get('collection_condition')
        condition_label = card_condition if card_condition else "EX+"
        if cheapest_good:
            print(f"   💶 Best {condition_label}: €{cheapest_good:.2f}")
            
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
                'old_school_legal': card.get('old_school_legal', False),
                'premodern_legal': card.get('premodern_legal', False),
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
        
        # Save incrementally to database (if using database source)
        if source in ("db", "all") and DATABASE_AVAILABLE:
            try:
                success = database.save_single_scan_deal(deal)
                if success:
                    print(f"   💾 Saved to database")
                else:
                    print(f"   ⚠️  Failed to save to database")
            except Exception as e:
                print(f"   ⚠️  Error saving to database: {e}")
        
        # Save incremental JSON backup every 10 cards to prevent data loss
        if i % 10 == 0 and i < len(cards):
            try:
                # Save incremental backup (with .partial suffix)
                incremental_file = save_results(deals, None, wishlist_file, source)
                if incremental_file and incremental_file.endswith('.json'):
                    # Rename to .partial.json for incremental saves
                    import os
                    partial_file = incremental_file.replace('.json', '.partial.json')
                    if os.path.exists(incremental_file):
                        os.rename(incremental_file, partial_file)
                        print(f"   💾 Incremental JSON backup: {partial_file} ({len(deals)} cards)")
            except Exception as e:
                print(f"   ⚠️  Could not save incremental backup: {e}")
        
        # Stop if rate limited
        if rate_limited:
            print(f"\n⚠️  Stopping scan due to rate limiting. Processed {len(deals)}/{len(cards)} cards.")
            break
        
        # Delay between cards (except last one) - longer delays to avoid rate limiting
        if i < len(cards):
            delay = random.uniform(15, 25)  # 15-25 seconds between cards to avoid rate limiting
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


def save_results(deals: List[Dict[str, Any]], output_file: Optional[str] = None, wishlist_file: Optional[str] = None, source: str = "json") -> str:
    """
    Save deals to JSON file and/or database.
    
    Args:
        deals: List of deal dictionaries
        output_file: Path to output file (None = auto-generate)
        wishlist_file: Source wishlist file (for generating filename, defaults to WISHLIST_FILE)
        source: Where wishlist was loaded from:
            - "json": Save to JSON file only (original behavior, backward compatible)
            - "db" or "all": Save to database via save_scan_deals()
        
    Returns:
        Path to saved file (or "database" if saved to DB only)
    """
    saved_to = []
    
    # Always save to JSON file for source="json" (backward compatible)
    # Also save to JSON for "db" and "all" modes to maintain history
    if True:  # Always save to JSON for now - keeps file-based history
        # Create results directory if it doesn't exist
        os.makedirs('results', exist_ok=True)
        
        # Generate filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # Use provided wishlist_file or fall back to global WISHLIST_FILE
            source_file = wishlist_file if wishlist_file else WISHLIST_FILE
            wishlist_name = os.path.splitext(os.path.basename(source_file))[0]
            output_file = f"results/{wishlist_name}_deals_{timestamp}.json"
        
        # Ensure output_file is in results directory if relative path
        if not os.path.isabs(output_file) and not output_file.startswith('results/'):
            output_file = f"results/{output_file}"
        
        # Prepare output data
        source_file = wishlist_file if wishlist_file else WISHLIST_FILE
        output_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'wishlist_file': source_file,
            'source': source,  # Track which source was used
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
        
        print(f"\n💾 Results saved to JSON: {output_file}")
        saved_to.append(f"JSON: {output_file}")
    
    # Save to database if source is "db" or "all"
    # Note: We don't call save_scan_deals here anymore because we're saving incrementally
    # during the scan. This function is only called at the end for final JSON save.
    # If you want to ensure all deals are in DB, they should already be there from incremental saves.
    if source in ("db", "all"):
        if not DATABASE_AVAILABLE:
            print(f"⚠️  Database not available, skipping database save")
        else:
            # Count how many deals were saved incrementally (they should already be in DB)
            try:
                # datetime is already imported at module level
                today = datetime.now().strftime('%Y-%m-%d')
                existing_count = len(database.get_cards_with_scan_date(today))
                if existing_count > 0:
                    print(f"💾 Database already contains {existing_count} deals for today (saved incrementally)")
                    saved_to.append(f"Database ({existing_count} deals)")
            except Exception as e:
                print(f"⚠️  Could not verify database contents: {e}")
    
    print(f"\n💾 Saved to: {', '.join(saved_to)}")
    return output_file if output_file else "database"


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
        # Try to save partial results before exiting
        if 'deals' in locals() and deals:
            try:
                print(f"\n💾 Attempting to save partial results ({len(deals)} cards)...")
                partial_output = save_results(deals, OUTPUT_FILE, WISHLIST_FILE, source)
                print(f"✅ Partial results saved to: {partial_output}")
            except Exception as save_error:
                print(f"⚠️  Could not save partial results: {save_error}")
        return []
    except Exception as e:
        print(f"\n\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        # Try to save partial results if we have any
        if 'deals' in locals() and deals:
            try:
                error_msg = str(e)
                is_rate_limit = 'RATE LIMITED' in error_msg.upper() or '429' in error_msg
                print(f"\n💾 Attempting to save partial results ({len(deals)} cards)...")
                partial_output = save_results(deals, OUTPUT_FILE, WISHLIST_FILE, source)
                if is_rate_limit:
                    print(f"⚠️  Rate limiting detected. Partial results saved to: {partial_output}")
                    print(f"   Processed {len(deals)} cards before rate limit.")
                else:
                    print(f"✅ Partial results saved to: {partial_output}")
            except Exception as save_error:
                print(f"⚠️  Could not save partial results: {save_error}")
        return []
    
    return deals


if __name__ == "__main__":
    main()

