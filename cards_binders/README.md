# MTG Cards Manager

A comprehensive web application for managing Magic: The Gathering cards, tracking your collection, managing your wishlist, and scanning the market for deals.

## 🎴 Features

### 🗂️ Collection Manager
Track your card collection. Record buy prices, condition, source, and sell prices for cards you own.

**Features:**
- **Collection tracking**: Record detailed information about cards you own
- **Buy price tracking**: Record what you paid for each card
- **Condition management**: Track card condition (Near Mint, Lightly Played, Moderately Played, Heavily Played, Damaged)
- **Source tracking**: Record where you bought each card (Cardmarket, Local Store, Trade, etc.)
- **Sell price tracking**: Track potential or actual sell prices
- **Binder-style display**: View your collection in a beautiful card binder format
- **Set-specific images**: Automatically fetches card images from Scryfall for the specified set
- **Card autocomplete**: Smart autocomplete for card names
- **Add/Edit/Archive**: Full CRUD operations for collection items

### 📋 Wishlist Manager
Manage your card wishlist. Add cards you want to buy, specify sets, and track what you're looking for.

**Features:**
- **Binder-style interface**: View your wishlist in a beautiful card binder format
- **Card autocomplete**: Smart autocomplete for card names using local database and Scryfall API
- **Set selection**: Filtered dropdown for selecting sets, ordered by release date (oldest first)
- **One card per set**: Each card in your wishlist is displayed once per set
- **Add/Edit cards**: Easy modal interface for adding and editing wishlist items
- **Archive cards**: Remove cards from wishlist and move them to archived list
- **Set-specific images**: Automatically fetches card images from Scryfall for the specified set
- **Image management**: On-demand image fetching when cards are displayed

### 📊 Market Scanner
Scan the Cardmarket for deals on cards in your wishlist. View prices, discounts, and find the best opportunities to buy.

**Features:**
- **Binder-style display**: Cards are shown like they're in a real Magic card binder with plastic sleeves
- **Flipable pages**: Navigate through pages of cards with smooth animations
- **Advanced filtering**: Filter by category (Excellent, Good, Fair), discount percentage, price range, sets, and countries
- **Sorting**: Sort by discount %, price, card name, or expansion
- **Seller grouping**: Option to group cards by seller, with one seller per row
- **Real-time stats**: See counts of cards by category
- **Price information**: View current price, average 30-day price, discount percentage, and volume data
- **Responsive design**: Works on desktop and mobile devices

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository** (or navigate to the project directory)

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up configuration** (optional):
   - Copy `config.env.template` to `config.env` if you need custom settings
   - Edit `config.env` with your preferences

### Running the Application

**Start the unified web application (without scanning):**
```bash
python main_app.py
```

This will start the server on `http://0.0.0.0:5010` by default and use existing market scan results.

**Run market scan before starting server:**
```bash
python main_app.py --scan
```

This will:
1. Scan the market for deals on cards in your wishlist
2. Save results to `results/wishlist_deals_YYYYMMDD_HHMMSS.json`
3. Start the web server with the new results

**Custom options:**
```bash
# Custom port
python main_app.py --port 6000

# Run scan with custom delay between requests
python main_app.py --scan --delay 15

# Custom host and port
python main_app.py --host 127.0.0.1 --port 5010

# Use a different wishlist file for scanning
python main_app.py --scan --wishlist-file my_wishlist.json
```

### Accessing the Application

Once the server is running, open your browser and navigate to:

- **Home**: `http://localhost:5010/`
- **Collection**: `http://localhost:5010/collection`
- **Wishlist**: `http://localhost:5010/wishlist`
- **Market Scanner**: `http://localhost:5010/market`

## 📁 Data Files

The application uses several JSON files to store data:

- **`wishlist.json`**: Your card wishlist (cards you want to buy)
- **`wishlist_archived.json`**: Archived wishlist items (removed cards)
- **`collection.json`**: Your card collection (cards you own)
- **`collection_archived.json`**: Archived collection items
- **`sets_data.json`**: List of available Magic: The Gathering sets
- **`results/`**: Directory containing market scan results (JSON files)

## 🔧 Individual Components

### Running Individual Components

While `main_app.py` provides a unified interface, you can also run individual components separately:

**Market Scanner (web_ui.py):**
```bash
python web_ui.py --port 5001
```

**Wishlist Manager (wishlist_ui.py):**
```bash
python wishlist_ui.py --port 5002
```

**Collection Manager (collection_ui.py):**
```bash
python collection_ui.py --port 5003
```

### Running Market Scans

To scan the market for deals on your wishlist:

```bash
python simple_version/wishlist_deals.py
```

This will:
1. Read your `wishlist.json` file
2. Scrape Cardmarket for current listings
3. Identify deals based on your criteria
4. Save results to `results/wishlist_deals_YYYYMMDD_HHMMSS.json`
5. Results can then be viewed in the Market Scanner UI

**Options:**
```bash
python simple_version/wishlist_deals.py --delay 15  # Delay between requests (default: 10-15 seconds)
```

## 🗂️ Collection Manager Details

### Adding Cards to Collection

1. Click the "➕ Add Card" button
2. Enter card name (with autocomplete)
3. Select sets
4. Enter optional information:
   - **Buy Price**: What you paid for the card (in €)
   - **Condition**: Card condition (dropdown)
   - **Source**: Where you bought it (e.g., "Cardmarket", "Local Store")
   - **Sell Price**: Potential or actual sell price (in €)
   - **Notes**: Any additional notes
5. Click "Save Card"

### Collection Fields

- **Buy Price**: Purchase price in euros
- **Condition**: Near Mint, Lightly Played, Moderately Played, Heavily Played, or Damaged
- **Source**: Where you acquired the card
- **Sell Price**: Potential or actual selling price
- **Notes**: Additional information about the card

### Display

Cards are displayed with:
- Card name and expansion
- Buy price (blue)
- Condition (yellow)
- Source (purple)
- Sell price (green)

## 📋 Wishlist Manager Details

### Adding Cards

1. Click the "➕ Add Card" button
2. Type the card name (autocomplete will suggest matches)
3. Select sets from the dropdown (filtered by typing)
4. Click "Save Card"

### Editing Cards

1. Click on any card in the binder
2. Modify the card name or sets
3. Click "Save Card"

### Archiving Cards

1. Click the "×" button on any card
2. Confirm the removal
3. The card will be moved to `wishlist_archived.json`

### Card Images

- Images are automatically fetched from Scryfall when needed
- Set-specific images are stored in `card_images_sets/`
- Generic images (oldest printing) are stored in `card_images/`
- Images are fetched on-demand when cards are displayed

## 🗂️ Collection Manager Details

### Adding Cards to Collection

1. Click the "➕ Add Card" button
2. Enter card name (with autocomplete)
3. Select sets
4. Enter optional information:
   - **Buy Price**: What you paid for the card (in €)
   - **Condition**: Card condition (dropdown)
   - **Source**: Where you bought it (e.g., "Cardmarket", "Local Store")
   - **Sell Price**: Potential or actual sell price (in €)
   - **Notes**: Any additional notes
5. Click "Save Card"

### Collection Fields

- **Buy Price**: Purchase price in euros
- **Condition**: Near Mint, Lightly Played, Moderately Played, Heavily Played, or Damaged
- **Source**: Where you acquired the card
- **Sell Price**: Potential or actual selling price
- **Notes**: Additional information about the card

### Display

Cards are displayed with:
- Card name and expansion
- Buy price (blue)
- Condition (yellow)
- Source (purple)
- Sell price (green)

## 🖼️ Image Management

### Image Directories

- **`card_images/`**: Generic card images (oldest printing)
- **`card_images_sets/`**: Set-specific card images (format: `card_name;set_name.jpg`)

### Image Fetching

Images are automatically fetched from Scryfall API when:
- A card is displayed and the image doesn't exist locally
- You add a new card with a specific set
- The image fetch endpoint is called (`/api/fetch-card-image`)

### Image Naming

- Generic: `card_name.jpg` (e.g., `black_lotus.jpg`)
- Set-specific: `card_name;set_name.jpg` (e.g., `black_lotus;alpha.jpg`)

## 🌐 API Endpoints

### Collection (`/collection`)

- `GET /collection` - Collection management page
- `GET /collection/api/collection` - Get full collection
- `GET /collection/api/collection-cards` - Get expanded cards (one per set)
- `GET /collection/api/sets` - Get available sets
- `POST /collection/api/collection` - Add new collection item
- `PUT /collection/api/collection/{index}` - Update collection item
- `DELETE /collection/api/collection/{index}` - Archive collection item
- `GET /collection/api/autocomplete-card` - Get card name autocomplete suggestions
- `GET /collection/api/fetch-card-image` - Fetch card image from Scryfall

## 📦 Dependencies

Key dependencies (see `requirements.txt` for full list):

- **FastAPI**: Modern web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI
- **Requests**: HTTP library for API calls
- **BeautifulSoup4**: HTML parsing for web scraping
- **Jinja2**: Template engine for HTML rendering

## 🏗️ Project Structure

```
mtgcards/
├── main_app.py              # Unified web application (main entry point)
├── web_ui.py                # Market scanner component
├── wishlist_ui.py           # Wishlist manager component
├── collection_ui.py         # Collection manager component
├── card_autocomplete.py    # Card name autocomplete functionality
├── card_image_fetcher.py   # Image fetching utilities
├── card_lookup.py          # Card lookup utilities
├── fetch_live_listings_simple.py  # Cardmarket scraping utilities
├── simple_version/
│   ├── wishlist_deals.py   # Market scanning script
│   └── discovery.py        # Discovery analysis script
├── web_templates/
│   ├── binder.html         # Market scanner UI template
│   ├── wishlist_binder.html # Wishlist UI template
│   └── collection_binder.html # Collection UI template
├── card_images/            # Generic card images
├── card_images_sets/       # Set-specific card images
├── results/                # Market scan results (JSON files)
├── wishlist.json           # Wishlist data
├── collection.json          # Collection data
├── sets_data.json          # Available sets list
└── requirements.txt        # Python dependencies
```

## 🚢 Deployment

### For Production

The application is designed to run on a single port with all three sections accessible via different routes. For subdomain deployment:

1. **Single Domain**: Use the unified `main_app.py` with routes:
   - `/` - Home
   - `/market` - Market Scanner
   - `/wishlist` - Wishlist
   - `/collection` - Collection

2. **Subdomains**: Use a reverse proxy (nginx/traefik) to route:
   - `market.yourdomain.com` → `/market`
   - `wishlist.yourdomain.com` → `/wishlist`
   - `collection.yourdomain.com` → `/collection`

### Example nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:5010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔍 Troubleshooting

### Images Not Loading

- Check that `card_images/` and `card_images_sets/` directories exist
- Verify Scryfall API is accessible (check network connectivity)
- Check browser console for 404 errors

### API Endpoints Returning 404

- Ensure you're using the correct prefixed paths (`/market/api/`, `/wishlist/api/`, `/collection/api/`)
- Check that the server is running on the correct port
- Verify the route handlers are properly registered

### Market Scanner Shows "No Cards Found"

- Ensure you have result JSON files in the `results/` directory
- Run `python simple_version/wishlist_deals.py` to generate results
- Check that the result files are valid JSON

## 📝 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📧 Support

[Add support/contact information here]
