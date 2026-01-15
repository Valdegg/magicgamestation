#!/usr/bin/env python3
"""
Simple test script for collection sorting functionality.
Tests the sorting logic without importing the full FastAPI module.
"""

import json
import sys
import os
from pathlib import Path


def load_collection(filepath="collection.json"):
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


def expand_collection_to_cards(collection):
    """Expand collection items to show one card per set."""
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
        
        if not sets:
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
                'collection_index': index
            })
        else:
            for expansion in sets:
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
                    'collection_index': index
                })
    
    return cards


def test_sort_functions():
    """Test the sorting functions."""
    print("=" * 60)
    print("Testing Sort Functions")
    print("=" * 60)
    
    # Load test data
    collection = load_collection()
    if not collection:
        print("❌ Could not load collection.json")
        return False
    
    cards = expand_collection_to_cards(collection)
    
    print(f"\nLoaded {len(cards)} cards from collection")
    print(f"First 5 cards:")
    for i, card in enumerate(cards[:5]):
        print(f"  {i+1}. {card.get('name')} - {card.get('expansion')} - ${card.get('buy_price', 0)}")
    
    # Test original order
    print("\n--- Testing Original Order ---")
    original_sorted = sorted(cards, key=lambda x: x.get('collection_index', 999999))
    print(f"Original order first 5:")
    for i, card in enumerate(original_sorted[:5]):
        print(f"  {i+1}. {card.get('name')} (index: {card.get('collection_index')})")
    
    # Test name sort (simulating JavaScript)
    print("\n--- Testing Name Sort (A-Z) ---")
    def sort_name(cards):
        def sort_key(card):
            name = (card.get('name') or '').lower()
            exp = (card.get('expansion') or '').lower()
            return (name, exp)
        return sorted(cards, key=sort_key)
    
    name_sorted = sort_name(cards)
    print(f"Name sorted first 5:")
    for i, card in enumerate(name_sorted[:5]):
        print(f"  {i+1}. {card.get('name')} - {card.get('expansion')}")
    
    # Verify name sort
    names = [(c.get('name') or '').lower() for c in name_sorted]
    is_name_sorted = all(names[i] <= names[i+1] for i in range(len(names)-1))
    print(f"✅ Name sort correct: {is_name_sorted}")
    
    # Test set sort
    print("\n--- Testing Set Sort (A-Z) ---")
    def sort_set(cards):
        def sort_key(card):
            exp = (card.get('expansion') or '').lower()
            name = (card.get('name') or '').lower()
            return (exp, name)
        return sorted(cards, key=sort_key)
    
    set_sorted = sort_set(cards)
    print(f"Set sorted first 5:")
    for i, card in enumerate(set_sorted[:5]):
        print(f"  {i+1}. {card.get('name')} - {card.get('expansion')}")
    
    # Verify set sort
    sets = [(c.get('expansion') or '').lower() for c in set_sorted]
    is_set_sorted = all(sets[i] <= sets[i+1] for i in range(len(sets)-1))
    print(f"✅ Set sort correct: {is_set_sorted}")
    
    # Test price sort
    print("\n--- Testing Price Sort (High to Low) ---")
    def sort_price(cards):
        def sort_key(card):
            price = -float(card.get('buy_price') or 0)  # Negative for descending
            name = (card.get('name') or '').lower()
            return (price, name)
        return sorted(cards, key=sort_key)
    
    price_sorted = sort_price(cards)
    print(f"Price sorted first 5:")
    for i, card in enumerate(price_sorted[:5]):
        print(f"  {i+1}. {card.get('name')} - ${card.get('buy_price', 0)} - {card.get('expansion')}")
    
    # Verify price sort
    prices = [float(c.get('buy_price') or 0) for c in price_sorted]
    is_price_sorted = all(prices[i] >= prices[i+1] for i in range(len(prices)-1))
    print(f"✅ Price sort correct: {is_price_sorted}")
    
    # Check that sorts produce different results
    print("\n--- Verification: Sorts produce different results ---")
    original_first_5 = [c.get('name') for c in original_sorted[:5]]
    name_first_5 = [c.get('name') for c in name_sorted[:5]]
    set_first_5 = [c.get('name') for c in set_sorted[:5]]
    price_first_5 = [c.get('name') for c in price_sorted[:5]]
    
    print(f"Original != Name: {original_first_5 != name_first_5}")
    print(f"Original != Set: {original_first_5 != set_first_5}")
    print(f"Original != Price: {original_first_5 != price_first_5}")
    
    return {
        'total_cards': len(cards),
        'name_sorted': is_name_sorted,
        'set_sorted': is_set_sorted,
        'price_sorted': is_price_sorted,
        'all_different': (
            original_first_5 != name_first_5 and
            original_first_5 != set_first_5 and
            original_first_5 != price_first_5
        )
    }


def main():
    """Run tests."""
    print("\n" + "=" * 60)
    print("COLLECTION SORTING TEST SUITE")
    print("=" * 60)
    
    try:
        results = test_sort_functions()
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total cards: {results['total_cards']}")
        print(f"Name sort: {'✅ PASS' if results['name_sorted'] else '❌ FAIL'}")
        print(f"Set sort: {'✅ PASS' if results['set_sorted'] else '❌ FAIL'}")
        print(f"Price sort: {'✅ PASS' if results['price_sorted'] else '❌ FAIL'}")
        print(f"All sorts different: {'✅ PASS' if results['all_different'] else '❌ FAIL'}")
        
        all_passed = all([
            results['name_sorted'],
            results['set_sorted'],
            results['price_sorted'],
            results['all_different']
        ])
        
        print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        
        return 0 if all_passed else 1
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

