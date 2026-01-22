#!/usr/bin/env python3
"""
Wishlist Management UI

A web interface for managing the MTG card wishlist.
Displays wishlist items in a card binder format, one card per set.
"""

import json
import os
import sys
import argparse
import re
import requests
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import authentication and database modules
import database
import auth

# Import card autocomplete functionality
try:
    from card_autocomplete import autocomplete_cards
except ImportError:
    autocomplete_cards = None
    print("Warning: card_autocomplete module not available", flush=True)

app = FastAPI(title="MTG Wishlist Manager", description="Wishlist Management Interface")

# Configuration
WISHLIST_FILE = "wishlist.json"
DEFAULT_PORT = 5002  # Different port from web_ui.py
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


def load_wishlist(filepath: str = WISHLIST_FILE, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load wishlist from database (if user_id provided) or JSON file (if None)."""
    if user_id is not None:
        # Load from database
        return database.get_user_wishlist(user_id)
    else:
        # Load from JSON file (backward compatibility for non-logged-in users)
        try:
            if not os.path.exists(filepath):
                return []
            with open(filepath, 'r', encoding='utf-8') as f:
                wishlist = json.load(f)
            return wishlist
        except Exception as e:
            print(f"Error loading wishlist: {e}")
            return []


def save_wishlist(wishlist: List[Dict[str, Any]], filepath: str = WISHLIST_FILE, user_id: Optional[int] = None) -> bool:
    """Save wishlist to database (if user_id provided) or JSON file (if None)."""
    if user_id is not None:
        # Save to database
        return database.save_user_wishlist(user_id, wishlist)
    else:
        # Save to JSON file (backward compatibility for non-logged-in users)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(wishlist, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving wishlist: {e}")
            return False


def load_archived_wishlist(filepath: str = "wishlist_archived.json", user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load archived wishlist from database (if user_id provided) or JSON file (if None)."""
    if user_id is not None:
        # Load archived items from database
        return database.get_archived_wishlist(user_id)
    else:
        # Load from JSON file (backward compatibility)
        try:
            if not os.path.exists(filepath):
                return []
            with open(filepath, 'r', encoding='utf-8') as f:
                archived = json.load(f)
            return archived
        except Exception as e:
            print(f"Error loading archived wishlist: {e}")
            return []


def save_archived_wishlist(archived: List[Dict[str, Any]], filepath: str = "wishlist_archived.json", user_id: Optional[int] = None) -> bool:
    """Save archived wishlist to JSON file. Note: For database users, archiving is handled directly by database.archive_wishlist_item()."""
    if user_id is not None:
        # For database users, archiving is handled by database.archive_wishlist_item()
        # This function is only used for JSON file fallback
        return True
    else:
        # Save to JSON file (backward compatibility)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(archived, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving archived wishlist: {e}")
            return False


def normalize_filename(name: str) -> str:
    """Normalize card name for filesystem filename."""
    original = name
    name = name.lower()
    name = re.sub(r"[',]", "", name)
    name = re.sub(r"[^a-z0-9]", "_", name)
    result = re.sub(r"_+", "_", name).strip("_")
    return result

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


def fetch_card_image_from_scryfall(card_name: str, set_name: Optional[str] = None) -> Optional[str]:
    """
    Fetch card image from Scryfall API and save to card_images_sets directory.
    If set_name is provided, fetches from that specific set; otherwise uses oldest printing.
    Returns the image path if successful, None otherwise.
    """
    print(f"   🔍 fetch_card_image_from_scryfall called for: '{card_name}'" + (f" (set: {set_name})" if set_name else ""), flush=True)
    try:
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
            # Try to find exact set match
            data = None
            set_name_lower = set_name.lower()
            set_code_lower = get_scryfall_set_code(set_name).lower()
            
            for card_data in results["data"]:
                card_set = card_data.get("set_name", "").lower()
                card_set_code = card_data.get("set", "").lower()
                # Match by set code (preferred) or set name
                # Special handling: International Edition maps to CEI, Collector's Edition to CED
                if (set_code_lower == card_set_code or 
                    set_name_lower in card_set or 
                    card_set in set_name_lower or  # Also check reverse contains
                    (set_name_lower == "international edition" and (card_set_code == "cei" or "intl" in card_set or "international" in card_set)) or
                    (set_name_lower == "collector's edition" and (card_set_code == "ced" or "collector" in card_set))):
                    data = card_data
                    print(f"   ✅ Matched card from {card_set_code} ({card_set})", flush=True)
                    break
            
            # If no exact match, use first result
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
        target_dir = IMAGE_DIR_SETS if set_name else IMAGE_DIR
        os.makedirs(target_dir, exist_ok=True)
        print(f"   📁 Image directory: {os.path.abspath(target_dir)}", flush=True)
        
        # Generate filename with set if provided
        filename = get_image_filename(card_name, set_name)
        filepath = os.path.join(target_dir, filename)
        print(f"   💾 Target filepath: {os.path.abspath(filepath)}", flush=True)
        
        # Check if file already exists
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            file_size = os.path.getsize(filepath)
            print(f"   ⏭️  Image already exists ({file_size} bytes), skipping download", flush=True)
            return f"/card_images_sets/{filename}" if set_name else f"/card_images/{filename}"
        
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


def expand_wishlist_to_cards(wishlist: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Expand wishlist items to show one card per set.
    Each wishlist item with multiple sets becomes multiple card entries.
    Images are fetched on-demand when requested by the browser (via /api/fetch-card-image).
    """
    cards = []
    
    for index, item in enumerate(wishlist):
        card_name = item.get('name', 'Unknown')
        sets = item.get('sets', [])
        notes = item.get('notes', '')
        max_price = item.get('max_price')
        
        # If no sets specified, create one entry with no set
        if not sets:
            cards.append({
                'name': card_name,
                'expansion': None,
                'notes': notes,
                'max_price': max_price,
                'wishlist_index': index  # Track original index for editing
            })
        else:
            # Create one card per set
            for expansion in sets:
                cards.append({
                    'name': card_name,
                    'expansion': expansion,
                    'notes': notes,
                    'max_price': max_price,
                    'wishlist_index': index  # Track original index for editing
                })
    
    return cards


@app.get("/", response_class=HTMLResponse)
async def wishlist_page():
    """Serve the wishlist management page."""
    html_path = Path("web_templates/wishlist_binder.html")
    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
            # Inject JavaScript to ensure expansion field is passed when moving to collection
            if 'move-to-collection-expansion-fix' not in html_content:
                move_script = """
    <script id="move-to-collection-expansion-fix">
    // Ensure expansion field is passed when moving wishlist items to collection
    (function() {
        'use strict';
        
        // Hook into card rendering functions to ensure expansion is stored in data attributes
        if (typeof createCardHTML === 'function') {
            const originalCreateCardHTML = window.createCardHTML;
            window.createCardHTML = function(card, cardIndex) {
                const html = originalCreateCardHTML.call(this, card, cardIndex);
                // Ensure expansion is in data attribute
                if (card.expansion) {
                    const temp = document.createElement('div');
                    temp.innerHTML = html;
                    const cardEl = temp.firstElementChild;
                    if (cardEl) {
                        cardEl.setAttribute('data-expansion', card.expansion);
                        cardEl.setAttribute('data-card-name', card.name || '');
                        return temp.innerHTML;
                    }
                }
                return html;
            };
        }
        
        // Also hook into any function that renders cards
        const cardRenderers = ['renderCard', 'displayCard', 'showCard', 'createCard'];
        cardRenderers.forEach(funcName => {
            if (typeof window[funcName] === 'function') {
                const original = window[funcName];
                window[funcName] = function(...args) {
                    const result = original.apply(this, args);
                    // If result is HTML string or element, ensure expansion is in data attribute
                    if (typeof result === 'string' && result.includes('expansion')) {
                        const temp = document.createElement('div');
                        temp.innerHTML = result;
                        const cardEl = temp.querySelector('[data-expansion], .card, [class*="card"]');
                        if (cardEl && args[0] && args[0].expansion) {
                            cardEl.setAttribute('data-expansion', args[0].expansion);
                        }
                        return temp.innerHTML;
                    }
                    return result;
                };
            }
        });
        
        // Store expansion whenever user interacts with a card
        // This ensures we always have the expansion available when move button is clicked
        document.addEventListener('click', function(e) {
            let target = e.target;
            let cardElement = null;
            
            // First check if the clicked element itself has expansion data
            if (target.dataset && target.dataset.cardExpansion) {
                window._pendingMoveExpansion = target.dataset.cardExpansion;
                window._lastClickedExpansion = target.dataset.cardExpansion;
                console.log('Found expansion on clicked element:', target.dataset.cardExpansion);
                return;
            }
            
            // Find the card element by walking up the DOM tree
            let current = target;
            let depth = 0;
            while (current && current !== document && depth < 15) {
                // Check if current element is a button with expansion data
                if (current.dataset && current.dataset.cardExpansion) {
                    window._pendingMoveExpansion = current.dataset.cardExpansion;
                    window._lastClickedExpansion = current.dataset.cardExpansion;
                    console.log('Found expansion on button:', current.dataset.cardExpansion);
                    return;
                }
                
                // Check for card indicators
                if (current.dataset && (current.dataset.expansion || current.dataset.cardName)) {
                    cardElement = current;
                    break;
                }
                // Check for card-like classes
                if (current.className && (
                    current.className.includes('card') || 
                    current.className.includes('Card') ||
                    current.classList.contains('card')
                )) {
                    cardElement = current;
                    break;
                }
                current = current.parentElement;
                depth++;
            }
            
            // Try to extract expansion from card element
            if (cardElement) {
                let expansion = null;
                
                // Method 1: Check data-expansion attribute
                if (cardElement.dataset && cardElement.dataset.expansion) {
                    expansion = cardElement.dataset.expansion;
                }
                
                // Method 2: Check for data-expansion in child elements
                if (!expansion) {
                    const expansionEl = cardElement.querySelector('[data-expansion]');
                    if (expansionEl && expansionEl.dataset.expansion) {
                        expansion = expansionEl.dataset.expansion;
                    }
                }
                
                // Method 3: Extract from text content (look for expansion names)
                if (!expansion) {
                    const cardText = cardElement.textContent || '';
                    // Common expansion patterns
                    const expansionPatterns = [
                        /(Fourth Edition)/i,
                        /(Antiquities)/i,
                        /(Alpha)/i,
                        /(Beta)/i,
                        /(Unlimited Edition)/i,
                        /(Revised Edition)/i,
                        /(International Edition)/i,
                        /([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+Edition)?)/i
                    ];
                    
                    for (const pattern of expansionPatterns) {
                        const match = cardText.match(pattern);
                        if (match && match[1]) {
                            expansion = match[1].trim();
                            break;
                        }
                    }
                }
                
                // Store expansion if found
                if (expansion && expansion !== 'null' && expansion !== 'undefined' && expansion !== '') {
                    window._lastClickedExpansion = expansion;
                    window._pendingMoveExpansion = expansion;
                    console.log('Stored expansion from card click:', expansion);
                    
                    // Clear after delay
                    setTimeout(() => {
                        if (window._pendingMoveExpansion === expansion) {
                            delete window._pendingMoveExpansion;
                        }
                    }, 5000);
                }
            }
        }, true); // Use capture phase
        
        // Intercept fetch calls to add expansion field to move-to-collection requests
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const url = args[0];
            const options = args[1] || {};
            
            // Handle move-to-collection requests
            if (typeof url === 'string' && url.includes('/move-to-collection') && options.method === 'POST') {
                let expansion = window._pendingMoveExpansion || window._lastClickedExpansion;
                
                // If still not found, try to extract from URL or find in DOM
                if (!expansion) {
                    // Try to find the card that was just clicked
                    const allCards = document.querySelectorAll('[data-expansion], [data-card-name]');
                    for (const card of allCards) {
                        if (card.dataset && card.dataset.expansion) {
                            expansion = card.dataset.expansion;
                            break;
                        }
                    }
                }
                
                // If expansion found, add it to the request
                if (expansion && expansion !== 'null' && expansion !== 'undefined' && expansion !== '') {
                    console.log('✅ Adding expansion to move-to-collection request:', expansion);
                    if (options.body) {
                        try {
                            const body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body;
                            // Always override if we have expansion
                            body.expansion = expansion;
                            options.body = JSON.stringify(body);
                            args[1] = options;
                            console.log('✅ Updated request body:', body);
                        } catch(e) {
                            console.error('❌ Error adding expansion to move-to-collection request:', e);
                        }
                    } else {
                        // Create body with expansion if it doesn't exist
                        options.body = JSON.stringify({ expansion: expansion });
                        args[1] = options;
                    }
                } else {
                    console.warn('⚠️ No expansion found for move-to-collection request. Available:', {
                        pending: window._pendingMoveExpansion,
                        lastClicked: window._lastClickedExpansion
                    });
                }
            }
            
            return originalFetch.apply(this, args);
        };
        
        // Also intercept XMLHttpRequest in case frontend uses that instead of fetch
        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalXHRSend = XMLHttpRequest.prototype.send;
        
        XMLHttpRequest.prototype.open = function(method, url, ...rest) {
            this._url = url;
            this._method = method;
            return originalXHROpen.apply(this, [method, url, ...rest]);
        };
        
        XMLHttpRequest.prototype.send = function(body) {
            if (this._url && this._url.includes('/move-to-collection') && this._method === 'POST') {
                let expansion = window._pendingMoveExpansion || window._lastClickedExpansion;
                
                if (expansion && expansion !== 'null' && expansion !== 'undefined' && expansion !== '') {
                    console.log('✅ Adding expansion to XMLHttpRequest move-to-collection:', expansion);
                    try {
                        const requestBody = body ? (typeof body === 'string' ? JSON.parse(body) : body) : {};
                        requestBody.expansion = expansion;
                        body = JSON.stringify(requestBody);
                        console.log('✅ Updated XMLHttpRequest body:', requestBody);
                    } catch(e) {
                        console.error('❌ Error adding expansion to XMLHttpRequest:', e);
                    }
                }
            }
            return originalXHRSend.apply(this, [body]);
        };
        
        // Watch for dynamically added move buttons and ensure they capture expansion
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        // Find move buttons in the added node
                        const moveButtons = node.querySelectorAll ? node.querySelectorAll(
                            'button, a, [onclick], [data-action], [class*="move"], [id*="move"]'
                        ) : [];
                        moveButtons.forEach(function(button) {
                            if (button.textContent && button.textContent.toLowerCase().includes('move')) {
                                // Find the card this button belongs to
                                const cardElement = button.closest('[data-expansion], [data-card-name], .card, [class*="card"]');
                                if (cardElement && cardElement.dataset && cardElement.dataset.expansion) {
                                    // Store expansion for this button
                                    button.setAttribute('data-card-expansion', cardElement.dataset.expansion);
                                    console.log('Tagged move button with expansion:', cardElement.dataset.expansion);
                                }
                            }
                        });
                    }
                });
            });
        });
        
        // Start observing
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // Also check existing buttons on page load
        setTimeout(function() {
            const existingButtons = document.querySelectorAll('button, a, [onclick], [data-action]');
            existingButtons.forEach(function(button) {
                if (button.textContent && button.textContent.toLowerCase().includes('move')) {
                    const cardElement = button.closest('[data-expansion], [data-card-name], .card, [class*="card"]');
                    if (cardElement && cardElement.dataset && cardElement.dataset.expansion) {
                        button.setAttribute('data-card-expansion', cardElement.dataset.expansion);
                    }
                }
            });
        }, 1000);
    })();
    </script>
"""
                # Inject JavaScript to safely handle form submissions and fix null reference errors
                if 'form-submission-fix' not in html_content:
                    form_fix_script = """
    <script id="form-submission-fix">
    // Safely handle form submissions for adding cards to wishlist
    // Fixes "Cannot read properties of null (reading 'value')" errors
    (function() {
        'use strict';
        
        // Intercept form submissions BEFORE they reach the original handler
        // This prevents null reference errors by handling submission ourselves
        document.addEventListener('submit', function(e) {
            const form = e.target;
            if (!form || form.tagName !== 'FORM') return;
            
            // Check if this is the add card form
            const formId = form.id || '';
            const formClass = form.className || '';
            const formAction = form.action || '';
            const formText = form.textContent || '';
            
                    // Skip auth forms - they have their own handler
                    if (formId === 'authForm' || formClass.includes('auth')) {
                        return; // Let auth form handle itself
                    }
                    
                    if (formText.includes('ADD CARD') || formText.includes('WISHLIST') || 
                        formId.includes('card') || formClass.includes('card') || 
                        (formAction.includes('wishlist') && !formAction.includes('/api/auth'))) {
                
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                
                try {
                    // Find form fields with multiple possible selectors
                    const cardNameSelectors = [
                        '[name="name"]',
                        '[name="card-name"]',
                        '[id*="card-name"]',
                        '[id*="name"]',
                        'input[type="text"]:not([type="hidden"])',
                        'input:first-of-type'
                    ];
                    
                    let cardNameField = null;
                    for (const selector of cardNameSelectors) {
                        const fields = form.querySelectorAll(selector);
                        for (const field of fields) {
                            // Skip hidden fields and buttons
                            if (field.type !== 'hidden' && field.type !== 'submit' && field.type !== 'button') {
                                cardNameField = field;
                                break;
                            }
                        }
                        if (cardNameField) break;
                    }
                    
                    if (!cardNameField) {
                        console.error('❌ Card name field not found. Available fields:', 
                            Array.from(form.querySelectorAll('input, select, textarea')).map(el => ({
                                name: el.name || el.id || 'unnamed',
                                type: el.type || el.tagName,
                                value: el.value || '',
                                visible: el.offsetParent !== null
                            }))
                        );
                        alert('Error: Could not find card name field. Please check the form.');
                        return false;
                    }
                    
                    const cardName = cardNameField.value ? cardNameField.value.trim() : '';
                    if (!cardName) {
                        alert('Please enter a card name.');
                        return false;
                    }
                    
                    // Find sets field - look for select elements or hidden inputs with sets
                    let sets = [];
                    const setsSelectors = [
                        'select[name="sets"]',
                        'select[name="set"]',
                        '[name="sets"]',
                        '[name="set"]',
                        'select',
                        'input[type="hidden"][name*="set"]'
                    ];
                    
                    let setsField = null;
                    for (const selector of setsSelectors) {
                        setsField = form.querySelector(selector);
                        if (setsField) break;
                    }
                    
                    if (setsField) {
                        if (setsField.tagName === 'SELECT') {
                            // Get selected options or all options if multiple select
                            const selected = Array.from(setsField.selectedOptions || []);
                            sets = selected.map(opt => opt.value || opt.textContent).filter(v => v);
                            
                            // If no selection, check for data attributes or tags
                            if (sets.length === 0) {
                                // Look for selected tags/chips
                                const tags = form.querySelectorAll('[data-set], [data-expansion], .tag, .chip');
                                sets = Array.from(tags).map(tag => {
                                    return tag.dataset.set || tag.dataset.expansion || tag.textContent.trim();
                                }).filter(v => v);
                            }
                        } else if (setsField.value) {
                            // Try to parse as JSON or comma-separated
                            try {
                                sets = JSON.parse(setsField.value);
                            } catch(e) {
                                sets = setsField.value.split(',').map(s => s.trim()).filter(s => s);
                            }
                        }
                    }
                    
                    // Also check for sets in tags/chips if not found yet
                    if (sets.length === 0) {
                        const tags = form.querySelectorAll('[data-set], [data-expansion], .tag, .chip, [class*="tag"]');
                        sets = Array.from(tags).map(tag => {
                            return tag.dataset.set || tag.dataset.expansion || tag.textContent.trim();
                        }).filter(v => v);
                    }
                    
                    console.log('✅ Form submission intercepted:', { cardName, sets });
                    
                    // Submit via fetch instead of form submission
                    const apiUrl = '/wishlist/api/wishlist';
                    fetch(apiUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            name: cardName,
                            sets: sets
                        })
                    })
                    .then(response => {
                        if (!response.ok) {
                            return response.json().then(err => Promise.reject(err));
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log('✅ Card added successfully:', data);
                        // Close modal if it exists
                        const modal = form.closest('.modal, [class*="modal"], [id*="modal"]');
                        if (modal) {
                            const closeBtn = modal.querySelector('[class*="close"], [aria-label*="close"], button:last-child');
                            if (closeBtn) closeBtn.click();
                        }
                        // Reload page or refresh cards
                        if (typeof window.loadCards === 'function') {
                            window.loadCards();
                        } else if (typeof window.location !== 'undefined') {
                            window.location.reload();
                        }
                    })
                    .catch(error => {
                        console.error('❌ Error adding card:', error);
                        alert('Error adding card: ' + (error.detail || error.message || 'Unknown error'));
                    });
                    
                    return false;
                } catch(error) {
                    console.error('❌ Error in form submission handler:', error);
                    console.error('   Stack:', error.stack);
                    alert('Error processing form: ' + error.message);
                    return false;
                }
            }
        }, true); // Use capture phase to intercept before other handlers
        
        // Form fix function - no-op since form handling is done via event listener above
        function initFormFix() {
            // Form submission is handled by the 'submit' event listener above
            // This function exists for compatibility with the MutationObserver calls
            console.log('Form fix initialized');
        }
        
        // Run immediately and after DOM loads
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initFormFix);
        } else {
            initFormFix();
        }
        
        // Also watch for dynamically added forms
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && (node.tagName === 'FORM' || node.querySelector('form'))) {
                        setTimeout(initFormFix, 100);
                    }
                });
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
        
        // Global error handler to catch null reference errors
        window.addEventListener('error', function(e) {
            if (e.message && e.message.includes('Cannot read properties of null') && e.message.includes('value')) {
                console.error('❌ Null reference error caught:', e.message);
                console.error('   File:', e.filename, 'Line:', e.lineno);
                console.error('   Stack:', e.error ? e.error.stack : 'No stack trace');
                
                // Try to find the problematic form
                const forms = document.querySelectorAll('form');
                forms.forEach((form, idx) => {
                    console.log(`Form ${idx}:`, {
                        id: form.id,
                        className: form.className,
                        action: form.action,
                        fields: Array.from(form.querySelectorAll('input, select, textarea')).map(el => ({
                            name: el.name || el.id || 'unnamed',
                            type: el.type || el.tagName,
                            value: el.value || '(empty)'
                        }))
                    });
                });
            }
        }, true);
    })();
    </script>
"""
                    # Inject before closing body tag
                    if '</body>' in html_content:
                        html_content = html_content.replace('</body>', form_fix_script + '\n</body>')
                    elif '</html>' in html_content:
                        html_content = html_content.replace('</html>', form_fix_script + '\n</html>')
                    else:
                        html_content += form_fix_script
                
                # Inject before closing body tag
                if '</body>' in html_content:
                    html_content = html_content.replace('</body>', move_script + '\n</body>')
                elif '</html>' in html_content:
                    html_content = html_content.replace('</html>', move_script + '\n</html>')
                else:
                    html_content += move_script
            
            # Inject CSS for header flexbox layout (for auth section)
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
                print("🔐 Injecting authentication UI into wishlist HTML template", flush=True)
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
                    print("✅ Authentication UI injected into wishlist header", flush=True)
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
                print("🔐 Injecting authentication JavaScript into wishlist", flush=True)
                auth_script = """
    <script id="auth-script">
        // Authentication functions for wishlist
        let isLoginMode = true;
        let isCheckingAuth = false;  // Prevent duplicate auth checks
        let wishlistReloadScheduled = false;  // Prevent duplicate wishlist reloads

        async function checkAuthStatus() {
            // Prevent duplicate calls
            if (isCheckingAuth) {
                console.log('Auth check already in progress, skipping...');
                return;
            }
            isCheckingAuth = true;
            try {
                const apiPath = window.location.pathname.includes('/wishlist') ? '/wishlist/api/auth/me' : '/api/auth/me';
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
                const apiPath = window.location.pathname.includes('/wishlist') 
                    ? `/wishlist/api/auth/${endpoint}` 
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
                    // Reload the page to show user's wishlist
                    console.log('Login successful, reloading page...');
                    setTimeout(() => {
                        window.location.reload();
                    }, 100);
                    return;
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
                const apiPath = window.location.pathname.includes('/wishlist') 
                    ? '/wishlist/api/auth/logout' 
                    : '/api/auth/logout';
                
                await fetch(apiPath, {
                    method: 'POST',
                    credentials: 'include'
                });
                
                // Reload the page to show shared wishlist
                console.log('Logout successful, reloading page...');
                setTimeout(() => {
                    window.location.reload();
                }, 100);
            } catch (error) {
                console.error('Error logging out:', error);
            }
        }

        // Intercept fetch requests to reload wishlist after adding/updating/deleting cards
        if (!window._wishlistReloadIntercepted) {
            window._wishlistReloadIntercepted = true;
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                const url = args[0];
                const options = args[1] || {};
                
                // Intercept POST/PUT/DELETE to /api/wishlist
                if (typeof url === 'string' && 
                    (url.includes('/api/wishlist') || url.includes('/wishlist/api/wishlist')) &&
                    (options.method === 'POST' || options.method === 'PUT' || options.method === 'DELETE')) {
                    
                    return originalFetch.apply(this, args).then(async response => {
                        // Check if request was successful
                        if (response.ok) {
                            try {
                                const data = await response.clone().json();
                                if (data.success) {
                                    console.log('✅ Wishlist operation successful, reloading...');
                                    // Reload wishlist after a short delay
                                    setTimeout(() => {
                                        if (typeof loadCards === 'function' && document.readyState === 'complete' && !wishlistReloadScheduled) {
                                            wishlistReloadScheduled = true;
                                            console.log('🔄 Reloading wishlist after card operation...');
                                            loadCards();
                                            setTimeout(() => {
                                                wishlistReloadScheduled = false;
                                            }, 1000);
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
        
        // Also check on window load
        let authCheckedOnLoad = false;
        window.addEventListener('load', function() {
            if (authCheckedOnLoad) return;
            authCheckedOnLoad = true;
            
            setTimeout(function() {
                checkAuthStatus();
                // Ensure modal is closed if user is authenticated
                const modal = document.getElementById('authModal');
                if (modal && modal.style.display === 'flex') {
                    fetch(window.location.pathname.includes('/wishlist') ? '/wishlist/api/auth/me' : '/api/auth/me', { 
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
            const storedPage = localStorage.getItem('wishlist_current_page');
            if (storedPage) {
                return parseInt(storedPage, 10);
            }
            
            return 1; // Default to page 1
        }
        
        function setCurrentPage(page) {
            localStorage.setItem('wishlist_current_page', page.toString());
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
            const storedPage = localStorage.getItem('wishlist_current_page');
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
        
        // Intercept wishlist update/save operations to store page
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const url = args[0];
            const options = args[1] || {};
            
            // Before PUT/POST to wishlist API, store current page
            if (typeof url === 'string' && url.includes('/api/wishlist') && (options.method === 'PUT' || options.method === 'POST')) {
                updateStoredPage();
                
                // After successful save, restore page
                return originalFetch.apply(this, args).then(response => {
                    if (response.ok) {
                        const storedPage = localStorage.getItem('wishlist_current_page');
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
            if (this._url && this._url.includes('/api/wishlist') && (this._method === 'PUT' || this._method === 'POST')) {
                updateStoredPage();
                
                const originalOnReadyStateChange = this.onreadystatechange;
                this.onreadystatechange = function() {
                    if (this.readyState === 4 && this.status >= 200 && this.status < 300) {
                        const storedPage = localStorage.getItem('wishlist_current_page');
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
            
            return HTMLResponse(content=html_content)
    else:
        return HTMLResponse(content="<h1>Wishlist Binder Template Not Found</h1>", status_code=404)


@app.get("/api/wishlist")
async def get_wishlist(request: Request):
    """Get the full wishlist."""
    user_id = auth.get_current_user(request)
    wishlist = load_wishlist(user_id=user_id)
    return JSONResponse({"wishlist": wishlist})


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


@app.get("/api/wishlist-cards")
async def get_wishlist_cards(request: Request):
    """Get wishlist expanded to cards (one per set). Automatically fetches missing images."""
    user_id = auth.get_current_user(request)
    wishlist = load_wishlist(user_id=user_id)
    cards = expand_wishlist_to_cards(wishlist)
    return JSONResponse({"cards": cards, "total": len(cards)})


@app.post("/api/wishlist")
async def add_wishlist_item(request: Request):
    """Add a new item to the wishlist."""
    try:
        data = await request.json()
        user_id = auth.get_current_user(request)
        
        # Validate required fields
        if 'name' not in data:
            raise HTTPException(status_code=400, detail="Missing 'name' field")
        
        # Create new item
        new_item = {
            'name': data['name'],
            'sets': data.get('sets', []),
            'notes': data.get('notes', ''),
        }
        
        # If logged in, add directly to database
        if user_id is not None:
            item_id = database.add_wishlist_item(user_id, new_item)
            if item_id is None:
                raise HTTPException(status_code=500, detail="Failed to add item to wishlist")
            return JSONResponse({"success": True, "message": "Item added successfully"})
        
        # If not logged in, use JSON file (backward compatibility)
        wishlist = load_wishlist(user_id=user_id)
        wishlist.append(new_item)
        
        if save_wishlist(wishlist, user_id=user_id):
            return JSONResponse({"success": True, "message": "Item added successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to save wishlist")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/wishlist/{index}")
async def update_wishlist_item(index: int, request: Request):
    """Update a wishlist item by index."""
    try:
        data = await request.json()
        user_id = auth.get_current_user(request)
        wishlist = load_wishlist(user_id=user_id)
        
        if index < 0 or index >= len(wishlist):
            raise HTTPException(status_code=404, detail="Item not found")
        
        # If logged in, update in database using item ID
        if user_id is not None:
            item = wishlist[index]
            item_id = item.get("id")
            if item_id is None:
                raise HTTPException(status_code=404, detail="Item ID not found")
            
            # Build update data
            update_data = {}
            if 'name' in data:
                update_data['name'] = data['name']
            if 'sets' in data:
                update_data['sets'] = data['sets']
            if 'notes' in data:
                update_data['notes'] = data['notes']
            
            if not database.update_wishlist_item(user_id, item_id, update_data):
                raise HTTPException(status_code=500, detail="Failed to update item in database")
            return JSONResponse({"success": True, "message": "Item updated successfully"})
        
        # If not logged in, use JSON file (backward compatibility)
        if 'name' in data:
            wishlist[index]['name'] = data['name']
        if 'sets' in data:
            wishlist[index]['sets'] = data['sets']
        if 'notes' in data:
            wishlist[index]['notes'] = data['notes']
        if 'max_price' in data:
            wishlist[index]['max_price'] = data['max_price']
        elif 'max_price' in wishlist[index] and data.get('max_price') is None:
            del wishlist[index]['max_price']
        
        if save_wishlist(wishlist, user_id=user_id):
            return JSONResponse({"success": True, "message": "Item updated successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to save wishlist")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/wishlist/{index}")
async def archive_wishlist_item(index: int, request: Request):
    """Archive a wishlist item by setting archived=1 in database or moving to wishlist_archived.json."""
    try:
        user_id = auth.get_current_user(request)
        wishlist = load_wishlist(user_id=user_id)
        
        if index < 0 or index >= len(wishlist):
            raise HTTPException(status_code=404, detail="Item not found")
        
        # If logged in, archive in database using item ID
        if user_id is not None:
            item = wishlist[index]
            item_id = item.get("id")
            if item_id is None:
                raise HTTPException(status_code=404, detail="Item ID not found")
            
            if not database.archive_wishlist_item(user_id, item_id):
                raise HTTPException(status_code=500, detail="Failed to archive item in database")
            
            return JSONResponse({
                "success": True, 
                "message": "Item archived successfully",
                "archived_item": item
            })
        
        # If not logged in, use JSON file (backward compatibility)
        # Get the item to archive
        item_to_archive = wishlist.pop(index)
        
        # Add timestamp to archived item
        item_to_archive['archived_at'] = datetime.now().isoformat()
        
        # Load existing archived items
        archived = load_archived_wishlist(user_id=user_id)
        archived.append(item_to_archive)
        
        # Save both files
        if save_wishlist(wishlist, user_id=user_id) and save_archived_wishlist(archived, user_id=user_id):
            return JSONResponse({
                "success": True, 
                "message": "Item archived successfully",
                "archived_item": item_to_archive
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save wishlist or archive")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/wishlist/{index}/move-to-collection")
async def move_wishlist_to_collection(index: int, request: Request):
    """Move a wishlist item (or specific set from a wishlist item) to collection (when buying it)."""
    try:
        data = await request.json()
        user_id = auth.get_current_user(request)
        
        # Load wishlist
        wishlist = load_wishlist(user_id=user_id)
        
        if index < 0 or index >= len(wishlist):
            raise HTTPException(status_code=404, detail="Wishlist item not found")
        
        # Get the item to move
        wishlist_item = wishlist[index]
        
        # Check if a specific expansion/set is provided
        selected_expansion = data.get('expansion') or data.get('set')
        all_sets = wishlist_item.get('sets', [])
        
        # Log for debugging
        print(f"   🔍 Move to collection request:", flush=True)
        print(f"      Card: {wishlist_item.get('name')}", flush=True)
        print(f"      All sets in wishlist item: {all_sets}", flush=True)
        print(f"      Selected expansion from request: {selected_expansion}", flush=True)
        print(f"      Request data keys: {list(data.keys())}", flush=True)
        print(f"      User ID: {user_id}", flush=True)
        
        # Create collection item with only the selected set(s)
        if selected_expansion:
            # Move only the selected set
            if selected_expansion not in all_sets:
                raise HTTPException(status_code=400, detail=f"Set '{selected_expansion}' not found in wishlist item")
            sets_to_move = [selected_expansion]
        else:
            # No specific set selected, move all sets (original behavior)
            sets_to_move = all_sets
        
        collection_item = {
            'name': wishlist_item.get('name'),
            'sets': sets_to_move
        }
        
        # Add optional collection fields if provided
        if 'buy_price' in data and data['buy_price']:
            collection_item['buy_price'] = data['buy_price']
            # Automatically set purchase_date if buy_price is provided
            if 'purchase_date' in data and data['purchase_date']:
                collection_item['purchase_date'] = data['purchase_date']
            else:
                # Default to current date if buy_price is set but no date provided
                collection_item['purchase_date'] = datetime.now().strftime('%Y-%m-%d')
        if 'condition' in data and data['condition']:
            collection_item['condition'] = data['condition']
        if 'source' in data and data['source']:
            collection_item['source'] = data['source']
        if 'sell_price' in data and data['sell_price']:
            collection_item['sell_price'] = data['sell_price']
            # Automatically set sale_date if sell_price is provided
            if 'sale_date' in data and data['sale_date']:
                collection_item['sale_date'] = data['sale_date']
            else:
                # Default to current date if sell_price is set but no date provided
                collection_item['sale_date'] = datetime.now().strftime('%Y-%m-%d')
        if 'notes' in data and data['notes']:
            collection_item['notes'] = data['notes']
        if 'language' in data and data['language']:
            collection_item['language'] = data['language']
        if 'foil' in data:
            collection_item['foil'] = bool(data['foil'])
        
        # Add timestamp
        collection_item['added_at'] = datetime.now().isoformat()
        collection_item['moved_from_wishlist'] = True
        
        # Handle database vs JSON file operations
        if user_id is not None:
            # Database operations for logged-in users
            wishlist_item_id = wishlist_item.get("id")
            if wishlist_item_id is None:
                raise HTTPException(status_code=404, detail="Wishlist item ID not found")
            
            if selected_expansion and len(all_sets) > 1:
                # Remove the selected set from wishlist item, keep others
                remaining_sets = [s for s in all_sets if s != selected_expansion]
                if not database.update_wishlist_item(user_id, wishlist_item_id, {"sets": remaining_sets}):
                    raise HTTPException(status_code=500, detail="Failed to update wishlist item")
            else:
                # Archive the entire wishlist item
                if not database.archive_wishlist_item(user_id, wishlist_item_id):
                    raise HTTPException(status_code=500, detail="Failed to archive wishlist item")
            
            # Add to collection in database
            collection_item_id = database.add_collection_item(user_id, collection_item)
            if collection_item_id is None:
                raise HTTPException(status_code=500, detail="Failed to add item to collection")
            
            return JSONResponse({
                "success": True,
                "message": "Card moved to collection successfully",
                "collection_item": collection_item
            })
        
        # JSON file operations for non-logged-in users (backward compatibility)
        # Determine which set(s) to move
        if selected_expansion:
            # Remove the selected set from wishlist item
            remaining_sets = [s for s in all_sets if s != selected_expansion]
            
            # If there are remaining sets, update the wishlist item; otherwise remove it
            if remaining_sets:
                wishlist[index]['sets'] = remaining_sets
                item_to_archive = wishlist_item.copy()
                item_to_archive['sets'] = [selected_expansion]  # Archive only the moved set
            else:
                # No remaining sets, remove the entire item from wishlist
                item_to_archive = wishlist.pop(index)
        else:
            # No specific set selected, move all sets (original behavior)
            item_to_archive = wishlist.pop(index)
        
        # Load collection
        collection_file = "collection.json"
        collection = []
        if os.path.exists(collection_file):
            with open(collection_file, 'r', encoding='utf-8') as f:
                collection = json.load(f)
        
        # Add to collection
        collection.append(collection_item)
        
        # Archive the moved wishlist item (or part of it)
        archived = load_archived_wishlist(user_id=user_id)
        item_to_archive['archived_at'] = datetime.now().isoformat()
        item_to_archive['moved_to_collection'] = True
        archived.append(item_to_archive)
        
        # Save all files
        if not save_wishlist(wishlist, user_id=user_id):
            raise HTTPException(status_code=500, detail="Failed to save wishlist")
        
        if not save_archived_wishlist(archived, user_id=user_id):
            raise HTTPException(status_code=500, detail="Failed to save archived wishlist")
        
        with open(collection_file, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        
        return JSONResponse({
            "success": True,
            "message": "Card moved to collection successfully",
            "collection_item": collection_item
        })
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
async def fetch_card_image(name: str, set: Optional[str] = None):
    """Fetch card image from Scryfall if it doesn't exist locally. Supports set-specific fetching."""
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
        
        # Fetch from Scryfall (with set if provided)
        image_path = fetch_card_image_from_scryfall(name, set)
        
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
            error_msg = str(e).lower()
            if "no such table" in error_msg:
                raise HTTPException(status_code=500, detail="Database not initialized. Please restart the server.")
            else:
                raise HTTPException(status_code=500, detail=f"Database error: {e}")
        
        if user_id is None:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Create session token
        token = auth.create_session_token(user_id)
        response = JSONResponse({"success": True, "message": "Registration successful", "username": username})
        response.set_cookie(
            key=auth.SESSION_COOKIE_NAME,
            value=token,
            max_age=auth.SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/"
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
            path="/"
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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


def main():
    """Run the wishlist UI server."""
    parser = argparse.ArgumentParser(description="MTG Wishlist Management UI")
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
    print(f"\n🎴 MTG Wishlist Manager")
    print(f"=" * 60)
    print(f"📋 Wishlist file: {WISHLIST_FILE}")
    print(f"🌐 Server starting on http://{args.host}:{args.port}")
    print(f"=" * 60)
    
    try:
        uvicorn.run(
            "wishlist_ui:app",
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

