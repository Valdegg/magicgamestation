# Python Line Count Analysis Report

**Generated:** January 14, 2026  
**Total Python Files:** 26  
**Total Lines of Code:** 15,192  

## 📊 Executive Summary

- **Largest File:** `collection_ui.py` (3,878 lines - 25.5% of total)
- **Smallest File:** `mtg_arbitrage/__init__.py` (7 lines)
- **Average Lines per File:** 584 lines
- **Median Lines per File:** 263 lines

---

## 📈 Files by Line Count (Largest First)

| File | Lines | Percentage | Category |
|------|-------|------------|----------|
| `collection_ui.py` | 3,878 | 25.5% | Core UI |
| `wishlist_ui.py` | 1,674 | 11.0% | Core UI |
| `fetch_live_listings_simple.py` | 1,140 | 7.5% | Data Scraping |
| `main_app.py` | 1,103 | 7.3% | Core Application |
| `simple_version/wishlist_deals.py` | 942 | 6.2% | Analysis |
| `web_ui.py` | 880 | 5.8% | Core UI |
| `trash/wishlist_deals_mitt.py` | 868 | 5.7% | Alternative Version |
| `check_missing_market_prices.py` | 657 | 4.3% | Utility |
| `simple_version/discovery.py` | 444 | 2.9% | Analysis |
| `mtg_arbitrage/wishlist.py` | 440 | 2.9% | Library |
| `determine_format_validity.py` | 436 | 2.9% | Utility |
| `mtg_arbitrage/utils.py` | 296 | 1.9% | Library |
| `analyze_imports.py` | 284 | 1.9% | Analysis |
| `tests/test_set_image_fetch.py` | 276 | 1.8% | Test |
| `card_autocomplete.py` | 270 | 1.8% | Library |
| `tests/test_sorting.py` | 263 | 1.7% | Test |
| `mtg_arbitrage/data_loader.py` | 246 | 1.6% | Library |
| `import_analysis_report.py` | 234 | 1.5% | Analysis |
| `tests/test_sorting_simple.py` | 216 | 1.4% | Test |
| `card_lookup.py` | 207 | 1.4% | Library |
| `card_image_fetcher.py` | 182 | 1.2% | Utility |
| `split_wishlist_by_format.py` | 103 | 0.7% | Utility |
| `mtg_arbitrage/config.py` | 77 | 0.5% | Library |
| `convert_to_eur.py` | 36 | 0.2% | Utility |
| `add_condition.py` | 33 | 0.2% | Utility |
| `mtg_arbitrage/__init__.py` | 7 | 0.0% | Library |

---

## 🏗️ Codebase Breakdown by Category

### Core Application (Website Essential)
| File | Lines | Purpose |
|------|-------|---------|
| `main_app.py` | 1,103 | Main FastAPI application |
| `web_ui.py` | 880 | Market scanner UI |
| `wishlist_ui.py` | 1,674 | Wishlist management UI |
| `collection_ui.py` | 3,878 | Collection management UI |
| **Subtotal:** | **7,535** | **49.6% of total** |

### Analysis & Data Processing
| File | Lines | Purpose |
|------|-------|---------|
| `simple_version/wishlist_deals.py` | 942 | Wishlist deals analysis |
| `simple_version/discovery.py` | 444 | Card discovery analysis |
| `fetch_live_listings_simple.py` | 1,140 | Web scraping for prices |
| `card_lookup.py` | 207 | Card data loading |
| `check_missing_market_prices.py` | 657 | Price checking utility |
| `determine_format_validity.py` | 436 | Format validation |
| **Subtotal:** | **3,826** | **25.2% of total** |

### Libraries & Utilities
| File | Lines | Purpose |
|------|-------|---------|
| `mtg_arbitrage/wishlist.py` | 440 | Wishlist utilities |
| `mtg_arbitrage/utils.py` | 296 | General utilities |
| `mtg_arbitrage/data_loader.py` | 246 | Data loading |
| `mtg_arbitrage/config.py` | 77 | Configuration |
| `mtg_arbitrage/__init__.py` | 7 | Package initialization |
| `card_autocomplete.py` | 270 | Card name autocomplete |
| `card_image_fetcher.py` | 182 | Image fetching utility |
| **Subtotal:** | **1,518** | **10.0% of total** |

### Standalone Utilities
| File | Lines | Purpose |
|------|-------|---------|
| `add_condition.py` | 33 | Add condition to collection |
| `convert_to_eur.py` | 36 | Currency conversion |
| `split_wishlist_by_format.py` | 103 | Split wishlist by format |
| **Subtotal:** | **172** | **1.1% of total** |

### Alternative/Archive Code
| File | Lines | Purpose |
|------|-------|---------|
| `trash/wishlist_deals_mitt.py` | 868 | Alternative wishlist analyzer |
| **Subtotal:** | **868** | **5.7% of total** |

### Analysis & Test Scripts
| File | Lines | Purpose |
|------|-------|---------|
| `analyze_imports.py` | 284 | Import analysis tool |
| `import_analysis_report.py` | 234 | Analysis reporting |
| `tests/test_sorting.py` | 263 | Sorting tests |
| `tests/test_sorting_simple.py` | 216 | Simple sorting tests |
| `tests/test_set_image_fetch.py` | 276 | Image fetch tests |
| **Subtotal:** | **1,273** | **8.4% of total** |

---

## 📏 Size Distribution Analysis

### By Line Ranges
- **Large Files (>1000 lines):** 4 files (15.4%)
  - `collection_ui.py` (3,878)
  - `wishlist_ui.py` (1,674)
  - `fetch_live_listings_simple.py` (1,140)
  - `main_app.py` (1,103)

- **Medium Files (500-1000 lines):** 3 files (11.5%)
  - `simple_version/wishlist_deals.py` (942)
  - `web_ui.py` (880)
  - `trash/wishlist_deals_mitt.py` (868)

- **Small Files (100-500 lines):** 13 files (50.0%)
  - Range: 77-657 lines

- **Tiny Files (<100 lines):** 6 files (23.1%)
  - Range: 7-77 lines

### Average Lines by Directory
- **Root level:** 584 lines average
- **mtg_arbitrage/:** 213 lines average
- **simple_version/:** 693 lines average
- **tests/:** 252 lines average
- **trash/:** 868 lines average

---

## 💡 Insights & Recommendations

### Complexity Analysis
1. **Most Complex:** `collection_ui.py` (25.5% of codebase) - Collection management UI
2. **High Complexity:** UI components dominate (49.6% of total code)
3. **Data Processing:** 25.2% dedicated to analysis and scraping
4. **Utility Code:** Only 10.0% in reusable libraries

### Potential Refactoring Opportunities
1. **collection_ui.py** is very large - consider breaking into smaller modules
2. **fetch_live_listings_simple.py** is complex - consider modularizing scraping logic
3. **UI components** could benefit from shared base classes

### Maintenance Notes
- **Test Coverage:** 8.4% of code is tests/analysis (good for maintenance)
- **Library Ratio:** 10.0% in reusable components (room for improvement)
- **Standalone Tools:** 7.4% in utilities (appropriate for this type of application)

---

## 🔍 Detailed File Analysis

### Top 5 Largest Files
1. **collection_ui.py** (3,878 lines) - Main collection management interface
2. **wishlist_ui.py** (1,674 lines) - Wishlist management interface
3. **fetch_live_listings_simple.py** (1,140 lines) - Cardmarket web scraper
4. **main_app.py** (1,103 lines) - FastAPI application setup and routing
5. **simple_version/wishlist_deals.py** (942 lines) - Wishlist price analysis

### Files Under 50 Lines
- `mtg_arbitrage/__init__.py` (7 lines) - Minimal package init
- `add_condition.py` (33 lines) - Simple utility script
- `convert_to_eur.py` (36 lines) - Simple currency converter

### Files Over 500 Lines (Complex)
- `collection_ui.py` (3,878) - Very complex UI
- `wishlist_ui.py` (1,674) - Complex UI
- `fetch_live_listings_simple.py` (1,140) - Complex scraping
- `main_app.py` (1,103) - Complex routing
- `simple_version/wishlist_deals.py` (942) - Complex analysis
- `web_ui.py` (880) - Complex UI
- `trash/wishlist_deals_mitt.py` (868) - Complex analysis
- `check_missing_market_prices.py` (657) - Complex utility

---

**Report generated by analyzing 26 Python files totaling 15,192 lines of code.**