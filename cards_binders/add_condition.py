#!/usr/bin/env python3
"""
Add "condition": "Excellent" to each item in collection.json
"""

import json
import os

def add_condition(input_file='collection.json', condition='Excellent'):
    """
    Read collection.json, add condition field to each item, and save back to the file
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, input_file)
    
    # Read the input file
    with open(input_path, 'r', encoding='utf-8') as f:
        collection = json.load(f)
    
    # Add condition to each item
    for item in collection:
        item['condition'] = condition
    
    # Write back to the same file
    with open(input_path, 'w', encoding='utf-8') as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully added condition '{condition}' to {len(collection)} items in {input_file}")

if __name__ == '__main__':
    add_condition()

