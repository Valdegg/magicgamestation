#!/usr/bin/env python3
"""
MTG Cards Unified Web Application

Combines three main sections:
1. Collection Manager - Manage your card collection
2. Wishlist Manager - Manage your card wishlist
3. Market Scanner - View deals and scan the market for wishlist items

All running on a single port with navigation between sections.
"""

import os
import sys
import argparse
import re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# Create main FastAPI app
app = FastAPI(
    title="MTG Cards Manager",
    description="Unified MTG Card Management System",
    version="1.0.0"
)

# Configuration
DEFAULT_PORT = 5010
IMAGE_DIR = "card_images"
IMAGE_DIR_SETS = "card_images_sets"

# Ensure image directories exist
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR_SETS, exist_ok=True)

# Mount static files
if os.path.exists(IMAGE_DIR):
    app.mount("/card_images", StaticFiles(directory=IMAGE_DIR), name="card_images")
if os.path.exists(IMAGE_DIR_SETS):
    app.mount("/card_images_sets", StaticFiles(directory=IMAGE_DIR_SETS), name="card_images_sets")
if os.path.exists('web_static'):
    app.mount("/static", StaticFiles(directory="web_static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Navigation HTML component
NAVIGATION_HTML = """
<nav class="main-navigation">
    <div class="nav-container">
        <a href="/" class="nav-logo">🎴 MTG Cards</a>
        <div class="nav-links">
            <a href="/" class="nav-link">Home</a>
            <a href="/collection" class="nav-link">Collection</a>
            <a href="/wishlist" class="nav-link">Wishlist</a>
            <a href="/market" class="nav-link">Market Scanner</a>
            <a href="/games" class="nav-link">Games</a>
        </div>
    </div>
</nav>
"""

NAVIGATION_CSS = """
<style>
.main-navigation {
    background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
    border-bottom: 2px solid #d4af37;
    padding: 0;
    position: sticky;
    top: 0;
    z-index: 1000;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.nav-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 15px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.nav-logo {
    font-size: 1.5em;
    font-weight: bold;
    color: #d4af37;
    text-decoration: none;
    font-family: 'Cinzel', serif;
    transition: color 0.2s;
}

.nav-logo:hover {
    color: #f4d03f;
}

.nav-links {
    display: flex;
    gap: 20px;
    align-items: center;
}

.nav-link {
    color: #e0e0e0;
    text-decoration: none;
    font-weight: 500;
    padding: 8px 16px;
    border-radius: 6px;
    transition: all 0.2s;
    font-size: 0.95em;
}

.nav-link:hover {
    background: rgba(212, 175, 55, 0.1);
    color: #d4af37;
}

.nav-link.active {
    background: rgba(212, 175, 55, 0.2);
    color: #d4af37;
    border-bottom: 2px solid #d4af37;
}

@media (max-width: 768px) {
    .nav-container {
        flex-direction: column;
        gap: 15px;
    }
    
    .nav-links {
        flex-wrap: wrap;
        justify-content: center;
        gap: 10px;
    }
    
    .nav-link {
        padding: 6px 12px;
        font-size: 0.85em;
    }
}
</style>
"""


def inject_navigation(html_content: str, current_section: str = "") -> str:
    """Inject navigation into HTML content."""
    if not html_content or not isinstance(html_content, str):
        return html_content
    
    # Update navigation links with active state
    nav_html = NAVIGATION_HTML
    nav_html = nav_html.replace('href="/" class="nav-link"', f'href="/" class="nav-link{" active" if current_section == "home" else ""}"')
    nav_html = nav_html.replace('href="/market" class="nav-link"', f'href="/market" class="nav-link{" active" if current_section == "market" else ""}"')
    nav_html = nav_html.replace('href="/wishlist" class="nav-link"', f'href="/wishlist" class="nav-link{" active" if current_section == "wishlist" else ""}"')
    nav_html = nav_html.replace('href="/collection" class="nav-link"', f'href="/collection" class="nav-link{" active" if current_section == "collection" else ""}"')
    nav_html = nav_html.replace('href="/games" class="nav-link"', f'href="/games" class="nav-link{" active" if current_section == "games" else ""}"')
    
    # Try to inject after <body> tag
    if "<body" in html_content:
        # Find the body tag and inject after it
        body_idx = html_content.find("<body")
        if body_idx != -1:
            # Find the closing > of body tag
            body_end = html_content.find(">", body_idx) + 1
            html_content = html_content[:body_end] + nav_html + "\n" + html_content[body_end:]
    elif "<body>" in html_content:
        html_content = html_content.replace("<body>", "<body>" + nav_html, 1)
    
    # Inject CSS in head
    if "</head>" in html_content:
        html_content = html_content.replace("</head>", NAVIGATION_CSS + "\n</head>", 1)
    elif "<head>" in html_content and "</head>" not in html_content:
        html_content = html_content.replace("<head>", "<head>" + NAVIGATION_CSS, 1)
    
    return html_content


@app.get("/", response_class=HTMLResponse)
async def home_page():
    """Home page with links to all sections."""
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MTG Cards Manager - Home</title>
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Source+Sans+Pro:wght@400;600&display=swap" rel="stylesheet">
        {NAVIGATION_CSS}
        <style>
            body {{
                font-family: 'Source Sans Pro', -apple-system, BlinkMacSystemFont, sans-serif;
                background: radial-gradient(ellipse at center, #3d3020 0%, #1a1510 50%, #0d0a08 100%);
                background-attachment: fixed;
                min-height: 100vh;
                margin: 0;
                padding: 0;
                color: #e0e0e0;
            }}
            
            .home-container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 60px 20px;
            }}
            
            .home-header {{
                text-align: center;
                margin-bottom: 60px;
            }}
            
            .home-header h1 {{
                font-family: 'Cinzel', serif;
                font-size: 3em;
                color: #d4af37;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
            }}
            
            .home-header p {{
                font-size: 1.2em;
                color: #b0b0b0;
            }}
            
            .sections-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 30px;
                margin-top: 40px;
            }}
            
            .section-card {{
                background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%);
                border: 2px solid #3a3a3a;
                border-radius: 12px;
                padding: 30px;
                text-align: center;
                transition: all 0.3s;
                cursor: pointer;
                text-decoration: none;
                color: inherit;
                display: block;
            }}
            
            .section-card:hover {{
                transform: translateY(-5px);
                border-color: #d4af37;
                box-shadow: 0 8px 24px rgba(212, 175, 55, 0.3);
            }}
            
            .section-card h2 {{
                font-family: 'Cinzel', serif;
                color: #d4af37;
                font-size: 1.8em;
                margin-bottom: 15px;
            }}
            
            .section-card p {{
                color: #b0b0b0;
                line-height: 1.6;
                margin-bottom: 20px;
            }}
            
            .section-icon {{
                font-size: 3em;
                margin-bottom: 15px;
            }}
            
            .section-link {{
                display: inline-block;
                padding: 10px 24px;
                background: linear-gradient(135deg, #d4af37 0%, #b8941f 100%);
                color: #1a1a1a;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                transition: all 0.2s;
            }}
            
            .section-link:hover {{
                background: linear-gradient(135deg, #f4d03f 0%, #d4af37 100%);
                transform: scale(1.05);
            }}
        </style>
    </head>
    <body>
        {NAVIGATION_HTML.replace('href="/" class="nav-link"', 'href="/" class="nav-link active"')}
        <div class="home-container">
            <div class="home-header">
                <h1>🎴 MTG Cards Manager</h1>
                <p>Your complete Magic: The Gathering card management system</p>
            </div>
            
            <div class="sections-grid">
                <a href="/collection" class="section-card">
                    <div class="section-icon">🗂️</div>
                    <h2>Collection</h2>
                    <p>Track your card collection. Record buy prices, condition, source, and sell prices for cards you own.</p>
                    <span class="section-link">Manage Collection →</span>
                </a>
                
                <a href="/wishlist" class="section-card">
                    <div class="section-icon">📋</div>
                    <h2>Wishlist</h2>
                    <p>Manage your card wishlist. Add cards you want to buy, specify sets, and track what you're looking for.</p>
                    <span class="section-link">Manage Wishlist →</span>
                </a>
                
                <a href="/market" class="section-card">
                    <div class="section-icon">📊</div>
                    <h2>Market Scanner</h2>
                    <p>Scan the market for deals on cards in your wishlist. View prices, discounts, and find the best opportunities to buy.</p>
                    <span class="section-link">View Market →</span>
                </a>
                
                <a href="/games" class="section-card">
                    <div class="section-icon">🎮</div>
                    <h2>Games</h2>
                    <p>Play Magic: The Gathering online. Create or join games, manage decks, and play with friends in real-time.</p>
                    <span class="section-link">Play Games →</span>
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# Import route handlers from each module
# We need to import the functions directly from the modules
import importlib
import web_ui
import wishlist_ui
import collection_ui

# Get route handlers from each module
market_index = web_ui.index
api_results = web_ui.api_results
api_deals = web_ui.api_deals
api_filter_options = web_ui.api_filter_options

wishlist_index = wishlist_ui.wishlist_page
get_wishlist = wishlist_ui.get_wishlist
get_sets = wishlist_ui.get_sets
get_wishlist_cards = wishlist_ui.get_wishlist_cards
add_wishlist_item = wishlist_ui.add_wishlist_item
update_wishlist_item = wishlist_ui.update_wishlist_item
archive_wishlist_item = wishlist_ui.archive_wishlist_item
move_wishlist_to_collection = wishlist_ui.move_wishlist_to_collection
wishlist_autocomplete = wishlist_ui.autocomplete_card_name
wishlist_fetch_image = wishlist_ui.fetch_card_image

collection_index = collection_ui.collection_page
get_collection = collection_ui.get_collection
collection_get_sets = collection_ui.get_sets
get_collection_cards = collection_ui.get_collection_cards
add_collection_item = collection_ui.add_collection_item
update_collection_item = collection_ui.update_collection_item
archive_collection_item = collection_ui.archive_collection_item
collection_autocomplete = collection_ui.autocomplete_card_name
collection_fetch_image = collection_ui.fetch_card_image

# Market Scanner routes
@app.get("/market", response_class=HTMLResponse)
async def market_route(request: Request):
    """Market scanner page with navigation."""
    try:
        response = await market_index()
        
        # Extract HTML content from response
        if isinstance(response, HTMLResponse):
            # For HTMLResponse, body is bytes
            html = response.body.decode('utf-8') if response.body else ""
        elif hasattr(response, 'body'):
            html = response.body.decode('utf-8') if isinstance(response.body, bytes) else str(response.body)
        else:
            html = str(response)
        
        if not html or html.strip() == "":
            return HTMLResponse(content="<h1>Error: Empty response from market scanner</h1>", status_code=500)
        
        # Update API paths in HTML to use /market prefix
        # Replace all occurrences of /api/ with /market/api/ (but not if already /market/api/)
        # This handles: "/api/, '/api/, `/api/, fetch("/api/, fetch('/api/, fetch(`/api/
        # Count occurrences before replacement for debugging
        api_count_before = html.count('/api/')
        html = re.sub(r'(?<!market)/api/', '/market/api/', html)
        api_count_after = html.count('/api/')
        market_api_count = html.count('/market/api/')
        
        print(f"Market route: Replaced {api_count_before} /api/ occurrences, {market_api_count} /market/api/ now present", flush=True)
        
        return HTMLResponse(content=inject_navigation(html, "market"))
    except Exception as e:
        import traceback
        error_msg = f"<h1>Error loading market scanner</h1><pre>{traceback.format_exc()}</pre>"
        print(f"Error in market_route: {e}", flush=True)
        traceback.print_exc()
        return HTMLResponse(content=error_msg, status_code=500)

@app.get("/market/api/results")
async def market_api_results():
    return await api_results()

@app.get("/market/api/deals")
async def market_api_deals(
    file: str = None,
    category: str = None,
    min_discount: float = None,
    sort: str = 'discount',
    order: str = 'desc',
    sets: str = None,
    countries: str = None,
    price_min: float = None,
    price_max: float = None
):
    return await api_deals(
        file=file,
        category=category,
        min_discount=min_discount,
        sort=sort,
        order=order,
        sets=sets,
        countries=countries,
        price_min=price_min,
        price_max=price_max
    )

@app.get("/market/api/filter-options")
async def market_api_filter_options(file: str = None):
    return await api_filter_options(file=file)

# Wishlist routes
@app.get("/wishlist", response_class=HTMLResponse)
async def wishlist_route(request: Request):
    """Wishlist page with navigation."""
    try:
        response = await wishlist_index()
        
        # Extract HTML content from response
        if isinstance(response, HTMLResponse):
            html = response.body.decode('utf-8') if response.body else ""
        elif hasattr(response, 'body'):
            html = response.body.decode('utf-8') if isinstance(response.body, bytes) else str(response.body)
        else:
            html = str(response)
        
        if not html or html.strip() == "":
            return HTMLResponse(content="<h1>Error: Empty response from wishlist</h1>", status_code=500)
        
        # Update API paths in HTML to use /wishlist prefix
        # Replace all occurrences of /api/ with /wishlist/api/ (but not if already /wishlist/api/)
        html = re.sub(r'(?<!wishlist)/api/', '/wishlist/api/', html)
        
        return HTMLResponse(content=inject_navigation(html, "wishlist"))
    except Exception as e:
        import traceback
        error_msg = f"<h1>Error loading wishlist</h1><pre>{traceback.format_exc()}</pre>"
        print(f"Error in wishlist_route: {e}", flush=True)
        traceback.print_exc()
        return HTMLResponse(content=error_msg, status_code=500)

@app.get("/wishlist/api/wishlist")
async def wishlist_api_wishlist():
    return await get_wishlist()

@app.get("/wishlist/api/sets")
async def wishlist_api_sets():
    return await get_sets()

@app.get("/wishlist/api/wishlist-cards")
async def wishlist_api_wishlist_cards():
    return await get_wishlist_cards()

@app.post("/wishlist/api/wishlist")
async def wishlist_api_add(request: Request):
    return await add_wishlist_item(request)

@app.put("/wishlist/api/wishlist/{index}")
async def wishlist_api_update(index: int, request: Request):
    return await update_wishlist_item(index, request)

@app.delete("/wishlist/api/wishlist/{index}")
async def wishlist_api_delete(index: int):
    return await archive_wishlist_item(index)

@app.post("/wishlist/api/wishlist/{index}/move-to-collection")
async def wishlist_api_move_to_collection(index: int, request: Request):
    return await move_wishlist_to_collection(index, request)

@app.get("/wishlist/api/autocomplete-card")
async def wishlist_api_autocomplete(q: str = ""):
    return await wishlist_autocomplete(q=q)

@app.get("/wishlist/api/fetch-card-image")
async def wishlist_api_fetch_image(name: str, set: str = None):
    return await wishlist_fetch_image(name=name, set=set)

# Collection routes
@app.get("/collection", response_class=HTMLResponse)
async def collection_route(request: Request):
    """Collection page with navigation."""
    try:
        response = await collection_index()
        
        # Extract HTML content from response
        if isinstance(response, HTMLResponse):
            html = response.body.decode('utf-8') if response.body else ""
        elif hasattr(response, 'body'):
            html = response.body.decode('utf-8') if isinstance(response.body, bytes) else str(response.body)
        else:
            html = str(response)
        
        if not html or html.strip() == "":
            return HTMLResponse(content="<h1>Error: Empty response from collection</h1>", status_code=500)
        
        # Update API paths in HTML to use /collection prefix
        # Replace all occurrences of /api/ with /collection/api/ (but not if already /collection/api/)
        html = re.sub(r'(?<!collection)/api/', '/collection/api/', html)
        
        return HTMLResponse(content=inject_navigation(html, "collection"))
    except Exception as e:
        import traceback
        error_msg = f"<h1>Error loading collection</h1><pre>{traceback.format_exc()}</pre>"
        print(f"Error in collection_route: {e}", flush=True)
        traceback.print_exc()
        return HTMLResponse(content=error_msg, status_code=500)

@app.get("/collection/api/collection")
async def collection_api_collection():
    return await get_collection()

@app.get("/collection/api/sets")
async def collection_api_sets():
    return await collection_get_sets()

@app.get("/collection/api/collection-cards")
async def collection_api_collection_cards():
    return await get_collection_cards()

@app.post("/collection/api/collection")
async def collection_api_add(request: Request):
    return await add_collection_item(request)

@app.put("/collection/api/collection/{index}")
async def collection_api_update(index: int, request: Request):
    return await update_collection_item(index, request)

@app.delete("/collection/api/collection/{index}")
async def collection_api_delete(index: int):
    return await archive_collection_item(index)

@app.get("/collection/api/autocomplete-card")
async def collection_api_autocomplete(q: str = ""):
    return await collection_autocomplete(q=q)

@app.get("/collection/api/fetch-card-image")
async def collection_api_fetch_image(name: str, set: str = None):
    return await collection_fetch_image(name=name, set=set)

# Games routes
@app.get("/games")
async def games_route(request: Request):
    """Games lobby page - redirects to full screen game frontend."""
    from fastapi.responses import RedirectResponse
    game_frontend_url = os.getenv("GAME_FRONTEND_URL", "http://localhost:5173")
    # Redirect directly to the game frontend for full screen experience
    return RedirectResponse(url=game_frontend_url)


def run_wishlist_analysis(wishlist_file: str = "wishlist.json", delay: float = 10.0):
    """Run wishlist deals analysis."""
    print("\n" + "=" * 60)
    print("🔍 Running Wishlist Deals Analysis")
    print("=" * 60)
    
    # Add simple_version to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'simple_version'))
    
    try:
        from wishlist_deals import check_wishlist_deals, save_results
        
        deals = check_wishlist_deals(
            wishlist_file=wishlist_file,
            delay_between_cards=delay,
            use_historical=True
        )
        
        if deals:
            output_file = save_results(deals, None)  # Auto-generate filename
            print(f"\n✅ Analysis complete! Results saved to: {output_file}")
            return output_file
        else:
            print("\n⚠️  No deals found")
            return None
    except Exception as e:
        print(f"\n❌ Error running wishlist analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run the unified web application."""
    parser = argparse.ArgumentParser(
        description="MTG Cards Unified Web Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_app.py                    # Start server without scanning (default)
  python main_app.py --scan             # Run market scan, then start server
  python main_app.py --scan --delay 15  # Run scan with custom delay
  python main_app.py --port 6000        # Start server on custom port
        """
    )
    parser.add_argument(
        '--port',
        type=int,
        default=DEFAULT_PORT,
        help=f'Port to run server on (default: {DEFAULT_PORT})'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--scan',
        action='store_true',
        dest='run_scan',
        default=False,
        help='Run market scan analysis before starting server (default: False)'
    )
    parser.add_argument(
        '--wishlist-file',
        type=str,
        default='wishlist.json',
        help='Path to wishlist JSON file for scanning (default: wishlist.json)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=10.0,
        help='Delay between cards when scanning (default: 10.0 seconds)'
    )
    
    args = parser.parse_args()
    
    # Run market scan if requested
    if args.run_scan:
        print("\n" + "=" * 60)
        print("🃏 MTG Cards Unified Manager - Running Market Scan")
        print("=" * 60)
        
        if not os.path.exists(args.wishlist_file):
            print(f"\n⚠️  Warning: Wishlist file '{args.wishlist_file}' not found.")
            print("   Skipping market scan. Server will start with existing results.")
        else:
            print(f"📋 Scanning market for wishlist: {args.wishlist_file}")
            run_wishlist_analysis(args.wishlist_file, args.delay)
            print("\n" + "=" * 60)
    
    import uvicorn
    print(f"\n🎴 MTG Cards Unified Manager")
    print(f"=" * 60)
    print(f"🌐 Server starting on http://{args.host}:{args.port}")
    print(f"\n🗂️  Collection:      http://{args.host}:{args.port}/collection")
    print(f"📋 Wishlist:        http://{args.host}:{args.port}/wishlist")
    print(f"📊 Market Scanner:  http://{args.host}:{args.port}/market")
    print(f"🎮 Games:           http://{args.host}:{args.port}/games")
    print(f"=" * 60)
    print(f"\n⚠️  Note: Games require the game backend (port 9000) and frontend (port 5173) to be running.")
    print(f"   Start them with: ./start_server.sh")
    print(f"=" * 60)
    
    try:
        uvicorn.run(
            "main_app:app",
            host=args.host,
            port=args.port,
            log_level="info",
            reload=False
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Server stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\n\n❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
