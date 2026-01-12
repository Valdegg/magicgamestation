#!/usr/bin/env python3
"""
Check which collection items don't have market prices and optionally fetch them.

This script:
1. Loads the collection
2. Expands to individual cards (one per set)
3. Matches against latest market scan results
4. Identifies cards without market prices
5. Optionally fetches market data for missing cards
6. Saves results to JSON files
"""

import json
import os
import sys
import glob
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configuration
COLLECTION_FILE = "collection.json"


def normalize_expansion_for_lookup(exp: str) -> Optional[str]:
    """
    Normalize expansion name for lookup (remove apostrophes, lowercase).
    Handles variations like "Urza's Legacy" vs "Urzas Legacy".
    Also handles "Revised" vs "Revised Edition" by normalizing both to "revised".
    """
    if not exp:
        return None
    # Remove apostrophes and normalize
    normalized = exp.replace("'", "").replace("'", "").replace("'", "").lower()
    # Handle common expansion name variations
    # "Revised Edition" -> "revised", "Revised" -> "revised"
    if normalized.startswith('revised'):
        return 'revised'
    # "Unlimited Edition" -> "unlimited", "Unlimited" -> "unlimited"
    if normalized.startswith('unlimited'):
        return 'unlimited'
    # "Fourth Edition" -> "fourth edition" (keep full name for this one)
    return normalized


def load_collection(filepath: str = COLLECTION_FILE) -> List[Dict[str, Any]]:
    """Load collection from JSON file."""
    try:
        if not os.path.exists(filepath):
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            collection = json.load(f)
        return collection
    except Exception as e:
        print(f"Error loading collection: {e}")
        return []


def load_latest_collection_scan_results() -> Dict[str, Dict[str, Any]]:
    """
    Load the most recent collection market scan results and create a lookup dictionary.
    
    Returns:
        Dictionary mapping (card_name, expansion, language) -> market data
    """
    results_dir = 'results'
    if not os.path.exists(results_dir):
        print(f"⚠️  Market scan: results directory not found: {results_dir}")
        return {}
    
    # Find all collection scan result files
    json_files = glob.glob(os.path.join(results_dir, 'collection_deals_*.json'))
    if not json_files:
        print(f"⚠️  Market scan: No collection_deals_*.json files found in {results_dir}")
        return {}
    
    # Sort by modification time, newest first
    json_files.sort(key=os.path.getmtime, reverse=True)
    latest_file = json_files[0]
    print(f"📊 Market scan: Loading latest scan results from {latest_file}")
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        print(f"📊 Market scan: File loaded, timestamp: {results.get('timestamp', 'unknown')}")
        
        # Normalize deal data
        deals = []
        if 'deals' in results or 'candidates' in results:
            deal_list = results.get('deals', []) or results.get('candidates', [])
            print(f"📊 Market scan: Found {len(deal_list)} deals in scan results")
            for deal in deal_list:
                card = deal.get('card', {})
                live_data = deal.get('live_data')
                
                # Skip deals without live_data (no_data category)
                if live_data is None:
                    continue
                
                url = live_data.get('url', '')
                
                # Extract language from URL if present (language=1,2,3,4,5)
                language_code = None
                language_name = None
                if url and 'language=' in url:
                    try:
                        match = re.search(r'language=(\d+)', url)
                        if match:
                            language_code = int(match.group(1))
                            # Map language code to language name (normalize English to None)
                            language_map = {1: None, 2: 'French', 3: 'German', 4: 'Spanish', 5: 'Italian'}
                            language_name = language_map.get(language_code, None)
                    except Exception as e:
                        pass
                
                # Use expansion_name from live_data (scraped) as primary source, fallback to card expansion
                expansion_from_live = live_data.get('expansion_name')
                expansion_from_card = card.get('expansion') or card.get('expansionName')
                # Prefer live_data expansion_name as it's what was actually scraped
                expansion = expansion_from_live or expansion_from_card or None
                
                normalized = {
                    'card_name': card.get('name', ''),
                    'expansion': expansion,
                    'price': live_data.get('cheapest_good_condition'),
                    'discount': deal.get('discounts', {}).get('discount_vs_market'),
                    'category': deal.get('category', 'unknown'),
                    'url': url,
                    'language': language_name,
                    'language_code': language_code,
                    'timestamp': results.get('timestamp', '')
                }
                deals.append(normalized)
        else:
            print(f"⚠️  Market scan: No 'deals' or 'candidates' key in results")
        
        # Create lookup dictionary: (name_lower, expansion_lower, language) -> market_data
        market_lookup = {}
        for deal in deals:
            card_name = deal.get('card_name', '').lower()
            expansion = deal.get('expansion')
            expansion_normalized = normalize_expansion_for_lookup(expansion) if expansion else None
            language = deal.get('language')
            
            # Create key with language (None for English/default)
            key = (card_name, expansion_normalized, language)
            
            # Store all language variants - prefer non-None language if available, otherwise keep first
            if key not in market_lookup:
                market_lookup[key] = deal
            elif deal.get('price') and language:  # Prefer entries with explicit language
                market_lookup[key] = deal
        
        print(f"✅ Market scan: Created lookup with {len(market_lookup)} entries")
        return market_lookup
    except Exception as e:
        print(f"❌ Error loading collection scan results: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return {}


def expand_collection_to_cards(collection: List[Dict[str, Any]], market_data: Dict) -> List[Dict[str, Any]]:
    """
    Expand collection items to show one card per set.
    Includes market value from market_data lookup.
    """
    cards = []
    
    for index, item in enumerate(collection):
        card_name = item.get('name', 'Unknown')
        sets = item.get('sets', [])
        notes = item.get('notes', '')
        buy_price = item.get('buy_price')
        condition = item.get('condition')
        source = item.get('source')
        sell_price = item.get('sell_price')
        language = item.get('language')
        foil = item.get('foil', False)
        
        # If no sets specified, create one entry with no set
        if not sets:
            # Try to find market data
            market_value = None
            collection_language = language if language and language.lower() not in ['', 'english'] else None
            lookup_key = (card_name.lower(), None, collection_language)
            if lookup_key in market_data:
                market_info = market_data[lookup_key]
                market_value = market_info.get('price')
            else:
                # Try without language (fallback for English)
                lookup_key_no_lang = (card_name.lower(), None, None)
                if lookup_key_no_lang in market_data:
                    market_info = market_data[lookup_key_no_lang]
                    market_value = market_info.get('price')
            
            cards.append({
                'name': card_name,
                'expansion': None,
                'notes': notes,
                'buy_price': buy_price,
                'condition': condition,
                'source': source,
                'sell_price': sell_price,
                'language': language,
                'foil': foil,
                'market_value': market_value,
                'collection_index': index
            })
        else:
            # Create one card per set
            for expansion in sets:
                # Try to find market data for this specific card+expansion
                market_value = None
                
                # Map expansion name if needed (for foreign languages)
                # This handles cases like "Revised Edition" + Italian -> "Foreign White Bordered"
                mapped_expansion = expansion
                if expansion and language:
                    try:
                        from mtg_arbitrage.wishlist import get_cardmarket_set_name
                        mapped_expansion = get_cardmarket_set_name(expansion, language)
                    except Exception:
                        # Fallback: manual mapping if import fails
                        expansion_lower = expansion.lower()
                        language_lower = language.lower() if language else ''
                        
                        # Revised Edition + non-English language -> Foreign White Bordered
                        if 'revised' in expansion_lower and language_lower not in ['', 'english']:
                            # Check if it's black bordered first
                            if 'black border' in expansion_lower:
                                mapped_expansion = 'Foreign Black Bordered'
                            else:
                                mapped_expansion = 'Foreign White Bordered'
                        # Fourth Edition (Foreign Black Border) -> Fourth Edition Black Bordered
                        elif 'fourth edition' in expansion_lower and 'black border' in expansion_lower:
                            mapped_expansion = 'Fourth Edition Black Bordered'
                        # Fourth Edition (Foreign Black Bordered) -> Fourth Edition Black Bordered
                        elif 'fourth edition' in expansion_lower and 'foreign' in expansion_lower:
                            mapped_expansion = 'Fourth Edition Black Bordered'
                
                # Try exact match first with mapped expansion
                mapped_exp_normalized = normalize_expansion_for_lookup(mapped_expansion) if mapped_expansion else None
                collection_language = language if language and language.lower() not in ['', 'english'] else None
                
                # Try with language first
                lookup_key = (card_name.lower(), mapped_exp_normalized, collection_language)
                if lookup_key in market_data:
                    market_info = market_data[lookup_key]
                    market_value = market_info.get('price')
                else:
                    # Try without language (fallback for English)
                    lookup_key_no_lang = (card_name.lower(), mapped_exp_normalized, None)
                    if lookup_key_no_lang in market_data:
                        market_info = market_data[lookup_key_no_lang]
                        market_value = market_info.get('price')
                    else:
                        # Try with original expansion name (in case mapping was wrong)
                        orig_exp_normalized = normalize_expansion_for_lookup(expansion) if expansion else None
                        lookup_key_orig = (card_name.lower(), orig_exp_normalized, collection_language)
                        if lookup_key_orig in market_data:
                            market_info = market_data[lookup_key_orig]
                            market_value = market_info.get('price')
                        else:
                            lookup_key_orig_no_lang = (card_name.lower(), orig_exp_normalized, None)
                            if lookup_key_orig_no_lang in market_data:
                                market_info = market_data[lookup_key_orig_no_lang]
                                market_value = market_info.get('price')
                
                cards.append({
                    'name': card_name,
                    'expansion': expansion,
                    'notes': notes,
                    'buy_price': buy_price,
                    'condition': condition,
                    'source': source,
                    'sell_price': sell_price,
                    'language': language,
                    'foil': foil,
                    'market_value': market_value,
                    'collection_index': index
                })
    
    return cards


def find_cards_without_market_prices():
    """Find all collection cards that don't have market prices."""
    
    print("=" * 60)
    print("🔍 Checking Collection for Missing Market Prices")
    print("=" * 60)
    
    # Load collection
    print("\n📋 Loading collection...")
    collection = load_collection()
    print(f"   Found {len(collection)} collection items")
    
    # Load market data
    print("\n📊 Loading market scan data...")
    market_data = load_latest_collection_scan_results()
    print(f"   Found {len(market_data)} market scan entries")
    
    # Expand collection to cards
    print("\n🃏 Expanding collection to individual cards...")
    cards = expand_collection_to_cards(collection, market_data)
    print(f"   Expanded to {len(cards)} cards")
    
    # Find cards without market prices
    print("\n🔍 Checking for missing market prices...")
    cards_without_market = []
    cards_with_market = []
    
    for card in cards:
        market_value = card.get('market_value')
        if market_value is None:
            cards_without_market.append({
                'name': card.get('name'),
                'expansion': card.get('expansion'),
                'language': card.get('language'),
                'foil': card.get('foil', False),
                'buy_price': card.get('buy_price'),
                'condition': card.get('condition'),
                'collection_index': card.get('collection_index'),
                'sets': collection[card.get('collection_index')].get('sets', []) if card.get('collection_index') is not None else [],
                'notes': card.get('notes', '')
            })
        else:
            cards_with_market.append({
                'name': card.get('name'),
                'expansion': card.get('expansion'),
                'market_value': market_value
            })
    
    print(f"\n📊 Results:")
    print(f"   ✅ Cards WITH market price: {len(cards_with_market)}")
    print(f"   ❌ Cards WITHOUT market price: {len(cards_without_market)}")
    
    # Group by card name to see patterns
    if cards_without_market:
        print(f"\n📋 Cards without market prices:")
        grouped = {}
        for card in cards_without_market:
            name = card['name']
            if name not in grouped:
                grouped[name] = []
            grouped[name].append(card)
        
        for name, items in sorted(grouped.items()):
            expansions = [item['expansion'] for item in items if item['expansion']]
            expansions_str = ', '.join(set(expansions)) if expansions else 'No expansion'
            print(f"   - {name} ({expansions_str}) - {len(items)} variant(s)")
    
    # Save results to JSON
    output_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'total_cards': len(cards),
            'cards_with_market_price': len(cards_with_market),
            'cards_without_market_price': len(cards_without_market),
            'market_scan_entries': len(market_data)
        },
        'cards_without_market_price': cards_without_market,
        'cards_with_market_price_sample': cards_with_market[:10]  # Include sample for reference
    }
    
    # Create output directory if it doesn't exist
    os.makedirs('results', exist_ok=True)
    
    # Save to file
    output_file = f"results/missing_market_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {output_file}")
    print(f"\n✅ Analysis complete!")
    print("=" * 60)
    
    return output_file, cards_without_market


def normalize_expansion_for_scanning(expansion: str) -> str:
    """
    Normalize expansion names for scanning to match Cardmarket price guide format.
    Handles cases like "Unlimited Edition" -> "Unlimited", "Revised Edition" -> "Revised".
    """
    if not expansion:
        return expansion
    
    expansion_lower = expansion.lower()
    
    # Handle "Edition" suffix - Cardmarket price guide often uses short names
    if expansion_lower.endswith(' edition'):
        # Remove " edition" suffix
        base = expansion[:-8].strip()  # Remove " Edition" (8 chars)
        # Special cases that need to stay as-is
        if base.lower() in ['fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth']:
            return expansion  # Keep "Fourth Edition" etc.
        return base
    
    return expansion


def convert_card_to_collection_item(card: Dict[str, Any], collection: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert a card (from expand_collection_to_cards) back to a collection item format
    for scanning purposes. Normalizes expansion names to match Cardmarket format.
    """
    collection_index = card.get('collection_index')
    if collection_index is not None and collection_index < len(collection):
        # Use the original collection item as base
        item = collection[collection_index].copy()
        # If the card has a specific expansion, create a new item with just that set
        expansion = card.get('expansion')
        if expansion:
            # Normalize expansion name for better matching with price guide
            normalized_expansion = normalize_expansion_for_scanning(expansion)
            item['sets'] = [normalized_expansion]
        return item
    
    # Fallback: create a new item from card data
    expansion = card.get('expansion')
    normalized_expansion = normalize_expansion_for_scanning(expansion) if expansion else None
    return {
        'name': card.get('name'),
        'sets': [normalized_expansion] if normalized_expansion else [],
        'language': card.get('language'),
        'foil': card.get('foil', False),
        'condition': card.get('condition'),
        'buy_price': card.get('buy_price'),
        'notes': card.get('notes', '')
    }


def fetch_missing_market_data(cards_without_market: List[Dict[str, Any]], 
                              collection: List[Dict[str, Any]],
                              use_historical: bool = True,
                              delay_between_cards: float = 10.0) -> List[Dict[str, Any]]:
    """
    Fetch market data for cards that don't have market prices.
    
    Args:
        cards_without_market: List of card dictionaries without market prices
        collection: Original collection list
        use_historical: Whether to use historical data for discount calculations
        delay_between_cards: Delay in seconds between scanning each card
        
    Returns:
        List of deal dictionaries in the same format as collection_deals
    """
    print("\n" + "=" * 60)
    print("📡 Fetching Market Data for Missing Cards")
    print("=" * 60)
    
    # Try to use venv if available
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_path = os.path.join(script_dir, 'venv')
    if os.path.exists(venv_path):
        # Add venv site-packages to path
        import site
        venv_site_packages = None
        # Try different Python version paths
        for py_version in ['3.12', '3.11', '3.10', '3.9']:
            potential_path = os.path.join(venv_path, 'lib', f'python{py_version}', 'site-packages')
            if os.path.exists(potential_path):
                venv_site_packages = potential_path
                break
        
        if venv_site_packages:
            sys.path.insert(0, venv_site_packages)
            print(f"✅ Using virtual environment: {venv_path}")
    
    try:
        # Import scanning function
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'simple_version'))
        from wishlist_deals import check_wishlist_deals
    except ImportError as e:
        print(f"❌ Error importing scanner: {e}")
        print("   Make sure the scanner module is available")
        print("   If pandas is missing, try:")
        print("     1. Activate virtual environment: source venv/bin/activate")
        print("     2. Install dependencies: pip install -r requirements.txt")
        print("   Or use --no-historical flag to skip pandas-dependent features")
        return []
    
    total_cards = len(cards_without_market)
    
    print(f"\n📊 Preparing to scan {total_cards} cards without market prices...")
    print(f"   Delay between cards: {delay_between_cards}s")
    print(f"   Use historical data: {use_historical}")
    print()
    
    # Convert all cards to collection items
    print("📋 Converting cards to collection items...")
    collection_items = []
    for card in cards_without_market:
        collection_item = convert_card_to_collection_item(card, collection)
        collection_items.append(collection_item)
        card_name = card.get('name', 'Unknown')
        expansion = card.get('expansion', 'Unknown')
        language = card.get('language')
        language_str = f" ({language})" if language else ""
        print(f"   - {card_name} - {expansion}{language_str}")
    
    # Create a single temporary wishlist file with all cards
    import tempfile
    temp_wishlist_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(collection_items, f, indent=2, ensure_ascii=False)
            temp_wishlist_file = f.name
        
        print(f"\n✅ Created temporary wishlist file with {len(collection_items)} cards")
        print(f"   File: {temp_wishlist_file}")
        print(f"\n🚀 Starting batch scan...")
        print("=" * 60)
        
        # Scan all cards in one batch
        all_deals = check_wishlist_deals(
            wishlist_file=temp_wishlist_file,
            delay_between_cards=delay_between_cards,
            use_historical=use_historical
        )
        
        print(f"\n✅ Batch scanning complete!")
        print(f"   Total deals fetched: {len(all_deals)}")
        
        return all_deals
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Scanning interrupted by user (Ctrl+C)")
        return []
    except Exception as e:
        print(f"\n❌ Error during batch scan: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        # Clean up temporary file
        if temp_wishlist_file and os.path.exists(temp_wishlist_file):
            try:
                os.unlink(temp_wishlist_file)
            except Exception:
                pass


def save_fetched_deals(deals: List[Dict[str, Any]], output_file: str = None) -> str:
    """
    Save fetched deals to a file in the same format as collection_deals_*.json
    
    Args:
        deals: List of deal dictionaries
        output_file: Optional output file path. If None, generates a timestamped filename
        
    Returns:
        Path to the saved file
    """
    if output_file is None:
        os.makedirs('results', exist_ok=True)
        output_file = f"results/missing_cards_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Calculate summary statistics
    total_deals = len(deals)
    excellent = len([d for d in deals if d.get('category') == 'excellent'])
    good = len([d for d in deals if d.get('category') == 'good'])
    fair = len([d for d in deals if d.get('category') == 'fair'])
    expensive = len([d for d in deals if d.get('category') == 'expensive'])
    no_data = len([d for d in deals if d.get('category') == 'no_data'])
    
    # Create output data in same format as collection_deals
    output_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'wishlist_file': COLLECTION_FILE,
        'config': {
            'min_discount': 0.0,
            'delay_between_cards': 10.0,
            'use_historical_data': True
        },
        'summary': {
            'total_deals': total_deals,
            'excellent': excellent,
            'good': good,
            'fair': fair,
            'expensive': expensive,
            'no_data': no_data
        },
        'deals': deals
    }
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Fetched deals saved to: {output_file}")
    print(f"   Summary: {total_deals} total deals ({excellent} excellent, {good} good, {fair} fair, {expensive} expensive, {no_data} no_data)")
    
    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check and optionally fetch market prices for collection cards')
    parser.add_argument('--fetch', action='store_true', 
                       help='Fetch market data for cards without prices')
    parser.add_argument('--delay', type=float, default=10.0,
                       help='Delay in seconds between scanning cards (default: 10.0)')
    parser.add_argument('--no-historical', action='store_true',
                       help='Do not use historical data for discount calculations')
    
    args = parser.parse_args()
    
    try:
        output_file, missing_cards = find_cards_without_market_prices()
        
        if missing_cards:
            print(f"\n⚠️  Found {len(missing_cards)} cards without market prices")
            print(f"   Review the results file: {output_file}")
            
            if args.fetch:
                print(f"\n{'='*60}")
                print("🚀 Starting fetch process...")
                print(f"{'='*60}")
                
                # Load collection for conversion
                collection = load_collection()
                
                # Fetch market data
                fetched_deals = fetch_missing_market_data(
                    cards_without_market=missing_cards,
                    collection=collection,
                    use_historical=not args.no_historical,
                    delay_between_cards=args.delay
                )
                
                if fetched_deals:
                    # Save fetched deals
                    deals_file = save_fetched_deals(fetched_deals)
                    print(f"\n✅ Fetch complete! Results saved to: {deals_file}")
                else:
                    print(f"\n⚠️  No deals were fetched")
            else:
                print(f"\n💡 Tip: Use --fetch to automatically fetch market data for these cards")
                print(f"   Example: python3 {sys.argv[0]} --fetch")
        else:
            print(f"\n✅ All cards have market prices!")
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

