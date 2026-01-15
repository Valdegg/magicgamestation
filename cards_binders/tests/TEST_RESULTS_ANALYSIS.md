# Test Results Analysis: Scryfall Image Fetching

## Issue Summary
Image fetching fails for International Edition, Alpha, and Beta sets, but works for Unlimited Edition.

## Test Cases
1. **International Edition** (CEI) - ❌ Fails
2. **Collector's Edition** (CED) - ❌ Fails  
3. **Alpha (Limited Edition)** (LEA) - ❌ Fails
4. **Beta (Limited Edition)** (LEB) - ❌ Fails
5. **Unlimited Edition** (2ED) - ✅ Works

## Current Implementation

### Set Code Mapping
- International Edition → `CEI` ✅ (correct)
- Collector's Edition → `CED` ✅ (correct)
- Alpha → `LEA` ✅ (correct)
- Beta → `LEB` ✅ (correct)
- Unlimited → `2ED` ✅ (correct)

### Query Format
Current code uses: `!"{card_name}" set:{set_code}`

## Potential Issues

### 1. Query Syntax
Scryfall API might require different syntax for certain sets:
- Some sets might need quotes: `set:"CEI"` vs `set:CEI`
- Some sets might need lowercase: `set:cei` vs `set:CEI`
- Some sets might need the full set name instead of code

### 2. Set Matching Logic
After getting results, the code tries to match by:
- Set code (exact match)
- Set name (contains match)
- Special cases for International/Collector's Edition

**Issue**: If the query returns multiple printings, the matching logic might not correctly identify the right one.

### 3. Scryfall API Behavior
Based on Scryfall documentation:
- Set codes are case-insensitive
- Some older sets might have different behavior
- The `unique:prints` parameter should return all printings

## Recommended Fixes

### Fix 1: Try Multiple Query Formats
When a query fails with 404, try alternative formats:
1. `set:{code}` (current)
2. `set:"{code}"` (with quotes)
3. `set:{code.lower()}` (lowercase)
4. `set:"{code.lower()}"` (lowercase with quotes)

### Fix 2: Fallback to Set Name
If set code query fails, try using the full set name:
- `set:"International Edition"` 
- `set:"Intl. Collectors' Edition"` (Scryfall's exact name)

### Fix 3: Improve Set Matching
After getting results, prioritize matching:
1. Exact set code match (case-insensitive)
2. Set name contains match
3. For International Edition, also check for "Intl. Collectors' Edition" or "CEI"
4. For Collector's Edition, check for "Collectors' Edition" or "CED"

### Fix 4: Handle 404 Gracefully
When Scryfall returns 404:
- Log the exact query used
- Try alternative query formats
- If all fail, return a helpful error message

## Code Changes Needed

### In `collection_ui.py` and `wishlist_ui.py`:

1. **Update `fetch_card_image_from_scryfall()`**:
   - Try multiple query formats if first one fails
   - Add fallback to set name if set code fails
   - Improve error logging

2. **Update `get_scryfall_set_code()`**:
   - Add mapping for Scryfall's exact set names
   - Handle "Intl. Collectors' Edition" → "CEI"

3. **Update set matching logic**:
   - Better handling for International Edition (CEI)
   - Better handling for Collector's Edition (CED)
   - Case-insensitive matching

## Test Queries to Verify

Based on Scryfall URLs:
- International Edition: https://scryfall.com/card/cei/263/mox-jet → `set:CEI` or `set:cei`
- Collector's Edition: https://scryfall.com/card/ced/263/mox-jet → `set:CED` or `set:ced`
- Alpha: https://scryfall.com/card/lea/262/mox-jet → `set:LEA` or `set:lea`
- Beta: https://scryfall.com/card/leb/263/mox-jet → `set:LEB` or `set:leb`
- Unlimited: https://scryfall.com/card/2ed/263/mox-jet → `set:2ED` or `set:2ed`

## Next Steps

1. Update code to try multiple query formats
2. Add better error handling and logging
3. Test with actual Scryfall API (outside sandbox)
4. Verify set matching logic works correctly

