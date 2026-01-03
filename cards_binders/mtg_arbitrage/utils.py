"""
Utility functions and configuration for MTG arbitrage.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from config.env if it exists
load_dotenv('config.env')

# Default configuration with environment variable overrides
DEFAULT_CONFIG = {
    "target_net_margin": float(os.getenv("TARGET_NET_MARGIN", "0.12")),
    "cardmarket_fee": float(os.getenv("CARDMARKET_FEE", "0.05")),
    "price_min": float(os.getenv("PRICE_MIN", "50.0")),
    "price_max": float(os.getenv("PRICE_MAX", "120.0")),
    "trend_discount_threshold": float(os.getenv("TREND_DISCOUNT_THRESHOLD", "0.05")),  # 5% for EX+ prices
    "rank_target": int(os.getenv("RANK_TARGET", "8")),
    "undercut_buffer": float(os.getenv("UNDERCUT_BUFFER", "0.10")),
    "min_avg7": float(os.getenv("MIN_AVG7", "0.01")),
}

def get_data_dir() -> str:
    """Get the data directory path."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def get_raw_data_dir() -> str:
    """Get the raw data directory path."""
    return os.path.join(get_data_dir(), "raw")

def ensure_dir_exists(path: str) -> None:
    """Ensure a directory exists, create if it doesn't."""
    os.makedirs(path, exist_ok=True)

def calculate_min_sell_price(buy_price: float, target_margin: float, fee_rate: float) -> float:
    """
    Calculate minimum sell price to achieve target margin after fees.
    
    Formula: S_min = B(1+m) / (1-f)
    where B = buy price, m = target margin, f = fee rate
    """
    return buy_price * (1 + target_margin) / (1 - fee_rate)

def is_profitable(buy_price: float, sell_price: float, target_margin: float, fee_rate: float) -> bool:
    """Check if a buy/sell pair meets the target margin after fees."""
    net_profit = sell_price * (1 - fee_rate) - buy_price
    actual_margin = net_profit / buy_price if buy_price > 0 else 0
    return actual_margin >= target_margin

def format_currency(amount: float) -> str:
    """Format amount as EUR currency."""
    return f"€{amount:.2f}"

def format_card_name_for_url(name: str, is_expansion: bool = False) -> str:
    """
    Format a card/expansion name for use in Cardmarket URLs (Title Case).
    
    Args:
        name: The card or expansion name to format
        is_expansion: True if formatting an expansion name, False for card names
    """
    if not name or str(name) == 'nan':
        return ""
    
    import unicodedata
    
    name_str = str(name)  # Convert to string to handle NaN/float values
    
    # Remove accents (Bíff → Biff)
    nfd = unicodedata.normalize('NFD', name_str)
    name_str = ''.join(char for char in nfd if not unicodedata.combining(char))
    
    # Replace special characters but keep apostrophes for now
    formatted = name_str.replace(",", "").replace(":", "")
    formatted = formatted.replace("(", "").replace(")", "").replace("&", "and")
    formatted = formatted.replace("!", "").replace("?", "").replace("/", "-")
    
    # Split apostrophe-s into separate word for card names (Yawgmoth's Will → Yawgmoth s Will)
    # This creates: "Yawgmoth-s-Will" for cards but "Urzas-Saga" for expansions
    formatted = formatted.replace("'s ", " s ").replace("'S ", " s ")
    
    # Clean up extra spaces and convert to title case
    # Handle both spaces and hyphens to properly capitalize "Ifh-Biff"
    words = formatted.split()
    title_words = []
    for word in words:
        if word:
            # Keep single-letter 's' lowercase (for possessives)
            if word.lower() == 's':
                title_words.append('s')
            else:
                # Split on hyphens and capitalize each part
                parts = word.split('-')
                capitalized_parts = [part.capitalize() for part in parts if part]
                title_words.append('-'.join(capitalized_parts))
    
    # Join with dashes for URL format
    result = "-".join(title_words)
    
    # Handle any remaining apostrophes (at end of words or standalone)
    result = result.replace("'s", "s").replace("'S", "S").replace("'", "")
    
    # Special case for expansions: "Urza-s-Saga" → "Urzas-Saga"
    # Card names keep the hyphen: "Yawgmoth-s-Will" stays as is
    if is_expansion:
        import re
        result = re.sub(r'([A-Z][a-z]+)-([s])-([A-Z])', r'\1\2-\3', result)
    
    return result

def get_cardmarket_url(card_id: int, card_name: str = None, expansion_name: str = None, url_type: str = "direct", include_filters: bool = True) -> str:
    """
    Generate Cardmarket URLs for a card with quality and language filters.
    
    Args:
        card_id: The idProduct from Cardmarket
        card_name: The card name (optional, for better URLs)
        expansion_name: The expansion/set name (required for proper URLs)
        url_type: "direct" for direct product page, "search" for search page, "search_name" for name-based search
        include_filters: If True, adds sellerCountry=7 (Germany). Always adds language=1 (English), minCondition=3 (Excellent+)
    
    Returns:
        URL string with quality/language filters and optional country filter
    """
    if url_type == "search":
        if include_filters:
            return f"https://www.cardmarket.com/en/Magic/Products/Search?idProduct={card_id}&sellerCountry=7&language=1&minCondition=3"
        else:
            return f"https://www.cardmarket.com/en/Magic/Products/Search?idProduct={card_id}&language=1&minCondition=3"
    elif url_type == "search_name" and card_name:
        # URL encode the card name for search
        import urllib.parse
        encoded_name = urllib.parse.quote(card_name)
        if include_filters:
            return f"https://www.cardmarket.com/en/Magic/Products/Singles?searchMode=v1&idCategory=1&idExpansion=0&searchString={encoded_name}&sellerCountry=7&language=1&minCondition=3"
        else:
            return f"https://www.cardmarket.com/en/Magic/Products/Singles?searchMode=v1&idCategory=1&idExpansion=0&searchString={encoded_name}&language=1&minCondition=3"
    else:  # direct
        base_url = ""
        if expansion_name and card_name and str(expansion_name) != 'nan':
            formatted_expansion = format_card_name_for_url(expansion_name, is_expansion=True)
            formatted_card = format_card_name_for_url(card_name, is_expansion=False)
            if formatted_expansion:  # Only use expansion if we have a valid one
                base_url = f"https://www.cardmarket.com/en/Magic/Products/Singles/{formatted_expansion}/{formatted_card}"
        
        if not base_url and card_name:
            formatted_name = format_card_name_for_url(card_name, is_expansion=False)
            base_url = f"https://www.cardmarket.com/en/Magic/Products/Singles/{formatted_name}-{card_id}"
        
        if not base_url:
            base_url = f"https://www.cardmarket.com/en/Magic/Products/Singles/{card_id}"
        
        # Always add language and condition filters, optionally add country filter
        if include_filters:
            return f"{base_url}?sellerCountry=7&language=1&minCondition=3"
        else:
            return f"{base_url}?language=1&minCondition=3"

def print_card_lookup_info(card_data: dict) -> None:
    """Print lookup information for a card."""
    card_id = card_data.get('idProduct')
    card_name = card_data.get('name') or card_data.get('Name', f"Card ID {card_id}")
    expansion_name = card_data.get('expansionName')
    
    print(f"\n🔍 {card_name}")
    if expansion_name and str(expansion_name) != 'nan':
        print(f"Set: {expansion_name}")
        print(f"Direct URL: {get_cardmarket_url(card_id, card_name, expansion_name, 'direct')}")
    else:
        print(f"Set: Unknown")
        print(f"Direct URL: {get_cardmarket_url(card_id, card_name, None, 'direct')}")
    
    print(f"Search by ID: {get_cardmarket_url(card_id, card_name, expansion_name, 'search')}")
    print(f"Search by Name: {get_cardmarket_url(card_id, card_name, expansion_name, 'search_name')}")
    
    if 'LOWEX+' in card_data:
        print(f"Buy price (LOWEX+): {format_currency(card_data['LOWEX+'])}")
    if 'TREND' in card_data:
        print(f"Market trend: {format_currency(card_data['TREND'])}")
    if 'trend_discount' in card_data:
        print(f"Discount: {card_data['trend_discount']*100:.1f}%")
