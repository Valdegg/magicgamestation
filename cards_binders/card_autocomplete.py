#!/usr/bin/env python3
"""
Card Autocomplete Module

Provides autocomplete functionality for Magic: The Gathering card names.
Combines local database prefix matching with Scryfall API autocomplete.

Usage as module:
    from card_autocomplete import autocomplete_cards
    
    results = autocomplete_cards("light", local_database=db, max_local=10, max_scryfall=5)

Usage as script:
    python card_autocomplete.py "light"
"""

import json
import requests
from typing import Dict, List, Optional, Tuple
from pathlib import Path


def load_local_database(database_path: str) -> Dict:
    """
    Load local card database from JSON file.
    
    Args:
        database_path: Path to cards.json file
        
    Returns:
        Dictionary mapping card IDs to card metadata, or empty dict if file not found
    """
    try:
        with open(database_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load local database from {database_path}: {e}")
        return {}


def get_unique_card_names(database: Dict) -> List[str]:
    """
    Extract unique card names from database.
    
    Args:
        database: Card database dictionary
        
    Returns:
        List of unique card names (case-preserved)
    """
    names = set()
    for card_data in database.values():
        if isinstance(card_data, dict) and 'name' in card_data:
            names.add(card_data['name'])
    return sorted(list(names))


def filter_local_cards(
    search_term: str,
    database: Dict,
    max_results: int = 10
) -> List[str]:
    """
    Filter local database cards by prefix match.
    
    Args:
        search_term: Search prefix (case-insensitive)
        database: Card database dictionary
        max_results: Maximum number of results to return
        
    Returns:
        List of matching card names (up to max_results)
    """
    if not search_term or not database:
        return []
    
    search_lower = search_term.lower()
    card_names = get_unique_card_names(database)
    
    matches = [
        name for name in card_names
        if name.lower().startswith(search_lower)
    ]
    
    return matches[:max_results]


def fetch_scryfall_autocomplete(
    search_term: str,
    timeout: int = 10
) -> Tuple[List[str], Optional[str]]:
    """
    Fetch autocomplete suggestions from Scryfall API.
    
    Args:
        search_term: Search prefix (minimum 2 characters)
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (list of card names, error message if any)
    """
    if not search_term or len(search_term) < 2:
        return [], None
    
    try:
        url = "https://api.scryfall.com/cards/autocomplete"
        params = {"q": search_term}
        
        response = requests.get(url, params=params, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("object") == "error":
                error_msg = data.get("details", data.get("type", "Unknown error"))
                return [], error_msg
            
            card_names = data.get("data", [])
            return card_names, None
        else:
            return [], f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return [], "Request timeout"
    except requests.exceptions.RequestException as e:
        return [], f"Request error: {str(e)}"
    except Exception as e:
        return [], f"Unexpected error: {str(e)}"


def autocomplete_cards(
    search_term: str,
    local_database: Optional[Dict] = None,
    database_path: Optional[str] = None,
    max_local: int = 10,
    max_scryfall: int = 5,
    exclude_local_from_scryfall: bool = True,
    timeout: int = 10
) -> Dict[str, any]:
    """
    Get autocomplete suggestions combining local database and Scryfall.
    
    Args:
        search_term: Search prefix to match
        local_database: Optional pre-loaded card database dictionary
        database_path: Optional path to cards.json file (used if local_database not provided)
        max_local: Maximum number of local results
        max_scryfall: Maximum number of Scryfall results
        exclude_local_from_scryfall: If True, filter out local cards from Scryfall results
        timeout: Scryfall API request timeout
        
    Returns:
        Dictionary with:
            - "local": List of matching local card names
            - "scryfall": List of Scryfall suggestions
            - "combined": Combined list (local first, then Scryfall)
            - "error": Error message if Scryfall fetch failed (None if successful)
    """
    # Load database if needed
    if local_database is None:
        if database_path:
            local_database = load_local_database(database_path)
        else:
            local_database = {}
    
    # Filter local cards
    local_matches = filter_local_cards(search_term, local_database, max_local)
    
    # Fetch from Scryfall (only if we have fewer than max_local local matches)
    scryfall_matches = []
    scryfall_error = None
    
    if len(local_matches) < max_local:
        scryfall_results, scryfall_error = fetch_scryfall_autocomplete(search_term, timeout)
        
        if scryfall_results:
            if exclude_local_from_scryfall:
                # Filter out cards we already have locally
                local_names_lower = {name.lower() for name in local_matches}
                scryfall_matches = [
                    name for name in scryfall_results
                    if name.lower() not in local_names_lower
                ][:max_scryfall]
            else:
                scryfall_matches = scryfall_results[:max_scryfall]
    
    # Combine results
    combined = local_matches + scryfall_matches
    
    return {
        "local": local_matches,
        "scryfall": scryfall_matches,
        "combined": combined,
        "error": scryfall_error
    }


def main():
    """Command-line interface for testing autocomplete."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python card_autocomplete.py <search_term> [database_path]")
        print("\nExample:")
        print("  python card_autocomplete.py light")
        print("  python card_autocomplete.py bolt ../frontend/public/data/cards.json")
        sys.exit(1)
    
    search_term = sys.argv[1]
    database_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"🔍 Searching for: '{search_term}'")
    print("-" * 60)
    
    # Try to find database if not provided
    if database_path is None:
        script_dir = Path(__file__).parent
        possible_paths = [
            script_dir / "../frontend/public/data/cards.json",
            script_dir / "frontend/public/data/cards.json",
            Path("../frontend/public/data/cards.json"),
            Path("frontend/public/data/cards.json"),
            Path("./cards.json")
        ]
        for path in possible_paths:
            abs_path = path.resolve()
            if abs_path.exists():
                database_path = str(abs_path)
                break
    
    if database_path:
        print(f"📚 Using database: {database_path}")
    else:
        print("📚 No local database found, using Scryfall only")
    
    print()
    
    # Perform autocomplete
    results = autocomplete_cards(
        search_term,
        database_path=database_path,
        max_local=10,
        max_scryfall=5
    )
    
    # Display results
    if results["local"]:
        print(f"✅ Local matches ({len(results['local'])}):")
        for name in results["local"]:
            print(f"   • {name}")
        print()
    
    if results["scryfall"]:
        print(f"🌐 Scryfall matches ({len(results['scryfall'])}):")
        for name in results["scryfall"]:
            print(f"   • {name}")
        print()
    
    if results["error"]:
        print(f"⚠️  Scryfall error: {results['error']}")
        print()
    
    if not results["local"] and not results["scryfall"]:
        print("❌ No matches found")
    
    print(f"\n📊 Total: {len(results['combined'])} suggestions")


if __name__ == "__main__":
    main()

