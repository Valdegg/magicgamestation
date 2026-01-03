"""
Functions to download and parse Cardmarket data (CSV and JSON).
"""

import os
import requests
import pandas as pd
import json
import gzip
from datetime import datetime
from typing import Tuple, Optional
from .utils import get_raw_data_dir, ensure_dir_exists

# Cardmarket URLs
PRICEGUIDE_URL = "https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_1.json"
PRODUCT_CATALOG_URL = "https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_1.json"

def download_data_file(url: str, filename: str, force_download: bool = False) -> str:
    """
    Download a data file from Cardmarket.
    
    Args:
        url: URL to download from
        filename: Local filename to save as
        force_download: Whether to force download even if file exists today
        
    Returns:
        Path to the downloaded file
    """
    raw_dir = get_raw_data_dir()
    ensure_dir_exists(raw_dir)
    
    # Add date to filename
    today = datetime.now().strftime("%Y%m%d")
    base_name, ext = os.path.splitext(filename)
    dated_filename = f"{base_name}_{today}{ext}"
    filepath = os.path.join(raw_dir, dated_filename)
    
    # Check if file already exists and is from today
    if os.path.exists(filepath) and not force_download:
        print(f"Using existing file: {filepath}")
        return filepath
    
    print(f"Downloading {url} to {filepath}")
    
    # Note: This is a placeholder implementation
    # Real implementation would need proper Cardmarket API access or scraping
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Handle binary files (like .gz) vs text files
        if filename.endswith('.gz') or filename.endswith('.zip'):
            with open(filepath, 'wb') as f:
                f.write(response.content)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
        return filepath
        
    except requests.RequestException as e:
        print(f"Error downloading {url}: {e}")
        raise Exception(f"Failed to download data from {url}: {e}")


def load_priceguide_json(force_download: bool = False) -> pd.DataFrame:
    """Load the price guide JSON from Cardmarket."""
    filepath = download_data_file(
        PRICEGUIDE_URL, 
        "priceguide.json", 
        force_download
    )
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract price guides from JSON structure
        price_guides = data.get('priceGuides', [])
        
        # Convert to DataFrame and rename columns to match expected format
        df = pd.DataFrame(price_guides)
        
        # Rename columns to match the expected format
        column_mapping = {
            'avg': 'AVG',
            'low': 'LOW', 
            'trend': 'TREND',
            'avg1': 'AVG1',
            'avg7': 'AVG7', 
            'avg30': 'AVG30',
            'low-foil': 'LOWFOIL',
            'avg-foil': 'AVGFOIL'
        }
        
        # Rename columns that exist
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        
        # Fix integer columns (convert floats to ints where appropriate)
        int_cols = ['idProduct', 'idCategory']
        for col in int_cols:
            if col in df.columns:
                df[col] = df[col].astype(int)
        
        # Clean up NaN values and add LOWEX+ column
        if 'LOW' in df.columns:
            df['LOWEX+'] = df['LOW'] * 1.1  # Assume EX+ is ~10% higher than LOW
        
        # Fill NaN values with 0 for numeric columns (except foil prices)
        numeric_cols = ['AVG', 'LOW', 'TREND', 'AVG1', 'AVG7', 'AVG30', 'LOWEX+']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        # For foil prices, keep NaN as they indicate non-foil cards
        # But convert to 0 for calculations where needed
        foil_cols = ['AVGFOIL', 'LOWFOIL', 'trend-foil', 'avg1-foil', 'avg7-foil', 'avg30-foil']
        for col in foil_cols:
            if col in df.columns:
                # Keep NaN but ensure they don't break calculations
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"Loaded price data for {len(df)} products (cleaned NaN values)")
        return df
    except Exception as e:
        print(f"Error loading price guide JSON: {e}")
        return pd.DataFrame()

def load_data(force_download: bool = False) -> pd.DataFrame:
    """
    Load price guide JSON data from Cardmarket.
    
    Returns:
        DataFrame with price guide data including card names and metadata
    """
    return load_priceguide_json(force_download)

# Legacy function kept for compatibility - now just returns the data as-is
def load_product_catalog(force_download: bool = False) -> pd.DataFrame:
    """Load the product catalog JSON from Cardmarket (contains card names)."""
    try:
        # Download the JSON file
        filepath = download_data_file(
            PRODUCT_CATALOG_URL, 
            "product_catalog.json", 
            force_download
        )
        
        # Read the JSON file
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract products from JSON structure
        products = data.get('products', [])
        df = pd.DataFrame(products)
        
        # Fix integer columns
        int_cols = ['idProduct', 'idCategory', 'idExpansion', 'idMetacard']
        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        print(f"Loaded product catalog with {len(df)} products")
        return df
        
    except Exception as e:
        print(f"Error loading product catalog: {e}")
        print("Continuing without card names...")
        return pd.DataFrame()

def load_expansion_mapping() -> dict:
    """Load the expansion mapping from idExpansion to expansion name."""
    try:
        raw_dir = get_raw_data_dir()
        mapping_file = os.path.join(raw_dir, "expansion_mapping.json")
        
        if not os.path.exists(mapping_file):
            print("⚠️  Expansion mapping not found. Run 'python create_expansion_mapping.py' first.")
            return {}
        
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        # Convert string keys back to integers
        int_mapping = {int(k): v for k, v in mapping.items()}
        print(f"✅ Loaded expansion mapping for {len(int_mapping)} expansions")
        return int_mapping
        
    except Exception as e:
        print(f"Error loading expansion mapping: {e}")
        return {}

def load_data_with_names(force_download: bool = False) -> pd.DataFrame:
    """
    Load price guide data enriched with card names from product catalog.
    
    Returns:
        DataFrame with price guide data plus card names, expansions, etc.
    """
    # Load price guide data
    price_data = load_priceguide_json(force_download)
    
    if price_data.empty:
        return price_data
    
    # Load product catalog for names
    catalog = load_product_catalog(force_download)
    
    if catalog.empty:
        print("⚠️  No card names available - using price data only")
        return price_data
    
    # Load expansion mapping
    expansion_map = load_expansion_mapping()
    
    # Merge on idProduct to add names
    merged = price_data.merge(catalog, on='idProduct', how='left')
    
    # Add expansion names if mapping is available
    if expansion_map:
        # Convert idExpansion to int for mapping (handle NaN values)
        merged['idExpansion'] = pd.to_numeric(merged['idExpansion'], errors='coerce').fillna(0).astype(int)
        merged['expansionName'] = merged['idExpansion'].map(expansion_map)
        expansions_mapped = merged['expansionName'].notna().sum()
        print(f"✅ Mapped {expansions_mapped}/{len(merged)} cards to expansion names ({expansions_mapped/len(merged)*100:.1f}%)")
    
    # Report merge results
    total_cards = len(price_data)
    cards_with_names = merged['name'].notna().sum()
    print(f"✅ Enriched {cards_with_names}/{total_cards} cards with names ({cards_with_names/total_cards*100:.1f}%)")
    
    return merged

def merge_product_data(products: pd.DataFrame, priceguide: pd.DataFrame = None) -> pd.DataFrame:
    """
    Legacy function - now just returns the price guide data since it includes all needed info.
    """
    if priceguide is not None:
        return priceguide
    return products
