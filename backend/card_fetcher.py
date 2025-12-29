import requests
import json
import os
import re
import time
from typing import Optional, Dict, Tuple

IMAGE_DIR = "../frontend/public/card_images"
DATA_DIR = "../frontend/public/data"
CARDS_JSON = os.path.join(DATA_DIR, "cards.json")

def normalize_name(name: str) -> str:
    """Normalize for IDs (lowercase, underscores, no set code)."""
    name = re.sub(r"[',]", "", name.lower())
    name = re.sub(r"[^a-z0-9]", "_", name)
    return re.sub(r"_+", "_", name).strip("_")

def normalize_filename(name: str) -> str:
    """Normalize for filesystem (lowercase)."""
    name = name.lower()
    name = re.sub(r"[',]", "", name)
    name = re.sub(r"[^a-z0-9]", "_", name)
    return re.sub(r"_+", "_", name).strip("_")

def fetch_card_data(card_name: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Fetch card data/image from Scryfall (oldest printing)."""
    print(f"   🔎 fetch_card_data called with: '{card_name}'", flush=True)
    try:
        params = {
            "q": f'!"{card_name}"',
            "order": "released",
            "dir": "asc",
            "unique": "prints"
        }
        print(f"   🔎 Scryfall query: {params['q']}", flush=True)
        resp = requests.get("https://api.scryfall.com/cards/search", params=params, timeout=10)
        
        print(f"   🔎 Scryfall response status: {resp.status_code}", flush=True)
        if resp.status_code != 200:
            error_msg = f"Scryfall error: {resp.status_code}"
            try:
                error_data = resp.json()
                if error_data.get("object") == "error":
                    error_msg = f"Scryfall error: {error_data.get('details', error_data.get('type', 'Unknown error'))}"
                    print(f"   ❌ Scryfall API error details: {error_data}", flush=True)
            except:
                pass
            print(f"   ❌ {error_msg}", flush=True)
            return False, None, error_msg
        
        results = resp.json()
        print(f"   🔎 Scryfall response object type: {results.get('object')}", flush=True)
        print(f"   🔎 Number of results: {len(results.get('data', []))}", flush=True)
        
        if results.get("object") == "error":
            error_details = results.get("details", results.get("type", "Unknown error"))
            print(f"   ❌ Scryfall returned error object: {error_details}", flush=True)
            return False, None, f"Scryfall error: {error_details}"
        
        if not results.get("data"):
            print(f"   ❌ No data in Scryfall response", flush=True)
            return False, None, "Card not found"
        
        data = results["data"][0]
        print(f"   📅 Fetching: {data.get('name')} ({data.get('set', 'UNK').upper()})", flush=True)
        
        # Extract Image URL
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
            return False, None, "No image found"

        # Build Metadata
        name = data.get("name")
        # Use simple normalized name as ID (no set code suffix)
        card_id = normalize_name(name)
        filename = f"{normalize_filename(name)}.jpg"
        print(f"   ✅ Generated card_id: '{card_id}', filename: '{filename}'", flush=True)
        
        metadata = {
            "id": card_id,
            "name": name,
            "set": data.get("set", "").upper(),
            "set_name": data.get("set_name"),
            "image": f"/card_images/{filename}",
            "type": data.get("type_line"),
            "mana_cost": data.get("mana_cost"),
            "cmc": data.get("cmc"),
            "oracle_text": data.get("oracle_text"),
            "colors": data.get("colors"),
            "scryfall_image_url": img_url
        }
        print(f"   ✅ Successfully built metadata for '{name}'", flush=True)
        return True, metadata, None

    except requests.exceptions.Timeout:
        error_msg = "Request timeout"
        print(f"   ❌ {error_msg}", flush=True)
        return False, None, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error: {str(e)}"
        print(f"   ❌ {error_msg}", flush=True)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"   ❌ {error_msg}", flush=True)
        import traceback
        print(f"   ❌ Traceback: {traceback.format_exc()}", flush=True)
        return False, None, error_msg

def download_image(url: str, filename: str) -> bool:
    """Download image to local directory."""
    print(f"   📥 download_image called: url='{url}', filename='{filename}'", flush=True)
    try:
        os.makedirs(IMAGE_DIR, exist_ok=True)
        filepath = os.path.join(IMAGE_DIR, filename)
        print(f"   📥 Downloading to: {filepath}", flush=True)
        
        resp = requests.get(url, headers={'User-Agent': 'MWS/1.0'}, timeout=30)
        print(f"   📥 Image download response status: {resp.status_code}", flush=True)
        if resp.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(resp.content)
            file_size = os.path.getsize(filepath)
            print(f"   ✅ Image downloaded successfully ({file_size} bytes)", flush=True)
            return True
        else:
            print(f"   ❌ Image download failed with status {resp.status_code}", flush=True)
            return False
    except Exception as e:
        print(f"   ❌ Download error: {e}", flush=True)
        import traceback
        print(f"   ❌ Download traceback: {traceback.format_exc()}", flush=True)
        return False

def update_cards_json(new_card: Dict) -> bool:
    """Update the local cards.json database."""
    print(f"   💾 update_cards_json called for card_id: '{new_card.get('id')}'", flush=True)
    try:
        db = {}
        if os.path.exists(CARDS_JSON):
            with open(CARDS_JSON, 'r') as f:
                db = json.load(f)
            print(f"   💾 Loaded existing database with {len(db)} cards", flush=True)
        else:
            print(f"   💾 Database file doesn't exist, creating new one", flush=True)
        
        # Cleanup temp field
        card_data = new_card.copy()
        card_data.pop("scryfall_image_url", None)
        
        card_id = card_data["id"]
        db[card_id] = card_data
        print(f"   💾 Adding/updating card '{card_id}' in database", flush=True)
        
        with open(CARDS_JSON, 'w') as f:
            json.dump(db, f, indent=2)
        print(f"   ✅ Database updated successfully (now {len(db)} cards)", flush=True)
        return True
    except Exception as e:
        print(f"   ❌ Database update error: {e}", flush=True)
        import traceback
        print(f"   ❌ Database update traceback: {traceback.format_exc()}", flush=True)
        return False
