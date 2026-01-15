# New Features & Specifications

## Auto-Scan New Collection Cards

**Feature:** Automatically run market scan when a card is added to collection

**Specification:**

### Trigger
- When: Card is successfully added via `POST /api/collection` endpoint
- Location: `cards_binders/collection_ui.py` - `add_collection_item()` function
- After: Card is saved to `collection.json`

### Behavior
1. **Single Card Scan**
   - Create temporary single-card JSON structure matching collection format
   - Run market scan for ONLY the newly added card
   - Use `check_wishlist_deals()` from `simple_version/wishlist_deals.py`
   - Scan should include all sets specified for the card

2. **Append to Latest Results**
   - Find most recent `collection_deals_*.json` file in `results/` directory
   - Load existing deals array from that file
   - Append new card's scan result(s) to the deals array
   - Update summary counts (total_deals, excellent, good, fair, expensive, no_data)
   - Save updated file back (preserving timestamp)

3. **Display in Browser**
   - Updated results file will automatically appear in browser
   - `load_latest_collection_scan_results()` already loads newest file by modification time
   - No browser refresh needed - new data will be available immediately

### Implementation Notes
- Run scan asynchronously (non-blocking) to avoid delaying API response
- Handle edge cases:
  - No existing `collection_deals_*.json` file → create new one
  - Scan fails → log error but don't fail card addition
  - Multiple sets per card → scan each set separately
- Use same delay/retry logic as full market scan
- Update file modification time so it remains "latest"

### Files to Modify
- `cards_binders/collection_ui.py` - `add_collection_item()` endpoint
- May need helper function in `simple_version/wishlist_deals.py` for single-card scanning

## Purchase and Sale Date Tracking

**Feature:** Include date of purchase and date of sale when registering buy/sell price when adding card

**Specification:**

### Trigger
- When: User enters `buy_price` or `sell_price` when adding/editing a card
- Location: `cards_binders/collection_ui.py` - `add_collection_item()` and `update_collection_item()` functions
- Frontend: `web_templates/collection_binder.html` - card add/edit form

### Behavior
1. **Date of Purchase**
   - When `buy_price` is provided, automatically capture and store `purchase_date`
   - Default to current date/time if not explicitly provided
   - Allow user to optionally specify a different purchase date
   - Store date in ISO format (YYYY-MM-DD) or ISO datetime format (YYYY-MM-DDTHH:MM:SS)
   - Display purchase date alongside buy price in card display

2. **Date of Sale**
   - When `sell_price` is provided, automatically capture and store `sale_date`
   - Default to current date/time if not explicitly provided
   - Allow user to optionally specify a different sale date
   - Store date in ISO format (YYYY-MM-DD) or ISO datetime format (YYYY-MM-DDTHH:MM:SS)
   - Display sale date alongside sell price in card display

3. **Data Storage**
   - Add `purchase_date` field to collection item when `buy_price` is set
   - Add `sale_date` field to collection item when `sell_price` is set
   - Both fields should be optional and nullable
   - If price is removed, corresponding date should also be removed (or kept for historical tracking - clarify requirement)

4. **Display Updates**
   - Show purchase date next to buy price in card hover overlay
   - Show sale date next to sell price in card hover overlay
   - Format dates in user-friendly format (e.g., "Jan 15, 2024" or "2024-01-15")
   - Consider adding date to card details view if available

### Implementation Notes
- Use Python's `datetime` module for date handling
- Store dates as ISO format strings in JSON for consistency
- Frontend should include date input fields (type="date") for purchase_date and sale_date
- Date inputs should be optional - if not provided, use current date
- Handle edge cases:
  - User removes buy_price → decide if purchase_date should be removed or kept
  - User removes sell_price → decide if sale_date should be removed or kept
  - User updates buy_price → decide if purchase_date should be updated or kept original
  - User updates sell_price → decide if sale_date should be updated or kept original
- Consider timezone handling if datetime format is used
- Ensure backward compatibility - existing cards without dates should still work

### Files to Modify
- `cards_binders/collection_ui.py` - `add_collection_item()` endpoint
- `cards_binders/collection_ui.py` - `update_collection_item()` endpoint
- `web_templates/collection_binder.html` - Add date input fields to card form
- `web_templates/collection_binder.html` - Update card display to show dates
- May need to update `wishlist_ui.py` - `move_wishlist_to_collection()` if dates should be captured there too

## Bottom Navigation Controls

**Feature:** Add "Add Cards" button at bottom next to "Sort by" button

**Specification:**

### Trigger
- When: Page loads and collection is displayed
- Location: Bottom of page, in the pagination/controls area
- Placement: Next to the "Sort by" dropdown control

### Behavior
1. **Add Cards Button**
   - Create a new button labeled "Add Cards" or "➕ Add Cards"
   - Position it at the bottom of the page, next to the "Sort by" dropdown
   - Button should trigger the same action as the existing "Add Card" functionality
   - Opens the card add/edit modal when clicked
   - Style should match existing button styles (consistent with page navigation buttons)

2. **Sort by Button Location**
   - Move or duplicate the "Sort by" dropdown to the bottom controls area
   - Position it next to the "Add Cards" button
   - Maintain existing sort functionality
   - Can keep original sort dropdown in header OR move it entirely to bottom (clarify preference)

3. **Layout**
   - Create a bottom controls container/bar if it doesn't exist
   - Position controls horizontally: [Add Cards] [Sort by: dropdown]
   - Place this control bar above or below the pagination controls (Previous/Next buttons)
   - Ensure controls are visible and accessible when scrolling through pages
   - Consider making controls sticky/fixed at bottom for easy access

4. **Styling**
   - Match existing button styles (`.page-btn` or similar)
   - Use consistent colors and hover effects
   - Ensure responsive design - controls should work on mobile/tablet
   - Add appropriate spacing between buttons

### Implementation Notes
- The "Sort by" dropdown is currently added dynamically via JavaScript in `collection_ui.py`
- Need to either:
  - Move the sort dropdown from header stats area to bottom controls
  - OR duplicate it in both locations
  - OR keep header version and add bottom version
- "Add Cards" button should call the same function that opens the add card modal
- Check if there's an existing function to open the modal (e.g., `openModal()`, `showAddCardModal()`)
- Handle edge cases:
  - Controls should be visible even when collection is empty
  - Controls should work correctly with pagination
  - Ensure controls don't overlap with pagination buttons
- Consider accessibility: proper button labels, keyboard navigation support

### Files to Modify
- `cards_binders/collection_ui.py` - Modify `addSortDropdown()` function to add controls at bottom
- `web_templates/collection_binder.html` - Add bottom controls container/bar structure
- `web_templates/collection_binder.html` - Add "Add Cards" button HTML and JavaScript handler
- May need to update CSS for bottom controls positioning and styling

## Add Card Modal UX Improvements

**Feature:** Updates to the Add Card to Collection modal for better user experience

**Specification:**

### Trigger
- When: Modal opens for adding/editing a card
- Location: `web_templates/collection_binder.html` - Add/Edit Card modal
- Fields affected: Purchase Date, Sale Date, Card Name autocomplete

### Behavior
1. **Default Dates to Current Date**
   - When modal opens, automatically set `purchaseDate` field to today's date (if not editing existing card)
   - When modal opens, automatically set `saleDate` field to today's date (if not editing existing card)
   - Format: Use ISO date format (YYYY-MM-DD) for date input fields
   - When editing existing card: Pre-populate with existing dates if they exist, otherwise default to current date
   - User can still manually change dates if needed

2. **Enter Key Navigation in Card Name Autocomplete**
   - When user types in Card Name field and autocomplete dropdown is visible
   - When user presses Enter key:
     - If autocomplete suggestion is selected/highlighted: Select that suggestion AND move focus to next field
     - If no suggestion selected but dropdown is visible: Select first suggestion (if any) AND move focus to next field
     - If dropdown is not visible or no suggestions: Move focus to next field (Sets input field)
   - Behavior should mimic Tab key functionality - move to next focusable field in form
   - Prevent form submission when Enter is pressed in autocomplete context
   - Ensure autocomplete dropdown closes when Enter is pressed

3. **Field Order**
   - Card Name → Sets → Buy Price → Purchase Date → Condition → Source → Sell Price → Sale Date → Notes
   - Enter key should follow this tab order when moving between fields

### Implementation Notes
- Use JavaScript's `new Date().toISOString().split('T')[0]` or similar to get current date in YYYY-MM-DD format
- Set date input values when modal opens: `document.getElementById('purchaseDate').value = currentDate`
- Handle both "Add Card" and "Edit Card" scenarios:
  - Add Card: Always default dates to current date
  - Edit Card: Use existing dates if present, otherwise default to current date
- For Enter key handling in autocomplete:
  - Listen for `keydown` or `keypress` event on Card Name input field
  - Check if `event.key === 'Enter'` or `event.keyCode === 13`
  - Check if autocomplete dropdown is visible (`cardNameDropdown` element)
  - If suggestion is selected, fill in the value first
  - Then use `event.preventDefault()` to prevent form submission
  - Use `document.getElementById('cardSetsInput').focus()` or `nextField.focus()` to move to next field
  - Close autocomplete dropdown after selection
- Ensure Enter key doesn't submit form when used in autocomplete context
- Test edge cases:
  - Empty autocomplete dropdown → still move to next field
  - Multiple suggestions → select highlighted/first one
  - No suggestions → just move to next field
  - User presses Enter multiple times → should cycle through fields

### Files to Modify
- `web_templates/collection_binder.html` - Add JavaScript to set default dates on modal open
- `web_templates/collection_binder.html` - Add Enter key handler for Card Name autocomplete
- `web_templates/collection_binder.html` - Update modal initialization/reset logic to set default dates
- May need to update autocomplete selection logic to handle Enter key properly

## Format Filter Checkboxes (Old School / Premodern)

**Feature:** Add filter checkboxes for Old School and Premodern formats to filter collection cards

**Specification:**

### Trigger
- When: Page loads and collection is displayed
- Location: Filter controls area (header stats section or bottom controls area)
- Placement: Next to existing "Show Sold Only" checkbox filter
- Default state: Both checkboxes checked (show cards that are Old School legal OR Premodern legal)

### Behavior
1. **Format Filter Checkboxes**
   - Create two checkboxes: "Old School" and "Premodern"
   - Both checkboxes should be checked by default
   - Position checkboxes next to existing "Show Sold Only" filter checkbox
   - Style should match existing filter checkbox (consistent colors, sizing, spacing)
   - Labels should be clear: "Old School" and "Premodern"

2. **Filtering Logic**
   - Cards are filtered based on `old_school_legal` and `premodern_legal` boolean fields in collection data
   - Filtering should work as an OR operation: show cards if EITHER checkbox is checked AND the card matches that format
   - Examples:
     - Both checked (default): Show all cards where `old_school_legal === true` OR `premodern_legal === true`
     - Only "Old School" checked: Show only cards where `old_school_legal === true`
     - Only "Premodern" checked: Show only cards where `premodern_legal === true`
     - Neither checked: Show no cards (or show all cards - clarify requirement)
   - Filter should work in combination with existing "Show Sold Only" filter (AND operation)

3. **State Persistence**
   - Store filter state in localStorage (similar to existing sort and filter state)
   - Keys: `collection_filter_old_school` and `collection_filter_premodern`
   - Restore filter state on page load
   - Default to both checked if no saved state exists

4. **Filter Application**
   - Filter should be applied client-side in JavaScript (similar to existing `filterCards()` function)
   - Filter should be applied after cards are loaded from API
   - Filter should work with pagination (filtered cards should be paginated)
   - Filter should work with sorting (sort should be applied to filtered results)
   - When filter changes, reset to page 1 and reload cards

5. **UI Updates**
   - Update card count display to reflect filtered count
   - Ensure filter checkboxes are visible in both header and bottom control areas (if bottom controls exist)
   - Sync checkbox state between header and bottom locations if both exist
   - Add visual feedback when filters are active (e.g., highlight active filters)

### Implementation Notes
- Cards in `collection.json` have `old_school_legal` and `premodern_legal` boolean fields
- Cards also have `format_validity` field which can be: "both", "old_school_only", "premodern_only", or "neither"
- Filter should check the boolean fields (`old_school_legal`, `premodern_legal`) rather than parsing `format_validity` string
- Handle edge cases:
  - Cards without format fields → treat as not matching any format (or show all - clarify requirement)
  - Cards with `old_school_legal: false` and `premodern_legal: false` → should be hidden when filters are active
  - Both checkboxes unchecked → decide behavior: show no cards OR show all cards regardless of format
- Filter should integrate with existing `filterCards()` function in `collection_ui.py`
- Filter state should sync with existing localStorage pattern used for sort and "Show Sold Only" filter
- When filter changes, trigger same reload mechanism as existing filter (clear `originalCards`, reload page, etc.)

### Data Structure
- Collection items have the following format fields:
  ```json
  {
    "old_school_legal": true,
    "premodern_legal": true,
    "format_validity": "both",
    "old_school_sets": ["2ed", "3ed"],
    "premodern_sets": ["4ed", "5ed"]
  }
  ```

### Files to Modify
- `cards_binders/collection_ui.py` - Add format filter checkboxes to filter controls area
- `cards_binders/collection_ui.py` - Update `filterCards()` function to include format filtering logic
- `cards_binders/collection_ui.py` - Add localStorage persistence for format filter state
- `cards_binders/collection_ui.py` - Sync format filter checkboxes between header and bottom locations
- May need to update `web_templates/collection_binder.html` if filter UI elements need HTML structure changes

## Format Filter Checkboxes for MTG Scanner (Old School / Premodern)

**Feature:** Add filter checkboxes for Old School and Premodern formats to filter wishlist deals in the MTG Scanner interface

**Specification:**

### Trigger
- When: Page loads and wishlist deals are displayed in MTG Scanner
- Location: FILTERS section in `web_templates/marketscan_binder.html`
- Placement: Add as a new filter group in the filter row, positioned after "Min Available Items" filter
- Default state: Both checkboxes checked (show cards that are Old School legal OR Premodern legal)

### Behavior
1. **Format Filter Checkboxes**
   - Create a new filter group labeled "🎯 Formats:" (or similar icon)
   - Add two checkboxes: "Old School" and "Premodern"
   - Both checkboxes should be checked by default
   - Position in the FILTERS section alongside existing filters (Sets, Countries, Price Range, Min Available Items)
   - Style should match existing filter groups (consistent colors, spacing, layout)
   - Checkboxes should be arranged horizontally: [☑ Old School] [☑ Premodern]

2. **Filtering Logic**
   - Cards are filtered based on `old_school_legal` and `premodern_legal` boolean fields in deal data
   - Filtering should work as an OR operation: show cards if EITHER checkbox is checked AND the card matches that format
   - Examples:
     - Both checked (default): Show all cards where `old_school_legal === true` OR `premodern_legal === true`
     - Only "Old School" checked: Show only cards where `old_school_legal === true`
     - Only "Premodern" checked: Show only cards where `premodern_legal === true`
     - Neither checked: Show no cards (or show all cards regardless of format - clarify requirement)
   - Filter should work in combination with all existing filters (Sets, Countries, Price Range, Category, etc.) - all filters use AND operation

3. **Data Flow**
   - Format information (`old_school_legal`, `premodern_legal`) must be present in wishlist.json items
   - When wishlist deals are processed, format fields should be preserved from wishlist items
   - Format fields should be included in the normalized deal data structure
   - Format fields should be passed through the API response to the frontend

4. **State Persistence**
   - Store filter state in localStorage (similar to existing filter state)
   - Keys: `scanner_filter_old_school` and `scanner_filter_premodern`
   - Restore filter state on page load
   - Default to both checked if no saved state exists

5. **Filter Application**
   - Filter should be applied client-side in JavaScript in the `applyFilters()` function
   - Filter should be applied after deals are loaded from API
   - Filter should work with all existing filters (Sets, Countries, Price Range, Category, Min Discount, etc.)
   - Filter should work with sorting
   - When filter changes, update displayed cards and summary counts immediately
   - Update card count display to reflect filtered count

6. **UI Updates**
   - Add format filter group to FILTERS section HTML structure
   - Update `applyFilters()` function to include format filtering logic
   - Update summary counts (Total Cards, Excellent, Good, Fair) to reflect filtered results
   - Ensure filter checkboxes are visible and accessible
   - Add visual feedback when filters are active (e.g., highlight active filters)

### Implementation Notes
- Wishlist items in `wishlist.json` should have `old_school_legal` and `premodern_legal` boolean fields (assumed to be present)
- Format fields should be preserved when wishlist items are loaded in `simple_version/wishlist_deals.py`
- Format fields should be included in the deal structure when deals are created
- Format fields should be included in normalized deal data in `web_ui.py` `normalize_deal_data()` function
- Format fields should be passed through API response (`/api/deals` endpoint)
- Handle edge cases:
  - Cards without format fields → treat as not matching any format (or show all - clarify requirement)
  - Cards with `old_school_legal: false` and `premodern_legal: false` → should be hidden when filters are active
  - Both checkboxes unchecked → decide behavior: show no cards OR show all cards regardless of format
- Filter should integrate with existing filter system in `marketscan_binder.html`
- Filter state should sync with existing localStorage pattern used for other filters
- When filter changes, trigger same update mechanism as existing filters (call `applyFilters()`, update counts, etc.)

### Data Structure
- Wishlist items should have format fields:
  ```json
  {
    "name": "Lightning Bolt",
    "sets": ["Beta", "Unlimited"],
    "old_school_legal": true,
    "premodern_legal": true,
    "format_validity": "both"
  }
  ```
- Normalized deal data should include format fields:
  ```json
  {
    "card_name": "Lightning Bolt",
    "expansion": "Beta",
    "old_school_legal": true,
    "premodern_legal": true,
    "format_validity": "both",
    ...
  }
  ```

### Files to Modify
- `web_templates/marketscan_binder.html` - Add format filter group HTML structure in FILTERS section
- `web_templates/marketscan_binder.html` - Update `applyFilters()` function to include format filtering logic
- `web_templates/marketscan_binder.html` - Add localStorage persistence for format filter state
- `web_templates/marketscan_binder.html` - Update filter initialization to set default format filter state
- `cards_binders/web_ui.py` - Update `normalize_deal_data()` function to include format fields from card data
- `cards_binders/simple_version/wishlist_deals.py` - Preserve format fields from wishlist items when creating deals
- May need to update `cards_binders/web_ui.py` `/api/deals` endpoint if server-side filtering is preferred (currently filters are client-side)

