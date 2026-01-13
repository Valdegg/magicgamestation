#!/usr/bin/env python3
"""
Determine format validity for cards in collection.json.

Classifies cards as Old School 93/94 legal, Premodern legal, both, or neither
based on their printings in specific sets.
"""

import json
import requests
import time
import shutil
import sys
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict

# Rate limiting: Scryfall asks for max 50-100 requests per second
# We'll be conservative and wait 0.1 seconds between requests
SCRYFALL_DELAY = 0.1

# Old School 93/94 legal sets (by name)
OLD_SCHOOL_SET_NAMES = [
    "Alpha",
    "Beta",
    "Unlimited Edition",
    "Revised Edition",
    "Arabian Nights",
    "Legends",
    "The Dark",
    "Fallen Empires",
    "Antiquities"
]

# Premodern legal sets (by name)
PREMODERN_SET_NAMES = [
    "Fourth Edition",
    "Ice Age",
    "Chronicles",
    "Homelands",
    "Alliances",
    "Mirage",
    "Visions",
    "Fifth Edition",
    "Weatherlight",
    "Tempest",
    "Stronghold",
    "Exodus",
    "Urza's Saga",
    "Urza's Legacy",
    "Classic Sixth Edition",
    "Urza's Destiny",
    "Mercadian Masques",
    "Nemesis",
    "Prophecy",
    "Invasion",
    "Planeshift",
    "Seventh Edition",
    "Apocalypse",
    "Odyssey",
    "Torment",
    "Judgment",
    "Onslaught",
    "Legions",
    "Scourge"
]

# Alternative names that might appear in collection.json
SET_NAME_ALIASES = {
    "Unlimited": "Unlimited Edition",
    "Revised": "Revised Edition",
    "Sixth Edition": "Classic Sixth Edition",
    "Classic Sixth Edition": "Classic Sixth Edition",
}

# Normalize set names (remove parenthetical suffixes, etc.)
def normalize_set_name(set_name: str) -> str:
    """
    Normalize set names by removing parenthetical suffixes and handling aliases.
    
    Examples:
        "Fourth Edition (Foreign Black Border)" -> "Fourth Edition"
        "Unlimited" -> "Unlimited Edition"
    """
    # Remove parenthetical suffixes
    if "(" in set_name:
        set_name = set_name.split("(")[0].strip()
    
    # Handle aliases
    if set_name in SET_NAME_ALIASES:
        return SET_NAME_ALIASES[set_name]
    
    return set_name


def fetch_all_sets() -> Dict[str, str]:
    """
    Fetch all sets from Scryfall and build a mapping of set_name -> set_code.
    
    Returns:
        Dictionary mapping set names to set codes
    """
    print("Fetching all sets from Scryfall...")
    url = "https://api.scryfall.com/sets"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("object") == "error":
            raise Exception(f"Scryfall API error: {data.get('details', 'Unknown error')}")
        
        sets = data.get("data", [])
        name_to_code = {}
        
        for set_obj in sets:
            set_name = set_obj.get("name", "")
            set_code = set_obj.get("code", "")
            if set_name and set_code:
                name_to_code[set_name] = set_code
                # Also add alternative names for common variations
                if set_name == "Unlimited Edition":
                    name_to_code["Unlimited"] = set_code
                elif set_name == "Revised Edition":
                    name_to_code["Revised"] = set_code
                elif set_name == "Classic Sixth Edition":
                    name_to_code["Sixth Edition"] = set_code
                # Handle set codes directly (in case we need them)
                name_to_code[set_code.upper()] = set_code  # Store uppercase version too
        
        print(f"Fetched {len(name_to_code)} sets from Scryfall")
        return name_to_code
        
    except Exception as e:
        print(f"Error fetching sets: {e}")
        raise


def get_set_codes(set_names: List[str], name_to_code: Dict[str, str]) -> Set[str]:
    """
    Convert set names to Scryfall set codes.
    
    Args:
        set_names: List of set names
        name_to_code: Mapping of set names to codes
        
    Returns:
        Set of set codes
    """
    codes = set()
    for name in set_names:
        # Normalize the name first
        normalized = normalize_set_name(name)
        
        # Try direct lookup
        if normalized in name_to_code:
            code = name_to_code[normalized]
            # Ensure lowercase (Scryfall codes are lowercase)
            codes.add(code.lower())
        else:
            print(f"Warning: Could not find set code for '{name}' (normalized: '{normalized}')")
    
    return codes


def resolve_card_to_oracle_id(card_name: str) -> Optional[str]:
    """
    Resolve a card name to its Oracle card ID.
    
    Args:
        card_name: Name of the card
        
    Returns:
        Oracle ID if found, None otherwise
    """
    time.sleep(SCRYFALL_DELAY)
    
    try:
        # Use exact name search
        url = "https://api.scryfall.com/cards/named"
        params = {"exact": card_name}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 404:
            # Try fuzzy search as fallback
            params = {"fuzzy": card_name}
            response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        if data.get("object") == "error":
            return None
        
        return data.get("oracle_id")
        
    except Exception as e:
        print(f"Error resolving card '{card_name}': {e}")
        return None


def fetch_all_printings(oracle_id: str) -> List[Dict]:
    """
    Fetch all printings for an Oracle card.
    
    Args:
        oracle_id: Oracle ID of the card
        
    Returns:
        List of printing objects
    """
    time.sleep(SCRYFALL_DELAY)
    
    all_printings = []
    url = f"https://api.scryfall.com/cards/search"
    params = {"q": f"oracleid:{oracle_id}", "unique": "prints"}
    
    try:
        while url:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                break
            
            data = response.json()
            if data.get("object") == "error":
                break
            
            printings = data.get("data", [])
            all_printings.extend(printings)
            
            # Check for pagination
            if data.get("has_more"):
                url = data.get("next_page")
                params = None  # next_page is a full URL
            else:
                url = None
        
        return all_printings
        
    except Exception as e:
        print(f"Error fetching printings for oracle_id '{oracle_id}': {e}")
        return []


def determine_format_validity(
    printings: List[Dict],
    old_school_codes: Set[str],
    premodern_codes: Set[str]
) -> Tuple[bool, bool, Set[str], Set[str]]:
    """
    Determine format validity based on printings.
    
    Args:
        printings: List of printing objects from Scryfall
        old_school_codes: Set of Old School legal set codes
        premodern_codes: Set of Premodern legal set codes
        
    Returns:
        Tuple of (is_old_school, is_premodern, old_school_sets, premodern_sets)
    """
    printed_set_codes = set()
    
    for printing in printings:
        set_code = printing.get("set", "").lower()
        if set_code:
            printed_set_codes.add(set_code)
    
    # Check intersections
    old_school_intersection = printed_set_codes & old_school_codes
    premodern_intersection = printed_set_codes & premodern_codes
    
    is_old_school = len(old_school_intersection) > 0
    is_premodern = len(premodern_intersection) > 0
    
    return is_old_school, is_premodern, old_school_intersection, premodern_intersection


def get_format_label(is_old_school: bool, is_premodern: bool) -> str:
    """Get format label string."""
    if is_old_school and is_premodern:
        return "both"
    elif is_old_school:
        return "old_school_only"
    elif is_premodern:
        return "premodern_only"
    else:
        return "neither"


def main():
    """Main function to process collection and add format validity."""
    # Determine input file from command line argument or default
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "collection.json"
    
    print("=" * 60)
    print("Format Validity Classifier")
    print(f"Processing: {input_file}")
    print("=" * 60)
    
    # Step 1: Fetch all sets and build mapping
    print("\n[1/5] Fetching set codes from Scryfall...")
    name_to_code = fetch_all_sets()
    
    # Step 2: Build set code allow-lists
    print("\n[2/5] Building format allow-lists...")
    old_school_codes = get_set_codes(OLD_SCHOOL_SET_NAMES, name_to_code)
    premodern_codes = get_set_codes(PREMODERN_SET_NAMES, name_to_code)
    
    print(f"Old School 93/94 sets: {len(old_school_codes)} codes")
    print(f"Premodern sets: {len(premodern_codes)} codes")
    
    # Step 3: Load collection/wishlist
    print(f"\n[3/5] Loading {input_file}...")
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            collection = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        return
    except Exception as e:
        print(f"Error loading {input_file}: {e}")
        return
    
    print(f"Loaded {len(collection)} items from {input_file}")
    
    # Step 4: Get unique card names and resolve to Oracle IDs
    print("\n[4/5] Resolving cards to Oracle IDs...")
    unique_card_names = set()
    for item in collection:
        if "name" in item:
            unique_card_names.add(item["name"])
    
    print(f"Found {len(unique_card_names)} unique card names")
    
    # Build Oracle ID cache
    card_name_to_oracle_id = {}
    card_name_to_format_info = {}
    
    for i, card_name in enumerate(sorted(unique_card_names), 1):
        print(f"  [{i}/{len(unique_card_names)}] Resolving: {card_name}")
        oracle_id = resolve_card_to_oracle_id(card_name)
        
        if not oracle_id:
            print(f"    ⚠️  Could not resolve Oracle ID for '{card_name}'")
            continue
        
        card_name_to_oracle_id[card_name] = oracle_id
        
        # Fetch all printings
        print(f"    Fetching all printings...")
        printings = fetch_all_printings(oracle_id)
        
        if not printings:
            print(f"    ⚠️  No printings found for '{card_name}'")
            continue
        
        # Determine format validity
        is_old_school, is_premodern, old_school_sets, premodern_sets = determine_format_validity(
            printings, old_school_codes, premodern_codes
        )
        
        format_label = get_format_label(is_old_school, is_premodern)
        
        card_name_to_format_info[card_name] = {
            "format_validity": format_label,
            "old_school_legal": is_old_school,
            "premodern_legal": is_premodern,
            "old_school_sets": sorted(list(old_school_sets)),
            "premodern_sets": sorted(list(premodern_sets)),
            "total_printings": len(printings)
        }
        
        print(f"    ✅ {format_label} (OS: {is_old_school}, PM: {is_premodern})")
    
    # Step 5: Update collection with format information
    print("\n[5/5] Updating collection.json with format information...")
    
    updated_count = 0
    for item in collection:
        card_name = item.get("name")
        if card_name and card_name in card_name_to_format_info:
            format_info = card_name_to_format_info[card_name]
            # Add format fields to the item
            item["format_validity"] = format_info["format_validity"]
            item["old_school_legal"] = format_info["old_school_legal"]
            item["premodern_legal"] = format_info["premodern_legal"]
            item["old_school_sets"] = format_info["old_school_sets"]
            item["premodern_sets"] = format_info["premodern_sets"]
            updated_count += 1
    
    # Save updated collection (with backup)
    output_file = input_file
    backup_file = f"{input_file}.backup"
    
    print(f"\nCreating backup: {backup_file}...")
    try:
        shutil.copy2(output_file, backup_file)
        print(f"✅ Backup created")
    except Exception as e:
        print(f"⚠️  Warning: Could not create backup: {e}")
        print("   Continuing anyway...")
    
    print(f"\nSaving updated file to {output_file}...")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        print(f"✅ Successfully updated {updated_count} items in {output_file}")
    except Exception as e:
        print(f"❌ Error saving {output_file}: {e}")
        print(f"   Your original file is backed up as {backup_file}")
        return
    
    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    format_counts = defaultdict(int)
    for item in collection:
        format_validity = item.get("format_validity", "unknown")
        format_counts[format_validity] += 1
    
    for format_type, count in sorted(format_counts.items()):
        print(f"  {format_type}: {count} cards")
    
    print(f"\n✅ Done! Updated {output_file}")


if __name__ == "__main__":
    main()
