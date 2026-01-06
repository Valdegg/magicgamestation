"""
Utility functions and configuration for MTG arbitrage.
"""

import os
from typing import Dict, Any, Optional
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

def map_condition_to_cardmarket_code(condition: str) -> int:
    """
    Map collection condition names to Cardmarket condition codes.
    
    Cardmarket condition codes:
    1 = Mint (MT)
    2 = Near Mint (NM)
    3 = Excellent (EX)
    4 = Good (GD)
    5 = Lightly Played (LP)
    6 = Played (PL)
    7 = Poor (PO)
    
    Args:
        condition: Condition string from collection (e.g., "Near Mint", "Excellent", "Poor (inked)")
    
    Returns:
        Cardmarket condition code (defaults to 3 = Excellent if not recognized)
    """
    if not condition:
        return 3  # Default to Excellent
    
    condition_lower = condition.lower().strip()
    
    # Map common condition names
    if 'mint' in condition_lower and 'near' not in condition_lower:
        return 1  # Mint
    elif 'near mint' in condition_lower or 'nm' in condition_lower:
        return 2  # Near Mint
    elif 'excellent' in condition_lower or 'ex' in condition_lower:
        return 3  # Excellent
    elif 'good' in condition_lower or 'gd' in condition_lower:
        return 4  # Good
    elif 'lightly played' in condition_lower or 'lp' in condition_lower:
        return 5  # Lightly Played
    elif 'played' in condition_lower and 'lightly' not in condition_lower or 'pl' in condition_lower:
        return 6  # Played
    elif 'poor' in condition_lower or 'po' in condition_lower:
        return 7  # Poor
    else:
        return 3  # Default to Excellent if not recognized


def get_cardmarket_language_code(language: str = None) -> int:
    """
    Map language name to Cardmarket language code.
    
    Cardmarket language codes:
    - English (default): 1
    - French: 2
    - German: 3
    - Spanish: 4
    - Italian: 5
    
    Args:
        language: Language name (e.g., "Italian", "French", "Spanish", "German")
    
    Returns:
        Language code (1-5), defaults to 1 (English) if not specified or unknown
    """
    if not language:
        return 1  # Default to English
    
    language_lower = language.lower().strip()
    
    if language_lower in ['french', 'français']:
        return 2
    elif language_lower in ['german', 'deutsch']:
        return 3
    elif language_lower in ['spanish', 'español']:
        return 4
    elif language_lower in ['italian', 'italiano']:
        return 5
    elif language_lower in ['english', '']:
        return 1  # Explicitly specify English
    
    return 1  # Default to English if unknown


def get_cardmarket_url(card_id: Optional[int], card_name: str = None, expansion_name: str = None, url_type: str = "direct", include_filters: bool = True, min_condition: int = None, alternative_name: str = None, is_foil: bool = False, language: str = None) -> str:
    """
    Generate Cardmarket URLs for a card with quality and language filters.
    
    Args:
        card_id: The idProduct from Cardmarket
        card_name: The card name (optional, for better URLs)
        expansion_name: The expansion/set name (required for proper URLs)
        url_type: "direct" for direct product page, "search" for search page, "search_name" for name-based search
        include_filters: If True, adds sellerCountry=7 (Germany)
        min_condition: Minimum condition code (1-7). Defaults to 3 (Excellent+) if None.
        alternative_name: Alternative card name (e.g., for foreign language cards)
        is_foil: If True, filters for foil versions only
        language: Language name (e.g., "Italian", "French") - maps to Cardmarket language code
    
    Returns:
        URL string with quality/language filters and optional country filter
    """
    # Default to Excellent+ if not specified
    if min_condition is None:
        min_condition = 3
    
    # Get language code (always returns 1-5, defaults to 1 for English)
    lang_code = get_cardmarket_language_code(language)
    lang_param = f"&language={lang_code}"  # Always include language parameter
    if url_type == "search":
        if card_id is None or card_id <= 0:
            # Can't search by ID without a valid card_id, fall back to name search
            if card_name:
                return get_cardmarket_url(card_id, card_name, expansion_name, 'search_name', include_filters, min_condition, alternative_name, is_foil, language)
            else:
                raise ValueError("Cannot create search URL: need either card_id or card_name")
        foil_param = "&isFoil=Y" if is_foil else ""
        if include_filters:
            return f"https://www.cardmarket.com/en/Magic/Products/Search?idProduct={card_id}&sellerCountry=7&minCondition={min_condition}{lang_param}{foil_param}"
        else:
            return f"https://www.cardmarket.com/en/Magic/Products/Search?idProduct={card_id}&minCondition={min_condition}{lang_param}{foil_param}"
    elif url_type == "search_name" and card_name:
        # URL encode the card name for search
        import urllib.parse
        encoded_name = urllib.parse.quote(card_name)
        foil_param = "&isFoil=Y" if is_foil else ""
        if include_filters:
            return f"https://www.cardmarket.com/en/Magic/Products/Singles?searchMode=v1&idCategory=1&idExpansion=0&searchString={encoded_name}&sellerCountry=7&minCondition={min_condition}{lang_param}{foil_param}"
        else:
            return f"https://www.cardmarket.com/en/Magic/Products/Singles?searchMode=v1&idCategory=1&idExpansion=0&searchString={encoded_name}&minCondition={min_condition}{lang_param}{foil_param}"
    else:  # direct
        base_url = ""
        # Use alternative_name if provided (for foreign card names like "Fabbrica di Mishra" -> "Mishra's Factory")
        effective_card_name = alternative_name if alternative_name else card_name
        
        # Prefer expansion + card name format (works without card_id)
        if expansion_name and effective_card_name and str(expansion_name) != 'nan':
            formatted_expansion = format_card_name_for_url(expansion_name, is_expansion=True)
            formatted_card = format_card_name_for_url(effective_card_name, is_expansion=False)
            if formatted_expansion:  # Only use expansion if we have a valid one
                base_url = f"https://www.cardmarket.com/en/Magic/Products/Singles/{formatted_expansion}/{formatted_card}"
        
        # Fallback: card name + card_id (only if card_id is valid)
        if not base_url and effective_card_name and card_id is not None and card_id > 0:
            formatted_name = format_card_name_for_url(effective_card_name, is_expansion=False)
            base_url = f"https://www.cardmarket.com/en/Magic/Products/Singles/{formatted_name}-{card_id}"
        
        # Last resort: card_id only (only if card_id is valid)
        if not base_url and card_id is not None and card_id > 0:
            base_url = f"https://www.cardmarket.com/en/Magic/Products/Singles/{card_id}"
        
        # If still no URL and we have a card name, use search fallback
        if not base_url and effective_card_name:
            import urllib.parse
            encoded_name = urllib.parse.quote(effective_card_name)
            foil_param = "&isFoil=Y" if is_foil else ""
            base_url = f"https://www.cardmarket.com/en/Magic/Products/Singles?searchString={encoded_name}{lang_param}{foil_param}"
            # For search URLs, we're done - return immediately
            return base_url
        
        # Always add condition filter, optionally add country filter, language filter, and foil filter
        foil_param = "&isFoil=Y" if is_foil else ""
        if include_filters:
            return f"{base_url}?sellerCountry=7&minCondition={min_condition}{lang_param}{foil_param}"
        else:
            return f"{base_url}?minCondition={min_condition}{lang_param}{foil_param}"

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
