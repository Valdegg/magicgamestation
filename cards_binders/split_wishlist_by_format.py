#!/usr/bin/env python3
"""
Split wishlist.json into format-specific files.

Creates:
- wishlist_old_school.json: Cards legal in Old School 93/94
- wishlist_premodern.json: Cards legal in Premodern
"""

import json
import sys


def split_wishlist(input_file="wishlist.json"):
    """
    Split wishlist into format-specific files.
    
    Args:
        input_file: Path to the wishlist JSON file
    """
    print("=" * 60)
    print("Wishlist Format Splitter")
    print("=" * 60)
    
    # Load wishlist
    print(f"\n[1/3] Loading {input_file}...")
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            wishlist = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' not found")
        return
    except Exception as e:
        print(f"❌ Error loading {input_file}: {e}")
        return
    
    print(f"✅ Loaded {len(wishlist)} cards from {input_file}")
    
    # Filter cards by format
    print("\n[2/3] Filtering cards by format...")
    
    old_school_cards = []
    premodern_cards = []
    
    for card in wishlist:
        # Check if card has format information
        old_school_legal = card.get("old_school_legal", False)
        premodern_legal = card.get("premodern_legal", False)
        
        # Add to Old School list if legal
        if old_school_legal:
            old_school_cards.append(card)
        
        # Add to Premodern list if legal
        if premodern_legal:
            premodern_cards.append(card)
    
    print(f"  Old School 93/94 legal: {len(old_school_cards)} cards")
    print(f"  Premodern legal: {len(premodern_cards)} cards")
    
    # Save split files
    print("\n[3/3] Saving split files...")
    
    # Save Old School wishlist
    old_school_file = "wishlist_old_school.json"
    try:
        with open(old_school_file, "w", encoding="utf-8") as f:
            json.dump(old_school_cards, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(old_school_cards)} cards to {old_school_file}")
    except Exception as e:
        print(f"❌ Error saving {old_school_file}: {e}")
        return
    
    # Save Premodern wishlist
    premodern_file = "wishlist_premodern.json"
    try:
        with open(premodern_file, "w", encoding="utf-8") as f:
            json.dump(premodern_cards, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(premodern_cards)} cards to {premodern_file}")
    except Exception as e:
        print(f"❌ Error saving {premodern_file}: {e}")
        return
    
    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Total cards processed: {len(wishlist)}")
    print(f"  Old School 93/94 cards: {len(old_school_cards)}")
    print(f"  Premodern cards: {len(premodern_cards)}")
    
    # Count cards that appear in both
    both_count = sum(1 for card in wishlist 
                     if card.get("old_school_legal") and card.get("premodern_legal"))
    print(f"  Cards legal in both formats: {both_count}")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    # Allow custom input file via command line
    input_file = sys.argv[1] if len(sys.argv) > 1 else "wishlist.json"
    split_wishlist(input_file)
