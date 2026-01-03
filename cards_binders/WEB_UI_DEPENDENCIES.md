# Web UI Dependencies - Complete Import Tree

This document traces all scripts and modules used by `web_ui.py`, including transitive imports.

## Direct Dependencies

`web_ui.py` directly imports:
- Standard library: `json`, `os`, `glob`, `sys`, `argparse`, `pathlib`, `datetime`, `typing`
- Third-party: `fastapi`, `jinja2`
- **Local scripts** (dynamically imported):
  - `simple_version/wishlist_deals.py` (via `run_wishlist_analysis()`)
  - `simple_version/discovery.py` (via `run_discovery_analysis()`)

## Transitive Dependencies

### 1. `simple_version/wishlist_deals.py`

**Direct imports:**
- Standard library: `json`, `time`, `random`, `os`, `sys`, `pathlib`, `datetime`, `typing`
- **Local modules:**
  - `card_lookup` → `load_cardmarket_data`
  - `mtg_arbitrage.wishlist` → `load_wishlist`, `filter_by_wishlist`
  - `mtg_arbitrage.utils` → `get_cardmarket_url`
  - `mtg_arbitrage.config` → `get_config`
  - `fetch_live_listings_simple` → `SimpleBrowserScraper`

### 2. `simple_version/discovery.py`

**Direct imports:**
- Standard library: `json`, `time`, `random`, `os`, `sys`, `datetime`, `typing`
- **Local modules:**
  - `card_lookup` → `load_cardmarket_data`, `exclude_wishlist_cards`, `find_cards_by_price_discount`
  - `mtg_arbitrage.utils` → `get_cardmarket_url`
  - `mtg_arbitrage.config` → `get_config`
  - `fetch_live_listings_simple` → `SimpleBrowserScraper`

### 3. `card_lookup.py`

**Direct imports:**
- Standard library: `typing`
- Third-party: `pandas`
- **Local modules:**
  - `mtg_arbitrage.data_loader` → `load_data_with_names`
  - `mtg_arbitrage.wishlist` → `load_wishlist`, `filter_by_wishlist`

### 4. `mtg_arbitrage/wishlist.py`

**Direct imports:**
- Standard library: `json`, `pathlib`, `typing`
- Third-party: `pandas`
- **No local module dependencies**

### 5. `mtg_arbitrage/utils.py`

**Direct imports:**
- Standard library: `os`, `typing`
- Third-party: `dotenv` (python-dotenv)
- **No local module dependencies**

### 6. `mtg_arbitrage/config.py`

**Direct imports:**
- Standard library: `os`, `typing`
- **No local module dependencies**

### 7. `mtg_arbitrage/data_loader.py`

**Direct imports:**
- Standard library: `os`, `datetime`, `typing`, `gzip`, `json`
- Third-party: `requests`, `pandas`
- **Local modules:**
  - `mtg_arbitrage.utils` → `get_raw_data_dir`, `ensure_dir_exists`

### 8. `fetch_live_listings_simple.py`

**Direct imports:**
- Standard library: `time`, `json`, `sys`, `random`, `re`, `typing`, `dataclasses`
- Third-party: `requests`, `beautifulsoup4` (bs4)
- **Optional dependencies:**
  - `brotli` (optional, for Brotli compression support)

## Complete Dependency Tree

```
web_ui.py
├── Standard Library
│   ├── json, os, glob, sys, argparse, pathlib, datetime, typing
│   └── (via subprocess calls)
├── Third-party
│   ├── fastapi
│   ├── jinja2
│   └── (via transitive imports: pandas, requests, beautifulsoup4, dotenv)
│
└── Local Scripts (dynamically imported)
    │
    ├── simple_version/wishlist_deals.py
    │   ├── card_lookup.py
    │   │   ├── mtg_arbitrage/data_loader.py
    │   │   │   └── mtg_arbitrage/utils.py
    │   │   │       └── dotenv (python-dotenv)
    │   │   └── mtg_arbitrage/wishlist.py
    │   ├── mtg_arbitrage/wishlist.py
    │   ├── mtg_arbitrage/utils.py
    │   ├── mtg_arbitrage/config.py
    │   └── fetch_live_listings_simple.py
    │       └── (optional: brotli)
    │
    └── simple_version/discovery.py
        ├── card_lookup.py (same as above)
        ├── mtg_arbitrage/utils.py
        ├── mtg_arbitrage/config.py
        └── fetch_live_listings_simple.py (same as above)
```

## Summary of Required Scripts

### Core Scripts Used:
1. **web_ui.py** - Main web server
2. **simple_version/wishlist_deals.py** - Wishlist analysis
3. **simple_version/discovery.py** - Card discovery
4. **card_lookup.py** - Card data loading and filtering
5. **fetch_live_listings_simple.py** - Web scraping
6. **mtg_arbitrage/wishlist.py** - Wishlist utilities
7. **mtg_arbitrage/utils.py** - URL generation, utilities
8. **mtg_arbitrage/config.py** - Configuration loading
9. **mtg_arbitrage/data_loader.py** - Cardmarket data loading

### Third-party Dependencies:
- **fastapi** - Web framework
- **jinja2** - Template engine
- **pandas** - Data manipulation
- **requests** - HTTP requests
- **beautifulsoup4** - HTML parsing
- **python-dotenv** - Environment variable loading
- **brotli** (optional) - Brotli compression support

### Data Files Used:
- `wishlist.json` - User's wishlist
- `config.env` - Configuration file
- Cardmarket data files (downloaded via `mtg_arbitrage/data_loader.py`)

## Notes

- `web_ui.py` does NOT directly import the analysis scripts - it dynamically imports them at runtime when `run_wishlist_analysis()` or `run_discovery_analysis()` are called
- The scripts are imported from `simple_version/` directory by adding it to `sys.path`
- `fetch_live_listings_simple.py` has an optional `brotli` dependency - it works without it but with reduced compression support
- All scripts share common dependencies like `card_lookup.py` and `mtg_arbitrage/*` modules

