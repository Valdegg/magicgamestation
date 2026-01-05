#!/usr/bin/env python3
"""
Convert collection.json to collection_eur.json by multiplying buy_price by 0.85
"""

import json
import os

def convert_to_eur(input_file='collection.json', output_file='collection_eur.json'):
    """
    Read collection.json, multiply all buy_price values by 0.85, and save to collection_eur.json
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, input_file)
    output_path = os.path.join(script_dir, output_file)
    
    # Read the input file
    with open(input_path, 'r', encoding='utf-8') as f:
        collection = json.load(f)
    
    # Multiply buy_price by 0.85 for each item
    for item in collection:
        if 'buy_price' in item:
            item['buy_price'] = round(item['buy_price'] * 0.85, 2)
    
    # Write to output file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully converted {len(collection)} items from {input_file} to {output_file}")
    print(f"All buy_price values have been multiplied by 0.85")

if __name__ == '__main__':
    convert_to_eur()

