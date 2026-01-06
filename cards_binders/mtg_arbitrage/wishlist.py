#!/usr/bin/env python3
"""
Wishlist-based candidate filtering for MTG arbitrage.

This module allows users to define specific cards they're interested in
and filters the data to only show those cards when good deals are available.
"""

import json
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path


def load_wishlist(filepath: str = "wishlist.json") -> List[Dict[str, Any]]:
    """Load wishlist from JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            wishlist = json.load(f)
        print(f"✅ Loaded wishlist with {len(wishlist)} items")
        return wishlist
    except FileNotFoundError:
        print(f"❌ Wishlist file not found: {filepath}")
        return []
    except Exception as e:
        print(f"❌ Error loading wishlist: {e}")
        return []


def create_sample_wishlist(filepath: str = "wishlist.json") -> None:
    """Create a sample wishlist file."""
    sample_wishlist = [
        {
            "name": "Black Lotus",
            "sets": ["Alpha", "Beta", "Unlimited"],
            "max_price": 50000,
            "notes": "Holy grail card"
        },
        {
            "name": "Demonic Tutor",
            "sets": ["Alpha", "Beta", "Unlimited"],
            "max_price": 200,
            "notes": "Classic staple"
        },
        {
            "name": "Lightning Bolt",
            "sets": ["Alpha", "Beta", "Unlimited"],
            "max_price": 150,
            "notes": "Iconic burn spell"
        }
    ]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sample_wishlist, f, indent=2)
    
    print(f"✅ Created sample wishlist: {filepath}")


def normalize_set_name_for_matching(name: str) -> str:
    """
    Normalize set name for fuzzy matching.
    Handles apostrophes, removes parentheticals, normalizes common variations.
    """
    if not name or pd.isna(name):
        return ''
    
    name_str = str(name)
    # Remove parentheticals
    name_str = name_str.split('(')[0].strip()
    # Remove "Edition" for matching (but keep "International" distinct)
    if 'international' not in name_str.lower():
        name_str = name_str.replace('Edition', '').strip()
    # Normalize apostrophes: "Urza's" -> "urzas", "Mishra's" -> "mishras"
    name_str = name_str.replace("'", "").replace("'", "").replace("'", "")
    # Normalize spaces and hyphens
    name_str = name_str.replace('-', ' ').replace('_', ' ')
    # Collapse multiple spaces
    import re
    name_str = re.sub(r'\s+', ' ', name_str).strip()
    return name_str.lower()


def get_cardmarket_set_name(set_name: str, language: str = None) -> str:
    """
    Map collection set names to Cardmarket set names.
    Special handling for:
    - International Edition (various formats)
    - Revised Edition + non-English language -> Foreign White Bordered (FWB)
    - Fourth Edition (Foreign Black Border) -> Fourth Edition Black Bordered
    """
    if not set_name:
        return set_name
    
    set_lower = set_name.lower()
    
    # International Edition - handle various formats
    if 'international' in set_lower:
        return 'International Edition'
    
    # Handle sets with "(Black Bordered)" pattern FIRST - this overrides language-based mapping
    # This catches: "Revised Edition (Black Bordered)" -> "Foreign Black Bordered"
    # Also handles: "Fourth Edition (Foreign Black Border)" -> "Fourth Edition Black Bordered"
    if '(black border' in set_lower or 'black border' in set_lower:
        # Check if it's Revised Edition (Black Bordered) -> Foreign Black Bordered
        if 'revised' in set_lower:
            mapped = 'Foreign Black Bordered'
            print(f"      🔄 Mapping set: '{set_name}' -> '{mapped}'")
            return mapped
        # Otherwise, remove the parenthetical and add "Black Bordered"
        base_set = set_name.split('(')[0].strip()
        if base_set:
            mapped = f'{base_set} Black Bordered'
            print(f"      🔄 Mapping set: '{set_name}' -> '{mapped}'")
            return mapped
    
    # Revised Edition + non-English language -> Foreign White Bordered (only if not black bordered)
    if 'revised' in set_lower and language and language.lower() not in ['', 'english']:
        return 'Foreign White Bordered'
    
    # Handle sets with "(Foreign Black Border)" or "(Foreign Black Bordered)" pattern
    # This catches: "Fourth Edition (Foreign Black Border)" -> "Fourth Edition Black Bordered"
    # Also handles: "Fourth Edition (Foreign Black Bordered)" -> "Fourth Edition Black Bordered"
    if '(foreign black border' in set_lower or 'foreign black border' in set_lower:
        # Remove the parenthetical and add "Black Bordered"
        base_set = set_name.split('(')[0].strip()
        if base_set:
            mapped = f'{base_set} Black Bordered'
            print(f"      🔄 Mapping set: '{set_name}' -> '{mapped}'")
            return mapped
    
    # Fourth Edition (Foreign Black Border) -> Fourth Edition Black Bordered (backup check)
    if 'fourth edition' in set_lower and 'foreign black border' in set_lower:
        mapped = 'Fourth Edition Black Bordered'
        print(f"      🔄 Mapping set: '{set_name}' -> '{mapped}'")
        return mapped
    
    return set_name


def filter_by_wishlist(data: pd.DataFrame, wishlist: List[Dict[str, Any]]) -> pd.DataFrame:
    """Filter data to only include cards from the wishlist."""
    if not wishlist or data.empty:
        return data
    
    # Create a list to store matching cards
    matching_cards = []
    
    for item in wishlist:
        item_display_name = item.get('name', 'Unknown')
        card_name = item.get('name', '').lower()
        alternative_name = item.get('alternative_name', '').lower()
        allowed_sets = item.get('sets', [])
        language = item.get('language', '')
        max_price = item.get('max_price', float('inf'))
        
        if not card_name:
            print(f"   ⚠️  Skipping item with no name: {item}")
            continue
        
        # Map set names to Cardmarket equivalents
        mapped_sets = [get_cardmarket_set_name(s, language) for s in allowed_sets]
        
        # Log what we're trying to match
        print(f"   🔍 Matching: {item_display_name} (sets: {allowed_sets})")
        if alternative_name:
            print(f"      Alternative name: {alternative_name}")
        if language:
            print(f"      Language: {language}")
        if mapped_sets != allowed_sets:
            print(f"      Mapped sets: {mapped_sets}")
        
        # Find cards matching the name (try main name first)
        # Escape special regex characters in card_name
        import re
        escaped_card_name = re.escape(card_name)
        name_matches = data[
            data['name'].str.lower().str.contains(escaped_card_name, na=False, regex=True)
        ].copy()
        
        print(f"      Found {len(name_matches)} cards matching name '{item_display_name}'")
        
        # If no matches and alternative_name exists, try alternative_name
        if name_matches.empty and alternative_name:
            escaped_alt_name = re.escape(alternative_name)
            name_matches = data[
                data['name'].str.lower().str.contains(escaped_alt_name, na=False, regex=True)
            ].copy()
            if not name_matches.empty:
                print(f"      ✅ Matched via alternative_name: {item_display_name} -> {alternative_name} ({len(name_matches)} cards)")
            else:
                print(f"      ❌ No matches for alternative_name '{alternative_name}' either")
        elif name_matches.empty:
            print(f"      ❌ No cards found matching name '{item_display_name}'")
        
        # Filter by sets if specified
        if mapped_sets:
            # Try exact match first
            exact_matches = name_matches[
                name_matches['expansionName'].isin(mapped_sets)
            ]
            
            print(f"      Found {len(exact_matches)} cards with exact set match: {mapped_sets}")
            
            # If no exact matches, try fuzzy matching (normalize apostrophes, etc.) on MAPPED sets only
            if exact_matches.empty:
                # Normalize set names for fuzzy matching (only on mapped sets, not original)
                normalized_allowed = [normalize_set_name_for_matching(s) for s in mapped_sets]
                
                set_matches = name_matches[
                    name_matches['expansionName'].apply(normalize_set_name_for_matching).isin(normalized_allowed)
                ]
                
                print(f"      Found {len(set_matches)} cards with fuzzy set match (normalized: {normalized_allowed})")
                
                # If still no matches, show what sets were found in name_matches
                if set_matches.empty and not name_matches.empty:
                    found_sets = name_matches['expansionName'].dropna().unique().tolist()
                    print(f"      ⚠️  Available sets in name matches: {found_sets[:10]}")  # Show first 10
                    print(f"      💡 Will use fallback URL building (card not in price guide)")
            else:
                set_matches = exact_matches
        else:
            set_matches = name_matches
            print(f"      No set filter applied, using all {len(set_matches)} name matches")
        
        # Filter by max price (using AVG7 as current market price)
        if 'AVG7' in set_matches.columns:
            price_matches = set_matches[
                set_matches['AVG7'] <= max_price
            ]
            if len(price_matches) < len(set_matches):
                print(f"      ⚠️  Price filter removed {len(set_matches) - len(price_matches)} cards (max_price: €{max_price})")
        else:
            price_matches = set_matches
        
        # Add wishlist metadata
        if not price_matches.empty:
            price_matches = price_matches.copy()
            price_matches['wishlist_item'] = item.get('name')
            price_matches['wishlist_notes'] = item.get('notes', '')
            price_matches['wishlist_max_price'] = max_price
            
            matching_cards.append(price_matches)
            print(f"      ✅ Successfully matched {len(price_matches)} card(s)")
        else:
            print(f"      ❌ FAILED to match: {item_display_name}")
            if name_matches.empty:
                print(f"         Reason: No cards found with name '{item_display_name}'")
                if alternative_name:
                    print(f"         (Also tried alternative_name '{alternative_name}')")
            elif set_matches.empty:
                print(f"         Reason: No cards found in sets {allowed_sets}")
                if mapped_sets != allowed_sets:
                    print(f"         (Also tried mapped sets {mapped_sets})")
                if not name_matches.empty:
                    found_sets = name_matches['expansionName'].dropna().unique().tolist()
                    print(f"         Available sets in name matches: {found_sets[:5]}")
            elif len(price_matches) < len(set_matches):
                print(f"         Reason: Price filter (max €{max_price}) excluded all matches")
        
        print()  # Blank line for readability
    
    if not matching_cards:
        print("❌ No cards found matching wishlist criteria")
        return pd.DataFrame()
    
    # Combine all matches
    result = pd.concat(matching_cards, ignore_index=True)
    
    # Remove duplicates (same card might match multiple wishlist items)
    if 'idProduct' in result.columns:
        result = result.drop_duplicates(subset=['idProduct'])
    
    print(f"✅ Found {len(result)} cards matching wishlist")
    return result


def analyze_wishlist_opportunities(data: pd.DataFrame, wishlist: List[Dict[str, Any]]) -> None:
    """Analyze current opportunities for wishlist items."""
    print("🎯 WISHLIST OPPORTUNITY ANALYSIS")
    print("=" * 50)
    
    wishlist_data = filter_by_wishlist(data, wishlist)
    
    if wishlist_data.empty:
        print("❌ No wishlist items found in current data")
        return
    
    # Group by wishlist item
    for item in wishlist:
        item_name = item.get('name')
        max_price = item.get('max_price', float('inf'))
        
        item_cards = wishlist_data[
            wishlist_data['wishlist_item'] == item_name
        ]
        
        if item_cards.empty:
            print(f"❌ {item_name}: Not found in data")
            continue
        
        print(f"\n🎯 {item_name} (max budget: €{max_price:,.0f})")
        print("-" * 40)
        
        for _, card in item_cards.iterrows():
            expansion = card.get('expansionName', 'Unknown')
            avg7 = card.get('AVG7', 0)
            trend = card.get('TREND', 0)
            avg30 = card.get('AVG30', 0)
            
            # Calculate opportunity score
            if trend > 0:
                discount = (trend - avg7) / trend * 100
                opportunity = "🟢 GOOD" if discount > 10 else "🟡 OK" if discount > 0 else "🔴 EXPENSIVE"
            else:
                discount = 0
                opportunity = "❓ UNKNOWN"
            
            print(f"   {expansion}: €{avg7:.2f} (vs trend €{trend:.2f}) - {opportunity}")
            if discount > 0:
                print(f"      Discount: {discount:.1f}%")


def create_wishlist_candidates(data: pd.DataFrame, wishlist_file: str = "wishlist.json") -> pd.DataFrame:
    """Create candidates based on wishlist instead of general filtering."""
    print("🎯 WISHLIST-BASED CANDIDATE SELECTION")
    print("=" * 50)
    
    # Load configuration for price filtering
    try:
        from .config import get_config
        config = get_config()
        price_min = config.get('WISHLIST_PRICE_MIN', 10.0)
        price_max = config.get('WISHLIST_PRICE_MAX', 500.0)
    except ImportError:
        # Fallback if config not available
        price_min = 10.0
        price_max = 500.0
    
    # Load wishlist
    wishlist = load_wishlist(wishlist_file)
    if not wishlist:
        print("❌ No wishlist available, falling back to regular filtering")
        return pd.DataFrame()
    
    # Filter by wishlist
    candidates = filter_by_wishlist(data, wishlist)
    
    if candidates.empty:
        return candidates
    
    # Apply basic quality filters
    if 'AVG30' in candidates.columns:
        # Remove cards with no monthly sales
        candidates = candidates[candidates['AVG30'] > 0]
        print(f"After liquidity filter: {len(candidates)} cards")
        
        # Apply configurable price range filter
        before_price_filter = len(candidates)
        candidates = candidates[
            (candidates['AVG30'] >= price_min) & 
            (candidates['AVG30'] <= price_max)
        ]
        removed_price = before_price_filter - len(candidates)
        if removed_price > 0:
            print(f"After price range filter (€{price_min:.0f}-€{price_max:.0f} AVG30): {len(candidates)} cards (removed {removed_price} cards)")
        else:
            print(f"After price range filter (€{price_min:.0f}-€{price_max:.0f} AVG30): {len(candidates)} cards")
    
    # Add discount calculation using AVG30 (consistent with main filtering)
    if 'TREND' in candidates.columns and 'AVG30' in candidates.columns:
        candidates = candidates.copy()
        candidates['real_discount'] = (candidates['TREND'] - candidates['AVG30']) / candidates['TREND']
        
        # Sort by discount (best opportunities first)
        candidates = candidates.sort_values('real_discount', ascending=False)
    
    print(f"✅ Final wishlist candidates: {len(candidates)}")
    return candidates


def print_wishlist_summary(candidates: pd.DataFrame) -> None:
    """Print a summary of wishlist candidates."""
    if candidates.empty:
        print("❌ No wishlist candidates available")
        return
    
    print("\n🎯 WISHLIST CANDIDATES SUMMARY")
    print("=" * 40)
    
    for i, (_, card) in enumerate(candidates.head(10).iterrows()):
        name = card.get('name', 'Unknown')
        expansion = card.get('expansionName', 'Unknown')
        avg7 = card.get('AVG7', 0)
        avg30 = card.get('AVG30', 0)
        trend = card.get('TREND', 0)
        discount = card.get('real_discount', 0) * 100
        notes = card.get('wishlist_notes', '')
        
        print(f"{i+1:2d}. {name} ({expansion})")
        print(f"    Monthly avg: €{avg30:.2f} | Trend: €{trend:.2f}")
        if discount > 0:
            print(f"    Discount: {discount:.1f}% (AVG30 vs TREND)")
        if notes:
            print(f"    Notes: {notes}")
        print()


if __name__ == "__main__":
    # Example usage
    from mtg_arbitrage.data_loader import load_data_with_names
    
    # Load data
    data = load_data_with_names()
    
    # Create wishlist candidates
    candidates = create_wishlist_candidates(data)
    
    # Show summary
    print_wishlist_summary(candidates)
