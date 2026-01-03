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


def filter_by_wishlist(data: pd.DataFrame, wishlist: List[Dict[str, Any]]) -> pd.DataFrame:
    """Filter data to only include cards from the wishlist."""
    if not wishlist or data.empty:
        return data
    
    # Create a list to store matching cards
    matching_cards = []
    
    for item in wishlist:
        card_name = item.get('name', '').lower()
        allowed_sets = item.get('sets', [])
        max_price = item.get('max_price', float('inf'))
        
        if not card_name:
            continue
        
        # Find cards matching the name
        name_matches = data[
            data['name'].str.lower().str.contains(card_name, na=False)
        ].copy()
        
        # Filter by sets if specified
        if allowed_sets:
            set_matches = name_matches[
                name_matches['expansionName'].isin(allowed_sets)
            ]
        else:
            set_matches = name_matches
        
        # Filter by max price (using AVG7 as current market price)
        if 'AVG7' in set_matches.columns:
            price_matches = set_matches[
                set_matches['AVG7'] <= max_price
            ]
        else:
            price_matches = set_matches
        
        # Add wishlist metadata
        if not price_matches.empty:
            price_matches = price_matches.copy()
            price_matches['wishlist_item'] = item.get('name')
            price_matches['wishlist_notes'] = item.get('notes', '')
            price_matches['wishlist_max_price'] = max_price
            
            matching_cards.append(price_matches)
    
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
