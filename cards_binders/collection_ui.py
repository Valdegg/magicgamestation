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
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import card autocomplete functionality
try:
    from card_autocomplete import autocomplete_cards
except ImportError:
    autocomplete_cards = None
    print("Warning: card_autocomplete module not available", flush=True)

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


def load_collection(filepath: str = COLLECTION_FILE) -> List[Dict[str, Any]]:
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


def save_collection(collection: List[Dict[str, Any]], filepath: str = COLLECTION_FILE) -> bool:
    """Save collection to JSON file."""
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


def expand_collection_to_cards(collection: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Expand collection items to show one card per set.
    Each collection item with multiple sets becomes multiple card entries.
    Images are fetched on-demand when requested by the browser (via /api/fetch-card-image).
    """
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
        
        # If no sets specified, create one entry with no set
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
                'collection_index': index  # Track original index for editing
            })
        else:
            # Create one card per set
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
                    'collection_index': index  # Track original index for editing
                })
    
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
        const originalFetch = window.fetch;
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
            
            return originalFetch.apply(this, args);
        };
        
        // Update card display to show language and foil
        function updateCardDisplays() {
            document.querySelectorAll('[data-card-name]').forEach(cardEl => {
                const language = cardEl.dataset.language;
                const foil = cardEl.dataset.foil === 'true';
                
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
            });
        }
        
        // Hook into card rendering to add language display and data attribute
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
            const response = await fetch(apiPath);
            const stats = await response.json();
            
            // Find existing stats container or create one
            let statsContainer = document.getElementById('archived-stats-container');
            if (!statsContainer) {
                // Try to find existing stats section and add after it
                const existingStats = document.querySelector('.stats-container, .stats-section, [class*="stat"]');
                if (existingStats && existingStats.parentElement) {
                    statsContainer = document.createElement('div');
                    statsContainer.id = 'archived-stats-container';
                    statsContainer.className = 'stats-container';
                    statsContainer.style.cssText = 'display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 15px; margin: 15px 0;';
                    existingStats.parentElement.insertBefore(statsContainer, existingStats.nextSibling);
                } else {
                    // Create at top of main content
                    const mainContent = document.querySelector('main, .container, .content, body');
                    if (mainContent) {
                        statsContainer = document.createElement('div');
                        statsContainer.id = 'archived-stats-container';
                        statsContainer.className = 'stats-container';
                        statsContainer.style.cssText = 'display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 15px; margin: 15px 0;';
                        mainContent.insertBefore(statsContainer, mainContent.firstChild);
                    }
                }
            }
            
            if (statsContainer) {
                // Create stat cards with compact styling
                const statCardStyle = 'background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%); border: 2px solid #3a3a3a; border-radius: 8px; padding: 12px 16px; min-width: 120px; text-align: center;';
                const statValueStyle = 'font-size: 1.5em; font-weight: bold; color: #ffffff; margin-bottom: 4px;';
                const statLabelStyle = 'font-size: 0.8em; color: #d4af37; text-transform: uppercase; letter-spacing: 0.5px;';
                
                statsContainer.innerHTML = `
                    <div style="${statCardStyle}">
                        <div style="${statValueStyle}">€${stats.total_cost.toFixed(2)}</div>
                        <div style="${statLabelStyle}">Total Cost</div>
                    </div>
                    <div style="${statCardStyle}">
                        <div style="${statValueStyle}">${stats.sold_count}</div>
                        <div style="${statLabelStyle}">Sold Items</div>
                    </div>
                    <div style="${statCardStyle}">
                        <div style="${statValueStyle}">€${stats.total_sold_amount.toFixed(2)}</div>
                        <div style="${statLabelStyle}">Total Sold</div>
                    </div>
                    <div style="${statCardStyle}">
                        <div style="${statValueStyle}">€${stats.total_profit.toFixed(2)}</div>
                        <div style="${statLabelStyle}">Total Profit</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading archived stats:', error);
        }
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
            setTimeout(fixRedundantStats, 500); // Wait a bit for other scripts to load stats
        });
    } else {
        loadArchivedStats();
        setTimeout(fixRedundantStats, 500);
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
            if (currentPage > 1) {
                setCurrentPage(currentPage);
            }
        }
        
        // Restore page on load
        function restorePage() {
            const storedPage = localStorage.getItem('collection_current_page');
            if (storedPage) {
                const page = parseInt(storedPage, 10);
                if (page > 1) {
                    setTimeout(() => {
                        goToPage(page);
                    }, 500);
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
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const url = args[0];
            const options = args[1] || {};
            
            // Before PUT/POST to collection API, store current page
            if (typeof url === 'string' && url.includes('/api/collection') && (options.method === 'PUT' || options.method === 'POST')) {
                updateStoredPage();
                
                // After successful save, restore page
                return originalFetch.apply(this, args).then(response => {
                    if (response.ok) {
                        const storedPage = localStorage.getItem('collection_current_page');
                        if (storedPage) {
                            setTimeout(() => {
                                goToPage(parseInt(storedPage, 10));
                            }, 300);
                        }
                    }
                    return response;
                });
            }
            
            return originalFetch.apply(this, args);
        };
        
        // Also intercept XMLHttpRequest
        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalXHRSend = XMLHttpRequest.prototype.send;
        
        XMLHttpRequest.prototype.open = function(method, url, ...rest) {
            this._url = url;
            this._method = method;
            return originalXHROpen.apply(this, [method, url, ...rest]);
        };
        
        XMLHttpRequest.prototype.send = function(body) {
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
            return originalXHRSend.apply(this, [body]);
        };
        
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
            }
        };
        
        // Add sort dropdown to UI
        function addSortDropdown() {
            // Check if dropdown already exists
            if (document.getElementById('collection-sort-dropdown')) {
                return;
            }
            
            // Find stats container - try multiple selectors
            let statsContainer = document.getElementById('archived-stats-container');
            if (!statsContainer) {
                // Try to find other stats containers
                statsContainer = document.querySelector('.stats-container, .stats-section, [class*="stat"]');
            }
            
            // Create sort container (compact, inline style)
            const sortContainer = document.createElement('div');
            sortContainer.id = 'collection-sort-container';
            sortContainer.style.cssText = 'display: flex; align-items: center; gap: 8px; margin-left: auto;';
            
            // Create label
            const label = document.createElement('label');
            label.textContent = 'Sort by:';
            label.setAttribute('for', 'collection-sort-dropdown');
            label.style.cssText = 'color: #d4af37; font-weight: 500; font-size: 13px; white-space: nowrap;';
            
            // Create dropdown
            const select = document.createElement('select');
            select.id = 'collection-sort-dropdown';
            select.style.cssText = 'padding: 6px 10px; border: 1px solid #444; background: #222; color: #fff; border-radius: 4px; font-size: 13px; cursor: pointer; min-width: 160px;';
            
            // Add options
            const options = [
                { value: 'original', text: 'Original Order' },
                { value: 'name', text: 'Card Name (A-Z)' },
                { value: 'set', text: 'Set (A-Z)' },
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
                if (!reloadTriggered) {
                    console.log('🔄 No reload function found, reloading page...');
                    setTimeout(() => {
                        window.location.reload();
                    }, 100);
                }
            });
            
            // Assemble container
            sortContainer.appendChild(label);
            sortContainer.appendChild(select);
            
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
            const originalFetch = window.fetch;
            
            window.fetch = function(...args) {
                const url = args[0];
                const options = args[1] || {};
                
                // Intercept collection-cards API response (handle both /api/ and /collection/api/ paths)
                if (typeof url === 'string' && (url.includes('/api/collection-cards') || url.includes('/collection/api/collection-cards'))) {
                    console.log(`🔄 Intercepting API call to: ${url}`);
                    console.log(`   Current sort: ${currentSort}`);
                    
                    return originalFetch.apply(this, args).then(async response => {
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
                                
                                // Apply current sort
                                const sortedCards = sortFunctions[currentSort](responseData.cards);
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
                
                return originalFetch.apply(this, args);
            };
        }
        
        // Also intercept XMLHttpRequest
        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalXHRSend = XMLHttpRequest.prototype.send;
        
        XMLHttpRequest.prototype.open = function(method, url, ...rest) {
            this._url = url;
            this._method = method;
            return originalXHROpen.apply(this, [method, url, ...rest]);
        };
        
        XMLHttpRequest.prototype.send = function(body) {
            const url = this._url;
            const method = this._method;
            
            // Intercept collection-cards API (handle both /api/ and /collection/api/ paths)
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
                                
                                // Apply current sort
                                const sortedCards = sortFunctions[currentSort](data.cards);
                                
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
            
            return originalXHRSend.apply(this, [body]);
        };
        
        // Initialize
        function init() {
            // Load saved sort preference
            const savedSort = localStorage.getItem('collection_sort');
            if (savedSort && sortFunctions[savedSort]) {
                currentSort = savedSort;
            }
            
            // Set up interceptors
            interceptAndSortAPI();
            
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
            
            return HTMLResponse(content=html_content)
    else:
        return HTMLResponse(content="<h1>Collection Binder Template Not Found</h1>", status_code=404)


@app.get("/api/collection")
async def get_collection():
    """Get the full collection."""
    collection = load_collection()
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


@app.get("/api/collection-cards")
async def get_collection_cards():
    """Get collection expanded to cards (one per set). Automatically fetches missing images."""
    collection = load_collection()
    cards = expand_collection_to_cards(collection)
    return JSONResponse({"cards": cards, "total": len(cards)})


@app.post("/api/collection")
async def add_collection_item(request: Request):
    """Add a new item to the collection."""
    try:
        data = await request.json()
        collection = load_collection()
        
        # Validate required fields
        if 'name' not in data:
            raise HTTPException(status_code=400, detail="Missing 'name' field")
        
        # Create new item
        new_item = {
            'name': data['name'],
            'sets': data.get('sets', []),
        }
        
        # Add collection-specific fields if provided
        if 'buy_price' in data:
            new_item['buy_price'] = data['buy_price']
        if 'condition' in data:
            new_item['condition'] = data['condition']
        if 'source' in data:
            new_item['source'] = data['source']
        if 'sell_price' in data:
            new_item['sell_price'] = data['sell_price']
        if 'notes' in data:
            new_item['notes'] = data['notes']
        if 'language' in data:
            new_item['language'] = data['language']
        if 'foil' in data:
            new_item['foil'] = bool(data['foil'])
        else:
            new_item['foil'] = False
        
        collection.append(new_item)
        
        if save_collection(collection):
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
        collection = load_collection()
        
        if index < 0 or index >= len(collection):
            raise HTTPException(status_code=404, detail="Item not found")
        
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
            elif 'buy_price' in collection[index]:
                del collection[index]['buy_price']
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
            elif 'sell_price' in collection[index]:
                del collection[index]['sell_price']
        if 'language' in data:
            if data['language'] is not None and data['language'] != '':
                collection[index]['language'] = data['language']
            elif 'language' in collection[index]:
                del collection[index]['language']
        if 'foil' in data:
            collection[index]['foil'] = bool(data['foil'])
        
        if save_collection(collection):
            return JSONResponse({"success": True, "message": "Item updated successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to save collection")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/collection/{index}")
async def archive_collection_item(index: int):
    """Archive a collection item by moving it to collection_archived.json."""
    try:
        collection = load_collection()
        
        if index < 0 or index >= len(collection):
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Get the item to archive
        item_to_archive = collection.pop(index)
        
        # Add timestamp to archived item
        item_to_archive['archived_at'] = datetime.now().isoformat()
        
        # Load existing archived items
        archived = load_archived_collection()
        archived.append(item_to_archive)
        
        # Save both files
        if save_collection(collection) and save_archived_collection(archived):
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
        
        collection = load_collection()
        
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
        
        if save_collection(reordered_collection):
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
async def get_archived_stats():
    """Get statistics for active collection items only (not archived)."""
    try:
        # Load only active collection
        collection = load_collection()
        
        total_cost = 0.0
        sold_count = 0
        total_sold_amount = 0.0
        total_profit = 0.0
        
        for item in collection:
            buy_price = item.get('buy_price')
            sell_price = item.get('sell_price')
            
            # Add buy_price to total cost if it exists
            if buy_price is not None:
                try:
                    buy_price_float = float(buy_price)
                    total_cost += buy_price_float
                except (ValueError, TypeError):
                    pass
            
            # Count items with sell_price > 0 as sold items and calculate profit
            if sell_price is not None:
                try:
                    sell_price_float = float(sell_price)
                    # Only count items with sell_price > 0 as sold items
                    if sell_price_float > 0:
                        sold_count += 1
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
            "total_cost": round(total_cost, 2),
            "sold_count": sold_count,
            "total_sold_amount": round(total_sold_amount, 2),
            "total_profit": round(total_profit, 2)
        })
    except Exception as e:
        return JSONResponse({
            "total_cost": 0.0,
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

