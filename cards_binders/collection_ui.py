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
                    'collection_index': index  # Track original index for editing
                })
    
    return cards


@app.get("/", response_class=HTMLResponse)
async def collection_page():
    """Serve the collection management page."""
    html_path = Path("web_templates/collection_binder.html")
    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
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

