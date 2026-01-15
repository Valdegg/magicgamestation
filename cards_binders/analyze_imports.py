#!/usr/bin/env python3
"""
Analyze imports to identify which scripts are used and which are unused.

This script traces imports starting from the entry point (start_website.sh -> main_app.py)
and identifies all scripts that are actually used vs those that are standalone utilities.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Set, Dict, List, Tuple
import re

# Entry point files
ENTRY_POINTS = [
    'main_app.py',
    'web_ui.py',  # Can be run standalone
    'wishlist_ui.py',  # Can be run standalone
    'collection_ui.py',  # Can be run standalone
]

# Files to exclude from analysis (test files, etc.)
EXCLUDE_PATTERNS = [
    r'^test_.*\.py$',
    r'^.*_test\.py$',
]


def should_exclude(filename: str) -> bool:
    """Check if a file should be excluded from analysis."""
    for pattern in EXCLUDE_PATTERNS:
        if re.match(pattern, filename):
            return True
    return False


def extract_imports(filepath: str) -> Set[str]:
    """Extract all import statements from a Python file."""
    imports = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content, filename=filepath)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    except Exception as e:
        print(f"Warning: Could not parse {filepath}: {e}")
    
    return imports


def find_python_files(directory: str = '.') -> List[str]:
    """Find all Python files in the directory."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and common exclusions
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'node_modules']]
        
        for file in files:
            if file.endswith('.py') and not should_exclude(file):
                filepath = os.path.join(root, file)
                python_files.append(filepath)
    
    return python_files


def normalize_module_name(module_name: str, current_dir: str) -> str:
    """Convert import name to file path."""
    # Handle relative imports
    if module_name.startswith('.'):
        return None  # Skip relative imports for now
    
    # Handle absolute imports
    # Check if it's a local module (no dots or starts with known local prefix)
    if '.' not in module_name:
        # Check if file exists in current directory or subdirectories
        possible_paths = [
            os.path.join(current_dir, f"{module_name}.py"),
            os.path.join(current_dir, module_name, "__init__.py"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.relpath(path)
        return None
    
    # Handle dotted imports (like mtg_arbitrage.wishlist)
    parts = module_name.split('.')
    base = parts[0]
    
    # Check if base module exists
    possible_paths = [
        os.path.join(current_dir, f"{base}.py"),
        os.path.join(current_dir, base, "__init__.py"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            # For submodules, check if the file exists
            if len(parts) > 1:
                submodule_path = os.path.join(os.path.dirname(path), f"{parts[1]}.py")
                if os.path.exists(submodule_path):
                    return os.path.relpath(submodule_path)
            return os.path.relpath(path)
    
    return None


def trace_imports(start_file: str, all_files: List[str], visited: Set[str] = None) -> Set[str]:
    """Recursively trace imports starting from a file."""
    if visited is None:
        visited = set()
    
    if start_file in visited:
        return set()
    
    visited.add(start_file)
    used_files = {start_file}
    
    # Extract imports from the file
    imports = extract_imports(start_file)
    
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(start_file))
    
    # Find which imports correspond to local files
    for module_name in imports:
        # Skip standard library and third-party imports
        if module_name in ['json', 'os', 'sys', 'argparse', 're', 'time', 'random', 
                          'math', 'datetime', 'typing', 'pathlib', 'glob', 'shutil',
                          'threading', 'collections', 'dataclasses', 'urllib', 'hashlib',
                          'fastapi', 'uvicorn', 'jinja2', 'pandas', 'requests', 
                          'bs4', 'beautifulsoup4', 'dotenv', 'gzip', 'brotli']:
            continue
        
        # Try to find the corresponding file
        module_file = normalize_module_name(module_name, current_dir)
        
        if module_file:
            # Resolve to absolute path
            abs_path = os.path.abspath(module_file)
            
            # Check if it's in our file list
            matching_files = [f for f in all_files if os.path.abspath(f) == abs_path]
            
            if matching_files:
                file_path = matching_files[0]
                # Recursively trace imports from this file
                sub_used = trace_imports(file_path, all_files, visited)
                used_files.update(sub_used)
    
    # Also check for dynamic imports (like sys.path.insert + import)
    # This is a simplified check - we'll look for common patterns
    try:
        with open(start_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for simple_version imports (common pattern in main_app.py)
        if 'simple_version' in content and 'sys.path.insert' in content:
            simple_version_dir = os.path.join(os.path.dirname(start_file), 'simple_version')
            if os.path.exists(simple_version_dir):
                for file in os.listdir(simple_version_dir):
                    if file.endswith('.py') and not file.startswith('__'):
                        file_path = os.path.join(simple_version_dir, file)
                        if file_path in all_files:
                            used_files.add(file_path)
                            sub_used = trace_imports(file_path, all_files, visited)
                            used_files.update(sub_used)

        # Check for specific imports that might be missed
        if 'card_lookup' in content:
            card_lookup_path = os.path.join(os.path.dirname(start_file), 'card_lookup.py')
            if os.path.exists(card_lookup_path) and card_lookup_path in all_files:
                used_files.add(card_lookup_path)
                sub_used = trace_imports(card_lookup_path, all_files, visited)
                used_files.update(sub_used)

        if 'fetch_live_listings_simple' in content:
            scraper_path = os.path.join(os.path.dirname(start_file), 'fetch_live_listings_simple.py')
            if os.path.exists(scraper_path) and scraper_path in all_files:
                used_files.add(scraper_path)
                sub_used = trace_imports(scraper_path, all_files, visited)
                used_files.update(sub_used)

    except Exception as e:
        pass
    
    return used_files


def main():
    """Main analysis function."""
    print("=" * 80)
    print("Import Analysis - Identifying Used vs Unused Scripts")
    print("=" * 80)
    print()
    
    # Find all Python files
    print("📁 Finding all Python files...")
    all_files = find_python_files('.')
    print(f"   Found {len(all_files)} Python files")
    print()
    
    # Get base names for comparison
    file_basenames = {os.path.basename(f): f for f in all_files}
    
    # Trace imports from entry points
    print("🔍 Tracing imports from entry points...")
    all_used_files = set()
    
    for entry_point in ENTRY_POINTS:
        if entry_point in file_basenames:
            file_path = file_basenames[entry_point]
            print(f"   Tracing from {entry_point}...")
            used = trace_imports(file_path, all_files)
            all_used_files.update(used)
            print(f"      Found {len(used)} files used by {entry_point}")
        else:
            print(f"   ⚠️  Entry point {entry_point} not found")
    
    print()
    
    # Identify unused files
    all_files_set = set(all_files)
    unused_files = all_files_set - all_used_files
    
    # Separate into categories
    used_files_list = sorted(all_used_files)
    unused_files_list = sorted(unused_files)
    
    # Print results
    print("=" * 80)
    print("📊 RESULTS")
    print("=" * 80)
    print()
    
    print(f"✅ USED FILES ({len(used_files_list)}):")
    print("-" * 80)
    for f in used_files_list:
        rel_path = os.path.relpath(f)
        print(f"   {rel_path}")
    print()
    
    print(f"❌ UNUSED FILES ({len(unused_files_list)}):")
    print("-" * 80)
    for f in unused_files_list:
        rel_path = os.path.relpath(f)
        print(f"   {rel_path}")
    print()
    
    # Summary
    print("=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    print(f"Total Python files: {len(all_files)}")
    print(f"Used files: {len(used_files_list)} ({len(used_files_list)/len(all_files)*100:.1f}%)")
    print(f"Unused files: {len(unused_files_list)} ({len(unused_files_list)/len(all_files)*100:.1f}%)")
    print()
    
    # Note about standalone scripts
    print("=" * 80)
    print("ℹ️  NOTES")
    print("=" * 80)
    print("""
Some files may appear as 'unused' but are actually standalone utilities:
- Scripts with `if __name__ == "__main__"` blocks can be run directly
- Test files are excluded from this analysis
- Some scripts may be used manually or by other systems

Review the unused files list carefully before deleting anything!
    """.strip())


if __name__ == '__main__':
    main()
