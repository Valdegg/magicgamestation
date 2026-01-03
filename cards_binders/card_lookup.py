#!/usr/bin/env python3
"""
Shared card lookup functionality for MTG arbitrage.

Abstracts the common functionality of loading Cardmarket data
and matching cards from wishlists or filtering by criteria.
"""

from typing import List, Dict, Any, Optional
import pandas as pd

from mtg_arbitrage.data_loader import load_data_with_names
from mtg_arbitrage.wishlist import load_wishlist, filter_by_wishlist


def load_cardmarket_data(force_download: bool = False) -> pd.DataFrame:
    """
    Load Cardmarket price guide data with card names.
    
    Args:
        force_download: Force download of fresh data
        
    Returns:
        DataFrame with price guide data
    """
    print(f"📊 Loading Cardmarket price guide data...")
    data = load_data_with_names(force_download=force_download)
    
    if data.empty:
        print("❌ No price guide data available")
        return pd.DataFrame()
    
    print(f"✅ Loaded {len(data):,} products with pricing data")
    return data


def get_wishlist_card_ids(wishlist_file: str = "wishlist.json") -> set:
    """
    Get set of card IDs from wishlist for exclusion.
    
    Args:
        wishlist_file: Path to wishlist JSON file
        
    Returns:
        Set of card IDs (idProduct) that are in the wishlist
    """
    print(f"📋 Loading wishlist from {wishlist_file}...")
    wishlist = load_wishlist(wishlist_file)
    
    if not wishlist:
        print("⚠️  No wishlist items found")
        return set()
    
    # Load data to match wishlist items to card IDs
    data = load_cardmarket_data()
    
    if data.empty:
        print("⚠️  Cannot match wishlist - no data available")
        return set()
    
    # Match wishlist items to cards
    matched_cards = filter_by_wishlist(data, wishlist)
    
    if matched_cards.empty:
        print("⚠️  No cards matched from wishlist")
        return set()
    
    # Extract card IDs
    card_ids = set(matched_cards['idProduct'].dropna().astype(int).tolist())
    print(f"✅ Found {len(card_ids)} card IDs in wishlist")
    
    return card_ids


def exclude_wishlist_cards(data: pd.DataFrame, wishlist_file: str = "wishlist.json") -> pd.DataFrame:
    """
    Filter out cards that are already in the wishlist.
    
    Args:
        data: DataFrame with card data
        wishlist_file: Path to wishlist JSON file
        
    Returns:
        DataFrame with wishlist cards excluded
    """
    if data.empty:
        return data
    
    wishlist_ids = get_wishlist_card_ids(wishlist_file)
    
    if not wishlist_ids:
        print("⚠️  No wishlist IDs to exclude")
        return data
    
    initial_count = len(data)
    filtered = data[~data['idProduct'].isin(wishlist_ids)]
    excluded_count = initial_count - len(filtered)
    
    print(f"📋 Excluded {excluded_count} cards already in wishlist ({len(filtered)} remaining)")
    
    return filtered


def find_cards_by_price_discount(
    data: pd.DataFrame,
    min_avg30: float = 0.0,
    max_avg30: float = float('inf'),
    discount_threshold: float = 0.25,
    min_liquidity: float = 0.01
) -> pd.DataFrame:
    """
    Find cards where AVG30 is significantly below TREND.
    
    Uses similar quality filters as main.py to exclude:
    - Cards with poor liquidity patterns
    - Condition bias (AVG7 suspiciously low vs AVG30)
    - Outliers (AVG30 much higher than TREND)
    - Cards with missing expansion names (likely new/unstable)
    
    Args:
        data: DataFrame with card data
        min_avg30: Minimum AVG30 price
        max_avg30: Maximum AVG30 price
        discount_threshold: Minimum discount percentage (AVG30 vs TREND)
        min_liquidity: Minimum AVG7 for liquidity check
        
    Returns:
        DataFrame with filtered cards sorted by discount
    """
    if data.empty:
        return pd.DataFrame()
    
    filtered = data.copy()
    initial_count = len(filtered)
    
    # Filter out cards with missing expansion names (new/unstable cards)
    if 'expansionName' in filtered.columns:
        before_expansion = len(filtered)
        filtered = filtered[
            (filtered['expansionName'].notna()) & 
            (filtered['expansionName'] != 'nan') &
            (filtered['expansionName'].astype(str) != 'nan')
        ]
        removed_expansion = before_expansion - len(filtered)
        if removed_expansion > 0:
            print(f"After expansion name filter (removed {removed_expansion} cards with missing set names): {len(filtered)} cards")
    
    # Filter by price range
    if 'AVG30' in filtered.columns:
        filtered = filtered[
            (filtered['AVG30'] >= min_avg30) &
            (filtered['AVG30'] <= max_avg30) &
            (filtered['AVG30'] > 0)  # Must have monthly sales
        ]
        print(f"After price range filter (€{min_avg30:.0f}-€{max_avg30:.0f} AVG30): {len(filtered)} cards")
    
    # Filter by liquidity (recent sales activity)
    if 'AVG7' in filtered.columns:
        filtered = filtered[filtered['AVG7'] >= min_liquidity]
        print(f"After liquidity filter (AVG7 >= {min_liquidity}): {len(filtered)} cards")
    
    # Filter by discount (AVG30 vs TREND) with quality filters
    if 'TREND' in filtered.columns and 'AVG30' in filtered.columns:
        # Only keep cards with meaningful trend data (> 1 EUR to avoid penny stocks)
        filtered = filtered[filtered['TREND'] > 1.0]
        
        # Filter out extreme outliers (AVG30 much higher than TREND suggests infrequent sales with outlier prices)
        if 'AVG30' in filtered.columns:
            before_outlier = len(filtered)
            filtered = filtered[
                (filtered['AVG30'] == 0) |  # No monthly data, or
                (filtered['AVG30'] <= filtered['TREND'] * 2.0)  # Monthly price not more than 2x trend
            ]
            removed_outlier = before_outlier - len(filtered)
            if removed_outlier > 0:
                print(f"After outlier filter (removed {removed_outlier} cards with AVG30 > 2x TREND): {len(filtered)} cards")
        
        # CONDITION BIAS FILTER: Remove cards where AVG7 is suspiciously low vs AVG30
        # This filters out cards where recent sales were likely poor condition
        if 'AVG7' in filtered.columns and 'AVG30' in filtered.columns:
            before_condition = len(filtered)
            # Keep cards where either:
            # 1. AVG7 is at least 75% of AVG30 (consistent pricing), OR
            # 2. AVG7 is 0 (no weekly data to compare)
            filtered = filtered[
                (filtered['AVG7'] == 0) |  # No weekly data
                (filtered['AVG7'] >= filtered['AVG30'] * 0.75)  # AVG7 within 25% of AVG30
            ]
            removed_condition = before_condition - len(filtered)
            if removed_condition > 0:
                print(f"After condition bias filter (removed {removed_condition} cards with suspicious AVG7 drops): {len(filtered)} cards")
        
        # Calculate discount: how much AVG30 is below TREND
        filtered = filtered.copy()
        filtered['discount_pct'] = ((filtered['TREND'] - filtered['AVG30']) / filtered['TREND']) * 100
        
        # Filter for cards with at least discount_threshold percentage discount
        filtered = filtered[filtered['discount_pct'] >= discount_threshold * 100]
        print(f"After discount filter (≥{discount_threshold*100:.0f}% below TREND): {len(filtered)} cards")
        
        # Sort by discount (highest first)
        filtered = filtered.sort_values('discount_pct', ascending=False)
    
    print(f"✅ Found {len(filtered)} discovery candidates (from {initial_count} total cards)")
    
    return filtered

