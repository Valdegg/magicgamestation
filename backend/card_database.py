"""
Card Database Utilities for Backend
Provides functions for working with the offline card database.
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional
from card_engine import Card, Player, Zone, ZoneType

# Cache for deck files to avoid repeated disk reads
_deck_cache: Dict[str, Dict] = {}

def normalize_card_id(name: str, set_code: str = None) -> str:
    """
    Normalize card name to create a consistent card ID.
    Set code is ignored as we use a single ID per card name.
    Example: "Lightning Bolt" -> "lightning_bolt"
    """
    normalized = re.sub(r"[',]", '', name.lower())
    normalized = re.sub(r'[^a-z0-9]', '_', normalized)
    normalized = re.sub(r'_+', '_', normalized).strip('_')
    return normalized

def load_card_database(path: str = "../frontend/public/data/cards.json") -> Dict:
    """Load card database from JSON file."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading card database from {path}: {e}")
        return {}

def get_card_metadata(database: Dict, card_id: str) -> Optional[Dict]:
    return database.get(card_id)

def load_deck(deck_name: str, base_path: str = "../frontend/public/decks", use_cache: bool = True) -> Dict:
    """Load a deck file with optional caching."""
    # Check cache first
    if use_cache and deck_name in _deck_cache:
        return _deck_cache[deck_name]
    
    # Try exact match first
    deck_path = Path(base_path) / f"{deck_name}.json"
    
    # If not found, try normalized filename (how save_deck saves it)
    if not deck_path.exists():
        normalized = re.sub(r'[^a-z0-9_]', '_', deck_name.lower())
        deck_path = Path(base_path) / f"{normalized}.json"

    try:
        with open(deck_path, 'r') as f:
            deck_data = json.load(f)
            # Cache the deck data
            if use_cache:
                _deck_cache[deck_name] = deck_data
            return deck_data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading deck {deck_path}: {e}")
        return {"name": deck_name, "main": [], "sideboard": []}

def clear_deck_cache(deck_name: Optional[str] = None):
    """Clear deck cache. If deck_name is None, clear all cached decks."""
    if deck_name:
        _deck_cache.pop(deck_name, None)
    else:
        _deck_cache.clear()

def extract_card_name_from_id(card_id: str) -> Optional[str]:
    """
    Extract card name from a card ID.
    Handles both new simple IDs ('lightning_bolt') and legacy IDs ('lightning_bolt_UNK').
    """
    # Check for legacy suffix pattern (e.g., _UNK or _A25)
    # If the last part is uppercase and 3-4 chars, likely a set code
    parts = card_id.split('_')
    if len(parts) > 1:
        last_part = parts[-1]
        if last_part.isupper() and (len(last_part) == 3 or last_part == "UNK"):
            parts.pop()
            
    return ' '.join(word.capitalize() for word in parts)

def find_card_by_name(database: Dict, card_name: str) -> Optional[str]:
    """Find a card ID by name (case-insensitive)."""
    target = card_name.lower()
    for card_id, metadata in database.items():
        if metadata.get('name', '').lower() == target:
            return card_id
    return None

def create_deck_for_player(deck_name: str, player: Player, database: Optional[Dict] = None) -> int:
    """Load a deck and create card instances for a player."""
    if database is None:
        database = load_card_database()
    
    deck = load_deck(deck_name, use_cache=True)
    library = player.zones[ZoneType.LIBRARY]
    sideboard = player.zones[ZoneType.SIDEBOARD]
    cards_loaded = 0
    
    def create_card_from_id(card_id: str, target_zone: Zone):
        """Helper function to create a card from card_id and add to target zone."""
        metadata = database.get(card_id, {})
        
        # If metadata missing, try to recover by re-normalizing or searching
        if not metadata:
            # Try finding by name if ID lookup failed
            name = extract_card_name_from_id(card_id)
            if name:
                found_id = find_card_by_name(database, name)
                if found_id:
                    card_id = found_id
                    metadata = database.get(found_id, {})
        
        # Prepare card data
        card_data = {
            'card_id': card_id,
            'set': metadata.get('set', ''),
            'type': metadata.get('type', ''),
            'image': metadata.get('image', ''),
            'mana_cost': metadata.get('mana_cost', ''),
            'cmc': metadata.get('cmc', 0),
            'oracle_text': metadata.get('oracle_text', ''),
            **metadata
        }
        card_name = metadata.get('name', card_id)
        
        # Debug logging for territorial kavu
        if 'territorial' in card_id.lower() or 'kavu' in card_id.lower():
            print(f"🔍 [create_deck_for_player] Card ID: '{card_id}', Using name: '{card_name}', Has metadata: {bool(metadata)}")
        
        card = Card(name=card_name, owner_id=player.id, data=card_data)
        target_zone.add(card)
        return 1
    
    # Load main deck cards
    for card_id in deck.get('main', []):
        cards_loaded += create_card_from_id(card_id, library)
    
    # Load sideboard cards if present
    for card_id in deck.get('sideboard', []):
        cards_loaded += create_card_from_id(card_id, sideboard)
    
    player.shuffle_library()
    main_count = len(deck.get('main', []))
    sideboard_count = len(deck.get('sideboard', []))
    print(f"✅ Loaded {main_count} main deck + {sideboard_count} sideboard = {cards_loaded} total cards from deck: {deck['name']}")
    return cards_loaded
