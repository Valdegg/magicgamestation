#!/usr/bin/env python3
"""
Manual import analysis based on code inspection.

This provides a more accurate analysis by manually tracing the known import chains.
"""

import os
from pathlib import Path

# Entry point
ENTRY_POINT = "main_app.py"

# Known import chains (manually traced from code inspection)
IMPORT_CHAIN = {
    # Entry point
    "main_app.py": [
        "web_ui.py",
        "wishlist_ui.py", 
        "collection_ui.py",
    ],
    
    # web_ui.py imports
    "web_ui.py": [
        # Dynamically imports:
        "simple_version/wishlist_deals.py",
        "simple_version/discovery.py",
    ],
    
    # wishlist_ui.py imports
    "wishlist_ui.py": [
        "card_autocomplete.py",  # Optional import
    ],
    
    # collection_ui.py imports  
    "collection_ui.py": [
        "card_autocomplete.py",  # Optional import
    ],
    
    # simple_version/wishlist_deals.py imports
    "simple_version/wishlist_deals.py": [
        "card_lookup.py",
        "mtg_arbitrage/wishlist.py",
        "mtg_arbitrage/utils.py",
        "mtg_arbitrage/config.py",
        "fetch_live_listings_simple.py",
    ],
    
    # simple_version/discovery.py imports
    "simple_version/discovery.py": [
        "card_lookup.py",
        "mtg_arbitrage/utils.py",
        "mtg_arbitrage/config.py",
        "fetch_live_listings_simple.py",
    ],
    
    # card_lookup.py imports
    "card_lookup.py": [
        "mtg_arbitrage/data_loader.py",
        "mtg_arbitrage/wishlist.py",
    ],
    
    # mtg_arbitrage/data_loader.py imports
    "mtg_arbitrage/data_loader.py": [
        "mtg_arbitrage/utils.py",
    ],
    
    # mtg_arbitrage/__init__.py (if exists, may import other modules)
    "mtg_arbitrage/__init__.py": [],
}

# Files that can be run standalone (have if __name__ == "__main__")
STANDALONE_SCRIPTS = [
    "add_condition.py",
    "check_missing_market_prices.py",
    "convert_to_eur.py",
    "determine_format_validity.py",
    "split_wishlist_by_format.py",
    "card_image_fetcher.py",
    "test_sorting.py",
    "test_sorting_simple.py",
    "test_set_image_fetch.py",
]

# Test files (excluded from unused analysis)
TEST_FILES = [
    "test_sorting.py",
    "test_sorting_simple.py",
    "test_set_image_fetch.py",
]


def find_all_python_files():
    """Find all Python files in the current directory."""
    python_files = []
    for root, dirs, files in os.walk('.'):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                rel_path = os.path.relpath(os.path.join(root, file))
                python_files.append(rel_path)
    
    return sorted(python_files)


def trace_imports(start_file, visited=None):
    """Recursively trace imports."""
    if visited is None:
        visited = set()
    
    if start_file in visited:
        return set()
    
    visited.add(start_file)
    used_files = {start_file}
    
    # Get imports for this file
    imports = IMPORT_CHAIN.get(start_file, [])
    
    for imported_file in imports:
        # Normalize path
        if not os.path.exists(imported_file):
            # Try with .py extension
            if not imported_file.endswith('.py'):
                imported_file_py = imported_file + '.py'
                if os.path.exists(imported_file_py):
                    imported_file = imported_file_py
        
        if os.path.exists(imported_file):
            sub_used = trace_imports(imported_file, visited)
            used_files.update(sub_used)
    
    return used_files


def main():
    """Main analysis."""
    print("=" * 80)
    print("Import Analysis Report - Used vs Unused Scripts")
    print("=" * 80)
    print()
    
    # Find all Python files
    all_files = find_all_python_files()
    print(f"📁 Found {len(all_files)} Python files")
    print()
    
    # Trace imports from entry point
    print(f"🔍 Tracing imports from {ENTRY_POINT}...")
    used_files = trace_imports(ENTRY_POINT)
    
    # Also check standalone entry points
    for entry in ["web_ui.py", "wishlist_ui.py", "collection_ui.py"]:
        if entry in all_files:
            print(f"   Also checking {entry}...")
            used_files.update(trace_imports(entry))
    
    print(f"   Found {len(used_files)} files in import chain")
    print()
    
    # Identify unused files
    all_files_set = set(all_files)
    unused_files = all_files_set - used_files
    
    # Remove test files from unused (they're intentionally standalone)
    unused_files = {f for f in unused_files if f not in TEST_FILES}
    
    # Separate unused into standalone utilities vs truly unused
    standalone_unused = {f for f in unused_files if f in STANDALONE_SCRIPTS}
    truly_unused = unused_files - standalone_unused
    
    # Print results
    print("=" * 80)
    print("✅ USED FILES (in import chain)")
    print("=" * 80)
    for f in sorted(used_files):
        print(f"   {f}")
    print()
    
    print("=" * 80)
    print("🔧 STANDALONE UTILITIES (can be run directly)")
    print("=" * 80)
    print("These files have if __name__ == '__main__' blocks and can be run standalone:")
    for f in sorted(standalone_unused):
        if f in all_files_set:
            print(f"   {f}")
    print()
    
    print("=" * 80)
    print("❌ TRULY UNUSED FILES")
    print("=" * 80)
    print("These files are not imported anywhere and don't appear to be standalone utilities:")
    for f in sorted(truly_unused):
        print(f"   {f}")
    print()
    
    # Summary
    print("=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    print(f"Total Python files: {len(all_files)}")
    print(f"Used files (in import chain): {len(used_files)}")
    print(f"Standalone utilities: {len(standalone_unused)}")
    print(f"Truly unused files: {len(truly_unused)}")
    print(f"Test files (excluded): {len([f for f in TEST_FILES if f in all_files_set])}")
    print()
    
    print("=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    print("""
1. USED FILES: Keep all files in the import chain - they're required for the website to work.

2. STANDALONE UTILITIES: Review these - they may be useful for manual operations:
   - add_condition.py - Add condition data to collection
   - check_missing_market_prices.py - Check for missing market prices
   - convert_to_eur.py - Currency conversion utility
   - determine_format_validity.py - Format validity checker
   - split_wishlist_by_format.py - Split wishlist by format
   - card_image_fetcher.py - Fetch card images

3. TRULY UNUSED FILES: These can likely be removed if not needed:
   - Review each file to confirm it's not used elsewhere
   - Check if they're referenced in documentation or scripts
   - Consider archiving instead of deleting

4. TEST FILES: Keep test files for now, or move to a tests/ directory.
    """.strip())


if __name__ == '__main__':
    main()
