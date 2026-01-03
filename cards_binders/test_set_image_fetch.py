#!/usr/bin/env python3
"""
Test script to fetch card images from different sets and analyze results.
Tests: International Edition, Alpha, Beta, Unlimited, Collector's Edition
"""

import json
import os
import requests
from typing import Dict, List, Optional

def get_scryfall_set_code(set_name: str) -> str:
    """
    Get Scryfall set code for a given set name.
    Returns the set code, or the original name if not found.
    Special handling for International Edition -> CEI, Collector's Edition -> CED.
    """
    # Special cases: Scryfall uses different codes
    if set_name.lower() == "international edition":
        return "CEI"
    if set_name.lower() == "collector's edition":
        return "CED"
    
    # Try to load sets_data.json to get the code
    try:
        sets_file = "sets_data.json"
        if os.path.exists(sets_file):
            with open(sets_file, 'r', encoding='utf-8') as f:
                sets_data = json.load(f)
            for set_data in sets_data:
                if set_data.get("name", "").lower() == set_name.lower():
                    code = set_data.get("code", "")
                    # Map our codes to Scryfall codes
                    if code == "IE":
                        return "CEI"  # International Edition -> CEI
                    if code == "CED":
                        return "CED"  # Collector's Edition -> CED
                    return code
    except Exception as e:
        print(f"   ⚠️  Error loading sets_data.json: {e}", flush=True)
    
    # Fallback to original name
    return set_name


def test_scryfall_query(card_name: str, set_name: str) -> Dict:
    """Test querying Scryfall API for a card from a specific set."""
    print(f"\n{'='*60}")
    print(f"Testing: {card_name} from {set_name}")
    print(f"{'='*60}")
    
    result = {
        "card_name": card_name,
        "set_name": set_name,
        "success": False,
        "error": None,
        "query_used": None,
        "scryfall_set_code": None,
        "found_cards": [],
        "selected_card": None
    }
    
    try:
        # Get Scryfall set code
        set_code = get_scryfall_set_code(set_name)
        result["scryfall_set_code"] = set_code
        print(f"📋 Set name: {set_name}")
        print(f"🔑 Scryfall set code: {set_code}")
        
        # Build query - try different formats
        # Format 1: set:CODE (no quotes, lowercase)
        query1 = f'!"{card_name}" set:{set_code.lower()}'
        # Format 2: set:"CODE" (with quotes)
        query2 = f'!"{card_name}" set:"{set_code}"'
        # Format 3: set:"CODE" (with quotes, lowercase)
        query3 = f'!"{card_name}" set:"{set_code.lower()}"'
        
        queries_to_try = [
            (query1, "set:CODE (lowercase)"),
            (query2, 'set:"CODE" (with quotes)'),
            (query3, 'set:"CODE" (lowercase, with quotes)')
        ]
        
        success = False
        successful_resp = None
        
        for query, description in queries_to_try:
            result["query_used"] = query
            print(f"🌐 Trying query ({description}): {query}")
            
            params = {
                "q": query,
                "unique": "prints"
            }
            
            try:
                resp = requests.get("https://api.scryfall.com/cards/search", params=params, timeout=10)
                print(f"📡 Response status: {resp.status_code}")
                
                if resp.status_code == 200:
                    success = True
                    successful_resp = resp
                    break
                elif resp.status_code == 404:
                    # Try next format
                    error_data = resp.json() if resp.content else {}
                    if error_data.get("object") == "error":
                        error_msg = error_data.get("details", error_data.get("type", "Unknown error"))
                        print(f"   Error: {error_msg}")
                    continue
                else:
                    error_data = resp.json() if resp.content else {}
                    if error_data.get("object") == "error":
                        error_msg = error_data.get("details", error_data.get("type", "Unknown error"))
                        print(f"   Error: {error_msg}")
                    continue
            except Exception as e:
                print(f"   Exception: {e}")
                continue
        
        if not success:
            result["error"] = "All query formats failed (404 or other error)"
            print(f"❌ All query formats failed")
            return result
        
        # Parse successful response
        print(f"✅ Successfully queried Scryfall")
        results = successful_resp.json()
        
        if results.get("object") == "error":
            result["error"] = results.get("details", results.get("type", "Unknown error"))
            print(f"❌ Scryfall error: {result['error']}")
            return result
        
        if not results.get("data"):
            result["error"] = "No cards found"
            print(f"❌ No cards found")
            return result
        
        cards = results.get("data", [])
        print(f"✅ Found {len(cards)} printings")
        
        # Collect info about all found cards
        for card in cards:
            card_info = {
                "name": card.get("name"),
                "set": card.get("set"),
                "set_name": card.get("set_name"),
                "set_type": card.get("set_type"),
                "released_at": card.get("released_at"),
                "collector_number": card.get("collector_number"),
                "has_image": "image_uris" in card or "card_faces" in card
            }
            result["found_cards"].append(card_info)
            print(f"  - {card_info['name']} ({card_info['set']} - {card_info['set_name']})")
        
        # Try to find exact match
        set_name_lower = set_name.lower()
        set_code_lower = set_code.lower()
        selected = None
        
        for card in cards:
            card_set = card.get("set_name", "").lower()
            card_set_code = card.get("set", "").lower()
            
            # Match by set code (preferred) or set name
            if (set_code_lower == card_set_code or 
                set_name_lower in card_set or 
                (set_name_lower == "international edition" and card_set_code == "cei") or
                (set_name_lower == "collector's edition" and card_set_code == "ced")):
                selected = card
                break
        
        if not selected:
            selected = cards[0]
            print(f"⚠️  Exact match not found, using first result")
        
        result["selected_card"] = {
            "name": selected.get("name"),
            "set": selected.get("set"),
            "set_name": selected.get("set_name"),
            "collector_number": selected.get("collector_number"),
            "has_image": "image_uris" in selected or "card_faces" in selected,
            "image_url": None
        }
        
        # Get image URL
        if "image_uris" in selected:
            result["selected_card"]["image_url"] = selected["image_uris"].get("large") or selected["image_uris"].get("normal")
        elif "card_faces" in selected:
            face = selected["card_faces"][0]
            if "image_uris" in face:
                result["selected_card"]["image_url"] = face["image_uris"].get("large") or face["image_uris"].get("normal")
        
        result["success"] = True
        print(f"✅ Selected: {result['selected_card']['name']} ({result['selected_card']['set']} - {result['selected_card']['set_name']})")
        if result["selected_card"]["image_url"]:
            print(f"🖼️  Image URL: {result['selected_card']['image_url']}")
        else:
            print(f"⚠️  No image URL found")
        
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    return result


def main():
    """Run tests for different sets."""
    print("🧪 Testing Scryfall Image Fetching for Different Sets")
    print("=" * 60)
    
    # Test cases: (card_name, set_name)
    test_cases = [
        ("Mox Jet", "International Edition"),
        ("Mox Jet", "Collector's Edition"),
        ("Mox Jet", "Alpha (Limited Edition)"),
        ("Mox Jet", "Beta (Limited Edition)"),
        ("Mox Jet", "Unlimited Edition"),
    ]
    
    results = []
    
    for card_name, set_name in test_cases:
        result = test_scryfall_query(card_name, set_name)
        results.append(result)
    
    # Save results
    output_file = "test_set_image_fetch_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")
    
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['card_name']} - {result['set_name']}")
        if result["success"]:
            print(f"   Set code: {result['scryfall_set_code']}")
            print(f"   Query used: {result['query_used']}")
            print(f"   Selected: {result['selected_card']['set']} - {result['selected_card']['set_name']}")
            print(f"   Has image: {result['selected_card']['has_image']}")
            if result['selected_card']['set'].upper() != result['scryfall_set_code'].upper():
                print(f"   ⚠️  Warning: Expected set code {result['scryfall_set_code']}, got {result['selected_card']['set']}")
        else:
            print(f"   Error: {result['error']}")
    
    print(f"\n💾 Results saved to: {output_file}")
    
    # Analysis
    print(f"\n{'='*60}")
    print("🔍 ANALYSIS")
    print(f"{'='*60}")
    
    failed = [r for r in results if not r["success"]]
    if failed:
        print(f"❌ Failed sets: {len(failed)}")
        for r in failed:
            print(f"   - {r['set_name']}: {r['error']}")
    
    successful = [r for r in results if r["success"]]
    if successful:
        print(f"\n✅ Successful sets: {len(successful)}")
        for r in successful:
            print(f"   - {r['set_name']} -> {r['scryfall_set_code']} (query: {r['query_used']})")
            if r['selected_card']['set'].upper() != r['scryfall_set_code'].upper():
                print(f"     ⚠️  Warning: Expected {r['scryfall_set_code']}, got {r['selected_card']['set']}")


if __name__ == "__main__":
    main()
