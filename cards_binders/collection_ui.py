#!/usr/bin/env python3
"""
Collection Management UI

A web interface for managing the MTG card collection.
Displays collection items in a card binder format, one card per set.
"""

import json
import os
import sys
import argparse
import re
import requests
import glob
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pathlib import Path
import threading

# Import card autocomplete functionality
try:
    from card_autocomplete import autocomplete_cards
except ImportError:
    autocomplete_cards = None
    print("Warning: card_autocomplete module not available", flush=True)

# Import database and authentication modules
import database
import auth

# Format legality sets (from determine_format_validity.py)
OLD_SCHOOL_SET_NAMES = [
    "Alpha", "Beta", "Unlimited Edition", "Revised Edition", "Arabian Nights",
    "Legends", "The Dark", "Fallen Empires", "Antiquities"
]

PREMODERN_SET_NAMES = [
    "Fourth Edition", "Ice Age", "Chronicles", "Homelands", "Alliances",
    "Mirage", "Visions", "Fifth Edition", "Weatherlight", "Tempest",
    "Stronghold", "Exodus", "Urza's Saga", "Urza's Legacy", "Classic Sixth Edition",
    "Urza's Destiny", "Mercadian Masques", "Nemesis", "Prophecy", "Invasion",
    "Planeshift", "Seventh Edition", "Apocalypse", "Odyssey", "Torment",
    "Judgment", "Onslaught", "Legions", "Scourge"
]

SET_NAME_ALIASES = {
    "Unlimited": "Unlimited Edition",
    "Revised": "Revised Edition",
    "Sixth Edition": "Classic Sixth Edition",
    "Classic Sixth Edition": "Classic Sixth Edition",
}

def normalize_set_name_for_format(set_name: str) -> str:
    """Normalize set name for format legality comparison."""
    if not set_name:
        return ""
    # Remove parenthetical suffixes like "(Foreign Black Bordered)"
    normalized = re.sub(r'\s*\([^)]*\)', '', set_name).strip()
    # Use alias if available
    return SET_NAME_ALIASES.get(normalized, normalized)

def determine_format_legality_from_sets(sets: List[str]) -> Dict[str, Any]:
    """
    Determine format legality based on set names.
    Returns dict with old_school_legal, premodern_legal, format_validity, etc.
    """
    if not sets:
        return {
            'old_school_legal': False,
            'premodern_legal': False,
            'format_validity': 'neither',
            'old_school_sets': [],
            'premodern_sets': []
        }
    
    old_school_sets = []
    premodern_sets = []
    
    for set_name in sets:
        normalized = normalize_set_name_for_format(set_name)
        
        # Check against Old School sets
        if normalized in OLD_SCHOOL_SET_NAMES:
            old_school_sets.append(set_name)
        # Also check original name
        elif set_name in OLD_SCHOOL_SET_NAMES:
            old_school_sets.append(set_name)
        
        # Check against Premodern sets
        if normalized in PREMODERN_SET_NAMES:
            premodern_sets.append(set_name)
        # Also check original name
        elif set_name in PREMODERN_SET_NAMES:
            premodern_sets.append(set_name)
    
    old_school_legal = len(old_school_sets) > 0
    premodern_legal = len(premodern_sets) > 0
    
    if old_school_legal and premodern_legal:
        format_validity = 'both'
    elif old_school_legal:
        format_validity = 'old_school_only'
    elif premodern_legal:
        format_validity = 'premodern_only'
    else:
        format_validity = 'neither'
    
    return {
        'old_school_legal': old_school_legal,
        'premodern_legal': premodern_legal,
        'format_validity': format_validity,
        'old_school_sets': old_school_sets,
        'premodern_sets': premodern_sets
    }

app = FastAPI(title="MTG Collection Manager", description="Collection Management Interface")

# Configuration
COLLECTION_FILE = "collection.json"
DEFAULT_PORT = 5003  # Different port from web_ui.py (5001) and wishlist_ui.py (5002)
IMAGE_DIR = "card_images"  # Directory for card images (oldest printing)
IMAGE_DIR_SETS = "card_images_sets"  # Directory for card images with set tracking

# Ensure image directories exist at startup
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR_SETS, exist_ok=True)
print(f"📁 Image directories initialized:", flush=True)
print(f"   - {os.path.abspath(IMAGE_DIR)} (oldest printing)", flush=True)
print(f"   - {os.path.abspath(IMAGE_DIR_SETS)} (set-specific)", flush=True)

# Mount static files - always mount since we create the directories above
app.mount("/card_images", StaticFiles(directory=IMAGE_DIR), name="card_images")
app.mount("/card_images_sets", StaticFiles(directory=IMAGE_DIR_SETS), name="card_images_sets")
print(f"✅ Static file mounts configured", flush=True)

# CORS middleware for API calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    database.init_db()
    print("✅ Database initialized", flush=True)


def load_collection(filepath: str = COLLECTION_FILE, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load collection from database (if user_id provided) or JSON file (if None)."""
    if user_id is not None:
        # Load from database
        return database.get_user_collection(user_id)
    else:
        # Load from JSON file (backward compatibility for non-logged-in users)
        try:
            if not os.path.exists(filepath):
                return []
            with open(filepath, 'r', encoding='utf-8') as f:
                collection = json.load(f)
            return collection
        except Exception as e:
            print(f"Error loading collection: {e}")
            return []


def save_collection(collection: List[Dict[str, Any]], filepath: str = COLLECTION_FILE, user_id: Optional[int] = None) -> bool:
    """Save collection to database (if user_id provided) or JSON file (if None)."""
    if user_id is not None:
        # Save to database
        return database.save_user_collection(user_id, collection)
    else:
        # Save to JSON file (backward compatibility for non-logged-in users)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(collection, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving collection: {e}")
            return False


def load_archived_collection(filepath: str = "collection_archived.json") -> List[Dict[str, Any]]:
    """Load archived collection from JSON file."""
    try:
        if not os.path.exists(filepath):
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            archived = json.load(f)
        return archived
    except Exception as e:
        print(f"Error loading archived collection: {e}")
        return []


def save_archived_collection(archived: List[Dict[str, Any]], filepath: str = "collection_archived.json") -> bool:
    """Save archived collection to JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(archived, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving archived collection: {e}")
        return False


def normalize_filename(name: str) -> str:
    """Normalize card name for filesystem filename."""
    original = name
    name = name.lower()
    name = re.sub(r"[',]", "", name)
    name = re.sub(r"[^a-z0-9]", "_", name)
    result = re.sub(r"_+", "_", name).strip("_")
    return result


def strip_variant_suffix(name: str) -> str:
    """Strip common variant suffixes like (IE), (Circle), etc. from card name."""
    # Remove patterns like (IE), (Circle), (A), (C), etc.
    name = re.sub(r'\s*\([^)]+\)\s*$', '', name)
    return name.strip()

def normalize_set_name(set_name: str) -> str:
    """Normalize set name for filesystem filename."""
    if not set_name:
        return ""
    name = set_name.lower()
    name = re.sub(r"[',]", "", name)
    # Normalize "bordered" to "border" to match existing filenames
    name = re.sub(r"\bbordered\b", "border", name)
    name = re.sub(r"[^a-z0-9]", "_", name)
    return re.sub(r"_+", "_", name).strip("_")

def get_image_filename(card_name: str, set_name: Optional[str] = None) -> str:
    """Generate image filename with optional set name."""
    card_part = normalize_filename(card_name)
    if set_name:
        set_part = normalize_set_name(set_name)
        return f"{card_part};{set_part}.jpg"
    return f"{card_part}.jpg"


def get_scryfall_set_code(set_name: str) -> str:
    """
    Get Scryfall set code for a given set name.
    Returns the set code, or the normalized name without parentheses if not found.
    Special handling for International Edition -> CEI, Collector's Edition -> CED.
    """
    # Normalize set name by removing parentheses (Scryfall doesn't use parentheses)
    normalized_name = set_name.replace("(", "").replace(")", "").strip()
    
    # Special cases: Scryfall uses different codes
    set_name_lower = set_name.lower()
    normalized_lower = normalized_name.lower()
    
    if "international edition" in normalized_lower:
        return "CEI"
    if "collector's edition" in normalized_lower or "collectors edition" in normalized_lower:
        return "CED"
    
    # Map foreign border sets to Scryfall codes
    if normalized_lower == "fourth edition foreign black border":
        return "4bb"
    if normalized_lower == "revised edition foreign black border":
        return "3bb"
    if normalized_lower == "revised edition foreign white border":
        return "3eb"  # Revised Edition Foreign White Border
    
    # Try to load sets_data.json to get the code
    try:
        sets_file = "sets_data.json"
        if os.path.exists(sets_file):
            with open(sets_file, 'r', encoding='utf-8') as f:
                sets_data = json.load(f)
            # Try both original and normalized names
            for name_to_try in [set_name, normalized_name]:
                for set_data in sets_data:
                    set_data_name = set_data.get("name", "").lower()
                    if set_data_name == name_to_try.lower() or set_data_name == normalized_lower:
                        code = set_data.get("code", "")
                        # Map our codes to Scryfall codes
                        if code == "IE":
                            return "CEI"  # International Edition -> CEI
                        if code == "CED":
                            return "CED"  # Collector's Edition -> CED
                        return code
    except Exception as e:
        print(f"   ⚠️  Error loading sets_data.json: {e}", flush=True)
    
    # Fallback to normalized name (without parentheses)
    return normalized_name


def fetch_card_image_from_scryfall(card_name: str, set_name: Optional[str] = None, language: Optional[str] = None) -> Optional[str]:
    """
    Fetch card image from Scryfall API and save to card_images_sets directory.
    If set_name is provided, fetches from that specific set; otherwise uses oldest printing.
    Returns the image path if successful, None otherwise.
    """
    print(f"   🔍 fetch_card_image_from_scryfall called for: '{card_name}'" + (f" (set: {set_name})" if set_name else ""), flush=True)
    try:
        # Check if image already exists BEFORE querying Scryfall
        target_dir = IMAGE_DIR_SETS if set_name else IMAGE_DIR
        os.makedirs(target_dir, exist_ok=True)
        
        # Generate filename with set if provided
        filename = get_image_filename(card_name, set_name)
        filepath = os.path.join(target_dir, filename)
        print(f"   💾 Checking filepath: {os.path.abspath(filepath)}", flush=True)
        
        # Check if file already exists
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            file_size = os.path.getsize(filepath)
            print(f"   ⏭️  Image already exists ({file_size} bytes), skipping Scryfall query", flush=True)
            return f"/card_images_sets/{filename}" if set_name else f"/card_images/{filename}"
        
        # Fallback: Try without variant suffix (e.g., "Mox Jet (IE)" -> "Mox Jet")
        card_name_without_variant = strip_variant_suffix(card_name)
        if card_name_without_variant != card_name:
            fallback_filename = get_image_filename(card_name_without_variant, set_name)
            fallback_filepath = os.path.join(target_dir, fallback_filename)
            print(f"   🔍 Trying fallback filepath: {os.path.abspath(fallback_filepath)}", flush=True)
            if os.path.exists(fallback_filepath) and os.path.getsize(fallback_filepath) > 0:
                file_size = os.path.getsize(fallback_filepath)
                print(f"   ✅ Found image with fallback name ({file_size} bytes): {fallback_filename}", flush=True)
                return f"/card_images_sets/{fallback_filename}" if set_name else f"/card_images/{fallback_filename}"
        
        # Build query - if set is specified, search for that set
        if set_name:
            # Get Scryfall set code (prefer code over name for better matching)
            set_code = get_scryfall_set_code(set_name)
            print(f"   🔑 Using Scryfall set code: {set_code}", flush=True)
            
            # Try multiple query formats if first one fails
            queries_to_try = [
                f'!"{card_name}" set:{set_code.lower()}',  # lowercase, no quotes
                f'!"{card_name}" set:"{set_code}"',  # with quotes
                f'!"{card_name}" set:"{set_code.lower()}"',  # lowercase with quotes
                f'!"{card_name}" set:{set_code}',  # original case, no quotes
            ]
            
            # Also try with set name as fallback
            set_name_variants = [
                set_name,
                set_name.replace(" (Limited Edition)", ""),  # Remove parenthetical
            ]
            # Add Scryfall's exact set name variants
            if "international edition" in set_name.lower():
                set_name_variants.extend(["Intl. Collectors' Edition", "International Collectors' Edition", "CEI"])
            if "collector's edition" in set_name.lower():
                set_name_variants.extend(["Collectors' Edition", "CED"])
            if "alpha" in set_name.lower() and "limited" in set_name.lower():
                set_name_variants.extend(["Limited Edition Alpha", "Alpha", "LEA"])
            if "beta" in set_name.lower() and "limited" in set_name.lower():
                set_name_variants.extend(["Limited Edition Beta", "Beta", "LEB"])
            
            for variant in set_name_variants:
                queries_to_try.append(f'!"{card_name}" set:"{variant}"')
            
            resp = None
            successful_query = None
            
            for query in queries_to_try:
                print(f"   🌐 Trying query: {query}", flush=True)
                params = {
                    "q": query,
                    "unique": "prints"
                }
                
                try:
                    resp = requests.get("https://api.scryfall.com/cards/search", params=params, timeout=10)
                    print(f"   📡 Scryfall API response status: {resp.status_code}", flush=True)
                    
                    if resp.status_code == 200:
                        successful_query = query
                        break
                    elif resp.status_code == 404:
                        # Try next query format
                        error_data = resp.json() if resp.content else {}
                        if error_data.get("object") == "error":
                            error_msg = error_data.get("details", error_data.get("type", ""))
                            print(f"   ⚠️  Query failed: {error_msg}", flush=True)
                        continue
                    else:
                        # Other error, log and try next
                        print(f"   ⚠️  Unexpected status {resp.status_code}, trying next format", flush=True)
                        continue
                except Exception as e:
                    print(f"   ⚠️  Exception with query: {e}", flush=True)
                    continue
            
            if not resp or resp.status_code != 200:
                print(f"   ❌ All query formats failed for set {set_name}", flush=True)
                return None
            
            print(f"   ✅ Successful query: {successful_query}", flush=True)
        else:
            # Query Scryfall for the card (oldest printing)
            params = {
                "q": f'!"{card_name}"',
                "order": "released",
                "dir": "asc",
                "unique": "prints"
            }
            
            print(f"   🌐 Querying Scryfall API with: {params['q']}", flush=True)
            resp = requests.get("https://api.scryfall.com/cards/search", params=params, timeout=10)
            print(f"   📡 Scryfall API response status: {resp.status_code}", flush=True)
            
            if resp.status_code != 200:
                print(f"   ❌ Scryfall API returned status {resp.status_code}", flush=True)
                return None
        
        results = resp.json()
        if results.get("object") == "error":
            error_details = results.get("details", results.get("type", "Unknown error"))
            print(f"   ❌ Scryfall API error: {error_details}", flush=True)
            return None
        
        if not results.get("data"):
            print(f"   ❌ No cards found in Scryfall response", flush=True)
            return None
        
        print(f"   ✅ Found {len(results.get('data', []))} printings in Scryfall", flush=True)
        
        # Select the appropriate printing
        if set_name:
            # Try to find exact set match, optionally filtered by language
            data = None
            set_name_lower = set_name.lower()
            set_code_lower = get_scryfall_set_code(set_name).lower()
            
            # Language code mapping (Scryfall uses 2-letter codes)
            language_codes = {
                "italian": "it",
                "spanish": "es",
                "french": "fr",
                "german": "de",
                "portuguese": "pt",
                "japanese": "ja",
                "korean": "ko",
                "chinese": "zh",
                "russian": "ru"
            }
            target_lang_code = None
            if language:
                target_lang_code = language_codes.get(language.lower())
            
            for card_data in results["data"]:
                card_set = card_data.get("set_name", "").lower()
                card_set_code = card_data.get("set", "").lower()
                card_lang = card_data.get("lang", "").lower()
                
                # Match by set code (preferred) or set name
                # Special handling: International Edition maps to CEI, Collector's Edition to CED
                set_matches = (set_code_lower == card_set_code or 
                              set_name_lower in card_set or 
                              card_set in set_name_lower or  # Also check reverse contains
                              (set_name_lower == "international edition" and (card_set_code == "cei" or "intl" in card_set or "international" in card_set)) or
                              (set_name_lower == "collector's edition" and (card_set_code == "ced" or "collector" in card_set)))
                
                if set_matches:
                    # If language is specified, prefer matching language
                    if target_lang_code:
                        if card_lang == target_lang_code:
                            data = card_data
                            print(f"   ✅ Matched card from {card_set_code} ({card_set}) with language {card_lang}", flush=True)
                            break
                    else:
                        # No language filter, use first match
                        if not data:
                            data = card_data
                            print(f"   ✅ Matched card from {card_set_code} ({card_set})", flush=True)
            
            # If no exact match with language, try without language filter
            if not data and target_lang_code:
                print(f"   ⚠️  No match found with language {target_lang_code}, trying without language filter", flush=True)
                for card_data in results["data"]:
                    card_set = card_data.get("set_name", "").lower()
                    card_set_code = card_data.get("set", "").lower()
                    set_matches = (set_code_lower == card_set_code or 
                                  set_name_lower in card_set or 
                                  card_set in set_name_lower)
                    if set_matches:
                        data = card_data
                        print(f"   ✅ Matched card from {card_set_code} ({card_set}) without language filter", flush=True)
                        break
            
            # If still no exact match, use first result
            if not data:
                data = results["data"][0]
                print(f"   ⚠️  Exact set match not found, using first result", flush=True)
        else:
            # Get the oldest printing
            data = results["data"][0]
        
        card_found_name = data.get("name", "Unknown")
        card_set = data.get("set_name", data.get("set", "UNK"))
        print(f"   📅 Using printing: {card_found_name} ({card_set})", flush=True)
        
        # Extract image URL
        img_url = None
        if "image_uris" in data:
            img_url = data["image_uris"].get("large") or data["image_uris"].get("normal")
            print(f"   ✅ Found image_uris: {img_url is not None}", flush=True)
        elif "card_faces" in data:
            print(f"   🔎 Card has {len(data.get('card_faces', []))} faces, checking first face", flush=True)
            face = data["card_faces"][0]
            if "image_uris" in face:
                img_url = face["image_uris"].get("large") or face["image_uris"].get("normal")
                print(f"   ✅ Found image_uris in card face: {img_url is not None}", flush=True)
        
        if not img_url:
            print(f"   ❌ No image URL found in card data", flush=True)
            print(f"   🔎 Card data keys: {list(data.keys())}", flush=True)
            return None
        
        # Use card_images_sets directory for set-specific images
        print(f"   📁 Image directory: {os.path.abspath(target_dir)}", flush=True)
        print(f"   💾 Target filepath: {os.path.abspath(filepath)}", flush=True)
        
        # Download image
        print(f"   📥 Downloading image from: {img_url[:80]}...", flush=True)
        img_resp = requests.get(img_url, headers={'User-Agent': 'MWS/1.0'}, timeout=30)
        print(f"   📡 Image download response status: {img_resp.status_code}", flush=True)
        
        if img_resp.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(img_resp.content)
            file_size = os.path.getsize(filepath)
            print(f"   ✅ Image downloaded successfully ({file_size} bytes) to {filepath}", flush=True)
            
            # Verify file exists
            if os.path.exists(filepath):
                print(f"   ✅ Verified file exists at: {os.path.abspath(filepath)}", flush=True)
            else:
                print(f"   ⚠️  WARNING: File was written but doesn't exist at: {os.path.abspath(filepath)}", flush=True)
            
            # Return the path relative to web root
            return f"/card_images_sets/{filename}" if set_name else f"/card_images/{filename}"
        else:
            print(f"   ❌ Image download failed with status {img_resp.status_code}", flush=True)
            return None
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timeout while fetching image for {card_name}", flush=True)
        return None
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request error while fetching image for {card_name}: {e}", flush=True)
        return None
    except Exception as e:
        print(f"   ❌ Unexpected error fetching image from Scryfall for {card_name}: {e}", flush=True)
        import traceback
        print(f"   ❌ Traceback: {traceback.format_exc()}", flush=True)
        return None


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


def find_or_create_latest_collection_deals_file() -> str:
    """
    Find the most recent collection_deals_*.json file, or create a new one if none exists.
    
    Returns:
        Path to the collection_deals file (existing or newly created)
    """
    results_dir = 'results'
    os.makedirs(results_dir, exist_ok=True)
    
    # Find all collection scan result files
    json_files = glob.glob(os.path.join(results_dir, 'collection_deals_*.json'))
    
    if json_files:
        # Sort by modification time, newest first
        json_files.sort(key=os.path.getmtime, reverse=True)
        latest_file = json_files[0]
        print(f"📊 Auto-scan: Found existing collection_deals file: {latest_file}", flush=True)
        return latest_file
    else:
        # Create new file with empty structure
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_file = os.path.join(results_dir, f'collection_deals_{timestamp}.json')
        initial_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'wishlist_file': 'collection.json',
            'config': {
                'min_discount': 0.0,
                'delay_between_cards': 0.0,
                'use_historical_data': True
            },
            'summary': {
                'total_deals': 0,
                'excellent': 0,
                'good': 0,
                'fair': 0,
                'expensive': 0,
                'no_data': 0
            },
            'deals': []
        }
        with open(new_file, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
        print(f"📊 Auto-scan: Created new collection_deals file: {new_file}", flush=True)
        return new_file


def append_deals_to_collection_file(deals_file: str, new_deals: List[Dict[str, Any]]) -> bool:
    """
    Append new deals to an existing collection_deals file and update summary counts.
    
    Args:
        deals_file: Path to the collection_deals JSON file
        new_deals: List of new deal dictionaries to append
        
    Returns:
        True if successful, False otherwise
    """
    if not new_deals:
        print(f"📊 Auto-scan: No new deals to append", flush=True)
        return True
    
    try:
        # Load existing file
        with open(deals_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Append new deals
        existing_deals = data.get('deals', [])
        existing_deals.extend(new_deals)
        data['deals'] = existing_deals
        
        # Update summary counts
        total_deals = len(existing_deals)
        excellent = len([d for d in existing_deals if d.get('category') == 'excellent'])
        good = len([d for d in existing_deals if d.get('category') == 'good'])
        fair = len([d for d in existing_deals if d.get('category') == 'fair'])
        expensive = len([d for d in existing_deals if d.get('category') == 'expensive'])
        no_data = len([d for d in existing_deals if d.get('category') == 'no_data'])
        
        data['summary'] = {
            'total_deals': total_deals,
            'excellent': excellent,
            'good': good,
            'fair': fair,
            'expensive': expensive,
            'no_data': no_data
        }
        
        # Update timestamp to current time (but keep original timestamp field)
        # This ensures the file remains "latest" by modification time
        data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Save updated file
        with open(deals_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Auto-scan: Appended {len(new_deals)} deal(s) to {deals_file}", flush=True)
        print(f"   Updated summary: {total_deals} total deals ({excellent} excellent, {good} good, {fair} fair, {expensive} expensive, {no_data} no_data)", flush=True)
        return True
    except Exception as e:
        print(f"❌ Auto-scan: Error appending deals to file: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False


def load_latest_collection_scan_results() -> Dict[str, Dict[str, Any]]:
    """
    Load the most recent collection market scan results and create a lookup dictionary.
    
    Returns:
        Dictionary mapping (card_name, expansion) -> market data
        Format: {(name_lower, expansion_lower): {'price': float, 'discount': float, 'category': str, ...}}
    """
    results_dir = 'results'
    if not os.path.exists(results_dir):
        print(f"⚠️  Market scan: results directory not found: {results_dir}", flush=True)
        return {}
    
    # Find all collection scan result files
    json_files = glob.glob(os.path.join(results_dir, 'collection_deals_*.json'))
    if not json_files:
        print(f"⚠️  Market scan: No collection_deals_*.json files found in {results_dir}", flush=True)
        return {}
    
    # Sort by modification time, newest first
    json_files.sort(key=os.path.getmtime, reverse=True)
    latest_file = json_files[0]
    print(f"📊 Market scan: Loading latest scan results from {latest_file}", flush=True)
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        print(f"📊 Market scan: File loaded, timestamp: {results.get('timestamp', 'unknown')}", flush=True)
        
        # Normalize deal data (reuse logic from web_ui.py)
        deals = []
        if 'deals' in results or 'candidates' in results:
            deal_list = results.get('deals', []) or results.get('candidates', [])
            print(f"📊 Market scan: Found {len(deal_list)} deals in scan results", flush=True)
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
                        import re
                        match = re.search(r'language=(\d+)', url)
                        if match:
                            language_code = int(match.group(1))
                            # Map language code to language name (normalize English to None)
                            language_map = {1: None, 2: 'French', 3: 'German', 4: 'Spanish', 5: 'Italian'}
                            language_name = language_map.get(language_code, None)
                    except Exception as e:
                        pass
                
                normalized = {
                    'card_name': card.get('name', ''),
                    'expansion': card.get('expansion') or card.get('expansionName') or None,
                    'price': live_data.get('cheapest_good_condition'),
                    'discount': deal.get('discounts', {}).get('discount_vs_market'),
                    'category': deal.get('category', 'unknown'),
                    'url': url,
                    'language': language_name,  # Store language extracted from URL (None for English/default)
                    'language_code': language_code,  # Store language code for matching
                    'timestamp': results.get('timestamp', '')
                }
                deals.append(normalized)
        else:
            print(f"⚠️  Market scan: No 'deals' or 'candidates' key in results", flush=True)
        
        # Create lookup dictionary: (name_lower, expansion_lower, language) -> market_data
        # Normalize expansion names to handle apostrophes (Urza's Legacy vs Urzas Legacy)
        # Include language in key to handle multiple cards with same name/set but different languages
        market_lookup = {}
        for deal in deals:
            card_name = deal.get('card_name', '').lower()
            expansion = deal.get('expansion')
            expansion_normalized = normalize_expansion_for_lookup(expansion) if expansion else None
            language = deal.get('language')  # Can be None for English/default
            
            # Create key with language (None for English/default)
            key = (card_name, expansion_normalized, language)
            
            # Store all language variants - prefer non-None language if available, otherwise keep first
            if key not in market_lookup:
                market_lookup[key] = deal
            elif deal.get('price') and language:  # Prefer entries with explicit language
                market_lookup[key] = deal
        
        print(f"✅ Market scan: Created lookup with {len(market_lookup)} entries", flush=True)
        if len(market_lookup) > 0:
            # Show first few examples
            sample_keys = list(market_lookup.keys())[:3]
            for key in sample_keys:
                lang_part = f", '{key[2]}'" if len(key) > 2 and key[2] else ", 'English'"
                print(f"   Example: ({key[0]}, '{key[1]}'{lang_part}) -> €{market_lookup[key].get('price', 'N/A')}", flush=True)
        
        return market_lookup
    except Exception as e:
        print(f"❌ Error loading collection scan results: {e}", flush=True)
        import traceback
        print(f"   Traceback: {traceback.format_exc()}", flush=True)
        return {}


def expand_collection_to_cards(collection: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Expand collection items to show one card per set.
    Each collection item with multiple sets becomes multiple card entries.
    Images are fetched on-demand when requested by the browser (via /api/fetch-card-image).
    Includes market value from most recent collection scan if available.
    """
    # Load market scan data once
    market_data = load_latest_collection_scan_results()
    print(f"📊 Collection cards: Loaded {len(market_data)} market scan entries", flush=True)
    
    cards = []
    matched_count = 0
    
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
        old_school_legal = item.get('old_school_legal', False)
        premodern_legal = item.get('premodern_legal', False)
        
        # If no sets specified, create one entry with no set
        if not sets:
            # Try to find market data
            market_value = None
            market_discount = None
            market_category = None
            market_url = None
            
            # Lookup key format matches load_latest_collection_scan_results: (name, expansion, language)
            collection_language = language if language and language.lower() not in ['', 'english'] else None
            lookup_key = (card_name.lower(), None, collection_language)
            if lookup_key in market_data:
                market_info = market_data[lookup_key]
                market_value = market_info.get('price')
                market_discount = market_info.get('discount')
                market_category = market_info.get('category')
                market_url = market_info.get('url')
                matched_count += 1
                if matched_count <= 3:  # Log first 3 matches
                    print(f"   ✅ Matched: {card_name} (no expansion, lang: {collection_language}) -> €{market_value}", flush=True)
            else:
                # Try without language (fallback for English)
                lookup_key_no_lang = (card_name.lower(), None, None)
                if lookup_key_no_lang in market_data:
                    market_info = market_data[lookup_key_no_lang]
                    market_value = market_info.get('price')
                    market_discount = market_info.get('discount')
                    market_category = market_info.get('category')
                    market_url = market_info.get('url')
                    matched_count += 1
                    if matched_count <= 3:  # Log first 3 matches
                        print(f"   ✅ Matched: {card_name} (no expansion, no lang) -> €{market_value}", flush=True)
            
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
                'old_school_legal': old_school_legal,
                'premodern_legal': premodern_legal,
                'market_value': market_value,
                'market_discount': market_discount,
                'market_category': market_category,
                'market_url': market_url,
                'collection_index': index  # Track original index for editing
            })
        else:
            # Create one card per set
            for expansion in sets:
                # Try to find market data for this specific card+expansion
                market_value = None
                market_discount = None
                market_category = None
                market_url = None
                
                # Map expansion name using same logic as scanning (e.g., Revised + Italian -> Foreign White Bordered)
                mapped_expansion = expansion
                if expansion and language:
                    try:
                        from mtg_arbitrage.wishlist import get_cardmarket_set_name
                        mapped_expansion = get_cardmarket_set_name(expansion, language)
                        if mapped_expansion != expansion:
                            print(f"   🔄 Matching: Mapped '{expansion}' -> '{mapped_expansion}' for {card_name}", flush=True)
                    except Exception as e:
                        print(f"   ⚠️  Error mapping expansion '{expansion}': {e}", flush=True)
                
                # Try exact match first with mapped expansion (normalized to handle apostrophes)
                # Include language in lookup key
                mapped_exp_normalized = normalize_expansion_for_lookup(mapped_expansion) if mapped_expansion else None
                collection_language = language if language and language.lower() not in ['', 'english'] else None
                
                # Try with language first (if collection item has language)
                lookup_key = (card_name.lower(), mapped_exp_normalized, collection_language)
                if lookup_key in market_data:
                    market_info = market_data[lookup_key]
                    market_value = market_info.get('price')
                    market_discount = market_info.get('discount')
                    market_category = market_info.get('category')
                    market_url = market_info.get('url')
                    matched_count += 1
                    if matched_count <= 3:  # Log first 3 matches
                        print(f"   ✅ Matched: {card_name} ({expansion} -> {mapped_expansion}, lang: {collection_language}) -> €{market_value}", flush=True)
                else:
                    # Try without language (fallback for English or if no language match)
                    lookup_key_no_lang = (card_name.lower(), mapped_exp_normalized, None)
                    if lookup_key_no_lang in market_data:
                        market_info = market_data[lookup_key_no_lang]
                        market_value = market_info.get('price')
                        market_discount = market_info.get('discount')
                        market_category = market_info.get('category')
                        market_url = market_info.get('url')
                        matched_count += 1
                        if matched_count <= 3:  # Log first 3 matches
                            print(f"   ✅ Matched (no lang): {card_name} ({expansion} -> {mapped_expansion}) -> €{market_value}", flush=True)
                    else:
                        # Try with 'English' as fallback (for old scan results that might have stored 'English' instead of None)
                        if collection_language is None:
                            lookup_key_english = (card_name.lower(), mapped_exp_normalized, 'English')
                            if lookup_key_english in market_data:
                                market_info = market_data[lookup_key_english]
                                market_value = market_info.get('price')
                                market_discount = market_info.get('discount')
                                market_category = market_info.get('category')
                                market_url = market_info.get('url')
                                matched_count += 1
                                if matched_count <= 3:  # Log first 3 matches
                                    print(f"   ✅ Matched (English fallback): {card_name} ({expansion} -> {mapped_expansion}) -> €{market_value}", flush=True)
                        # If still no match, try with original expansion name (normalized, fallback)
                        if market_value is None:
                            exp_normalized = normalize_expansion_for_lookup(expansion) if expansion else None
                            lookup_key_original = (card_name.lower(), exp_normalized, collection_language)
                            if lookup_key_original in market_data:
                                market_info = market_data[lookup_key_original]
                                market_value = market_info.get('price')
                                market_discount = market_info.get('discount')
                                market_category = market_info.get('category')
                                market_url = market_info.get('url')
                                matched_count += 1
                                if matched_count <= 3:  # Log first 3 matches
                                    print(f"   ✅ Matched (original normalized): {card_name} ({expansion}) -> €{market_value}", flush=True)
                            else:
                                # Try fuzzy match - check if expansion name contains or is contained (normalized)
                                # Also check language matches
                                for (name_key, exp_key, lang_key), market_info in market_data.items():
                                    if name_key == card_name.lower():
                                        # Check language match:
                                        # - Exact match: same language (including both None for English)
                                        # - English fallback: if collection item has no language (None), also match 'English' or None
                                        if collection_language is None:
                                            lang_matches = (lang_key is None) or (lang_key == 'English')
                                        else:
                                            lang_matches = (collection_language == lang_key)
                                        
                                        # Check if expansions match (fuzzy) - try mapped expansion first (normalized)
                                        if exp_key and mapped_exp_normalized and lang_matches:
                                            if exp_key in mapped_exp_normalized or mapped_exp_normalized in exp_key:
                                                market_value = market_info.get('price')
                                                market_discount = market_info.get('discount')
                                                market_category = market_info.get('category')
                                                market_url = market_info.get('url')
                                                matched_count += 1
                                                if matched_count <= 3:  # Log first 3 matches
                                                    print(f"   ✅ Fuzzy matched: {card_name} ({expansion} -> {mapped_expansion}, lang: {collection_language}) -> €{market_value} (matched {exp_key}, scan lang: {lang_key})", flush=True)
                                                break
                                        # Fallback to original expansion for fuzzy matching (normalized)
                                        elif exp_key and exp_normalized and lang_matches:
                                            if exp_key in exp_normalized or exp_normalized in exp_key:
                                                market_value = market_info.get('price')
                                                market_discount = market_info.get('discount')
                                                market_category = market_info.get('category')
                                                market_url = market_info.get('url')
                                                matched_count += 1
                                                if matched_count <= 3:  # Log first 3 matches
                                                    print(f"   ✅ Fuzzy matched: {card_name} ({expansion}, lang: {collection_language}) -> €{market_value} (matched {exp_key}, scan lang: {lang_key})", flush=True)
                                                break
                
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
                    'old_school_legal': old_school_legal,
                    'premodern_legal': premodern_legal,
                    'market_value': market_value,
                    'market_discount': market_discount,
                    'market_category': market_category,
                    'market_url': market_url,
                    'collection_index': index  # Track original index for editing
                })
    
    print(f"📊 Collection cards: Expanded to {len(cards)} cards, matched {matched_count} with market data", flush=True)
    return cards


@app.get("/", response_class=HTMLResponse)
async def collection_page():
    """Serve the collection management page."""
    html_path = Path("web_templates/collection_binder.html")
    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
            # Inject JavaScript to add language field support
            if 'language-field-support' not in html_content:
                language_script = """
    <script id="language-field-support">
    // Language field support for collection modal and card display
    (function() {
        'use strict';
        
        const LANGUAGE_OPTIONS = [
            { value: '', text: 'English (default)' },
            { value: 'Italian', text: 'Italian' },
            { value: 'Spanish', text: 'Spanish' },
            { value: 'French', text: 'French' },
            { value: 'German', text: 'German' },
            { value: 'Portuguese', text: 'Portuguese' },
            { value: 'Japanese', text: 'Japanese' },
            { value: 'Korean', text: 'Korean' },
            { value: 'Chinese', text: 'Chinese' },
            { value: 'Russian', text: 'Russian' }
        ];
        
        // Add language and foil fields to modal
        function addLanguageField() {
            const notesField = document.querySelector('textarea[placeholder*="notes" i], textarea[placeholder*="Notes" i]');
            if (!notesField || (notesField.parentElement.querySelector('[name="language"]') && notesField.parentElement.querySelector('[name="foil"]'))) return;
            
            const select = document.createElement('select');
            select.name = 'language';
            select.id = 'card-language';
            select.style.cssText = 'width: 100%; padding: 8px; margin: 10px 0 15px 0; border: 1px solid #444; background: #222; color: #fff; border-radius: 4px; font-size: 14px;';
            
            LANGUAGE_OPTIONS.forEach(lang => {
                const opt = document.createElement('option');
                opt.value = lang.value;
                opt.textContent = lang.text;
                select.appendChild(opt);
            });
            
            const label = document.createElement('label');
            label.textContent = 'Language:';
            label.setAttribute('for', 'card-language');
            label.style.cssText = 'display: block; margin-top: 10px; margin-bottom: 5px; color: #d4af37; font-weight: 500;';
            
            notesField.parentElement.insertBefore(label, notesField.nextSibling);
            notesField.parentElement.insertBefore(select, label.nextSibling);
            
            // Add foil checkbox
            const foilLabel = document.createElement('label');
            foilLabel.textContent = 'Foil:';
            foilLabel.setAttribute('for', 'card-foil');
            foilLabel.style.cssText = 'display: block; margin-top: 10px; margin-bottom: 5px; color: #d4af37; font-weight: 500;';
            
            const foilCheckbox = document.createElement('input');
            foilCheckbox.type = 'checkbox';
            foilCheckbox.name = 'foil';
            foilCheckbox.id = 'card-foil';
            foilCheckbox.checked = false;
            foilCheckbox.style.cssText = 'width: auto; margin-right: 8px; transform: scale(1.2);';
            
            const foilContainer = document.createElement('div');
            foilContainer.style.cssText = 'display: flex; align-items: center; margin-top: 10px; margin-bottom: 15px;';
            foilContainer.appendChild(foilCheckbox);
            foilContainer.appendChild(document.createTextNode('Foil'));
            
            notesField.parentElement.insertBefore(foilLabel, notesField.nextSibling);
            notesField.parentElement.insertBefore(foilContainer, foilLabel.nextSibling);
        }
        
        // Intercept fetch calls to add language to API requests
        if (!window.originalFetch) {
            window.originalFetch = window.fetch;
        }
        window.fetch = function(...args) {
            const url = args[0];
            const options = args[1] || {};
            
            // Handle collection save/update
            if (typeof url === 'string' && url.includes('/api/collection') && (options.method === 'POST' || options.method === 'PUT')) {
                if (options.body) {
                    try {
                        const body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body;
                        const langField = document.querySelector('[name="language"]');
                        if (langField) {
                            const langValue = langField.value || '';
                            body.language = langValue;
                        }
                        const foilField = document.querySelector('[name="foil"]');
                        if (foilField) {
                            body.foil = foilField.checked;
                        }
                        if (langField || foilField) {
                            options.body = JSON.stringify(body);
                            args[1] = options;
                        }
                    } catch(e) {
                        console.error('Error adding language to request:', e);
                    }
                }
            }
            
            // Handle image fetch - add language parameter
            if (typeof url === 'string' && url.includes('/api/fetch-card-image')) {
                // Try to get language from the card being rendered
                const activeCard = document.querySelector('[data-card-name]');
                const language = activeCard?.dataset.language;
                if (language && language !== '' && language.toLowerCase() !== 'english') {
                    const separator = url.includes('?') ? '&' : '?';
                    args[0] = url + separator + 'language=' + encodeURIComponent(language);
                }
            }
            
            return window.originalFetch.apply(this, args);
        };
        
        // Update card display to show language, foil, and market value
        function updateCardDisplays() {
            document.querySelectorAll('[data-card-name]').forEach(cardEl => {
                const language = cardEl.dataset.language;
                const foil = cardEl.dataset.foil === 'true';
                const marketValue = cardEl.dataset.marketValue;
                const marketDiscount = cardEl.dataset.marketDiscount;
                const marketCategory = cardEl.dataset.marketCategory;
                const marketUrl = cardEl.dataset.marketUrl;
                
                if (language && language !== '' && language.toLowerCase() !== 'english') {
                    // Check if language already displayed
                    if (cardEl.querySelector('.card-language')) return;
                    
                    const expansionDiv = cardEl.querySelector('.card-expansion, [class*="expansion"]');
                    if (expansionDiv) {
                        const langDiv = document.createElement('div');
                        langDiv.className = 'card-language';
                        langDiv.textContent = language;
                        langDiv.style.cssText = 'color: #d4af37; font-size: 0.85em; margin-top: 2px; font-weight: 500;';
                        expansionDiv.parentNode.insertBefore(langDiv, expansionDiv.nextSibling);
                    }
                }
                
                if (foil && !cardEl.querySelector('.card-foil')) {
                    const expansionDiv = cardEl.querySelector('.card-expansion, [class*="expansion"]');
                    if (expansionDiv) {
                        const foilDiv = document.createElement('div');
                        foilDiv.className = 'card-foil';
                        foilDiv.textContent = '★ Foil';
                        foilDiv.style.cssText = 'color: #ffd700; font-size: 0.85em; margin-top: 2px; font-weight: 600; text-shadow: 0 0 3px rgba(255, 215, 0, 0.5);';
                        const langDiv = cardEl.querySelector('.card-language');
                        if (langDiv) {
                            langDiv.parentNode.insertBefore(foilDiv, langDiv.nextSibling);
                        } else {
                            expansionDiv.parentNode.insertBefore(foilDiv, expansionDiv.nextSibling);
                        }
                    }
                }
                
                // Display market value if available
                if (marketValue && !cardEl.querySelector('.card-market-value')) {
                    const cardName = cardEl.dataset.cardName || cardEl.textContent?.substring(0, 30) || 'Unknown';
                    console.log(`🔍 updateCardDisplays: Market value found for ${cardName}: €${marketValue}`);
                    
                    // Try multiple selectors to find where to insert market value
                    let insertPoint = cardEl.querySelector('.card-price, [class*="price"], [class*="buy"], [class*="cost"], [class*="bought"]');
                    
                    // If no price element found, try to find condition or any info section
                    if (!insertPoint) {
                        insertPoint = cardEl.querySelector('.card-condition, [class*="condition"], .card-info, [class*="info"]');
                    }
                    
                    // If still nothing, try to find the card overlay or details section
                    if (!insertPoint) {
                        insertPoint = cardEl.querySelector('.card-overlay, [class*="overlay"], .card-details, [class*="details"]');
                    }
                    
                    // Debug: log what we found
                    if (insertPoint) {
                        console.log(`✅ updateCardDisplays: Found insert point for ${cardName}:`, insertPoint.className || insertPoint.tagName);
                    } else {
                        console.warn(`⚠️  updateCardDisplays: No insert point found for ${cardName}`);
                        console.log(`   Card element structure:`, cardEl.innerHTML.substring(0, 300));
                    }
                    
                    if (insertPoint) {
                        const marketDiv = document.createElement('div');
                        marketDiv.className = 'card-market-value';
                        
                        const value = parseFloat(marketValue);
                        let marketText = `Market: €${value.toFixed(2)}`;
                        
                        // Add category color coding
                        let color = '#e0e0e0'; // Default gray
                        if (marketCategory === 'excellent') {
                            color = '#4ade80'; // Green
                        } else if (marketCategory === 'good') {
                            color = '#fbbf24'; // Yellow/Amber
                        } else if (marketCategory === 'fair') {
                            color = '#60a5fa'; // Blue
                        } else if (marketCategory === 'expensive') {
                            color = '#f87171'; // Red
                        }
                        
                        marketDiv.textContent = marketText;
                        marketDiv.style.cssText = `color: ${color}; font-size: 1em; margin-top: 4px; font-weight: 500;`;
                        
                        // Add hover tooltip with debug info
                        const debugInfo = `Market Value: €${value.toFixed(2)}\\n` +
                            (marketDiscount ? `Discount: ${parseFloat(marketDiscount).toFixed(1)}%\\n` : '') +
                            `Category: ${marketCategory || 'unknown'}\\n` +
                            `Card: ${cardName}`;
                        marketDiv.title = debugInfo;
                        
                        // Add hover event for debugging
                        marketDiv.addEventListener('mouseenter', function() {
                            console.log('🖱️  Market value hover (updateCardDisplays):', {
                                card: cardName,
                                marketValue: value,
                                discount: marketDiscount,
                                category: marketCategory,
                                url: marketUrl
                            });
                        });
                        
                        // Make it clickable if URL available
                        if (marketUrl) {
                            marketDiv.style.cursor = 'pointer';
                            marketDiv.style.textDecoration = 'underline';
                            marketDiv.title += '\\n\\nClick to view on Cardmarket';
                            marketDiv.addEventListener('click', function(e) {
                                e.stopPropagation();
                                console.log('🔗 Opening Cardmarket URL:', marketUrl);
                                window.open(marketUrl, '_blank');
                            });
                        }
                        
                        // Insert after the found element
                        if (insertPoint.nextSibling) {
                            insertPoint.parentNode.insertBefore(marketDiv, insertPoint.nextSibling);
                            console.log(`✅ updateCardDisplays: Inserted market value for ${cardName} after insertPoint`);
                        } else {
                            insertPoint.parentNode.appendChild(marketDiv);
                            console.log(`✅ updateCardDisplays: Appended market value for ${cardName} to parent`);
                        }
                    } else {
                        console.warn(`❌ updateCardDisplays: Could not insert market value for ${cardName} - no insert point found`);
                    }
                } else if (marketValue) {
                    console.debug(`ℹ️  updateCardDisplays: Market value already displayed for card`);
                }
            });
        }
        
        // Hook into card rendering to add language, foil, and market value display and data attributes
        if (typeof createCardHTML === 'function') {
            const original = createCardHTML;
            window.createCardHTML = function(card, cardIndex) {
                const html = original.call(this, card, cardIndex);
                const temp = document.createElement('div');
                temp.innerHTML = html;
                const cardEl = temp.firstElementChild;
                
                if (cardEl) {
                    // Always store language in data attribute (even if English/empty)
                    if (card.language !== undefined) {
                        cardEl.setAttribute('data-language', card.language || '');
                    }
                    
                    // Store foil in data attribute
                    if (card.foil !== undefined) {
                        cardEl.setAttribute('data-foil', card.foil ? 'true' : 'false');
                    }
                    
                    // Store market value data attributes
                    if (card.market_value !== undefined && card.market_value !== null) {
                        cardEl.setAttribute('data-market-value', card.market_value);
                    }
                    if (card.market_discount !== undefined && card.market_discount !== null) {
                        cardEl.setAttribute('data-market-discount', card.market_discount);
                    }
                    if (card.market_category !== undefined && card.market_category !== null) {
                        cardEl.setAttribute('data-market-category', card.market_category);
                    }
                    if (card.market_url !== undefined && card.market_url !== null) {
                        cardEl.setAttribute('data-market-url', card.market_url);
                    }
                    
                    // Store market value data attributes
                    if (card.market_value !== undefined && card.market_value !== null) {
                        cardEl.setAttribute('data-market-value', card.market_value);
                    }
                    if (card.market_discount !== undefined && card.market_discount !== null) {
                        cardEl.setAttribute('data-market-discount', card.market_discount);
                    }
                    if (card.market_category !== undefined && card.market_category !== null) {
                        cardEl.setAttribute('data-market-category', card.market_category);
                    }
                    if (card.market_url !== undefined && card.market_url !== null) {
                        cardEl.setAttribute('data-market-url', card.market_url);
                    }
                    
                    // Display language if not English/empty
                    if (card.language && card.language !== '' && card.language.toLowerCase() !== 'english') {
                        const expansion = cardEl.querySelector('.card-expansion, [class*="expansion"]');
                        if (expansion && !cardEl.querySelector('.card-language')) {
                            const langDiv = document.createElement('div');
                            langDiv.className = 'card-language';
                            langDiv.textContent = card.language;
                            langDiv.style.cssText = 'color: #d4af37; font-size: 0.85em; margin-top: 2px; font-weight: 500;';
                            expansion.parentNode.insertBefore(langDiv, expansion.nextSibling);
                        }
                    }
                    
                    // Display foil indicator if true
                    if (card.foil === true) {
                        const expansion = cardEl.querySelector('.card-expansion, [class*="expansion"]');
                        if (expansion && !cardEl.querySelector('.card-foil')) {
                            const foilDiv = document.createElement('div');
                            foilDiv.className = 'card-foil';
                            foilDiv.textContent = '★ Foil';
                            foilDiv.style.cssText = 'color: #ffd700; font-size: 0.85em; margin-top: 2px; font-weight: 600; text-shadow: 0 0 3px rgba(255, 215, 0, 0.5);';
                            const langDiv = cardEl.querySelector('.card-language');
                            if (langDiv) {
                                langDiv.parentNode.insertBefore(foilDiv, langDiv.nextSibling);
                            } else {
                                expansion.parentNode.insertBefore(foilDiv, expansion.nextSibling);
                            }
                        }
                    }
                    
                    // Display market value if available
                    if (card.market_value !== undefined && card.market_value !== null && !cardEl.querySelector('.card-market-value')) {
                        console.log(`🔍 Market value found for ${card.name}: €${card.market_value}`, card);
                        
                        // Try multiple selectors to find where to insert market value
                        let insertPoint = cardEl.querySelector('.card-price, [class*="price"], [class*="buy"], [class*="cost"], [class*="bought"]');
                        
                        // If no price element found, try to find condition or any info section
                        if (!insertPoint) {
                            insertPoint = cardEl.querySelector('.card-condition, [class*="condition"], .card-info, [class*="info"]');
                        }
                        
                        // If still nothing, try to find the card overlay or details section
                        if (!insertPoint) {
                            insertPoint = cardEl.querySelector('.card-overlay, [class*="overlay"], .card-details, [class*="details"]');
                        }
                        
                        // Debug: log what we found
                        if (insertPoint) {
                            console.log(`✅ Found insert point for ${card.name}:`, insertPoint.className || insertPoint.tagName);
                        } else {
                            console.warn(`⚠️  No insert point found for ${card.name}, card structure:`, cardEl.innerHTML.substring(0, 200));
                        }
                        
                        if (insertPoint) {
                            const marketDiv = document.createElement('div');
                            marketDiv.className = 'card-market-value';
                            
                            const marketValue = parseFloat(card.market_value);
                            let marketText = `Market: €${marketValue.toFixed(2)}`;
                            
                            // Add category color coding
                            let color = '#e0e0e0'; // Default gray
                            if (card.market_category === 'excellent') {
                                color = '#4ade80'; // Green
                            } else if (card.market_category === 'good') {
                                color = '#fbbf24'; // Yellow/Amber
                            } else if (card.market_category === 'fair') {
                                color = '#60a5fa'; // Blue
                            } else if (card.market_category === 'expensive') {
                                color = '#f87171'; // Red
                            }
                            
                            marketDiv.textContent = marketText;
                            marketDiv.style.cssText = `color: ${color}; font-size: 0.9em; margin-top: 4px; font-weight: 500;`;
                            
                            // Add hover tooltip with debug info
                            const debugInfo = `Market Value: €${marketValue.toFixed(2)}\\n` +
                                (card.market_discount ? `Discount: ${parseFloat(card.market_discount).toFixed(1)}%\\n` : '') +
                                `Category: ${card.market_category || 'unknown'}\\n` +
                                `Card: ${card.name}\\n` +
                                `Expansion: ${card.expansion || 'none'}`;
                            marketDiv.title = debugInfo;
                            
                            // Add hover event for debugging
                            marketDiv.addEventListener('mouseenter', function() {
                                console.log('🖱️  Market value hover:', {
                                    card: card.name,
                                    expansion: card.expansion,
                                    marketValue: marketValue,
                                    discount: card.market_discount,
                                    category: card.market_category,
                                    url: card.market_url
                                });
                            });
                            
                            // Make it clickable if URL available
                            if (card.market_url) {
                                marketDiv.style.cursor = 'pointer';
                                marketDiv.style.textDecoration = 'underline';
                                marketDiv.title += '\\n\\nClick to view on Cardmarket';
                                marketDiv.addEventListener('click', function(e) {
                                    e.stopPropagation();
                                    console.log('🔗 Opening Cardmarket URL:', card.market_url);
                                    window.open(card.market_url, '_blank');
                                });
                            }
                            
                            // Insert after the found element
                            if (insertPoint.nextSibling) {
                                insertPoint.parentNode.insertBefore(marketDiv, insertPoint.nextSibling);
                                console.log(`✅ Inserted market value for ${card.name} after insertPoint`);
                            } else {
                                insertPoint.parentNode.appendChild(marketDiv);
                                console.log(`✅ Appended market value for ${card.name} to parent`);
                            }
                        } else {
                            console.warn(`❌ Could not insert market value for ${card.name} - no insert point found`);
                        }
                    } else if (card.market_value === null || card.market_value === undefined) {
                        // Log when market value is missing
                        if (card.name && card.name !== 'Unknown') {
                            console.debug(`ℹ️  No market value for ${card.name} (${card.expansion || 'no expansion'})`);
                        }
                    }
                    
                    return temp.innerHTML;
                }
                return html;
            };
        }
        
        // Initialize
        function init() {
            const checkAndAdd = () => {
                addLanguageField();
                updateCardDisplays();
            };
            
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => {
                    setTimeout(checkAndAdd, 500);
                    setInterval(checkAndAdd, 1000);
                });
            } else {
                setTimeout(checkAndAdd, 500);
                setInterval(checkAndAdd, 1000);
            }
            
            // Watch for modal opens and populate foil field when editing
            const observer = new MutationObserver((mutations) => {
                checkAndAdd();
                // Try to populate foil checkbox when modal opens with existing card data
                const foilCheckbox = document.querySelector('[name="foil"]');
                if (foilCheckbox) {
                    // Check if we're editing - look for card data in the modal or form
                    const form = foilCheckbox.closest('form');
                    if (form) {
                        // Try to get card data from various possible sources
                        const cardDataAttr = form.getAttribute('data-card-data');
                        if (cardDataAttr) {
                            try {
                                const cardData = JSON.parse(cardDataAttr);
                                if (cardData.foil !== undefined) {
                                    foilCheckbox.checked = Boolean(cardData.foil);
                                }
                            } catch(e) {}
                        }
                        // Also check if card data is stored elsewhere in the form
                        const hiddenInputs = form.querySelectorAll('input[type="hidden"]');
                        hiddenInputs.forEach(input => {
                            if (input.name === 'card_data' || input.name === 'original_card') {
                                try {
                                    const cardData = JSON.parse(input.value);
                                    if (cardData.foil !== undefined) {
                                        foilCheckbox.checked = Boolean(cardData.foil);
                                    }
                                } catch(e) {}
                            }
                        });
                    }
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
        
        // Debug function: Check market data for cards
        window.debugMarketData = function() {
            console.log('🔍 Debugging Market Data');
            console.log('='.repeat(60));
            
            // Check API response
            fetch('/api/collection-cards')
                .then(res => res.json())
                .then(data => {
                    console.log(`📊 Total cards: ${data.cards.length}`);
                    const withMarket = data.cards.filter(c => c.market_value !== undefined && c.market_value !== null);
                    console.log(`📊 Cards with market data: ${withMarket.length}`);
                    
                    if (withMarket.length > 0) {
                        console.log('✅ Sample cards with market data:');
                        withMarket.slice(0, 5).forEach(card => {
                            console.log(`   - ${card.name} (${card.expansion || 'no expansion'}): €${card.market_value}`, card);
                        });
                    } else {
                        console.warn('⚠️  No cards have market data!');
                        console.log('   First 5 cards:', data.cards.slice(0, 5).map(c => ({
                            name: c.name,
                            expansion: c.expansion,
                            has_market_value: c.market_value !== undefined
                        })));
                    }
                    
                    // Check DOM elements
                    const cardElements = document.querySelectorAll('[data-card-name], [class*="card"]');
                    console.log(`\n📋 Found ${cardElements.length} card elements in DOM`);
                    
                    let foundMarketValues = 0;
                    cardElements.forEach((el, idx) => {
                        if (el.querySelector('.card-market-value')) {
                            foundMarketValues++;
                            if (foundMarketValues <= 3) {
                                console.log(`   ✅ Card ${idx} has market value displayed`);
                            }
                        }
                        if (el.dataset.marketValue) {
                            console.log(`   📊 Card ${idx} has market data attribute: €${el.dataset.marketValue}`);
                        }
                    });
                    
                    console.log(`\n📊 Summary: ${foundMarketValues} cards have market value displayed in DOM`);
                })
                .catch(err => console.error('❌ Error checking market data:', err));
        };
        
        // Log when cards are loaded
        if (!window.originalFetch) {
            window.originalFetch = window.fetch;
        }
        window.fetch = function(...args) {
            const url = args[0];
            if (typeof url === 'string' && url.includes('/api/collection-cards')) {
                return window.originalFetch.apply(this, args).then(response => {
                    response.clone().json().then(data => {
                        const withMarket = data.cards.filter(c => c.market_value !== undefined && c.market_value !== null);
                        console.log(`📊 Cards loaded: ${data.cards.length} total, ${withMarket.length} with market data`);
                        if (withMarket.length > 0) {
                            console.log('   Sample:', withMarket.slice(0, 3).map(c => `${c.name}: €${c.market_value}`).join(', '));
                        }
                    });
                    return response;
                });
            }
            return window.originalFetch.apply(this, args);
        };
        
        init();
    })();
    </script>
"""
                # Inject language support script
                if '</body>' in html_content:
                    html_content = html_content.replace('</body>', language_script + '\n</body>')
                elif '</html>' in html_content:
                    html_content = html_content.replace('</html>', language_script + '\n</html>')
                else:
                    html_content += language_script
            
            # Inject JavaScript for Enter key navigation in set autocomplete
            if 'set-autocomplete-enter-navigation' not in html_content:
                set_navigation_script = """
    <script id="set-autocomplete-enter-navigation">
    // Enter key navigation for set autocomplete - move to buy price field after selection
    (function() {
        'use strict';
        
        function setupSetEnterNavigation() {
            // Find set input field - look for various possible selectors
            const setInputSelectors = [
                'input[placeholder*="search sets" i]',
                'input[placeholder*="Type to search sets" i]',
                'input[id*="set"]',
                'input[name*="set"]',
                'input[type="text"]'
            ];
            
            let setInput = null;
            for (const selector of setInputSelectors) {
                const inputs = document.querySelectorAll(selector);
                for (const input of inputs) {
                    // Skip if it's the card name input
                    if (input.placeholder && input.placeholder.toLowerCase().includes('card name')) {
                        continue;
                    }
                    // Check if it's related to sets (has "set" in placeholder, id, name, or nearby label)
                    const label = input.closest('form, div, fieldset')?.querySelector('label');
                    if (label && (label.textContent.toLowerCase().includes('set') || 
                        input.placeholder.toLowerCase().includes('set'))) {
                        setInput = input;
                        break;
                    }
                }
                if (setInput) break;
            }
            
            if (!setInput) {
                // Try to find by looking for input near a "Sets" label
                const labels = document.querySelectorAll('label');
                for (const label of labels) {
                    if (label.textContent.toLowerCase().includes('sets')) {
                        const input = label.nextElementSibling || 
                                     label.parentElement?.querySelector('input[type="text"]');
                        if (input && input.type === 'text') {
                            setInput = input;
                            break;
                        }
                    }
                }
            }
            
            if (!setInput) return; // Can't find set input, skip
            
            // Check if we've already added a listener to this input
            if (setInput.dataset.enterNavigationAdded === 'true') return;
            setInput.dataset.enterNavigationAdded = 'true';
            
            // Find buy price field - look for various possible selectors
            function findBuyPriceField() {
                const buyPriceSelectors = [
                    'input[placeholder*="buy price" i]',
                    'input[placeholder*="e.g. 25.50" i]',
                    'input[id*="buy"]',
                    'input[name*="buy"]',
                    'input[type="number"]',
                    'input[type="text"]'
                ];
                
                // Get all inputs in the form/modal
                const form = setInput.closest('form, div[class*="modal"], div[id*="modal"]');
                if (!form) return null;
                
                const allInputs = Array.from(form.querySelectorAll('input[type="text"], input[type="number"]'));
                
                // Find buy price field by checking labels or placeholders
                for (const input of allInputs) {
                    // Skip the set input itself
                    if (input === setInput) continue;
                    
                    const label = input.closest('form, div, fieldset')?.querySelector('label');
                    const hasBuyPriceLabel = label && label.textContent.toLowerCase().includes('buy price');
                    const hasBuyPricePlaceholder = input.placeholder && input.placeholder.toLowerCase().includes('buy price');
                    const hasBuyPriceId = input.id && input.id.toLowerCase().includes('buy');
                    const hasBuyPriceName = input.name && input.name.toLowerCase().includes('buy');
                    
                    if (hasBuyPriceLabel || hasBuyPricePlaceholder || hasBuyPriceId || hasBuyPriceName) {
                        return input;
                    }
                }
                
                // Fallback: find input after set input in DOM order
                let foundSetInput = false;
                for (const input of allInputs) {
                    if (input === setInput) {
                        foundSetInput = true;
                        continue;
                    }
                    if (foundSetInput && input.type !== 'hidden' && input.type !== 'submit' && input.type !== 'button') {
                        return input;
                    }
                }
                
                return null;
            }
            
            // Handle Enter key on set input
            setInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.keyCode === 13) {
                    // Check if autocomplete dropdown is visible
                    const dropdown = document.querySelector('[class*="dropdown"], [class*="autocomplete"], [class*="suggestions"]');
                    const isDropdownVisible = dropdown && dropdown.style.display !== 'none' && dropdown.offsetParent !== null;
                    
                    // If dropdown is visible, wait a moment for selection to complete
                    if (isDropdownVisible) {
                        e.preventDefault();
                        e.stopPropagation();
                        
                        // Wait a bit for the selection to be processed
                        setTimeout(() => {
                            const buyPriceField = findBuyPriceField();
                            if (buyPriceField) {
                                buyPriceField.focus();
                                buyPriceField.select(); // Select text for easy replacement
                            }
                        }, 100);
                    } else {
                        // No dropdown visible, just move to next field
                        e.preventDefault();
                        e.stopPropagation();
                        
                        const buyPriceField = findBuyPriceField();
                        if (buyPriceField) {
                            buyPriceField.focus();
                            buyPriceField.select();
                        }
                    }
                }
            });
            
            // Also handle when a set chip/tag is clicked (selection completed)
            // Watch for set chips being added
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) {
                            // Check if it's a set chip/tag
                            const isSetChip = node.classList && (
                                Array.from(node.classList).some(c => c.toLowerCase().includes('chip') || 
                                                                   c.toLowerCase().includes('tag')) ||
                                node.getAttribute('data-set') ||
                                node.textContent && node.textContent.trim().length > 0
                            );
                            
                            if (isSetChip && setInput.value) {
                                // Set was just selected, move focus to buy price
                                setTimeout(() => {
                                    const buyPriceField = findBuyPriceField();
                                    if (buyPriceField && document.activeElement === setInput) {
                                        buyPriceField.focus();
                                        buyPriceField.select();
                                    }
                                }, 50);
                            }
                        }
                    });
                });
            });
            
            // Observe the form/modal for changes
            const form = setInput.closest('form, div[class*="modal"], div[id*="modal"]');
            if (form) {
                observer.observe(form, { childList: true, subtree: true });
            }
        }
        
        // Setup when DOM is ready
        function initSetNavigation() {
            setupSetEnterNavigation();
        }
        
        // Run immediately and on DOM changes
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initSetNavigation);
        } else {
            initSetNavigation();
        }
        
        // Watch for dynamically added modals/forms
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1 && (
                        node.tagName === 'FORM' || 
                        node.classList?.contains('modal') ||
                        node.querySelector('form, input[placeholder*="set" i]')
                    )) {
                        setTimeout(setupSetEnterNavigation, 100);
                    }
                });
            });
        });
        
        observer.observe(document.body, { childList: true, subtree: true });
    })();
    </script>
"""
                # Inject set navigation script
                if '</body>' in html_content:
                    html_content = html_content.replace('</body>', set_navigation_script + '\n</body>')
                elif '</html>' in html_content:
                    html_content = html_content.replace('</html>', set_navigation_script + '\n</html>')
                else:
                    html_content += set_navigation_script
            
            # Inject JavaScript to load archived stats if not already present
            if 'archived-stats' not in html_content:
                # Find </body> or </script> tag to inject before
                stats_script = """
    <script>
    // Load archived collection statistics
    async function loadArchivedStats() {
        try {
            // Use current path to determine API prefix
            const apiPath = window.location.pathname.includes('/collection') ? '/collection/api/archived-stats' : '/api/archived-stats';
            const response = await fetch(apiPath, {
                credentials: 'include'  // Include session cookie for authentication
            });
            const stats = await response.json();
            
            // Find or create stats container - always place at bottom after pagination
            let statsContainer = document.getElementById('archived-stats-container');
            
            // Function to find pagination controls (NEXT/PREVIOUS buttons)
            function findPaginationContainer() {
                // Method 1: Find by NEXT button text
                const allButtons = Array.from(document.querySelectorAll('button, a, [role="button"]'));
                const nextButton = allButtons.find(btn => {
                    const text = (btn.textContent || '').trim().toUpperCase();
                    return text.includes('NEXT') || text.includes('►');
                });
                
                if (nextButton && nextButton.parentElement) {
                    return nextButton.parentElement;
                }
                
                // Method 2: Find by "PAGE X OF Y" text
                const pageIndicators = Array.from(document.querySelectorAll('*')).filter(el => {
                    const text = (el.textContent || '').toUpperCase();
                    return text.match(/PAGE\s+\d+\s+OF\s+\d+/);
                });
                
                if (pageIndicators.length > 0 && pageIndicators[0].parentElement) {
                    return pageIndicators[0].parentElement;
                }
                
                // Method 3: Search for common pagination container classes
                const containers = document.querySelectorAll('[class*="pagination"], [class*="page-control"], [class*="page-nav"], [id*="pagination"], [id*="page-control"]');
                if (containers.length > 0) {
                    return containers[containers.length - 1]; // Get last one
                }
                
                return null;
            }
            
            // Hide "Total Cards" display and the "95" number
            function hideTotalCardsDisplay() {
                // Find elements containing "Total Cards" text that are NOT our stats
                const allElements = Array.from(document.querySelectorAll('*'));
                allElements.forEach(el => {
                    const text = (el.textContent || '').trim();
                    const isTotalCards = (text === 'Total Cards' || text.startsWith('Total Cards')) && 
                                       !el.closest('#archived-stats-container') &&
                                       el.textContent.length < 50;
                    
                    // Also hide elements that are just a number (like "95") and are likely total cards display
                    const isJustNumber = /^\d+$/.test(text) && 
                                        !el.closest('#archived-stats-container') &&
                                        el.textContent.length < 10 &&
                                        (el.classList.toString().includes('stat') || 
                                         el.id.includes('stat') ||
                                         el.parentElement?.classList.toString().includes('stat') ||
                                         el.parentElement?.id.includes('stat') ||
                                         el.nextElementSibling?.textContent?.includes('Total Cards') ||
                                         el.previousElementSibling?.textContent?.includes('Total Cards'));
                    
                    if (isTotalCards || isJustNumber) {
                        // Hide the parent container if it's a stat display
                        let targetEl = el;
                        let parent = el.parentElement;
                        
                        // Look up to 3 levels for the stat container
                        for (let i = 0; i < 3 && parent; i++) {
                            if (parent.classList.toString().includes('stat') || 
                                parent.id.includes('stat') ||
                                parent.querySelector('[class*="number"], [class*="value"]') ||
                                parent.textContent.includes('Total Cards')) {
                                targetEl = parent;
                                break;
                            }
                            parent = parent.parentElement;
                        }
                        
                        targetEl.style.display = 'none';
                    }
                });
                
                // Also look for elements positioned in bottom-left that might be the "95" display
                // Check for elements with just numbers that are positioned absolutely or in a specific location
                const numberElements = Array.from(document.querySelectorAll('*')).filter(el => {
                    const text = (el.textContent || '').trim();
                    return /^\d+$/.test(text) && 
                           text.length <= 3 && 
                           !el.closest('#archived-stats-container') &&
                           !el.closest('[class*="pagination"]') &&
                           !el.closest('[id*="pagination"]');
                });
                
                numberElements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const isBottomLeft = rect.left < window.innerWidth * 0.3 && 
                                      rect.bottom > window.innerHeight * 0.7;
                    
                    if (isBottomLeft || el.classList.toString().includes('stat') || el.id.includes('stat')) {
                        let targetEl = el;
                        let parent = el.parentElement;
                        
                        // Check if parent contains "Total Cards" text
                        for (let i = 0; i < 2 && parent; i++) {
                            if (parent.textContent.includes('Total Cards') || 
                                parent.classList.toString().includes('stat') ||
                                parent.id.includes('stat')) {
                                targetEl = parent;
                                break;
                            }
                            parent = parent.parentElement;
                        }
                        
                        targetEl.style.display = 'none';
                    }
                });
            }
            
            if (!statsContainer) {
                // Find pagination container
                const paginationContainer = findPaginationContainer();
                const mainContent = document.querySelector('main, .container, .content, body');
                
                statsContainer = document.createElement('div');
                statsContainer.id = 'archived-stats-container';
                statsContainer.className = 'stats-container';
                statsContainer.style.cssText = 'display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 15px; margin: 15px 0;';
                
                if (paginationContainer && paginationContainer.parentElement) {
                    // Insert after pagination container
                    paginationContainer.parentElement.insertBefore(statsContainer, paginationContainer.nextSibling);
                } else if (mainContent) {
                    // Append at bottom of main content
                    mainContent.appendChild(statsContainer);
                }
                
                // Hide Total Cards display
                setTimeout(hideTotalCardsDisplay, 100);
            } else {
                // Stats container already exists - move it after pagination if needed
                const paginationContainer = findPaginationContainer();
                if (paginationContainer && paginationContainer.parentElement && statsContainer.parentElement) {
                    // Check if stats are before pagination
                    const paginationIndex = Array.from(paginationContainer.parentElement.children).indexOf(paginationContainer);
                    const statsIndex = Array.from(statsContainer.parentElement.children).indexOf(statsContainer);
                    if (statsIndex <= paginationIndex || statsContainer.parentElement !== paginationContainer.parentElement) {
                        // Move stats after pagination
                        paginationContainer.parentElement.insertBefore(statsContainer, paginationContainer.nextSibling);
                    }
                }
                
                // Hide Total Cards display
                setTimeout(hideTotalCardsDisplay, 100);
            }
            
            if (statsContainer) {
                // Two-row layout: What we have | What we have sold
                statsContainer.style.cssText = 'display: flex; flex-direction: column; align-items: center; gap: 20px; margin: 20px 0;';
                
                const rowStyle = 'display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 20px; width: 100%;';
                const statCardStyle = 'background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%); border: 2px solid #3a3a3a; border-radius: 10px; padding: 16px 24px; min-width: 140px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); transition: transform 0.2s, box-shadow 0.2s;';
                const statCardHoverStyle = 'transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);';
                const statValueStyle = 'font-size: 1.8em; font-weight: bold; color: #ffffff; margin-bottom: 6px; line-height: 1.2;';
                const statLabelStyle = 'font-size: 0.75em; color: #d4af37; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;';
                const rowTitleStyle = 'font-size: 0.9em; color: #d4af37; text-transform: uppercase; letter-spacing: 2px; font-weight: 600; margin-bottom: 12px; text-align: center; width: 100%;';
                
                // Profit color: green if positive, red if negative
                const profitColor = stats.total_profit >= 0 ? '#4ade80' : '#f87171';
                
                statsContainer.innerHTML = `
                    <div style="${rowStyle}">
                        <div style="${rowTitleStyle}">What We Have</div>
                        <div style="${statCardStyle}" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0, 0, 0, 0.4)';" onmouseout="this.style.transform=''; this.style.boxShadow='';">
                            <div style="${statValueStyle}">${stats.collection_count || 0}</div>
                            <div style="${statLabelStyle}">Items</div>
                        </div>
                        <div style="${statCardStyle}" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0, 0, 0, 0.4)';" onmouseout="this.style.transform=''; this.style.boxShadow='';">
                            <div style="${statValueStyle}">€${(stats.total_cost || 0).toFixed(2)}</div>
                            <div style="${statLabelStyle}">Total Cost</div>
                        </div>
                        <div style="${statCardStyle}" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0, 0, 0, 0.4)';" onmouseout="this.style.transform=''; this.style.boxShadow='';">
                            <div style="${statValueStyle}">€${(stats.total_market_value || 0).toFixed(2)}</div>
                            <div style="${statLabelStyle}">Current Value</div>
                        </div>
                    </div>
                    <div style="${rowStyle}">
                        <div style="${rowTitleStyle}">What We Have Sold</div>
                        <div style="${statCardStyle}" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0, 0, 0, 0.4)';" onmouseout="this.style.transform=''; this.style.boxShadow='';">
                            <div style="${statValueStyle}">${stats.sold_count || 0}</div>
                            <div style="${statLabelStyle}">Items Sold</div>
                        </div>
                        <div style="${statCardStyle}" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0, 0, 0, 0.4)';" onmouseout="this.style.transform=''; this.style.boxShadow='';">
                            <div style="${statValueStyle}">€${(stats.total_sold_amount || 0).toFixed(2)}</div>
                            <div style="${statLabelStyle}">Total Sold</div>
                        </div>
                        <div style="${statCardStyle}" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0, 0, 0, 0.4)';" onmouseout="this.style.transform=''; this.style.boxShadow='';">
                            <div style="${statValueStyle}; color: ${profitColor}">€${(stats.total_profit || 0).toFixed(2)}</div>
                            <div style="${statLabelStyle}">Total Profit</div>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading archived stats:', error);
        }
    }
    
    // Move all stats sections to bottom after pagination
    function moveStatsToBottom() {
        // Find pagination container
        function findPaginationContainer() {
            const allButtons = Array.from(document.querySelectorAll('button, a, [role="button"]'));
            const nextButton = allButtons.find(btn => {
                const text = (btn.textContent || '').trim().toUpperCase();
                return text.includes('NEXT') || text.includes('►');
            });
            
            if (nextButton && nextButton.parentElement) {
                return nextButton.parentElement;
            }
            
            const pageIndicators = Array.from(document.querySelectorAll('*')).filter(el => {
                const text = (el.textContent || '').toUpperCase();
                return text.match(/PAGE\s+\d+\s+OF\s+\d+/);
            });
            
            if (pageIndicators.length > 0 && pageIndicators[0].parentElement) {
                return pageIndicators[0].parentElement;
            }
            
            const containers = document.querySelectorAll('[class*="pagination"], [class*="page-control"], [class*="page-nav"], [id*="pagination"], [id*="page-control"]');
            if (containers.length > 0) {
                return containers[containers.length - 1];
            }
            
            return null;
        }
        
        // Hide "Total Cards" display and the "95" number
        function hideTotalCardsDisplay() {
            const allElements = Array.from(document.querySelectorAll('*'));
            allElements.forEach(el => {
                const text = (el.textContent || '').trim();
                const isTotalCards = (text === 'Total Cards' || text.startsWith('Total Cards')) && 
                                   !el.closest('#archived-stats-container') &&
                                   el.textContent.length < 50;
                
                // Also hide elements that are just a number (like "95") and are likely total cards display
                const isJustNumber = /^\d+$/.test(text) && 
                                    !el.closest('#archived-stats-container') &&
                                    el.textContent.length < 10 &&
                                    (el.classList.toString().includes('stat') || 
                                     el.id.includes('stat') ||
                                     el.parentElement?.classList.toString().includes('stat') ||
                                     el.parentElement?.id.includes('stat') ||
                                     el.nextElementSibling?.textContent?.includes('Total Cards') ||
                                     el.previousElementSibling?.textContent?.includes('Total Cards'));
                
                if (isTotalCards || isJustNumber) {
                    let targetEl = el;
                    let parent = el.parentElement;
                    
                    for (let i = 0; i < 3 && parent; i++) {
                        if (parent.classList.toString().includes('stat') || 
                            parent.id.includes('stat') ||
                            parent.querySelector('[class*="number"], [class*="value"]') ||
                            parent.textContent.includes('Total Cards')) {
                            targetEl = parent;
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    
                    targetEl.style.display = 'none';
                }
            });
            
            // Also look for elements positioned in bottom-left that might be the "95" display
            const numberElements = Array.from(document.querySelectorAll('*')).filter(el => {
                const text = (el.textContent || '').trim();
                return /^\d+$/.test(text) && 
                       text.length <= 3 && 
                       !el.closest('#archived-stats-container') &&
                       !el.closest('[class*="pagination"]') &&
                       !el.closest('[id*="pagination"]');
            });
            
            numberElements.forEach(el => {
                const rect = el.getBoundingClientRect();
                const isBottomLeft = rect.left < window.innerWidth * 0.3 && 
                                  rect.bottom > window.innerHeight * 0.7;
                
                if (isBottomLeft || el.classList.toString().includes('stat') || el.id.includes('stat')) {
                    let targetEl = el;
                    let parent = el.parentElement;
                    
                    for (let i = 0; i < 2 && parent; i++) {
                        if (parent.textContent.includes('Total Cards') || 
                            parent.classList.toString().includes('stat') ||
                            parent.id.includes('stat')) {
                            targetEl = parent;
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    
                    targetEl.style.display = 'none';
                }
            });
        }
        
        const paginationContainer = findPaginationContainer();
        if (!paginationContainer || !paginationContainer.parentElement) {
            hideTotalCardsDisplay();
            return;
        }
        
        // Find all stats containers (excluding our archived-stats-container)
        const allStatsContainers = document.querySelectorAll('.stats-container, .stats-section, [class*="stat"]:not(#archived-stats-container)');
        
        // Also look for elements containing "What We Have", etc. (but we'll handle "Total Cards" separately to hide it)
        const statTexts = ['What We Have', 'What We Have Sold', 'Items', 'Total Cost', 'Current Value'];
        const potentialStatsElements = Array.from(document.querySelectorAll('div, section')).filter(el => {
            const text = el.textContent || '';
            return statTexts.some(statText => text.includes(statText)) && 
                   el.children.length > 0 &&
                   !el.id.includes('archived-stats');
        });
        
        // Combine all stats elements
        const allStatsElements = Array.from(allStatsContainers).concat(potentialStatsElements);
        
        // Move each stats element to after pagination
        allStatsElements.forEach(statsEl => {
            if (statsEl.parentElement && statsEl !== paginationContainer && !paginationContainer.contains(statsEl)) {
                // Check if it's already after pagination
                const paginationIndex = Array.from(paginationContainer.parentElement.children).indexOf(paginationContainer);
                const statsIndex = Array.from(statsEl.parentElement.children).indexOf(statsEl);
                
                if (statsIndex <= paginationIndex || statsEl.parentElement !== paginationContainer.parentElement) {
                    // Move to after pagination
                    paginationContainer.parentElement.insertBefore(statsEl, paginationContainer.nextSibling);
                }
            }
        });
        
        // Also ensure archived-stats-container is after pagination
        const archivedStats = document.getElementById('archived-stats-container');
        if (archivedStats && archivedStats.parentElement === paginationContainer.parentElement) {
            const paginationIndex = Array.from(paginationContainer.parentElement.children).indexOf(paginationContainer);
            const statsIndex = Array.from(archivedStats.parentElement.children).indexOf(archivedStats);
            if (statsIndex <= paginationIndex) {
                paginationContainer.parentElement.insertBefore(archivedStats, paginationContainer.nextSibling);
            }
        } else if (archivedStats && paginationContainer.parentElement) {
            // Move to after pagination
            paginationContainer.parentElement.insertBefore(archivedStats, paginationContainer.nextSibling);
        }
        
        // Hide Total Cards display
        hideTotalCardsDisplay();
    }
    
    // Fix redundant stats display - remove duplicate "Collection Items" if it matches "Total Cards"
    function fixRedundantStats() {
        // Find all stat cards
        const statCards = document.querySelectorAll('[class*="stat"], .stat-card, [class*="card"]');
        const statTexts = Array.from(statCards).map(card => {
            const label = card.querySelector('[class*="label"], [class*="text"]');
            return label ? label.textContent.trim() : '';
        });
        
        // Check if "Total Cards" and "Collection Items" both exist and show the same value
        const totalCardsIndex = statTexts.findIndex(text => text.toLowerCase().includes('total cards'));
        const collectionItemsIndex = statTexts.findIndex(text => text.toLowerCase().includes('collection items'));
        
        if (totalCardsIndex !== -1 && collectionItemsIndex !== -1 && totalCardsIndex !== collectionItemsIndex) {
            const totalCardsCard = statCards[totalCardsIndex];
            const collectionItemsCard = statCards[collectionItemsIndex];
            
            const totalCardsValue = totalCardsCard.querySelector('[class*="value"], [class*="number"]')?.textContent.trim();
            const collectionItemsValue = collectionItemsCard.querySelector('[class*="value"], [class*="number"]')?.textContent.trim();
            
            // If values are the same, remove "Collection Items" and update "Total Cards" label
            if (totalCardsValue === collectionItemsValue) {
                collectionItemsCard.remove();
                const totalCardsLabel = totalCardsCard.querySelector('[class*="label"], [class*="text"]');
                if (totalCardsLabel) {
                    totalCardsLabel.textContent = 'Total Cards';
                }
            }
        }
    }
    
    // Load stats when page is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            loadArchivedStats();
            setTimeout(() => {
                moveStatsToBottom();
                fixRedundantStats();
            }, 800); // Wait a bit for other scripts to load stats and DOM to settle
        });
    } else {
        loadArchivedStats();
        setTimeout(() => {
            moveStatsToBottom();
            fixRedundantStats();
        }, 800);
    }
    </script>
"""
                # Inject before closing body tag
                if '</body>' in html_content:
                    html_content = html_content.replace('</body>', stats_script + '\n</body>')
                elif '</html>' in html_content:
                    html_content = html_content.replace('</html>', stats_script + '\n</html>')
                else:
                    html_content += stats_script
            
            # Inject JavaScript for pagination support (remember page after edit, add Last Page button)
            if 'pagination-support' not in html_content:
                pagination_script = """
    <script id="pagination-support">
    // Pagination support: remember page after edit and add Last Page button
    (function() {
        'use strict';
        
        // Store current page before editing
        function getCurrentPage() {
            // Try various methods to get current page
            const pageIndicator = document.querySelector('[class*="page"], [id*="page"], [data-page]');
            if (pageIndicator) {
                const text = pageIndicator.textContent || '';
                const match = text.match(/(\d+)\s+of\s+(\d+)/i) || text.match(/page\s+(\d+)/i);
                if (match) {
                    return parseInt(match[1], 10);
                }
                // Try data attribute
                if (pageIndicator.dataset && pageIndicator.dataset.page) {
                    return parseInt(pageIndicator.dataset.page, 10);
                }
            }
            
            // Try to find page in URL hash
            const hash = window.location.hash;
            if (hash) {
                const match = hash.match(/page[=:]?(\d+)/i);
                if (match) {
                    return parseInt(match[1], 10);
                }
            }
            
            // Try to find page in localStorage
            const storedPage = localStorage.getItem('collection_current_page');
            if (storedPage) {
                return parseInt(storedPage, 10);
            }
            
            return 1; // Default to page 1
        }
        
        function setCurrentPage(page) {
            localStorage.setItem('collection_current_page', page.toString());
        }
        
        function getTotalPages() {
            const pageIndicator = document.querySelector('[class*="page"], [id*="page"]');
            if (pageIndicator) {
                const text = pageIndicator.textContent || '';
                const match = text.match(/(\d+)\s+of\s+(\d+)/i);
                if (match) {
                    return parseInt(match[2], 10);
                }
            }
            return null;
        }
        
        function goToPage(page) {
            // Try various methods to navigate to a page
            const pageInput = document.querySelector('input[type="number"][name*="page"], input[type="number"][id*="page"]');
            if (pageInput) {
                pageInput.value = page;
                pageInput.dispatchEvent(new Event('change', { bubbles: true }));
                return;
            }
            
            // Try to find page navigation function
            if (typeof window.goToPage === 'function') {
                window.goToPage(page);
                return;
            }
            
            if (typeof window.setPage === 'function') {
                window.setPage(page);
                return;
            }
            
            // Try to click page number buttons
            const pageButtons = document.querySelectorAll('button[data-page], [onclick*="page"], [onclick*="Page"]');
            for (const btn of pageButtons) {
                if (btn.textContent && btn.textContent.trim() === page.toString()) {
                    btn.click();
                    return;
                }
            }
            
            // Fallback: trigger custom event
            window.dispatchEvent(new CustomEvent('gotoPage', { detail: { page: page } }));
        }
        
        function goToLastPage() {
            // Find Next button and click it 5 times
            const nextButton = Array.from(document.querySelectorAll('button, a, [role="button"]')).find(btn => {
                const text = (btn.textContent || '').trim().toUpperCase();
                return text.includes('NEXT') && !text.includes('LAST');
            });
            
            if (nextButton) {
                // Click Next button 5 times with delays
                let clickCount = 0;
                const maxClicks = 5;
                
                function clickNext() {
                    if (clickCount < maxClicks) {
                        nextButton.click();
                        clickCount++;
                        setTimeout(clickNext, 300); // Wait 300ms between clicks
                    }
                }
                
                clickNext();
            }
        }
        
        // Store current page periodically
        function updateStoredPage() {
            const currentPage = getCurrentPage();
            if (currentPage && currentPage > 0) {
                console.log(`💾 Storing page ${currentPage} to localStorage`);
                setCurrentPage(currentPage);
            }
        }
        
        // Make updateStoredPage globally accessible for sorting script
        window.updateStoredPage = updateStoredPage;
        
        // Also store page whenever user navigates pages
        function setupPageNavigationTracking() {
            // Track clicks on pagination buttons
            document.addEventListener('click', function(e) {
                const target = e.target;
                // Check if it's a pagination button
                if (target && (target.textContent && (target.textContent.includes('Next') || target.textContent.includes('Prev') || target.textContent.match(/\d+/)))) {
                    // Wait a bit for page to change, then store it
                    setTimeout(() => {
                        updateStoredPage();
                    }, 200);
                }
            });
            
            // Track page input changes
            const pageInput = document.querySelector('input[type="number"][name*="page"], input[type="number"][id*="page"]');
            if (pageInput) {
                pageInput.addEventListener('change', function() {
                    setTimeout(() => {
                        updateStoredPage();
                    }, 200);
                });
            }
        }
        
        // Restore page on load
        function restorePage() {
            const storedPage = localStorage.getItem('collection_current_page');
            if (storedPage) {
                const page = parseInt(storedPage, 10);
                if (page > 1) {
                    console.log(`📄 Restoring page ${page} from localStorage`);
                    // Try multiple times with increasing delays to ensure it works
                    setTimeout(() => {
                        goToPage(page);
                    }, 100);
                    setTimeout(() => {
                        goToPage(page);
                    }, 500);
                    setTimeout(() => {
                        goToPage(page);
                    }, 1000);
                    setTimeout(() => {
                        goToPage(page);
                    }, 2000);
                }
            }
        }
        
        // Add Last Page button to pagination controls
        function addLastPageButton() {
            // Check if button already exists
            if (document.querySelector('[data-action="last-page"]')) {
                return;
            }
            
            // Find Next button - search more broadly
            let nextButton = null;
            let paginationContainer = null;
            
            // Method 1: Find by text content "NEXT"
            const allButtons = Array.from(document.querySelectorAll('button, a, [role="button"]'));
            nextButton = allButtons.find(btn => {
                const text = (btn.textContent || '').trim().toUpperCase();
                return text.includes('NEXT') && !text.includes('LAST');
            });
            
            if (nextButton) {
                paginationContainer = nextButton.parentElement;
            }
            
            // Method 2: Find pagination container by looking for "PAGE X OF Y" text
            if (!paginationContainer) {
                const pageIndicators = Array.from(document.querySelectorAll('*')).filter(el => {
                    const text = (el.textContent || '').toUpperCase();
                    return text.match(/PAGE\s+\d+\s+OF\s+\d+/);
                });
                
                if (pageIndicators.length > 0) {
                    paginationContainer = pageIndicators[0].parentElement;
                    // Try to find NEXT button near the indicator
                    const nearbyButtons = Array.from(paginationContainer.querySelectorAll('button, a, [role="button"]'));
                    nextButton = nearbyButtons.find(btn => {
                        const text = (btn.textContent || '').trim().toUpperCase();
                        return text.includes('NEXT') && !text.includes('LAST');
                    });
                }
            }
            
            // Method 3: Search for common pagination container classes
            if (!paginationContainer) {
                const containers = document.querySelectorAll('[class*="pagination"], [class*="page-control"], [class*="page-nav"], [id*="pagination"], [id*="page-control"]');
                for (const container of containers) {
                    const buttons = Array.from(container.querySelectorAll('button, a'));
                    const found = buttons.find(btn => {
                        const text = (btn.textContent || '').trim().toUpperCase();
                        return text.includes('NEXT') && !text.includes('LAST');
                    });
                    if (found) {
                        nextButton = found;
                        paginationContainer = container;
                        break;
                    }
                }
            }
            
            if (nextButton && paginationContainer) {
                // Create Last Page button with same styling as Next button
                const lastPageButton = document.createElement(nextButton.tagName.toLowerCase());
                lastPageButton.textContent = 'SKIP +3 ▶▶';
                lastPageButton.setAttribute('data-action', 'last-page');
                
                // Copy styles from Next button
                if (nextButton.style.cssText) {
                    lastPageButton.style.cssText = nextButton.style.cssText;
                } else {
                    // Apply default styling that matches the theme
                    lastPageButton.style.cssText = 'padding: 8px 16px; margin: 0 5px; background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%); color: #d4af37; border: 1px solid #d4af37; border-radius: 4px; cursor: pointer; font-weight: bold;';
                }
                
                // Copy classes from Next button
                if (nextButton.className) {
                    lastPageButton.className = nextButton.className;
                }
                
                lastPageButton.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    goToLastPage();
                });
                
                // Insert after Next button
                if (nextButton.nextSibling) {
                    nextButton.parentNode.insertBefore(lastPageButton, nextButton.nextSibling);
                } else {
                    nextButton.parentNode.appendChild(lastPageButton);
                }
                
                console.log('✅ Last Page button added successfully');
            } else {
                console.warn('⚠️ Could not find Next button or pagination container');
            }
        }
        
        // Intercept collection update/save operations to store page
        if (!window.originalFetch) {
            window.originalFetch = window.fetch;
        }
        window.fetch = function(...args) {
            const url = args[0];
            const options = args[1] || {};
            
            // Before PUT/POST to collection API, store current page
            if (typeof url === 'string' && url.includes('/api/collection') && (options.method === 'PUT' || options.method === 'POST')) {
                const currentPage = getCurrentPage();
                console.log(`💾 Storing current page ${currentPage} before save`);
                updateStoredPage();
                
                // After successful save, restore page (with multiple attempts in case of reload)
                return window.originalFetch.apply(this, args).then(response => {
                    if (response.ok) {
                        const storedPage = localStorage.getItem('collection_current_page');
                        console.log(`✅ Save successful, restoring page ${storedPage}`);
                        if (storedPage) {
                            const pageNum = parseInt(storedPage, 10);
                            // Try immediately
                            setTimeout(() => {
                                console.log(`📄 Attempting to restore page ${pageNum} (immediate)`);
                                goToPage(pageNum);
                            }, 100);
                            // Try after potential reload
                            setTimeout(() => {
                                console.log(`📄 Attempting to restore page ${pageNum} (delayed)`);
                                goToPage(pageNum);
                            }, 500);
                            setTimeout(() => {
                                console.log(`📄 Attempting to restore page ${pageNum} (delayed 2)`);
                                goToPage(pageNum);
                            }, 1500);
                            setTimeout(() => {
                                console.log(`📄 Attempting to restore page ${pageNum} (delayed 3)`);
                                goToPage(pageNum);
                            }, 3000);
                        }
                    }
                    return response;
                });
            }
            
            return window.originalFetch.apply(this, args);
        };
        
        // Also intercept XMLHttpRequest for page restoration
        // Only intercept PUT/POST requests, let sorting handle GET requests
        // Note: This runs BEFORE sorting script, so we capture the real original
        if (!window._xhrInterceptedForPageRestore) {
            window._xhrInterceptedForPageRestore = true;
            // Capture the REAL original (before any other overrides)
            const realOriginalXHROpen = XMLHttpRequest.prototype.open;
            const realOriginalXHRSend = XMLHttpRequest.prototype.send;
            
            // Override open to store url/method (needed for send to check)
            XMLHttpRequest.prototype.open = function(method, url, ...rest) {
                this._url = url;
                this._method = method;
                // Call through to real original (sorting script will wrap this later)
                return realOriginalXHROpen.apply(this, [method, url, ...rest]);
            };
            
            // Override send to add page restoration logic for PUT/POST
            XMLHttpRequest.prototype.send = function(body) {
                // Only handle PUT/POST for page restoration
                if (this._url && this._url.includes('/api/collection') && (this._method === 'PUT' || this._method === 'POST')) {
                    updateStoredPage();
                    
                    const originalOnReadyStateChange = this.onreadystatechange;
                    this.onreadystatechange = function() {
                        if (this.readyState === 4 && this.status >= 200 && this.status < 300) {
                            const storedPage = localStorage.getItem('collection_current_page');
                            if (storedPage) {
                                setTimeout(() => {
                                    goToPage(parseInt(storedPage, 10));
                                }, 300);
                            }
                        }
                        if (originalOnReadyStateChange) {
                            originalOnReadyStateChange.apply(this, arguments);
                        }
                    };
                }
                // Call through to real original (sorting script will wrap this later for GET requests)
                return realOriginalXHRSend.apply(this, [body]);
            };
        }
        
        // Initialize on page load
        function init() {
            // Try to add Last Page button multiple times with delays
            function tryAddButton() {
                addLastPageButton();
            }
            
            // Restore page if coming back from edit
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => {
                    // Try immediately and then with delays
                    tryAddButton();
                    setTimeout(tryAddButton, 500);
                    setTimeout(tryAddButton, 1000);
                    setTimeout(tryAddButton, 2000);
                    setTimeout(() => {
                        restorePage();
                        setupPageNavigationTracking();
                        // Update stored page periodically
                        setInterval(updateStoredPage, 2000);
                    }, 1500);
                });
            } else {
                // Try immediately and then with delays
                tryAddButton();
                setTimeout(tryAddButton, 500);
                setTimeout(tryAddButton, 1000);
                setTimeout(tryAddButton, 2000);
                setTimeout(() => {
                    restorePage();
                    setupPageNavigationTracking();
                    setInterval(updateStoredPage, 2000);
                }, 1500);
            }
            
            // Watch for pagination controls being added dynamically
            const observer = new MutationObserver(() => {
                // Debounce to avoid too many calls
                if (!window._lastPageButtonTimeout) {
                    window._lastPageButtonTimeout = setTimeout(() => {
                        addLastPageButton();
                        window._lastPageButtonTimeout = null;
                    }, 300);
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
        
        init();
    })();
    </script>
"""
                # Inject before closing body tag
                if '</body>' in html_content:
                    html_content = html_content.replace('</body>', pagination_script + '\n</body>')
                elif '</html>' in html_content:
                    html_content = html_content.replace('</html>', pagination_script + '\n</html>')
                else:
                    html_content += pagination_script
            
            # Inject JavaScript for sorting support
            if 'sorting-support' not in html_content:
                sorting_script = """
    <script id="sorting-support">
    // Sorting support for collection cards
    (function() {
        'use strict';
        
        let originalCards = [];
        let currentSort = 'original'; // Default: original JSON order
        let showSoldOnly = false; // Default: show unsold cards (sell_price is 0 or null)
        let oldSchoolFilter = true; // Default: show Old School legal cards
        let premodernFilter = true; // Default: show Premodern legal cards
        
        // Function to update "No Cards" message based on filter state
        function updateNoCardsMessage(filtersActive, totalCards) {
            // Check if any filters are actually active
            const hasActiveFilters = showSoldOnly || oldSchoolFilter || premodernFilter;
            
            // Find all elements containing "NO CARDS" or "No Cards" messages
            const allElements = Array.from(document.querySelectorAll('*'));
            const noCardsElements = allElements.filter(el => {
                const text = (el.textContent || '').trim().toUpperCase();
                return (text.includes('NO CARDS') || text.includes('NO CARDS IN COLLECTION')) &&
                       !el.closest('#archived-stats-container') &&
                       !el.closest('[class*="stat"]') &&
                       el.textContent.length < 200; // Avoid matching large blocks
            });
            
            noCardsElements.forEach(el => {
                const originalText = el.textContent || '';
                const isCurrentlyFiltered = originalText.includes('MATCH') || originalText.includes('filter') || originalText.includes('Filter');
                
                // Only show filtered message if filters are active AND there are cards but none match
                if (filtersActive && totalCards > 0 && hasActiveFilters) {
                    // Build filter description
                    const activeFilters = [];
                    if (showSoldOnly) {
                        activeFilters.push('Show Sold Only');
                    }
                    if (oldSchoolFilter && !premodernFilter) {
                        activeFilters.push('Old School');
                    } else if (premodernFilter && !oldSchoolFilter) {
                        activeFilters.push('Premodern');
                    } else if (oldSchoolFilter && premodernFilter) {
                        activeFilters.push('Old School or Premodern');
                    }
                    
                    // Update message
                    const newText = `NO CARDS MATCH THE CURRENT FILTERS`;
                    const subText = `You have ${totalCards} card${totalCards !== 1 ? 's' : ''} in your collection, but none match the selected filters.`;
                    
                    // Update the main message
                    if (el.textContent.toUpperCase().includes('NO CARDS')) {
                        el.textContent = newText;
                        el.style.color = '#d4af37';
                        el.style.fontSize = el.style.fontSize || '2em';
                        el.style.fontWeight = 'bold';
                        
                        // Find or create subtitle
                        let subtitle = el.nextElementSibling;
                        if (!subtitle || (!subtitle.textContent.includes('You have') && !subtitle.textContent.includes('Click'))) {
                            subtitle = document.createElement('div');
                            subtitle.style.cssText = 'color: #999; font-size: 1em; margin-top: 10px;';
                            el.parentNode.insertBefore(subtitle, el.nextSibling);
                        }
                        subtitle.textContent = subText;
                    }
                } else {
                    // Reset to original message if no filters active or no cards at all
                    if (isCurrentlyFiltered) {
                        el.textContent = 'NO CARDS IN COLLECTION';
                        el.style.color = el.style.color || '#d4af37';
                        el.style.fontSize = el.style.fontSize || '2em';
                        el.style.fontWeight = 'bold';
                        
                        const subtitle = el.nextElementSibling;
                        if (subtitle && subtitle.textContent.includes('You have')) {
                            subtitle.textContent = 'Click "Add Card" to start building your collection!';
                        }
                    }
                }
            });
        }
        
        // Filter function: filter cards based on sell_price and format legality
        function filterCards(cards) {
            let filtered = cards;
            
            // First filter by sold/unsold status
            if (showSoldOnly) {
                // Show only sold cards (non-zero sell_price)
                filtered = filtered.filter(card => {
                    const sellPrice = parseFloat(card.sell_price) || 0;
                    return sellPrice > 0;
                });
            } else {
                // Show only unsold cards (zero or null sell_price)
                filtered = filtered.filter(card => {
                    const sellPrice = parseFloat(card.sell_price) || 0;
                    return sellPrice === 0;
                });
            }
            
            // Then filter by format legality (OR operation: show if matches any checked format)
            if (oldSchoolFilter || premodernFilter) {
                filtered = filtered.filter(card => {
                    // Check if card has format info (not undefined/null)
                    const hasOldSchoolInfo = card.old_school_legal !== undefined && card.old_school_legal !== null;
                    const hasPremodernInfo = card.premodern_legal !== undefined && card.premodern_legal !== null;
                    
                    // If card has no format info at all, show it (fallback for cards without format fields)
                    if (!hasOldSchoolInfo && !hasPremodernInfo) {
                        return true;
                    }
                    
                    const oldSchool = card.old_school_legal === true;
                    const premodern = card.premodern_legal === true;
                    
                    // Show card ONLY if it matches at least one checked format
                    // Cards with "neither" format_validity (both false) are hidden when filters are active
                    return (oldSchoolFilter && oldSchool) || (premodernFilter && premodern);
                });
            } else {
                // If neither checkbox is checked, show all cards (user wants to see everything)
                // This includes cards with format_validity: "neither"
            }
            
            return filtered;
        }
        
        // Expansion mapping: chronological order (key) -> set name (value)
        // Lower numbers are older sets
        const expansionChronologicalOrder = {
            "1": "Alpha", "2": "Beta", "3": "Unlimited", "4": "Arabian Nights",
            "5": "Antiquities", "6": "Revised", "7": "Legends", "8": "The Dark",
            "9": "Fallen Empires", "10": "Fourth Edition", "11": "Ice Age",
            "12": "Chronicles", "14": "Homelands", "15": "Alliances", "16": "Mirage",
            "17": "Visions", "18": "Weatherlight", "19": "Tempest", "20": "Stronghold",
            "21": "Exodus", "23": "Fifth Edition", "24": "Portal Second Age",
            "25": "Portal", "26": "Urza's Saga", "27": "Urza's Legacy",
            "28": "Urza's Destiny", "29": "Sixth Edition", "30": "Portal Three Kingdoms",
            "31": "Mercadian Masques", "32": "Nemesis", "33": "Prophecy",
            "34": "Invasion", "35": "Planeshift", "36": "Apocalypse",
            "37": "Seventh Edition", "38": "Odyssey", "39": "Torment",
            "40": "Judgment", "41": "Onslaught", "42": "Legions", "43": "Scourge",
            "44": "Eighth Edition", "45": "Mirrodin", "46": "Darksteel",
            "47": "Fifth Dawn", "48": "Champions of Kamigawa", "49": "Ninth Edition",
            "50": "Saviors of Kamigawa", "51": "Betrayers of Kamigawa",
            "53": "Dissension", "70": "Future Sight", "72": "International Edition",
            "73": "European Unlimited", "74": "Tenth Edition", "81": "Euro Lands: Red",
            "102": "Shards of Alara", "108": "Alara Reborn", "1206": "Scars of Mirrodin",
            "1253": "Mirrodin Besieged Phyrexian Faction Pack", "1327": "Innistrad",
            "1332": "Fourth Edition: Black Bordered", "1345": "Dark Ascension",
            "1424": "Gatecrash", "1435": "Dragon's Maze", "1444": "Modern Masters",
            "1449": "Magic 2014", "1457": "Theros", "1469": "Born of the Gods",
            "1481": "Journey into Nyx", "1483": "Conspiracy", "1485": "Magic 2015",
            "1495": "Khans of Tarkir", "1522": "Fate Reforged", "1587": "Ugin's Fate",
            "1592": "Alara Block All-Foil", "1601": "Dragons of Tarkir",
            "1641": "Modern Masters 2015", "1652": "Magic Origins",
            "1676": "Oath of the Gatewatch", "1694": "Shadows over Innistrad",
            "1695": "Eldritch Moon", "1696": "Eternal Masters",
            "1702": "Conspiracy: Take the Crown", "1727": "Modern Masters 2017",
            "1729": "Amonkhet", "1731": "Hour of Devastation",
            "1803": "Amonkhet Standard Showdown", "1811": "Iconic Masters",
            "1821": "Unstable", "1822": "Dominaria", "1847": "Ixalan Standard Showdown",
            "2111": "Battlebond", "2397": "Ultimate Masters", "2398": "Ultimate Box Topper",
            "2582": "Throne of Eldraine Theme Booster (Red)",
            "2694": "Throne of Eldraine: Promo Pack", "2999": "Theros Beyond Death: Promo Pack",
            "3048": "Core 2021", "3053": "Jumpstart", "3204": "Double Masters",
            "3404": "Zendikar Rising Theme Booster (White)",
            "3454": "Commander Legends Collector",
            "3489": "Zendikar Rising Expeditions Box Topper",
            "3500": "Zendikar Rising: Promos: Promo Pack"
        };
        
        // Build reverse lookup: normalized set name -> chronological order
        const setNameToOrder = {};
        function normalizeSetName(name) {
            if (!name) return '';
            // Normalize: lowercase, remove "Edition" suffix, trim
            return name.toLowerCase()
                .replace(/\s+edition$/i, '')
                .replace(/['']/g, "'")
                .trim();
        }
        
        // Build the reverse lookup
        for (const [order, setName] of Object.entries(expansionChronologicalOrder)) {
            const normalizedName = normalizeSetName(setName);
            setNameToOrder[normalizedName] = parseInt(order, 10);
            // Also store original for exact matches
            setNameToOrder[setName.toLowerCase()] = parseInt(order, 10);
        }
        
        // Function to get chronological order for a set name
        function getSetChronologicalOrder(setName) {
            if (!setName) return 999999; // Unknown sets go to end
            const normalized = normalizeSetName(setName);
            if (setNameToOrder[normalized] !== undefined) {
                return setNameToOrder[normalized];
            }
            // Try lowercase exact match
            const lower = setName.toLowerCase();
            if (setNameToOrder[lower] !== undefined) {
                return setNameToOrder[lower];
            }
            // Fuzzy match: check if any known set name is contained
            for (const [knownName, order] of Object.entries(setNameToOrder)) {
                if (normalized.includes(knownName) || knownName.includes(normalized)) {
                    return order;
                }
            }
            return 999999; // Unknown sets go to end
        }
        
        // Sort functions
        const sortFunctions = {
            'original': (cards) => {
                // Sort by collection_index to maintain original JSON order
                return [...cards].sort((a, b) => {
                    const indexA = a.collection_index !== undefined ? a.collection_index : 999999;
                    const indexB = b.collection_index !== undefined ? b.collection_index : 999999;
                    return indexA - indexB;
                });
            },
            'name': (cards) => {
                return [...cards].sort((a, b) => {
                    const nameA = (a.name || '').toLowerCase();
                    const nameB = (b.name || '').toLowerCase();
                    if (nameA < nameB) return -1;
                    if (nameA > nameB) return 1;
                    // If names are equal, sort by expansion
                    const expA = (a.expansion || '').toLowerCase();
                    const expB = (b.expansion || '').toLowerCase();
                    return expA.localeCompare(expB);
                });
            },
            'set': (cards) => {
                return [...cards].sort((a, b) => {
                    const setA = (a.expansion || '').toLowerCase();
                    const setB = (b.expansion || '').toLowerCase();
                    if (setA < setB) return -1;
                    if (setA > setB) return 1;
                    // If sets are equal, sort by card name
                    const nameA = (a.name || '').toLowerCase();
                    const nameB = (b.name || '').toLowerCase();
                    return nameA.localeCompare(nameB);
                });
            },
            'price': (cards) => {
                return [...cards].sort((a, b) => {
                    const priceA = parseFloat(a.buy_price) || 0;
                    const priceB = parseFloat(b.buy_price) || 0;
                    // Sort descending (highest price first)
                    if (priceB > priceA) return 1;
                    if (priceB < priceA) return -1;
                    // If prices are equal, sort by name
                    const nameA = (a.name || '').toLowerCase();
                    const nameB = (b.name || '').toLowerCase();
                    return nameA.localeCompare(nameB);
                });
            },
            'set_chrono': (cards) => {
                return [...cards].sort((a, b) => {
                    const orderA = getSetChronologicalOrder(a.expansion);
                    const orderB = getSetChronologicalOrder(b.expansion);
                    if (orderA < orderB) return -1;
                    if (orderA > orderB) return 1;
                    // If sets are same order, sort by card name
                    const nameA = (a.name || '').toLowerCase();
                    const nameB = (b.name || '').toLowerCase();
                    return nameA.localeCompare(nameB);
                });
            }
        };
        
        // Create sort dropdown element (reusable function)
        function createSortDropdown(id, containerId) {
            // Create label
            const label = document.createElement('label');
            label.textContent = 'Sort by:';
            label.setAttribute('for', id);
            label.style.cssText = 'color: #d4af37; font-weight: 500; font-size: 13px; white-space: nowrap;';
            
            // Create dropdown
            const select = document.createElement('select');
            select.id = id;
            select.style.cssText = 'padding: 6px 10px; border: 1px solid #444; background: #222; color: #fff; border-radius: 4px; font-size: 13px; cursor: pointer; min-width: 160px;';
            
            // Add options
            const options = [
                { value: 'original', text: 'Original Order' },
                { value: 'name', text: 'Card Name (A-Z)' },
                { value: 'set', text: 'Set (A-Z)' },
                { value: 'set_chrono', text: 'Set (Chronological)' },
                { value: 'price', text: 'Price (High to Low)' }
            ];
            
            options.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt.value;
                option.textContent = opt.text;
                if (opt.value === currentSort) {
                    option.selected = true;
                }
                select.appendChild(option);
            });
            
            // Add change handler
            select.addEventListener('change', function(e) {
                const oldSort = currentSort;
                currentSort = e.target.value;
                localStorage.setItem('collection_sort', currentSort);
                console.log(`🔄 Sort changed from "${oldSort}" to "${currentSort}"`);
                
                // Sync both dropdowns if they exist
                const headerDropdown = document.getElementById('collection-sort-dropdown');
                const bottomDropdown = document.getElementById('bottom-collection-sort-dropdown');
                if (headerDropdown && headerDropdown !== e.target) {
                    headerDropdown.value = currentSort;
                }
                if (bottomDropdown && bottomDropdown !== e.target) {
                    bottomDropdown.value = currentSort;
                }
                
                // Clear the original cards to force a re-fetch
                originalCards = [];
                
                // Try to find the current page number
                let currentPage = 1;
                const pageIndicator = document.querySelector('[class*="page"], [id*="page"]');
                if (pageIndicator) {
                    const text = pageIndicator.textContent || '';
                    const match = text.match(/(\d+)\s+of\s+(\d+)/i) || text.match(/page\s+(\d+)/i);
                    if (match) {
                        currentPage = parseInt(match[1], 10);
                    }
                }
                
                // Try multiple approaches to trigger a reload
                let reloadTriggered = false;
                
                // Method 1: Try to find and call page load function
                const reloadFuncs = ['loadPage', 'showPage', 'goToPage', 'setPage', 'loadCards', 'refreshCards'];
                for (const funcName of reloadFuncs) {
                    if (typeof window[funcName] === 'function') {
                        try {
                            console.log(`🔄 Triggering reload via ${funcName}(${currentPage})`);
                            window[funcName](currentPage);
                            reloadTriggered = true;
                            break;
                        } catch(e) {
                            console.warn(`Failed to call ${funcName}:`, e);
                        }
                    }
                }
                
                // Method 2: Dispatch event
                if (!reloadTriggered) {
                    window.dispatchEvent(new CustomEvent('sortChanged', { 
                        detail: { sort: currentSort, page: currentPage } 
                    }));
                }
                
                // Method 3: If nothing else works, reload the page
                // BUT preserve the current page in localStorage before reloading
                if (!reloadTriggered) {
                    console.log('🔄 No reload function found, reloading page...');
                    // Store current page before reload (use global function if available, or fallback)
                    if (typeof window.updateStoredPage === 'function') {
                        window.updateStoredPage();
                    } else {
                        // Fallback: store page manually
                        const pageIndicator = document.querySelector('[class*="page"], [id*="page"]');
                        if (pageIndicator) {
                            const text = pageIndicator.textContent || '';
                            const match = text.match(/(\d+)\s+of\s+(\d+)/i) || text.match(/page\s+(\d+)/i);
                            if (match) {
                                const page = parseInt(match[1], 10);
                                localStorage.setItem('collection_current_page', page.toString());
                                console.log(`💾 Stored page ${page} (fallback)`);
                            }
                        }
                    }
                    setTimeout(() => {
                        window.location.reload();
                    }, 100);
                }
            });
            
            return { label, select };
        }
        
        // Create filter checkbox element
        function createFilterCheckbox(id) {
            // Create container
            const container = document.createElement('div');
            container.style.cssText = 'display: flex; align-items: center; gap: 6px;';
            
            // Create checkbox
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = id;
            checkbox.checked = showSoldOnly;
            checkbox.style.cssText = 'width: 16px; height: 16px; cursor: pointer;';
            
            // Create label
            const label = document.createElement('label');
            label.setAttribute('for', id);
            label.textContent = 'Show Sold Only';
            label.style.cssText = 'color: #d4af37; font-weight: 500; font-size: 13px; cursor: pointer; white-space: nowrap;';
            
            // Add change handler
            checkbox.addEventListener('change', function(e) {
                const oldFilter = showSoldOnly;
                showSoldOnly = e.target.checked;
                localStorage.setItem('collection_show_sold_only', showSoldOnly.toString());
                console.log(`🔄 Filter changed from "${oldFilter}" to "${showSoldOnly}"`);
                
                // Sync both checkboxes if they exist
                const headerCheckbox = document.getElementById('collection-filter-checkbox');
                const bottomCheckbox = document.getElementById('bottom-collection-filter-checkbox');
                if (headerCheckbox && headerCheckbox !== e.target) {
                    headerCheckbox.checked = showSoldOnly;
                }
                if (bottomCheckbox && bottomCheckbox !== e.target) {
                    bottomCheckbox.checked = showSoldOnly;
                }
                
                // Also sync sort dropdowns to ensure they stay in sync
                const headerDropdown = document.getElementById('collection-sort-dropdown');
                const bottomDropdown = document.getElementById('bottom-collection-sort-dropdown');
                if (headerDropdown) {
                    headerDropdown.value = currentSort;
                }
                if (bottomDropdown) {
                    bottomDropdown.value = currentSort;
                }
                
                // Update "No Cards" message after filter change
                if (originalCards && originalCards.length > 0) {
                    const filtered = filterCards(originalCards);
                    setTimeout(() => {
                        updateNoCardsMessage(filtered.length === 0 && originalCards.length > 0, originalCards.length);
                    }, 100);
                }
                
                // Clear the original cards to force a re-fetch
                originalCards = [];
                
                // Try to find the current page number
                let currentPage = 1;
                const pageIndicator = document.querySelector('[class*="page"], [id*="page"]');
                if (pageIndicator) {
                    const text = pageIndicator.textContent || '';
                    const match = text.match(/(\d+)\s+of\s+(\d+)/i) || text.match(/page\s+(\d+)/i);
                    if (match) {
                        currentPage = parseInt(match[1], 10);
                    }
                }
                
                // Try multiple approaches to trigger a reload
                let reloadTriggered = false;
                
                // Method 1: Try to find and call page load function
                const reloadFuncs = ['loadPage', 'showPage', 'goToPage', 'setPage', 'loadCards', 'refreshCards'];
                for (const funcName of reloadFuncs) {
                    if (typeof window[funcName] === 'function') {
                        try {
                            console.log(`🔄 Triggering reload via ${funcName}(${currentPage})`);
                            window[funcName](currentPage);
                            reloadTriggered = true;
                            break;
                        } catch(e) {
                            console.warn(`Failed to call ${funcName}:`, e);
                        }
                    }
                }
                
                // Method 2: Dispatch event
                if (!reloadTriggered) {
                    window.dispatchEvent(new CustomEvent('filterChanged', { 
                        detail: { showSoldOnly: showSoldOnly, page: currentPage } 
                    }));
                }
                
                // Method 3: If nothing else works, reload the page
                if (!reloadTriggered) {
                    console.log('🔄 No reload function found, reloading page...');
                    if (typeof window.updateStoredPage === 'function') {
                        window.updateStoredPage();
                    } else {
                        const pageIndicator = document.querySelector('[class*="page"], [id*="page"]');
                        if (pageIndicator) {
                            const text = pageIndicator.textContent || '';
                            const match = text.match(/(\d+)\s+of\s+(\d+)/i) || text.match(/page\s+(\d+)/i);
                            if (match) {
                                const page = parseInt(match[1], 10);
                                localStorage.setItem('collection_current_page', page.toString());
                            }
                        }
                    }
                    setTimeout(() => {
                        window.location.reload();
                    }, 100);
                }
            });
            
            container.appendChild(checkbox);
            container.appendChild(label);
            
            return container;
        }
        
        // Create format filter checkbox element (Old School or Premodern)
        function createFormatFilterCheckbox(id, labelText, filterType) {
            // Create container
            const container = document.createElement('div');
            container.style.cssText = 'display: flex; align-items: center; gap: 6px;';
            
            // Create checkbox
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = id;
            
            // Set initial checked state based on filter type
            if (filterType === 'old_school') {
                checkbox.checked = oldSchoolFilter;
            } else if (filterType === 'premodern') {
                checkbox.checked = premodernFilter;
            }
            
            checkbox.style.cssText = 'width: 16px; height: 16px; cursor: pointer;';
            
            // Create label
            const label = document.createElement('label');
            label.setAttribute('for', id);
            label.textContent = labelText;
            label.style.cssText = 'color: #d4af37; font-weight: 500; font-size: 13px; cursor: pointer; white-space: nowrap;';
            
            // Add change handler
            checkbox.addEventListener('change', function(e) {
                const oldOldSchool = oldSchoolFilter;
                const oldPremodern = premodernFilter;
                
                // Update the appropriate filter variable
                if (filterType === 'old_school') {
                    oldSchoolFilter = e.target.checked;
                    localStorage.setItem('collection_filter_old_school', oldSchoolFilter.toString());
                    console.log(`🔄 Old School filter changed from "${oldOldSchool}" to "${oldSchoolFilter}"`);
                } else if (filterType === 'premodern') {
                    premodernFilter = e.target.checked;
                    localStorage.setItem('collection_filter_premodern', premodernFilter.toString());
                    console.log(`🔄 Premodern filter changed from "${oldPremodern}" to "${premodernFilter}"`);
                }
                
                // Sync both checkboxes if they exist (header and bottom)
                const headerCheckbox = document.getElementById(id);
                const bottomCheckbox = document.getElementById('bottom-' + id);
                if (headerCheckbox && headerCheckbox !== e.target) {
                    headerCheckbox.checked = e.target.checked;
                }
                if (bottomCheckbox && bottomCheckbox !== e.target) {
                    bottomCheckbox.checked = e.target.checked;
                }
                
                // Update "No Cards" message after filter change
                if (originalCards && originalCards.length > 0) {
                    const filtered = filterCards(originalCards);
                    setTimeout(() => {
                        updateNoCardsMessage(filtered.length === 0 && originalCards.length > 0, originalCards.length);
                    }, 100);
                }
                
                // Also sync the other format checkbox
                if (filterType === 'old_school') {
                    const otherHeaderCheckbox = document.getElementById('collection-filter-premodern');
                    const otherBottomCheckbox = document.getElementById('bottom-collection-filter-premodern');
                    if (otherHeaderCheckbox) {
                        otherHeaderCheckbox.checked = premodernFilter;
                    }
                    if (otherBottomCheckbox) {
                        otherBottomCheckbox.checked = premodernFilter;
                    }
                } else if (filterType === 'premodern') {
                    const otherHeaderCheckbox = document.getElementById('collection-filter-old-school');
                    const otherBottomCheckbox = document.getElementById('bottom-collection-filter-old-school');
                    if (otherHeaderCheckbox) {
                        otherHeaderCheckbox.checked = oldSchoolFilter;
                    }
                    if (otherBottomCheckbox) {
                        otherBottomCheckbox.checked = oldSchoolFilter;
                    }
                }
                
                // Clear the original cards to force a re-fetch
                originalCards = [];
                
                // Try to find the current page number
                let currentPage = 1;
                const pageIndicator = document.querySelector('[class*="page"], [id*="page"]');
                if (pageIndicator) {
                    const text = pageIndicator.textContent || '';
                    const match = text.match(/(\d+)\s+of\s+(\d+)/i) || text.match(/page\s+(\d+)/i);
                    if (match) {
                        currentPage = parseInt(match[1], 10);
                    }
                }
                
                // Try multiple approaches to trigger a reload
                let reloadTriggered = false;
                
                // Method 1: Try to find and call page load function
                const reloadFuncs = ['loadPage', 'showPage', 'goToPage', 'setPage', 'loadCards', 'refreshCards'];
                for (const funcName of reloadFuncs) {
                    if (typeof window[funcName] === 'function') {
                        try {
                            console.log(`🔄 Triggering reload via ${funcName}(${currentPage})`);
                            window[funcName](currentPage);
                            reloadTriggered = true;
                            break;
                        } catch(e) {
                            console.warn(`Failed to call ${funcName}:`, e);
                        }
                    }
                }
                
                // Method 2: Dispatch event
                if (!reloadTriggered) {
                    window.dispatchEvent(new CustomEvent('filterChanged', { 
                        detail: { 
                            showSoldOnly: showSoldOnly, 
                            oldSchoolFilter: oldSchoolFilter,
                            premodernFilter: premodernFilter,
                            page: currentPage 
                        } 
                    }));
                }
                
                // Method 3: If nothing else works, reload the page
                if (!reloadTriggered) {
                    console.log('🔄 No reload function found, reloading page...');
                    if (typeof window.updateStoredPage === 'function') {
                        window.updateStoredPage();
                    } else {
                        const pageIndicator = document.querySelector('[class*="page"], [id*="page"]');
                        if (pageIndicator) {
                            const text = pageIndicator.textContent || '';
                            const match = text.match(/(\d+)\s+of\s+(\d+)/i) || text.match(/page\s+(\d+)/i);
                            if (match) {
                                const page = parseInt(match[1], 10);
                                localStorage.setItem('collection_current_page', page.toString());
                                console.log(`💾 Stored page ${page} (fallback)`);
                            }
                        }
                    }
                    setTimeout(() => {
                        window.location.reload();
                    }, 100);
                }
            });
            
            container.appendChild(checkbox);
            container.appendChild(label);
            
            return container;
        }
        
        // Add sort dropdown to UI (header and bottom)
        function addSortDropdown() {
            // Check if header dropdown already exists
            const headerExists = document.getElementById('collection-sort-dropdown');
            const bottomExists = document.getElementById('bottom-collection-sort-dropdown');
            
            // Add header dropdown if it doesn't exist
            if (!headerExists) {
                // Find stats container - try multiple selectors
                let statsContainer = document.getElementById('archived-stats-container');
                if (!statsContainer) {
                    // Try to find other stats containers
                    statsContainer = document.querySelector('.stats-container, .stats-section, [class*="stat"]');
                }
                
                // Create sort container (compact, inline style)
                const sortContainer = document.createElement('div');
                sortContainer.id = 'collection-sort-container';
                sortContainer.style.cssText = 'display: flex; align-items: center; gap: 12px; margin-left: auto; flex-wrap: wrap;';
                
                const { label, select } = createSortDropdown('collection-sort-dropdown', 'collection-sort-container');
                const filterCheckbox = createFilterCheckbox('collection-filter-checkbox');
                const oldSchoolCheckbox = createFormatFilterCheckbox('collection-filter-old-school', 'Old School', 'old_school');
                const premodernCheckbox = createFormatFilterCheckbox('collection-filter-premodern', 'Premodern', 'premodern');
                
                // Assemble container
                sortContainer.appendChild(label);
                sortContainer.appendChild(select);
                sortContainer.appendChild(filterCheckbox);
                sortContainer.appendChild(oldSchoolCheckbox);
                sortContainer.appendChild(premodernCheckbox);
                
                // Insert into stats container or create wrapper
                if (statsContainer) {
                    // Ensure stats container has flex layout to accommodate sort dropdown
                    const currentStyle = statsContainer.style.cssText || '';
                    if (!currentStyle.includes('display: flex')) {
                        statsContainer.style.cssText = (currentStyle ? currentStyle + ' ' : '') + 'display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 15px;';
                    } else if (!currentStyle.includes('align-items')) {
                        statsContainer.style.cssText = currentStyle + ' align-items: center;';
                    }
                    
                    // Make stats more compact if they exist
                    const statCards = statsContainer.querySelectorAll('div[style*="background"]');
                    statCards.forEach(card => {
                        const currentCardStyle = card.style.cssText || '';
                        // Reduce padding and font sizes if not already compact
                        if (currentCardStyle.includes('padding: 20px') || currentCardStyle.includes('font-size: 2em')) {
                            card.style.cssText = currentCardStyle
                                .replace(/padding:\s*20px/g, 'padding: 12px 16px')
                                .replace(/font-size:\s*2em/g, 'font-size: 1.5em')
                                .replace(/min-width:\s*150px/g, 'min-width: 120px');
                        }
                    });
                    
                    // Add sort dropdown to stats container (only if not already added)
                    if (!statsContainer.querySelector('#collection-sort-container')) {
                        statsContainer.appendChild(sortContainer);
                    }
                } else {
                    // If no stats container found, try to find main content and create a wrapper
                    const mainContent = document.querySelector('main, .container, .content, body');
                    if (mainContent) {
                        // Create a wrapper for stats and sort
                        const wrapper = document.createElement('div');
                        wrapper.style.cssText = 'display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 15px; margin: 15px 0;';
                        wrapper.appendChild(sortContainer);
                        mainContent.insertBefore(wrapper, mainContent.firstChild);
                    }
                }
            }
        }
        
        // Apply sorting to cards
        function applySorting() {
            if (!originalCards || originalCards.length === 0) {
                // Try to get cards from API if not already loaded
                const apiPath = window.location.pathname.includes('/collection') 
                    ? '/collection/api/collection-cards' 
                    : '/api/collection-cards';
                
                fetch(apiPath)
                    .then(res => res.json())
                    .then(data => {
                        if (data.cards && Array.isArray(data.cards)) {
                            originalCards = data.cards;
                            applySorting();
                        }
                    })
                    .catch(err => console.warn('Error fetching cards for sorting:', err));
                return;
            }
            
            const sortedCards = sortFunctions[currentSort](originalCards);
            console.log(`Applying sort "${currentSort}" to ${sortedCards.length} cards`);
            
            // Try to find and update the cards array in the global scope
            // This depends on how the frontend stores cards
            if (typeof window.cards !== 'undefined') {
                window.cards = sortedCards;
            }
            
            // Try to trigger a re-render by calling the render function
            // Look for common render function names
            const renderFunctions = [
                'renderCards',
                'displayCards',
                'showCards',
                'updateCards',
                'refreshCards',
                'loadCards',
                'render',
                'update'
            ];
            
            for (const funcName of renderFunctions) {
                if (typeof window[funcName] === 'function') {
                    try {
                        window[funcName](sortedCards);
                        console.log(`✅ Applied sorting (${currentSort}) using ${funcName}`);
                        return;
                    } catch(e) {
                        console.warn(`Error calling ${funcName}:`, e);
                    }
                }
            }
            
            // Dispatch custom event for other scripts to listen to
            window.dispatchEvent(new CustomEvent('cardsSorted', { 
                detail: { cards: sortedCards, sort: currentSort } 
            }));
            
            console.warn('⚠️ Could not find frontend render function. Sorting will take effect on next page load/refresh.');
        }
        
        // Listen for card updates from the frontend
        window.addEventListener('cardsLoaded', function(e) {
            if (e.detail && e.detail.cards) {
                originalCards = e.detail.cards;
                applySorting();
            }
        });
        
        // Store sorted cards globally for the frontend to access
        function reorderCardsInDOM(sortedCards) {
            console.log(`⚠️ reorderCardsInDOM called with ${sortedCards.length} cards - trying alternative approach`);
            
            // Store sorted cards in a global variable that the frontend can access
            window._sortedCards = sortedCards;
            
            // Try to find and call the frontend's render/load function
            // Look for functions that might reload the page
            const reloadFunctions = [
                'loadPage',
                'showPage', 
                'renderPage',
                'displayPage',
                'goToPage',
                'setPage',
                'refreshPage',
                'updatePage'
            ];
            
            for (const funcName of reloadFunctions) {
                if (typeof window[funcName] === 'function') {
                    try {
                        // Try calling with page 1
                        window[funcName](1);
                        console.log(`✅ Triggered page reload using ${funcName}(1)`);
                        return;
                    } catch(e) {
                        console.warn(`Error calling ${funcName}:`, e);
                    }
                }
            }
            
            // If no reload function found, try to trigger a custom event that the page might listen to
            window.dispatchEvent(new CustomEvent('reloadCards', { 
                detail: { cards: sortedCards } 
            }));
            
            // Also try to find current page and reload it
            const pageIndicator = document.querySelector('[class*="page"], [id*="page"]');
            if (pageIndicator) {
                const text = pageIndicator.textContent || '';
                const match = text.match(/(\d+)\s+of\s+(\d+)/i) || text.match(/page\s+(\d+)/i);
                if (match) {
                    const currentPage = parseInt(match[1], 10);
                    // Try to trigger a page change to force refresh
                    if (typeof window.goToPage === 'function') {
                        setTimeout(() => {
                            window.goToPage(currentPage);
                        }, 50);
                    } else if (typeof window.loadPage === 'function') {
                        setTimeout(() => {
                            window.loadPage(currentPage);
                        }, 50);
                    }
                }
            }
            
            console.warn('⚠️ Could not find a way to reload the page. Sorting may not be visible until page refresh.');
        }
        
        // Intercept API calls to sort cards before they're displayed
        function interceptAndSortAPI() {
            if (!window.originalFetch) {
                window.originalFetch = window.fetch;
            }
            
            window.fetch = function(...args) {
                const url = args[0];
                const options = args[1] || {};
                
                // Intercept collection-cards API response (handle both /api/ and /collection/api/ paths)
                if (typeof url === 'string' && (url.includes('/api/collection-cards') || url.includes('/collection/api/collection-cards'))) {
                    console.log(`🔄 Intercepting API call to: ${url}`);
                    console.log(`   Current sort: ${currentSort}`);
                    
                    return window.originalFetch.apply(this, args).then(async response => {
                        if (!response.ok) {
                            console.log(`❌ Response not OK: ${response.status}`);
                            return response;
                        }
                        
                        try {
                            // Read the response body
                            const responseData = await response.json();
                            
                            if (responseData.cards && Array.isArray(responseData.cards)) {
                                // Store original cards
                                originalCards = responseData.cards;
                                console.log(`📦 Stored ${originalCards.length} original cards`);
                                
                                // Apply filter first
                                const filteredCards = filterCards(responseData.cards);
                                console.log(`🔍 Filtered to ${filteredCards.length} cards (showSoldOnly: ${showSoldOnly}, Old School: ${oldSchoolFilter}, Premodern: ${premodernFilter})`);
                                
                                // Update "No Cards" message if filters are active and no cards match
                                if (filteredCards.length === 0 && responseData.cards.length > 0) {
                                    setTimeout(() => {
                                        updateNoCardsMessage(true, responseData.cards.length);
                                    }, 100);
                                } else if (filteredCards.length === 0 && responseData.cards.length === 0) {
                                    setTimeout(() => {
                                        updateNoCardsMessage(false, 0);
                                    }, 100);
                                } else {
                                    setTimeout(() => {
                                        updateNoCardsMessage(false, 0);
                                    }, 100);
                                }
                                
                                // Apply current sort
                                const sortedCards = sortFunctions[currentSort](filteredCards);
                                console.log(`✅ Sorted ${sortedCards.length} cards using: ${currentSort}`);
                                console.log(`   First 3 cards: ${sortedCards.slice(0, 3).map(c => c.name).join(', ')}`);
                                
                                // Create new response with sorted cards
                                const sortedData = {
                                    ...responseData,
                                    cards: sortedCards
                                };
                                
                                // Create a new Response with sorted data
                                const sortedResponse = new Response(JSON.stringify(sortedData), {
                                    status: response.status,
                                    statusText: response.statusText,
                                    headers: {
                                        'Content-Type': 'application/json'
                                    }
                                });
                                
                                // Override the json() method to return sorted data
                                sortedResponse.json = () => Promise.resolve(sortedData);
                                
                                return sortedResponse;
                            } else {
                                console.warn('⚠️ Response has no cards array');
                            }
                        } catch(e) {
                            console.error('❌ Error intercepting and sorting cards:', e);
                        }
                        
                        return response;
                    });
                }

                return window.originalFetch.apply(this, args);
            };
        }

        // Also intercept XMLHttpRequest for sorting
        // Store originals globally so pagination script can use them
        window.originalXHROpenSort = XMLHttpRequest.prototype.open;
        window.originalXHRSendSort = XMLHttpRequest.prototype.send;
        const originalXHROpenSort = window.originalXHROpenSort;
        const originalXHRSendSort = window.originalXHRSendSort;

        XMLHttpRequest.prototype.open = function(method, url, ...rest) {
            this._url = url;
            this._method = method;
            return originalXHROpenSort.apply(this, [method, url, ...rest]);
        };
        
        XMLHttpRequest.prototype.send = function(body) {
            const url = this._url;
            const method = this._method;
            
            // Intercept collection-cards API for GET requests (handle both /api/ and /collection/api/ paths)
            // For PUT/POST, let pagination script handle it
            if (url && (url.includes('/api/collection-cards') || url.includes('/collection/api/collection-cards')) && method === 'GET') {
                const originalOnReadyStateChange = this.onreadystatechange;
                const originalOnLoad = this.onload;
                
                this.onreadystatechange = function() {
                    if (this.readyState === 4 && this.status >= 200 && this.status < 300) {
                        try {
                            const responseText = this.responseText;
                            const data = JSON.parse(responseText);
                            
                            if (data.cards && Array.isArray(data.cards)) {
                                // Store original cards
                                originalCards = data.cards;
                                
                                // Apply filter first
                                const filteredCards = filterCards(data.cards);
                                console.log(`🔍 Filtered to ${filteredCards.length} cards (showSoldOnly: ${showSoldOnly}, Old School: ${oldSchoolFilter}, Premodern: ${premodernFilter})`);
                                
                                // Update "No Cards" message if filters are active and no cards match
                                if (filteredCards.length === 0 && data.cards.length > 0) {
                                    setTimeout(() => {
                                        updateNoCardsMessage(true, data.cards.length);
                                    }, 100);
                                } else if (filteredCards.length === 0 && data.cards.length === 0) {
                                    setTimeout(() => {
                                        updateNoCardsMessage(false, 0);
                                    }, 100);
                                } else {
                                    setTimeout(() => {
                                        updateNoCardsMessage(false, 0);
                                    }, 100);
                                }
                                
                                // Apply current sort
                                const sortedCards = sortFunctions[currentSort](filteredCards);
                                
                                // Update response
                                const sortedData = {
                                    ...data,
                                    cards: sortedCards
                                };
                                
                                // Replace responseText
                                Object.defineProperty(this, 'responseText', {
                                    writable: true,
                                    value: JSON.stringify(sortedData)
                                });
                                
                                // Update response if it exists
                                if (this.response) {
                                    Object.defineProperty(this, 'response', {
                                        writable: true,
                                        value: sortedData
                                    });
                                }
                                
                                console.log(`✅ Sorted ${sortedCards.length} cards in XHR using: ${currentSort}`);
                            }
                        } catch(e) {
                            console.warn('Error sorting cards in XHR:', e);
                        }
                    }
                    
                    if (originalOnReadyStateChange) {
                        originalOnReadyStateChange.apply(this, arguments);
                    }
                };
                
                this.onload = function() {
                    if (originalOnLoad) {
                        originalOnLoad.apply(this, arguments);
                    }
                };
            }
            
            return originalXHRSendSort.apply(this, [body]);
        };
        
        // Initialize
        function init() {
            // Load saved sort preference
            const savedSort = localStorage.getItem('collection_sort');
            if (savedSort && sortFunctions[savedSort]) {
                currentSort = savedSort;
            }
            
            // Load saved filter preference
            const savedFilter = localStorage.getItem('collection_show_sold_only');
            if (savedFilter !== null) {
                showSoldOnly = savedFilter === 'true';
            }
            
            // Load saved format filter preferences
            const savedOldSchoolFilter = localStorage.getItem('collection_filter_old_school');
            if (savedOldSchoolFilter !== null) {
                oldSchoolFilter = savedOldSchoolFilter === 'true';
            }
            
            const savedPremodernFilter = localStorage.getItem('collection_filter_premodern');
            if (savedPremodernFilter !== null) {
                premodernFilter = savedPremodernFilter === 'true';
            }
            
            // Set up interceptors
            interceptAndSortAPI();
            
            // Check and update "No Cards" message after page loads
            setTimeout(() => {
                if (originalCards && originalCards.length > 0) {
                    const filtered = filterCards(originalCards);
                    updateNoCardsMessage(filtered.length === 0 && originalCards.length > 0, originalCards.length);
                }
            }, 1000);
            
            // Add dropdown after a delay to ensure DOM is ready
            function tryAddDropdown() {
                addSortDropdown();
            }
            
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => {
                    setTimeout(tryAddDropdown, 500);
                    setTimeout(tryAddDropdown, 1000);
                    setTimeout(tryAddDropdown, 2000);
                });
            } else {
                setTimeout(tryAddDropdown, 500);
                setTimeout(tryAddDropdown, 1000);
                setTimeout(tryAddDropdown, 2000);
            }
            
            // Watch for dynamically added content
            const observer = new MutationObserver(() => {
                if (!document.getElementById('collection-sort-dropdown')) {
                    tryAddDropdown();
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
        
        init();
    })();
    </script>
"""
                # Inject before closing body tag
                if '</body>' in html_content:
                    html_content = html_content.replace('</body>', sorting_script + '\n</body>')
                elif '</html>' in html_content:
                    html_content = html_content.replace('</html>', sorting_script + '\n</html>')
                else:
                    html_content += sorting_script
            
            # Inject CSS for header flexbox layout
            if 'id="auth-section-style"' not in html_content:
                header_css = """
    <style id="auth-section-style">
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        #authModal {
            display: none;
        }
        #authModal[style*="flex"] {
            display: flex !important;
        }
    </style>
"""
                if '<head>' in html_content:
                    html_content = html_content.replace('<head>', '<head>' + header_css)
                elif '</head>' in html_content:
                    html_content = html_content.replace('</head>', header_css + '</head>')
            
            # NOTE: Authentication UI is now injected globally via main_app.py navigation
            # The global auth is accessible from all pages including Home
            
            if False:  # Old per-page auth injection - disabled, now handled globally
                print("🔐 Injecting authentication UI into HTML template", flush=True)
                auth_ui = """
            <div class="auth-section" id="authSection" style="margin-left: auto; display: flex; align-items: center;">
                <div id="authButtons" style="display: none;">
                    <button onclick="showLoginModal()" style="padding: 8px 16px; margin: 0 5px; background: #4a5568; color: white; border: none; border-radius: 4px; cursor: pointer;">Login</button>
                    <button onclick="showRegisterModal()" style="padding: 8px 16px; margin: 0 5px; background: #2d3748; color: white; border: none; border-radius: 4px; cursor: pointer;">Register</button>
                </div>
                <div id="userInfo" style="display: none;">
                    <span id="usernameDisplay" style="color: #d4af37; margin-right: 10px;"></span>
                    <button onclick="logout()" style="padding: 8px 16px; background: #c53030; color: white; border: none; border-radius: 4px; cursor: pointer;">Logout</button>
                </div>
            </div>
"""
                # Insert auth UI before closing </header> tag
                if '</header>' in html_content:
                    html_content = html_content.replace('</header>', auth_ui + '\n        </header>')
                    print("✅ Authentication UI injected into header", flush=True)
                else:
                    print("⚠️  Warning: </header> tag not found, auth UI not injected", flush=True)
                
                # Add authentication modal before </body>
                auth_modal = """
        <!-- Login/Register Modal -->
        <div id="authModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10000; justify-content: center; align-items: center;">
            <div style="background: #1a202c; padding: 30px; border-radius: 8px; max-width: 400px; width: 90%;">
                <h2 id="authModalTitle" style="color: #d4af37; margin-top: 0;">Login</h2>
                <form id="authForm" onsubmit="handleAuth(event)">
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; color: #e2e8f0; margin-bottom: 5px;">Username:</label>
                        <input type="text" id="authUsername" required style="width: 100%; padding: 8px; background: #2d3748; color: white; border: 1px solid #4a5568; border-radius: 4px; box-sizing: border-box;">
                    </div>
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; color: #e2e8f0; margin-bottom: 5px;">Password:</label>
                        <input type="password" id="authPassword" required style="width: 100%; padding: 8px; background: #2d3748; color: white; border: 1px solid #4a5568; border-radius: 4px; box-sizing: border-box;">
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button type="submit" style="flex: 1; padding: 10px; background: #4a5568; color: white; border: none; border-radius: 4px; cursor: pointer;">Submit</button>
                        <button type="button" onclick="hideAuthModal()" style="flex: 1; padding: 10px; background: #718096; color: white; border: none; border-radius: 4px; cursor: pointer;">Cancel</button>
                    </div>
                    <div id="authError" style="color: #fc8181; margin-top: 10px; display: none;"></div>
                </form>
            </div>
        </div>
"""
                if '</body>' in html_content:
                    html_content = html_content.replace('</body>', auth_modal + '\n    </body>')
            
            # NOTE: Authentication JavaScript is now injected globally via main_app.py
            # The global auth is accessible from all pages including Home
            if False:  # Old per-page auth script injection - disabled
                print("🔐 Injecting authentication JavaScript", flush=True)
                auth_script = """
    <script id="auth-script">
        // Authentication functions
        let isLoginMode = true;
        let isCheckingAuth = false;  // Prevent duplicate auth checks
        let collectionReloadScheduled = false;  // Prevent duplicate collection reloads

        async function checkAuthStatus() {
            // Prevent duplicate calls
            if (isCheckingAuth) {
                console.log('Auth check already in progress, skipping...');
                return;
            }
            isCheckingAuth = true;
            try {
                const apiPath = window.location.pathname.includes('/collection') ? '/collection/api/auth/me' : '/api/auth/me';
                console.log('Checking auth status at:', apiPath);
                const response = await fetch(apiPath, { 
                    credentials: 'include',
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                const data = await response.json();
                console.log('Auth status response:', data);
                
                const authButtons = document.getElementById('authButtons');
                const userInfo = document.getElementById('userInfo');
                const usernameDisplay = document.getElementById('usernameDisplay');
                const modal = document.getElementById('authModal');
                
                if (data.authenticated) {
                    if (authButtons) authButtons.style.display = 'none';
                    if (userInfo) userInfo.style.display = 'block';
                    if (usernameDisplay) usernameDisplay.textContent = data.username;
                    // Close modal if it's open
                    if (modal) {
                        modal.style.display = 'none';
                    }
                    console.log('User authenticated:', data.username);
                    
                    // Ensure "Add Card" button is visible when logged in
                    // Look for various possible selectors for the Add Card button
                    const addCardSelectors = [
                        'button[onclick*="add"]',
                        'button[onclick*="Add"]',
                        'button:contains("Add Card")',
                        '[id*="add-card"]',
                        '[id*="addCard"]',
                        '[class*="add-card"]',
                        'button[title*="Add"]',
                        'a[onclick*="add"]'
                    ];
                    
                    // Also check for buttons with text content
                    const allButtons = document.querySelectorAll('button, a, [role="button"]');
                    allButtons.forEach(btn => {
                        const text = (btn.textContent || '').toLowerCase();
                        if (text.includes('add card') || text.includes('add new') || text.includes('➕')) {
                            btn.style.display = '';
                            btn.style.visibility = 'visible';
                            btn.removeAttribute('hidden');
                            console.log('✅ Made Add Card button visible:', btn);
                        }
                    });
                    
                    // Try to find and show Add Card button by common patterns
                    setTimeout(() => {
                        const addCardBtn = document.querySelector('[onclick*="showAdd"], [onclick*="addCard"], [onclick*="openAdd"], button:contains("Add"), a:contains("Add")');
                        if (addCardBtn) {
                            addCardBtn.style.display = '';
                            addCardBtn.style.visibility = 'visible';
                            addCardBtn.removeAttribute('hidden');
                            console.log('✅ Found and made Add Card button visible');
                        }
                    }, 500);
                } else {
                    if (authButtons) authButtons.style.display = 'block';
                    if (userInfo) userInfo.style.display = 'none';
                    console.log('User not authenticated');
                }
            } catch (error) {
                console.error('Error checking auth status:', error);
                const authButtons = document.getElementById('authButtons');
                const userInfo = document.getElementById('userInfo');
                if (authButtons) authButtons.style.display = 'block';
                if (userInfo) userInfo.style.display = 'none';
            } finally {
                isCheckingAuth = false;
            }
        }

        function showLoginModal() {
            isLoginMode = true;
            document.getElementById('authModalTitle').textContent = 'Login';
            document.getElementById('authModal').style.display = 'flex';
            document.getElementById('authError').style.display = 'none';
            document.getElementById('authUsername').value = '';
            document.getElementById('authPassword').value = '';
        }

        function showRegisterModal() {
            isLoginMode = false;
            document.getElementById('authModalTitle').textContent = 'Register';
            document.getElementById('authModal').style.display = 'flex';
            document.getElementById('authError').style.display = 'none';
            document.getElementById('authUsername').value = '';
            document.getElementById('authPassword').value = '';
        }

        function hideAuthModal() {
            document.getElementById('authModal').style.display = 'none';
            document.getElementById('authError').style.display = 'none';
        }

        async function handleAuth(event) {
            event.preventDefault();
            const username = document.getElementById('authUsername').value;
            const password = document.getElementById('authPassword').value;
            const errorDiv = document.getElementById('authError');
            
            try {
                const endpoint = isLoginMode ? 'login' : 'register';
                const apiPath = window.location.pathname.includes('/collection') 
                    ? `/collection/api/auth/${endpoint}` 
                    : `/api/auth/${endpoint}`;
                
                const response = await fetch(apiPath, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username, password }),
                    credentials: 'include'
                });
                
                const data = await response.json();
                
                if (response.ok && data.success) {
                    hideAuthModal();
                    await checkAuthStatus();
                    // Reload the page to show user's collection
                    // This ensures all data and rendering is properly refreshed
                    console.log('Login successful, reloading page...');
                    setTimeout(() => {
                        window.location.reload();
                    }, 100);
                    return; // Early return to prevent further processing
                    
                    // OLD CODE - kept for reference but not executed
                    if (false && typeof loadCollection === 'function' && document.readyState === 'complete' && !collectionReloadScheduled) {
                        collectionReloadScheduled = true;
                        setTimeout(() => {
                            console.log('Reloading collection after login...');
                            loadCollection();
                            // Also reload statistics to show user's collection stats
                            if (typeof loadArchivedStats === 'function') {
                                loadArchivedStats();
                            }
                            collectionReloadScheduled = false;
                        }, 300);
                    }
                } else {
                    errorDiv.textContent = data.detail || 'Authentication failed';
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.textContent = 'Error: ' + error.message;
                errorDiv.style.display = 'block';
            }
        }

        async function logout() {
            try {
                const apiPath = window.location.pathname.includes('/collection') 
                    ? '/collection/api/auth/logout' 
                    : '/api/auth/logout';
                
                await fetch(apiPath, {
                    method: 'POST',
                    credentials: 'include'
                });
                
                // Reload the page to show shared collection
                // This ensures all data and rendering is properly refreshed  
                console.log('Logout successful, reloading page...');
                setTimeout(() => {
                    window.location.reload();
                }, 100);
            } catch (error) {
                console.error('Error logging out:', error);
            }
        }

        // Intercept fetch requests to reload collection after adding/updating/deleting cards
        if (!window._collectionReloadIntercepted) {
            window._collectionReloadIntercepted = true;
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                const url = args[0];
                const options = args[1] || {};
                
                // Intercept POST/PUT/DELETE to /api/collection
                if (typeof url === 'string' && 
                    (url.includes('/api/collection') || url.includes('/collection/api/collection')) &&
                    (options.method === 'POST' || options.method === 'PUT' || options.method === 'DELETE')) {
                    
                    return originalFetch.apply(this, args).then(async response => {
                        // Check if request was successful
                        if (response.ok) {
                            try {
                                const data = await response.clone().json();
                                if (data.success) {
                                    console.log('✅ Card operation successful, reloading collection...');
                                    // Reload collection after a short delay
                                    setTimeout(() => {
                                        if (typeof loadCollection === 'function' && document.readyState === 'complete' && !collectionReloadScheduled) {
                                            collectionReloadScheduled = true;
                                            console.log('🔄 Reloading collection after card operation...');
                                            loadCollection();
                                            // Also reload statistics to reflect updated collection
                                            if (typeof loadArchivedStats === 'function') {
                                                setTimeout(() => {
                                                    loadArchivedStats();
                                                }, 500);
                                            }
                                            setTimeout(() => {
                                                collectionReloadScheduled = false;
                                            }, 1000);
                                        } else if (typeof window.location !== 'undefined') {
                                            // Fallback: reload page if loadCollection function not available
                                            console.log('🔄 Page reload (loadCollection not available)...');
                                            window.location.reload();
                                        }
                                    }, 300);
                                }
                            } catch(e) {
                                // Response might not be JSON, ignore
                            }
                        }
                        return response;
                    });
                }
                
                return originalFetch.apply(this, args);
            };
        }
        
        // Check auth status on page load
        // Use multiple methods to ensure it runs, but only once
        let authInitialized = false;
        function initAuth() {
            if (authInitialized) return;
            authInitialized = true;
            
            // First, ensure modal is hidden
            const modal = document.getElementById('authModal');
            if (modal) {
                modal.style.display = 'none';
            }
            // Small delay to ensure cookies are available, then check auth
            setTimeout(checkAuthStatus, 100);
        }
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initAuth);
        } else {
            // DOM already loaded
            initAuth();
        }
        
        // Also check on window load (after all resources loaded)
        // Only check once to avoid duplicate calls
        let authCheckedOnLoad = false;
        window.addEventListener('load', function() {
            if (authCheckedOnLoad) return;
            authCheckedOnLoad = true;
            
            setTimeout(function() {
                checkAuthStatus();
                // Ensure modal is closed if user is authenticated
                const modal = document.getElementById('authModal');
                if (modal && modal.style.display === 'flex') {
                    // Double-check auth status before closing
                    fetch(window.location.pathname.includes('/collection') ? '/collection/api/auth/me' : '/api/auth/me', { 
                        credentials: 'include' 
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data.authenticated && modal) {
                            modal.style.display = 'none';
                        }
                    });
                }
            }, 200);
        });
        
        // Close auth modal with ESC key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                const authModal = document.getElementById('authModal');
                if (authModal && authModal.style.display === 'flex') {
                    hideAuthModal();
                }
            }
        });
        
        // Close auth modal when clicking outside (on backdrop)
        document.addEventListener('click', function(event) {
            const authModal = document.getElementById('authModal');
            if (event.target === authModal) {
                hideAuthModal();
            }
        });
    </script>
"""
                if '</body>' in html_content:
                    html_content = html_content.replace('</body>', auth_script + '\n    </body>')
                elif '</script>' in html_content:
                    # Insert before last </script> tag
                    html_content = html_content.rsplit('</script>', 1)[0] + auth_script + '\n    </script>' + html_content.rsplit('</script>', 1)[1]
            
            return HTMLResponse(content=html_content)
    else:
        return HTMLResponse(content="<h1>Collection Binder Template Not Found</h1>", status_code=404)


# Authentication endpoints
@app.post("/api/auth/register")
async def register(request: Request):
    """Register a new user."""
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required")
        
        if len(username) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
        
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        password_hash = auth.hash_password(password)
        try:
            user_id = database.create_user(username, password_hash)
        except sqlite3.OperationalError as e:
            # Database/table doesn't exist
            error_msg = str(e).lower()
            if "no such table" in error_msg:
                raise HTTPException(status_code=500, detail="Database not initialized. Please contact administrator.")
            else:
                raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")
        
        if user_id is None:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Create session token
        token = auth.create_session_token(user_id)
        response = JSONResponse({"success": True, "message": "User registered successfully", "username": username})
        response.set_cookie(
            key=auth.SESSION_COOKIE_NAME,
            value=token,
            max_age=auth.SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/"  # Make cookie available site-wide
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login")
async def login(request: Request):
    """Login a user."""
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required")
        
        user = database.get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        if not auth.verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Create session token
        token = auth.create_session_token(user["id"])
        response = JSONResponse({"success": True, "message": "Login successful", "username": username})
        response.set_cookie(
            key=auth.SESSION_COOKIE_NAME,
            value=token,
            max_age=auth.SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/"  # Make cookie available site-wide
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/logout")
async def logout():
    """Logout the current user."""
    response = JSONResponse({"success": True, "message": "Logout successful"})
    response.delete_cookie(key=auth.SESSION_COOKIE_NAME, path="/")
    return response


@app.get("/api/auth/me")
async def get_current_user_info(request: Request):
    """Get current user information."""
    user_id = auth.get_current_user(request)
    if user_id is None:
        return JSONResponse({"authenticated": False})
    
    user = database.get_user_by_id(user_id)
    if not user:
        return JSONResponse({"authenticated": False})
    
    return JSONResponse({"authenticated": True, "username": user["username"], "user_id": user["id"]})


@app.get("/api/collection")
async def get_collection(request: Request):
    """Get the full collection."""
    user_id = auth.get_current_user(request)
    collection = load_collection(user_id=user_id)
    return JSONResponse({"collection": collection})


@app.get("/api/sets")
async def get_sets():
    """Get list of available sets."""
    try:
        sets_file = "sets_data.json"
        if os.path.exists(sets_file):
            with open(sets_file, 'r', encoding='utf-8') as f:
                sets_data = json.load(f)
            return JSONResponse({"sets": sets_data})
        else:
            return JSONResponse({"sets": []})
    except Exception as e:
        return JSONResponse({"sets": [], "error": str(e)})


# Cache file for card printings
CARD_PRINTINGS_CACHE_FILE = "card_printings_cache.json"
SCRYFALL_DELAY = 0.1  # Rate limiting for Scryfall API


def load_printings_cache() -> Dict[str, List[Dict]]:
    """Load the card printings cache from file."""
    try:
        if os.path.exists(CARD_PRINTINGS_CACHE_FILE):
            with open(CARD_PRINTINGS_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading printings cache: {e}", flush=True)
    return {}


def save_printings_cache(cache: Dict[str, List[Dict]]):
    """Save the card printings cache to file."""
    try:
        with open(CARD_PRINTINGS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving printings cache: {e}", flush=True)


def resolve_card_to_oracle_id(card_name: str) -> Optional[str]:
    """Resolve a card name to its Oracle card ID using Scryfall."""
    import time
    time.sleep(SCRYFALL_DELAY)
    
    try:
        # Use exact name search first
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
        print(f"Error resolving card '{card_name}': {e}", flush=True)
        return None


def fetch_card_printings_from_scryfall(oracle_id: str) -> List[Dict]:
    """Fetch all printings for an Oracle card from Scryfall."""
    import time
    time.sleep(SCRYFALL_DELAY)
    
    all_printings = []
    url = "https://api.scryfall.com/cards/search"
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
                time.sleep(SCRYFALL_DELAY)  # Rate limit between pages
            else:
                url = None
        
        return all_printings
    except Exception as e:
        print(f"Error fetching printings for oracle_id '{oracle_id}': {e}", flush=True)
        return []


@app.get("/api/card-printings")
async def get_card_printings(name: str):
    """
    Get all valid printings (sets) for a specific card name.
    Results are cached to avoid repeated API calls.
    
    Returns:
        JSON with sets array containing valid printings for the card.
    """
    if not name or not name.strip():
        return JSONResponse({"sets": [], "error": "Card name is required"})
    
    card_name = name.strip()
    cache_key = card_name.lower()
    
    # Check cache first
    cache = load_printings_cache()
    if cache_key in cache:
        print(f"Cache hit for card printings: {card_name}", flush=True)
        return JSONResponse({"sets": cache[cache_key], "cached": True})
    
    print(f"Cache miss for card printings: {card_name}, fetching from Scryfall...", flush=True)
    
    # Resolve card name to Oracle ID
    oracle_id = resolve_card_to_oracle_id(card_name)
    if not oracle_id:
        return JSONResponse({"sets": [], "error": f"Card '{card_name}' not found"})
    
    # Fetch all printings
    printings = fetch_card_printings_from_scryfall(oracle_id)
    if not printings:
        return JSONResponse({"sets": [], "error": f"No printings found for '{card_name}'"})
    
    # Extract unique sets from printings
    # Format: [{name: "Set Name", code: "ABC", released: "YYYY-MM-DD"}, ...]
    sets_dict = {}
    for printing in printings:
        set_name = printing.get("set_name", "")
        set_code = printing.get("set", "").upper()
        released = printing.get("released_at", "")
        
        if set_name and set_code and set_code not in sets_dict:
            sets_dict[set_code] = {
                "name": set_name,
                "code": set_code,
                "released": released[:7] if released else "",  # YYYY-MM format
                "type": printing.get("set_type", "").replace("_", " ").title()
            }
    
    # Convert to list and sort by release date (newest first)
    sets_list = sorted(
        sets_dict.values(),
        key=lambda x: x.get("released", ""),
        reverse=True
    )
    
    # Cache the result
    cache[cache_key] = sets_list
    save_printings_cache(cache)
    print(f"Cached {len(sets_list)} printings for: {card_name}", flush=True)
    
    return JSONResponse({"sets": sets_list, "cached": False})


@app.get("/api/collection-cards")
async def get_collection_cards(request: Request):
    """Get collection expanded to cards (one per set). Automatically fetches missing images."""
    user_id = auth.get_current_user(request)
    collection = load_collection(user_id=user_id)
    cards = expand_collection_to_cards(collection)
    
    # Debug: Count how many cards have market data
    cards_with_market = [c for c in cards if c.get('market_value') is not None]
    print(f"📊 API: Returning {len(cards)} cards, {len(cards_with_market)} have market data", flush=True)
    if cards_with_market:
        print(f"   Sample cards with market data:", flush=True)
        for card in cards_with_market[:3]:
            print(f"      - {card.get('name')} ({card.get('expansion')}): €{card.get('market_value')}", flush=True)
    
    return JSONResponse({"cards": cards, "total": len(cards)})


def auto_scan_collection_card(collection_item: Dict[str, Any]):
    """
    Background task to automatically scan a newly added collection card.
    Runs asynchronously to avoid blocking the API response.
    """
    try:
        print(f"🔍 Auto-scan: Starting market scan for card: {collection_item.get('name', 'Unknown')}", flush=True)
        
        # Import here to avoid circular dependencies
        # Add simple_version to path (wishlist_deals.py is in simple_version/)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        simple_version_path = os.path.join(script_dir, 'simple_version')
        if simple_version_path not in sys.path:
            sys.path.insert(0, simple_version_path)
        from wishlist_deals import scan_single_collection_card
        
        # Run scan for the single card
        deals = scan_single_collection_card(collection_item, use_historical=True)
        
        if not deals:
            print(f"⚠️  Auto-scan: No deals found for {collection_item.get('name', 'Unknown')}", flush=True)
            return
        
        # Find or create latest collection_deals file
        deals_file = find_or_create_latest_collection_deals_file()
        
        # Append deals to file
        if append_deals_to_collection_file(deals_file, deals):
            print(f"✅ Auto-scan: Successfully scanned and saved results for {collection_item.get('name', 'Unknown')}", flush=True)
        else:
            print(f"❌ Auto-scan: Failed to save results for {collection_item.get('name', 'Unknown')}", flush=True)
    except Exception as e:
        print(f"❌ Auto-scan: Error during auto-scan: {e}", flush=True)
        import traceback
        traceback.print_exc()


@app.post("/api/collection")
async def add_collection_item(request: Request, background_tasks: BackgroundTasks):
    """Add a new item to the collection."""
    try:
        data = await request.json()
        user_id = auth.get_current_user(request)
        
        # Validate required fields
        if 'name' not in data:
            raise HTTPException(status_code=400, detail="Missing 'name' field")
        
        # Auto-populate format legality fields if not provided
        sets = data.get('sets', [])
        if sets and ('old_school_legal' not in data or 'premodern_legal' not in data):
            format_info = determine_format_legality_from_sets(sets)
            # Only populate if not already provided
            if 'old_school_legal' not in data:
                data['old_school_legal'] = format_info['old_school_legal']
            if 'premodern_legal' not in data:
                data['premodern_legal'] = format_info['premodern_legal']
            if 'format_validity' not in data:
                data['format_validity'] = format_info['format_validity']
            if 'old_school_sets' not in data:
                data['old_school_sets'] = format_info['old_school_sets']
            if 'premodern_sets' not in data:
                data['premodern_sets'] = format_info['premodern_sets']
        
        # If logged in, add directly to database
        if user_id is not None:
            item_id = database.add_collection_item(user_id, data)
            if item_id is None:
                raise HTTPException(status_code=500, detail="Failed to add item to collection")
            # Trigger auto-scan in background
            background_tasks.add_task(auto_scan_collection_card, data)
            print(f"📊 Auto-scan: Scheduled background scan for {data.get('name', 'Unknown')}", flush=True)
            return JSONResponse({"success": True, "message": "Item added successfully"})
        
        # If not logged in, use JSON file (backward compatibility)
        collection = load_collection(user_id=user_id)
        
        # Create new item
        new_item = {
            'name': data['name'],
            'sets': sets,
        }
        
        # Add collection-specific fields if provided
        if 'buy_price' in data:
            new_item['buy_price'] = data['buy_price']
            # Automatically set purchase_date if buy_price is provided
            if 'purchase_date' in data and data['purchase_date']:
                new_item['purchase_date'] = data['purchase_date']
            else:
                # Default to current date if buy_price is set but no date provided
                new_item['purchase_date'] = datetime.now().strftime('%Y-%m-%d')
        if 'condition' in data:
            new_item['condition'] = data['condition']
        if 'source' in data:
            new_item['source'] = data['source']
        if 'sell_price' in data:
            new_item['sell_price'] = data['sell_price']
            # Automatically set sale_date if sell_price is provided
            if 'sale_date' in data and data['sale_date']:
                new_item['sale_date'] = data['sale_date']
            else:
                # Default to current date if sell_price is set but no date provided
                new_item['sale_date'] = datetime.now().strftime('%Y-%m-%d')
        if 'notes' in data:
            new_item['notes'] = data['notes']
        if 'language' in data:
            new_item['language'] = data['language']
        if 'foil' in data:
            new_item['foil'] = bool(data['foil'])
        else:
            new_item['foil'] = False
        
        # Add format legality fields (auto-populated above if sets were provided)
        if 'old_school_legal' in data:
            new_item['old_school_legal'] = data['old_school_legal']
        if 'premodern_legal' in data:
            new_item['premodern_legal'] = data['premodern_legal']
        if 'format_validity' in data:
            new_item['format_validity'] = data['format_validity']
        if 'old_school_sets' in data:
            new_item['old_school_sets'] = data['old_school_sets']
        if 'premodern_sets' in data:
            new_item['premodern_sets'] = data['premodern_sets']
        
        collection.append(new_item)
        
        if save_collection(collection, user_id=user_id):
            # Trigger auto-scan in background (non-blocking)
            background_tasks.add_task(auto_scan_collection_card, new_item)
            print(f"📊 Auto-scan: Scheduled background scan for {new_item.get('name', 'Unknown')}", flush=True)
            return JSONResponse({"success": True, "message": "Item added successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to save collection")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/collection/{index}")
async def update_collection_item(index: int, request: Request):
    """Update a collection item by index."""
    try:
        data = await request.json()
        user_id = auth.get_current_user(request)
        collection = load_collection(user_id=user_id)
        
        if index < 0 or index >= len(collection):
            raise HTTPException(status_code=404, detail="Item not found")
        
        # If logged in, update in database using item ID
        if user_id is not None:
            item = collection[index]
            item_id = item.get("id")
            if item_id is None:
                raise HTTPException(status_code=404, detail="Item ID not found")
            
            # Update item in database
            if database.update_collection_item(user_id, item_id, data):
                return JSONResponse({"success": True, "message": "Item updated successfully"})
            else:
                raise HTTPException(status_code=500, detail="Failed to update collection item")
        
        # If not logged in, update in JSON (backward compatibility)
        
        # Update item
        if 'name' in data:
            collection[index]['name'] = data['name']
        if 'sets' in data:
            collection[index]['sets'] = data['sets']
        if 'notes' in data:
            collection[index]['notes'] = data['notes']
        
        # Update collection-specific fields
        if 'buy_price' in data:
            if data['buy_price'] is not None and data['buy_price'] != '':
                collection[index]['buy_price'] = data['buy_price']
                # Update purchase_date if buy_price is set
                if 'purchase_date' in data and data['purchase_date']:
                    collection[index]['purchase_date'] = data['purchase_date']
                elif 'purchase_date' not in collection[index]:
                    # Set default date if buy_price is set but no date exists
                    collection[index]['purchase_date'] = datetime.now().strftime('%Y-%m-%d')
            elif 'buy_price' in collection[index]:
                del collection[index]['buy_price']
                # Remove purchase_date when buy_price is removed
                if 'purchase_date' in collection[index]:
                    del collection[index]['purchase_date']
        # Handle purchase_date separately (in case user wants to update date without changing price)
        if 'purchase_date' in data:
            if data['purchase_date'] is not None and data['purchase_date'] != '':
                collection[index]['purchase_date'] = data['purchase_date']
            elif 'purchase_date' in collection[index] and 'buy_price' not in collection[index]:
                # Only remove date if buy_price is also not present
                del collection[index]['purchase_date']
        if 'condition' in data:
            if data['condition'] is not None and data['condition'] != '':
                collection[index]['condition'] = data['condition']
            elif 'condition' in collection[index]:
                del collection[index]['condition']
        if 'source' in data:
            if data['source'] is not None and data['source'] != '':
                collection[index]['source'] = data['source']
            elif 'source' in collection[index]:
                del collection[index]['source']
        if 'sell_price' in data:
            if data['sell_price'] is not None and data['sell_price'] != '':
                collection[index]['sell_price'] = data['sell_price']
                # Update sale_date if sell_price is set
                if 'sale_date' in data and data['sale_date']:
                    collection[index]['sale_date'] = data['sale_date']
                elif 'sale_date' not in collection[index]:
                    # Set default date if sell_price is set but no date exists
                    collection[index]['sale_date'] = datetime.now().strftime('%Y-%m-%d')
            elif 'sell_price' in collection[index]:
                del collection[index]['sell_price']
                # Remove sale_date when sell_price is removed
                if 'sale_date' in collection[index]:
                    del collection[index]['sale_date']
        # Handle sale_date separately (in case user wants to update date without changing price)
        if 'sale_date' in data:
            if data['sale_date'] is not None and data['sale_date'] != '':
                collection[index]['sale_date'] = data['sale_date']
            elif 'sale_date' in collection[index] and 'sell_price' not in collection[index]:
                # Only remove date if sell_price is also not present
                del collection[index]['sale_date']
        if 'language' in data:
            if data['language'] is not None and data['language'] != '':
                collection[index]['language'] = data['language']
            elif 'language' in collection[index]:
                del collection[index]['language']
        if 'foil' in data:
            collection[index]['foil'] = bool(data['foil'])
        
        if save_collection(collection, user_id=user_id):
            return JSONResponse({"success": True, "message": "Item updated successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to save collection")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/collection/{index}")
async def archive_collection_item(index: int, request: Request):
    """Archive a collection item by moving it to collection_archived.json."""
    try:
        user_id = auth.get_current_user(request)
        collection = load_collection(user_id=user_id)
        
        if index < 0 or index >= len(collection):
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Get the item to archive
        item_to_archive = collection.pop(index)
        
        # If logged in, delete from database
        if user_id is not None:
            item_id = item_to_archive.get("id")
            if item_id is not None:
                database.delete_collection_item(user_id, item_id)
            # Also save updated collection (without the deleted item)
            if save_collection(collection, user_id=user_id):
                # Archive functionality for logged-in users could be added later
                return JSONResponse({
                    "success": True, 
                    "message": "Item deleted successfully",
                    "archived_item": item_to_archive
                })
            else:
                raise HTTPException(status_code=500, detail="Failed to save collection")
        
        # If not logged in, use JSON archive (backward compatibility)
        
        # Add timestamp to archived item
        item_to_archive['archived_at'] = datetime.now().isoformat()
        
        # Load existing archived items
        archived = load_archived_collection()
        archived.append(item_to_archive)
        
        # Save both files
        if save_collection(collection, user_id=user_id) and save_archived_collection(archived):
            return JSONResponse({
                "success": True, 
                "message": "Item archived successfully",
                "archived_item": item_to_archive
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save collection or archive")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/collection/reorder")
async def reorder_collection(request: Request):
    """Reorder collection items based on provided order array."""
    try:
        data = await request.json()
        order = data.get('order', [])
        user_id = auth.get_current_user(request)
        collection = load_collection(user_id=user_id)
        
        # Validate order array
        if len(order) != len(collection):
            raise HTTPException(
                status_code=400, 
                detail=f"Order array length ({len(order)}) doesn't match collection length ({len(collection)})"
            )
        
        # Validate all indices are present
        if set(order) != set(range(len(collection))):
            raise HTTPException(
                status_code=400, 
                detail="Order array must contain all indices from 0 to collection length - 1"
            )
        
        # Reorder collection based on the provided order
        reordered_collection = [collection[i] for i in order]
        
        if save_collection(reordered_collection, user_id=user_id):
            return JSONResponse({
                "success": True, 
                "message": "Collection reordered successfully"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save reordered collection")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/search-cards")
async def search_cards(q: str = ""):
    """Search for cards by name (placeholder - could integrate with Cardmarket API)."""
    # This is a placeholder - in the future could integrate with card lookup
    return JSONResponse({"cards": [], "query": q})


@app.get("/api/autocomplete-card")
async def autocomplete_card_name(q: str = ""):
    """Get autocomplete suggestions for card names."""
    if not q or len(q) < 1:
        return JSONResponse({"suggestions": []})
    
    if autocomplete_cards is None:
        # Fallback to Scryfall only if module not available
        try:
            response = requests.get(
                "https://api.scryfall.com/cards/autocomplete",
                params={"q": q},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("object") != "error":
                    return JSONResponse({"suggestions": data.get("data", [])[:10]})
        except Exception as e:
            print(f"Error fetching autocomplete from Scryfall: {e}", flush=True)
        return JSONResponse({"suggestions": []})
    
    # Use card_autocomplete module
    try:
        results = autocomplete_cards(
            q,
            max_local=10,
            max_scryfall=10,
            exclude_local_from_scryfall=True,
            timeout=5
        )
        return JSONResponse({
            "suggestions": results.get("combined", [])[:15],  # Limit to 15 total
            "local": results.get("local", []),
            "scryfall": results.get("scryfall", [])
        })
    except Exception as e:
        print(f"Error in autocomplete: {e}", flush=True)
        return JSONResponse({"suggestions": [], "error": str(e)})


@app.get("/api/fetch-card-image")
async def fetch_card_image(name: str, set: Optional[str] = None, language: Optional[str] = None):
    """Fetch card image from Scryfall if it doesn't exist locally. Supports set-specific fetching and language filtering."""
    try:
        # Generate filename with set if provided
        filename = get_image_filename(name, set)
        target_dir = IMAGE_DIR_SETS if set else IMAGE_DIR
        filepath = os.path.join(target_dir, filename)
        
        # Check if image already exists
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return JSONResponse({
                "success": True,
                "image_path": f"/card_images_sets/{filename}" if set else f"/card_images/{filename}",
                "message": "Image already exists"
            })
        
        # Fallback: Try without variant suffix (e.g., "Mox Jet (IE)" -> "Mox Jet")
        name_without_variant = strip_variant_suffix(name)
        if name_without_variant != name:
            fallback_filename = get_image_filename(name_without_variant, set)
            fallback_filepath = os.path.join(target_dir, fallback_filename)
            if os.path.exists(fallback_filepath) and os.path.getsize(fallback_filepath) > 0:
                return JSONResponse({
                    "success": True,
                    "image_path": f"/card_images_sets/{fallback_filename}" if set else f"/card_images/{fallback_filename}",
                    "message": "Image already exists (found without variant suffix)"
                })
        
        # Fetch from Scryfall (with set and language if provided)
        image_path = fetch_card_image_from_scryfall(name, set, language)
        
        if image_path:
            return JSONResponse({
                "success": True,
                "image_path": image_path,
                "message": "Image fetched successfully"
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "Could not fetch image from Scryfall"
            }, status_code=404)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)


@app.get("/api/archived-stats")
async def get_archived_stats(request: Request):
    """Get statistics for active collection items only (not archived)."""
    try:
        # Load collection for the current user (or collection.json if not logged in)
        user_id = auth.get_current_user(request)
        collection = load_collection(user_id=user_id)
        
        total_cost = 0.0
        sold_count = 0
        total_sold_amount = 0.0
        total_profit = 0.0
        collection_count = 0  # Items not sold
        
        # Filter out sold items before calculating market value (same as total_cost)
        active_collection = []
        for item in collection:
            sell_price = item.get('sell_price')
            is_sold = False
            if sell_price is not None:
                try:
                    sell_price_float = float(sell_price)
                    if sell_price_float > 0:
                        is_sold = True
                except (ValueError, TypeError):
                    pass
            
            if not is_sold:
                active_collection.append(item)
        
        # Calculate total current market value from expanded cards (only active/unsold items)
        cards = expand_collection_to_cards(active_collection)
        total_market_value = 0.0
        cards_with_market = 0
        cards_without_market = 0
        for card in cards:
            market_value = card.get('market_value')
            if market_value is not None:
                try:
                    total_market_value += float(market_value)
                    cards_with_market += 1
                except (ValueError, TypeError):
                    cards_without_market += 1
            else:
                cards_without_market += 1
        
        print(f"📊 Stats: {len(cards)} active cards (excluding sold), {cards_with_market} with market value, {cards_without_market} without", flush=True)
        print(f"📊 Stats: Total market value = €{total_market_value:.2f}", flush=True)
        
        for item in collection:
            buy_price = item.get('buy_price')
            sell_price = item.get('sell_price')
            
            # Count as collection item if not sold (sell_price is None or 0)
            is_sold = False
            if sell_price is not None:
                try:
                    sell_price_float = float(sell_price)
                    if sell_price_float > 0:
                        is_sold = True
                except (ValueError, TypeError):
                    pass
            
            if not is_sold:
                collection_count += 1
                # Add buy_price to total cost only for items still in collection (not sold)
                if buy_price is not None:
                    try:
                        buy_price_float = float(buy_price)
                        total_cost += buy_price_float
                    except (ValueError, TypeError):
                        pass
            
            # Count items with sell_price > 0 as sold items and calculate profit
            if is_sold:
                sold_count += 1
                try:
                    sell_price_float = float(sell_price)
                    total_sold_amount += sell_price_float
                    
                    # Calculate profit only if buy_price also exists
                    if buy_price is not None:
                        try:
                            buy_price_float = float(buy_price)
                            total_profit += (sell_price_float - buy_price_float)
                        except (ValueError, TypeError):
                            pass
                except (ValueError, TypeError):
                    pass
        
        return JSONResponse({
            "collection_count": collection_count,
            "total_cost": round(total_cost, 2),
            "total_market_value": round(total_market_value, 2),
            "sold_count": sold_count,
            "total_sold_amount": round(total_sold_amount, 2),
            "total_profit": round(total_profit, 2)
        })
    except Exception as e:
        return JSONResponse({
            "collection_count": 0,
            "total_cost": 0.0,
            "total_market_value": 0.0,
            "sold_count": 0,
            "total_sold_amount": 0.0,
            "total_profit": 0.0,
            "error": str(e)
        }, status_code=500)


def main():
    """Run the collection UI server."""
    parser = argparse.ArgumentParser(description="MTG Collection Management UI")
    parser.add_argument(
        '--port',
        type=int,
        default=DEFAULT_PORT,
        help=f'Port to run server on (default: {DEFAULT_PORT})'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    args = parser.parse_args()
    
    import uvicorn
    print(f"\n🎴 MTG Collection Manager")
    print(f"=" * 60)
    print(f"📋 Collection file: {COLLECTION_FILE}")
    print(f"🌐 Server starting on http://{args.host}:{args.port}")
    print(f"=" * 60)
    
    try:
        uvicorn.run(
            "collection_ui:app",
            host=args.host,
            port=args.port,
            log_level="info",
            reload=False
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Server stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\n\n❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

