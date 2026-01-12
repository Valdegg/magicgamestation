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

