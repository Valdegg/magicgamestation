# Import Analysis Report

This document identifies which scripts are used by the website (`start_website.sh` → `main_app.py`) and which are standalone utilities or unused.

## Entry Point Chain

```
start_website.sh
  └─> main_app.py (port 5010)
       ├─> web_ui.py (Market Scanner)
       ├─> wishlist_ui.py (Wishlist Manager)
       └─> collection_ui.py (Collection Manager)
```

## ✅ USED FILES (Required for Website)

These files are imported and used by the website:

### Core Application Files
- **main_app.py** - Main unified web application entry point
- **web_ui.py** - Market scanner UI (displays deals)
- **wishlist_ui.py** - Wishlist management UI
- **collection_ui.py** - Collection management UI

### Supporting Modules
- **card_autocomplete.py** - Card name autocomplete (used by wishlist_ui and collection_ui)

### Analysis Scripts (used by web_ui.py)
- **simple_version/wishlist_deals.py** - Wishlist deals analysis
- **simple_version/discovery.py** - Card discovery analysis

### Data Loading & Scraping (used by analysis scripts)
- **card_lookup.py** - Card data loading and filtering
- **fetch_live_listings_simple.py** - Web scraper for live Cardmarket prices

### MTG Arbitrage Package (used by data loading)
- **mtg_arbitrage/__init__.py** - Package marker (needed for imports)
- **mtg_arbitrage/config.py** - Configuration loading
- **mtg_arbitrage/data_loader.py** - Cardmarket data loading
- **mtg_arbitrage/utils.py** - URL generation and utilities
- **mtg_arbitrage/wishlist.py** - Wishlist utilities

**Total: 14 files**

---

## 🔧 STANDALONE UTILITIES (Can be run directly)

These files have `if __name__ == "__main__"` blocks and can be run independently:

1. **add_condition.py** - Add condition data to collection items
2. **check_missing_market_prices.py** - Check for missing market prices in results
3. **convert_to_eur.py** - Currency conversion utility
4. **determine_format_validity.py** - Check format validity (Old School, Premodern)
5. **trash/wishlist_deals_mitt.py** - Alternative version of wishlist_deals.py

**Recommendation:** Keep these if you use them for manual operations. They're useful utilities.

### Utility Scripts (no main block but standalone)
6. **card_image_fetcher.py** - Fetch card images from Scryfall
7. **split_wishlist_by_format.py** - Split wishlist by format (Old School, Premodern)

---

## 📊 ANALYSIS SCRIPTS (Temporary)

These files were created for analysis and can be removed after review:

1. **analyze_imports.py** - Import analysis script (this file)
2. **import_analysis_report.py** - Analysis report generator

---

## 🧪 TEST FILES (Excluded from analysis)

These are test files and are intentionally standalone:

1. **tests/test_sorting.py** - Test sorting functionality
2. **tests/test_sorting_simple.py** - Simple sorting tests
3. **tests/test_set_image_fetch.py** - Test image fetching

**Recommendation:** Keep for now, or move to a `tests/` directory.

---

## 📊 Summary

- **Total Python files:** 23
- **Used by website:** 14 files (60.9%)
- **Standalone utilities:** 7 files (30.4%)
- **Analysis scripts:** 2 files (8.7%)

---

## 💡 Cleanup Recommendations

### Safe to Remove (After Review)
1. `trash/wishlist_deals_mitt.py` - If you don't need this alternative version
2. `analyze_imports.py` - Temporary analysis script
3. `import_analysis_report.py` - Temporary analysis script

### Keep (Useful Utilities)
- All standalone utilities listed above
- Test files (or move to `tests/` directory)

### Must Keep
- All files in the "USED FILES" section - these are required for the website to function

---

## Import Chain Visualization

```
main_app.py
├── web_ui.py
│   ├── simple_version/wishlist_deals.py
│   │   ├── card_lookup.py
│   │   │   ├── mtg_arbitrage/data_loader.py
│   │   │   │   └── mtg_arbitrage/utils.py
│   │   │   └── mtg_arbitrage/wishlist.py
│   │   ├── mtg_arbitrage/wishlist.py
│   │   ├── mtg_arbitrage/utils.py
│   │   ├── mtg_arbitrage/config.py
│   │   └── fetch_live_listings_simple.py
│   └── simple_version/discovery.py
│       ├── card_lookup.py (see above)
│       ├── mtg_arbitrage/utils.py
│       ├── mtg_arbitrage/config.py
│       └── fetch_live_listings_simple.py
├── wishlist_ui.py
│   └── card_autocomplete.py (optional)
└── collection_ui.py
    └── card_autocomplete.py (optional)
```

---

Generated: 2025-01-14
Analysis: Manual verification + automated script
Note: Automated analysis missed some dynamic imports (sys.path manipulation)
