# MTG Card Binder Web UI

A beautiful web interface that displays MTG card deals in a binder format, like flipping through pages of a Magic card binder.

## Features

- 🃏 **Binder-style display**: Cards are shown like they're in a real Magic card binder with plastic sleeves
- 📄 **Flipable pages**: Navigate through pages of cards with smooth animations
- 🔍 **Filtering**: Filter by category (Excellent, Good, Fair, Expensive)
- 📊 **Sorting**: Sort by discount %, price, card name, or expansion
- 🎯 **Real-time stats**: See counts of cards by category
- 📱 **Responsive**: Works on desktop and mobile devices

## Usage

### Option 1: Run analysis + Web UI together

Run analysis using simple_version scripts and then start the web UI:

**Wishlist deals:**
```bash
python web_ui.py --wishlist
```

**Discovery:**
```bash
python web_ui.py --discovery
```

**Both:**
```bash
python web_ui.py --wishlist --discovery
```

This will:
1. Run the analysis (wishlist deals or discovery)
2. Save results to JSON files in `results/` directory
3. Start the web UI server automatically
4. Open your browser to `http://localhost:5000` to view the binder interface

### Option 2: Just view existing results

If you already have result JSON files in the `results/` directory:

```bash
python web_ui.py
```

Then open your browser to: `http://localhost:5001`

### Command Line Options

```bash
python web_ui.py [options]

Options:
  --wishlist              Run wishlist deals analysis before starting web UI
  --discovery             Run discovery analysis before starting web UI
  --wishlist-file FILE    Path to wishlist JSON file (default: wishlist.json)
  --delay SECONDS         Delay between cards when scraping (default: 10.0)
  --port PORT             Port to run server on (default: 5001)
  --min-avg30 PRICE       Min AVG30 for discovery (default: 10.0)
  --max-avg30 PRICE        Max AVG30 for discovery (default: 500.0)
  --max-candidates NUM    Max candidates to scrape for discovery (default: 10)
```

**Examples:**
```bash
# Run wishlist analysis with custom delay
python web_ui.py --wishlist --delay 5.0

# Run discovery with custom price range
python web_ui.py --discovery --min-avg30 20.0 --max-avg30 200.0 --max-candidates 5

# Run both analyses, then view results
python web_ui.py --wishlist --discovery
```

## Controls

- **Result File**: Select which result file to view
- **Category Filter**: Filter cards by deal quality (Excellent, Good, Fair, Expensive)
- **Sort By**: Choose how to sort cards (Discount %, Price, Name, Expansion)
- **Min Discount**: Filter to show only cards with at least X% discount
- **Page Navigation**: Use Previous/Next buttons or arrow keys to navigate pages

## Keyboard Shortcuts

- `←` Left Arrow: Previous page
- `→` Right Arrow: Next page

## Card Display

Each card shows:
- **Front**: Card image (if available), name, expansion, price, discount percentage, and category badge
- **Back**: Detailed information including seller, condition, market baseline, and link to CardMarket

Hover over cards to see a 3D tilt effect, making them feel like real cards in sleeves.

## Technical Details

- **Backend**: FastAPI (Python) with Uvicorn
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Data Format**: Reads JSON files from `results/` directory
- **Port**: Default port 5001 (configurable in `web_ui.py`, changed from 5000 to avoid macOS AirPlay Receiver conflict)

## Requirements

Install the required packages:

```bash
pip install fastapi uvicorn jinja2
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## File Structure

```
mtgcards/
├── web_ui.py              # Flask backend server
├── web_templates/
│   └── binder.html        # Frontend HTML/CSS/JS
├── web_static/            # Static assets (if needed)
└── results/               # JSON result files
    ├── wishlist_*.json
    ├── *_candidates_*.json
    └── ...
```

## Troubleshooting

**No result files found:**
- Make sure you've run an analysis that generates JSON files
- Check that JSON files are in the `results/` directory

**Cards not displaying:**
- Check browser console for errors
- Verify JSON file format is correct
- Make sure card images exist in `card_images/` directory (optional)

**Server won't start:**
- Check if port 5000 is already in use
- Make sure FastAPI is installed: `pip install fastapi uvicorn jinja2`
- Check for Python errors in the terminal

