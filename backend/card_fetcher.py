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
    """Normalize for filesystem (Preserve Case)."""
    name = re.sub(r"[',]", "", name)
    name = re.sub(r"[^a-zA-Z0-9]", "_", name)
    return re.sub(r"_+", "_", name).strip("_")

def fetch_card_data(card_name: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Fetch card data/image from Scryfall (oldest printing)."""
    try:
        params = {
            "q": f'!"{card_name}"',
            "order": "released",
            "dir": "asc",
            "unique": "prints"
        }
        resp = requests.get("https://api.scryfall.com/cards/search", params=params, timeout=10)
        
        if resp.status_code != 200:
            return False, None, f"Scryfall error: {resp.status_code}"
        
        results = resp.json()
        if results.get("object") == "error" or not results.get("data"):
            return False, None, "Card not found"
        
        data = results["data"][0]
        print(f"   📅 Fetching: {data.get('name')} ({data.get('set', 'UNK').upper()})")
        
        # Extract Image URL
        img_url = None
        if "image_uris" in data:
            img_url = data["image_uris"].get("large") or data["image_uris"].get("normal")
        elif "card_faces" in data:
            face = data["card_faces"][0]
            if "image_uris" in face:
                img_url = face["image_uris"].get("large") or face["image_uris"].get("normal")
        
        if not img_url:
            return False, None, "No image found"

        # Build Metadata
        name = data.get("name")
        # Use simple normalized name as ID (no set code suffix)
        card_id = normalize_name(name)
        filename = f"{normalize_filename(name)}.jpg"
        
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
        return True, metadata, None

    except Exception as e:
        return False, None, str(e)

def download_image(url: str, filename: str) -> bool:
    """Download image to local directory."""
    try:
        os.makedirs(IMAGE_DIR, exist_ok=True)
        filepath = os.path.join(IMAGE_DIR, filename)
        
        resp = requests.get(url, headers={'User-Agent': 'MWS/1.0'}, timeout=30)
        if resp.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(resp.content)
            return True
        return False
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False

def update_cards_json(new_card: Dict) -> bool:
    """Update the local cards.json database."""
    try:
        db = {}
        if os.path.exists(CARDS_JSON):
            with open(CARDS_JSON, 'r') as f:
                db = json.load(f)
        
        # Cleanup temp field
        card_data = new_card.copy()
        card_data.pop("scryfall_image_url", None)
        
        db[card_data["id"]] = card_data
        
        with open(CARDS_JSON, 'w') as f:
            json.dump(db, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Database update error: {e}")
        return False
