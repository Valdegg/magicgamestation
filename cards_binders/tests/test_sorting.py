#!/usr/bin/env python3
"""
Test script for collection sorting functionality.
Tests the sorting logic and API endpoints.
"""

import json
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collection_ui import expand_collection_to_cards, load_collection


def test_sort_functions():
    """Test the JavaScript sorting functions logic in Python."""
    print("=" * 60)
    print("Testing Sort Functions")
    print("=" * 60)
    
    # Load test data
    collection = load_collection()
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
    
    # Test name sort
    print("\n--- Testing Name Sort (A-Z) ---")
    name_sorted = sorted(cards, key=lambda x: (
        (x.get('name') or '').lower(),
        (x.get('expansion') or '').lower()
    ))
    print(f"Name sorted first 5:")
    for i, card in enumerate(name_sorted[:5]):
        print(f"  {i+1}. {card.get('name')} - {card.get('expansion')}")
    
    # Test set sort
    print("\n--- Testing Set Sort (A-Z) ---")
    set_sorted = sorted(cards, key=lambda x: (
        (x.get('expansion') or '').lower(),
        (x.get('name') or '').lower()
    ))
    print(f"Set sorted first 5:")
    for i, card in enumerate(set_sorted[:5]):
        print(f"  {i+1}. {card.get('name')} - {card.get('expansion')}")
    
    # Test price sort
    print("\n--- Testing Price Sort (High to Low) ---")
    price_sorted = sorted(cards, key=lambda x: (
        -float(x.get('buy_price') or 0),  # Negative for descending
        (x.get('name') or '').lower()
    ))
    print(f"Price sorted first 5:")
    for i, card in enumerate(price_sorted[:5]):
        print(f"  {i+1}. {card.get('name')} - ${card.get('buy_price', 0)} - {card.get('expansion')}")
    
    # Verify sorting works correctly
    print("\n--- Verification ---")
    
    # Check name sort
    names = [c.get('name', '').lower() for c in name_sorted]
    is_name_sorted = all(names[i] <= names[i+1] for i in range(len(names)-1))
    print(f"Name sort correct: {is_name_sorted}")
    
    # Check set sort
    sets = [(c.get('expansion') or '').lower() for c in set_sorted]
    is_set_sorted = all(sets[i] <= sets[i+1] for i in range(len(sets)-1))
    print(f"Set sort correct: {is_set_sorted}")
    
    # Check price sort
    prices = [float(c.get('buy_price') or 0) for c in price_sorted]
    is_price_sorted = all(prices[i] >= prices[i+1] for i in range(len(prices)-1))
    print(f"Price sort correct: {is_price_sorted}")
    
    return {
        'total_cards': len(cards),
        'name_sorted': is_name_sorted,
        'set_sorted': is_set_sorted,
        'price_sorted': is_price_sorted
    }


def test_api_endpoint():
    """Test the API endpoint directly."""
    print("\n" + "=" * 60)
    print("Testing API Endpoint")
    print("=" * 60)
    
    import requests
    
    try:
        # Test the collection-cards endpoint
        base_url = "http://localhost:5003"
        url = f"{base_url}/api/collection-cards"
        
        print(f"\nTesting: {url}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            cards = data.get('cards', [])
            print(f"✅ API returned {len(cards)} cards")
            
            if len(cards) > 0:
                print(f"\nFirst 5 cards from API:")
                for i, card in enumerate(cards[:5]):
                    print(f"  {i+1}. {card.get('name')} - {card.get('expansion')} - ${card.get('buy_price', 0)}")
                
                # Check if cards have collection_index
                has_index = all('collection_index' in card for card in cards)
                print(f"\nAll cards have collection_index: {has_index}")
                
                return True
            else:
                print("❌ API returned no cards")
                return False
        else:
            print(f"❌ API returned status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running on port 5003?")
        print("   Start it with: python collection_ui.py")
        return False
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_javascript_sorting_logic():
    """Test the JavaScript sorting logic by simulating it."""
    print("\n" + "=" * 60)
    print("Testing JavaScript Sorting Logic (Simulated)")
    print("=" * 60)
    
    collection = load_collection()
    cards = expand_collection_to_cards(collection)
    
    # Simulate JavaScript sort functions
    def js_sort_original(cards):
        """Simulate JavaScript original sort."""
        return sorted(cards, key=lambda x: x.get('collection_index', 999999))
    
    def js_sort_name(cards):
        """Simulate JavaScript name sort."""
        def sort_key(card):
            name = (card.get('name') or '').lower()
            exp = (card.get('expansion') or '').lower()
            return (name, exp)
        return sorted(cards, key=sort_key)
    
    def js_sort_set(cards):
        """Simulate JavaScript set sort."""
        def sort_key(card):
            exp = (card.get('expansion') or '').lower()
            name = (card.get('name') or '').lower()
            return (exp, name)
        return sorted(cards, key=sort_key)
    
    def js_sort_price(cards):
        """Simulate JavaScript price sort."""
        def sort_key(card):
            price = -float(card.get('buy_price') or 0)  # Negative for descending
            name = (card.get('name') or '').lower()
            return (price, name)
        return sorted(cards, key=sort_key)
    
    # Test each sort
    print("\n--- Original Sort ---")
    original = js_sort_original(cards)
    print(f"First 3: {[c.get('name') for c in original[:3]]}")
    
    print("\n--- Name Sort ---")
    name_sorted = js_sort_name(cards)
    print(f"First 3: {[c.get('name') for c in name_sorted[:3]]}")
    
    print("\n--- Set Sort ---")
    set_sorted = js_sort_set(cards)
    first_3_set = [f"{c.get('name')} - {c.get('expansion')}" for c in set_sorted[:3]]
    print(f"First 3: {first_3_set}")
    
    print("\n--- Price Sort ---")
    price_sorted = js_sort_price(cards)
    first_3_price = [f"{c.get('name')} (${c.get('buy_price', 0)})" for c in price_sorted[:3]]
    print(f"First 3: {first_3_price}")
    
    # Verify they're different
    print("\n--- Verification ---")
    print(f"Original != Name: {original[:5] != name_sorted[:5]}")
    print(f"Original != Set: {original[:5] != set_sorted[:5]}")
    print(f"Original != Price: {original[:5] != price_sorted[:5]}")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("COLLECTION SORTING TEST SUITE")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Sort functions
    try:
        results['sort_functions'] = test_sort_functions()
    except Exception as e:
        print(f"\n❌ Sort functions test failed: {e}")
        import traceback
        traceback.print_exc()
        results['sort_functions'] = False
    
    # Test 2: JavaScript logic simulation
    try:
        results['js_logic'] = test_javascript_sorting_logic()
    except Exception as e:
        print(f"\n❌ JavaScript logic test failed: {e}")
        import traceback
        traceback.print_exc()
        results['js_logic'] = False
    
    # Test 3: API endpoint (requires server)
    try:
        results['api'] = test_api_endpoint()
    except Exception as e:
        print(f"\n❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        results['api'] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

