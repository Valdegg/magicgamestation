#!/usr/bin/env python3
"""
MTG Card Binder Web UI

A beautiful web interface that displays MTG card deals in a binder format,
like flipping through pages of a Magic card binder.

Can run analysis using simple_version scripts and then serve the results.
"""

import json
import os
import glob
import sys
import argparse
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

app = FastAPI(title="MTG Card Binder", description="MTG Card Deal Binder Interface")

# Configuration
RESULTS_DIR = 'results'
DEFAULT_PORT = 5001  # Changed from 5000 to avoid conflict with macOS AirPlay Receiver

# Mount static files and templates
if os.path.exists('card_images'):
    app.mount("/card_images", StaticFiles(directory="card_images"), name="card_images")

if os.path.exists('web_static'):
    app.mount("/static", StaticFiles(directory="web_static"), name="static")

# Setup Jinja2 templates
jinja_env = Environment(loader=FileSystemLoader("web_templates"))


def load_json_results(json_file: str) -> Dict[str, Any]:
    """Load JSON results file."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {json_file}: {e}")
        return {}


def normalize_deal_data(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalize deal data from different JSON formats into a unified structure.
    Handles both main.py results and simple_version results.
    """
    deals = []
    
    # Check if this is a simple_version format (wishlist_deals.py or discovery.py)
    if 'deals' in results or 'candidates' in results:
        # Simple version format
        deal_list = results.get('deals', []) or results.get('candidates', [])
        for deal in deal_list:
            card = deal.get('card', {})
            live_data = deal.get('live_data', {})
            discounts = deal.get('discounts', {})
            
            # Get expansion - try multiple fields
            expansion = card.get('expansion') or card.get('expansionName') or ''
            if not expansion or expansion.strip() == '':
                expansion = None  # Use None instead of 'Unknown'
            
            # Get country
            country = live_data.get('cheapest_good_details', {}).get('country', '')
            if not country or country.strip() == '':
                country = None  # Use None instead of 'Unknown'
            
            normalized = {
                'card_name': card.get('name', 'Unknown'),
                'expansion': expansion,
                'card_id': card.get('card_id') or card.get('idProduct'),
                'price': live_data.get('cheapest_good_condition'),
                'condition': live_data.get('cheapest_good_details', {}).get('condition', 'Unknown'),
                'seller': live_data.get('cheapest_good_details', {}).get('seller', 'Unknown'),
                'seller_country': country,
                'discount': discounts.get('discount_vs_market'),
                'market_baseline': discounts.get('market_baseline'),
                'category': deal.get('category', 'unknown'),
                'url': live_data.get('url', ''),
                'total_listings': live_data.get('total_listings', 0),
                'available_items_total': live_data.get('available_items_total'),  # Liquidity indicator
                'historical': card.get('historical', {}),
                'source': results.get('wishlist_file', 'Unknown')
            }
            deals.append(normalized)
    
    # Check if this is main.py format (excellent_deals, good_deals, etc.)
    elif 'excellent_deals' in results or 'good_deals' in results:
        for category in ['excellent_deals', 'good_deals', 'expensive_deals', 'no_data']:
            for result in results.get(category, []):
                card_data = result.get('card_data', {})
                live_analysis = result.get('live_analysis') or result.get('live_data', {})
                
                if not live_analysis:
                    continue
                
                cheapest_details = live_analysis.get('cheapest_good_condition_details', {})
                if not cheapest_details:
                    continue
                
                # Get expansion
                expansion = card_data.get('expansionName', '')
                if not expansion or expansion.strip() == '':
                    expansion = None  # Use None instead of 'Unknown'
                
                # Get country
                country = cheapest_details.get('country', '')
                if not country or country.strip() == '':
                    country = None  # Use None instead of 'Unknown'
                
                normalized = {
                    'card_name': card_data.get('name', 'Unknown'),
                    'expansion': expansion,
                    'card_id': card_data.get('idProduct'),
                    'price': live_analysis.get('cheapest_good_condition'),
                    'condition': cheapest_details.get('condition', 'Unknown'),
                    'seller': cheapest_details.get('seller', 'Unknown'),
                    'seller_country': country,
                    'discount': None,  # Will calculate from top_6_sellers if available
                    'market_baseline': None,
                    'category': category.replace('_deals', ''),
                    'url': live_analysis.get('url', ''),
                    'total_listings': live_analysis.get('total_listings', 0),
                    'historical': {
                        'trend': card_data.get('TREND', 0),
                        'avg30': card_data.get('AVG30', 0),
                        'avg7': card_data.get('AVG7', 0)
                    },
                    'source': result.get('source', results.get('run_type', 'Unknown'))
                }
                
                # Calculate discount if we have top sellers
                top_sellers = live_analysis.get('top_6_sellers', [])
                if top_sellers and len(top_sellers) >= 2:
                    baseline_sellers = top_sellers[1:5] if len(top_sellers) >= 5 else top_sellers[1:]
                    if baseline_sellers:
                        avg_baseline = sum(s['price'] for s in baseline_sellers) / len(baseline_sellers)
                        cheapest_price = normalized['price']
                        if cheapest_price and avg_baseline > 0:
                            normalized['discount'] = ((avg_baseline - cheapest_price) / avg_baseline) * 100
                            normalized['market_baseline'] = avg_baseline
                
                deals.append(normalized)
    
    return deals


def get_all_results_files() -> List[str]:
    """Get all JSON result files."""
    if not os.path.exists(RESULTS_DIR):
        return []
    
    json_files = glob.glob(os.path.join(RESULTS_DIR, '*.json'))
    # Sort by modification time, newest first
    json_files.sort(key=os.path.getmtime, reverse=True)
    return json_files


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main page."""
    template = jinja_env.get_template("binder.html")
    return HTMLResponse(content=template.render())


@app.get("/api/results")
async def api_results():
    """Get all available result files."""
    files = get_all_results_files()
    file_info = []
    
    for file_path in files:
        try:
            results = load_json_results(file_path)
            filename = os.path.basename(file_path)
            
            # Count deals
            deals = normalize_deal_data(results)
            
            file_info.append({
                'filename': filename,
                'path': file_path,
                'timestamp': results.get('timestamp', ''),
                'total_deals': len(deals),
                'excellent': len([d for d in deals if d.get('category') == 'excellent']),
                'good': len([d for d in deals if d.get('category') == 'good']),
                'fair': len([d for d in deals if d.get('category') == 'fair']),
                'expensive': len([d for d in deals if d.get('category') == 'expensive']),
            })
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    return JSONResponse(content=file_info)


@app.get("/api/deals")
async def api_deals(
    file: Optional[str] = None,
    category: Optional[str] = None,
    min_discount: Optional[float] = None,
    sort: str = 'discount',
    order: str = 'desc',
    sets: Optional[str] = None,  # Comma-separated list of sets
    countries: Optional[str] = None,  # Comma-separated list of countries
    price_min: Optional[float] = None,
    price_max: Optional[float] = None
):
    """Get deals from a specific result file."""
    if not file:
        # Use latest file if none specified
        files = get_all_results_files()
        if not files:
            return JSONResponse(content={'deals': [], 'error': 'No result files found'})
        file = files[0]
    
    # Ensure file is in results directory (security)
    if not file.startswith(RESULTS_DIR):
        file = os.path.join(RESULTS_DIR, file)
    
    if not os.path.exists(file):
        return JSONResponse(content={'deals': [], 'error': f'File not found: {file}'})
    
    results = load_json_results(file)
    deals = normalize_deal_data(results)
    
    # Apply filters
    if category:
        deals = [d for d in deals if d.get('category') == category]
    
    if min_discount is not None:
        deals = [d for d in deals if d.get('discount') and d.get('discount') >= min_discount]
    
    # Filter by sets (expansions)
    if sets:
        allowed_sets = [s.strip().lower() for s in sets.split(',') if s.strip()]
        if allowed_sets:
            deals = [d for d in deals if d.get('expansion') and str(d.get('expansion', '')).lower() in allowed_sets]
    
    # Filter by countries
    if countries:
        allowed_countries = [c.strip().lower() for c in countries.split(',') if c.strip()]
        if allowed_countries:
            deals = [d for d in deals if d.get('seller_country') and str(d.get('seller_country', '')).lower() in allowed_countries]
    
    # Filter by price range
    if price_min is not None:
        deals = [d for d in deals if d.get('price') and d.get('price') >= price_min]
    
    if price_max is not None:
        deals = [d for d in deals if d.get('price') and d.get('price') <= price_max]
    
    # Apply sorting
    reverse = order == 'desc'
    
    if sort == 'discount':
        deals.sort(key=lambda x: x.get('discount') or -999, reverse=reverse)
    elif sort == 'price':
        deals.sort(key=lambda x: x.get('price') or 999999, reverse=reverse)
    elif sort == 'name':
        deals.sort(key=lambda x: x.get('card_name', '').lower(), reverse=reverse)
    elif sort == 'expansion':
        deals.sort(key=lambda x: x.get('expansion', '').lower(), reverse=reverse)
    
    return JSONResponse(content={
        'deals': deals,
        'total': len(deals),
        'file': os.path.basename(file)
    })


@app.get("/api/filter-options")
async def api_filter_options(file: Optional[str] = None):
    """Get available filter options (sets, countries) from the newest file."""
    if not file:
        files = get_all_results_files()
        if not files:
            return JSONResponse(content={'sets': [], 'countries': []})
        file = files[0]
    
    if not file.startswith(RESULTS_DIR):
        file = os.path.join(RESULTS_DIR, file)
    
    if not os.path.exists(file):
        return JSONResponse(content={'sets': [], 'countries': []})
    
    results = load_json_results(file)
    deals = normalize_deal_data(results)
    
    # Extract unique sets and countries, excluding 'Unknown' and empty values
    sets = sorted(set(
        d.get('expansion', '') for d in deals 
        if d.get('expansion') and d.get('expansion') != 'Unknown' and d.get('expansion').strip()
    ))
    countries = sorted(set(
        d.get('seller_country', '') for d in deals 
        if d.get('seller_country') and d.get('seller_country') != 'Unknown' and d.get('seller_country').strip()
    ))
    
    return JSONResponse(content={
        'sets': sets,
        'countries': countries
    })


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


def run_discovery_analysis(
    wishlist_file: str = "wishlist.json",
    min_avg30: float = 10.0,
    max_avg30: float = 500.0,
    historical_discount: float = 0.05,
    live_discount: float = 7.0,
    max_candidates: int = 10,
    delay: float = 10.0
):
    """Run discovery analysis."""
    print("\n" + "=" * 60)
    print("🔍 Running Discovery Analysis")
    print("=" * 60)
    
    # Add simple_version to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'simple_version'))
    
    try:
        from discovery import discover_cards, save_discovery_results
        from datetime import datetime
        
        cards = discover_cards(
            wishlist_file=wishlist_file,
            min_avg30=min_avg30,
            max_avg30=max_avg30,
            historical_discount_threshold=historical_discount,
            live_discount_threshold=live_discount,
            min_liquidity=0.01,
            max_candidates_to_scrape=max_candidates,
            delay_between_cards=delay
        )
        
        if cards:
            # Generate output filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"results/discovery_{timestamp}.json"
            os.makedirs('results', exist_ok=True)
            
            save_discovery_results(cards, output_file)
            print(f"\n✅ Analysis complete! Results saved to: {output_file}")
            return output_file
        else:
            print("\n⚠️  No discovery candidates found")
            return None
    except Exception as e:
        print(f"\n❌ Error running discovery analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run the web server, optionally running analysis first."""
    import uvicorn
    
    parser = argparse.ArgumentParser(
        description="MTG Card Binder Web UI - View deals in a binder format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python web_ui.py                    # Run wishlist analysis, then start web UI (default)
  python web_ui.py --no-wishlist      # Skip analysis, just view existing results
  python web_ui.py --discovery        # Run both wishlist and discovery analyses
  python web_ui.py --no-wishlist --discovery  # Run only discovery analysis
        """
    )
    
    parser.add_argument(
        '--no-wishlist',
        action='store_false',
        dest='run_wishlist',
        default=True,  # Run by default
        help='Skip wishlist analysis (default: runs wishlist analysis automatically)'
    )
    
    parser.add_argument(
        '--discovery',
        action='store_true',
        dest='run_discovery',
        default=False,
        help='Run discovery analysis before starting web UI'
    )
    
    parser.add_argument(
        '--wishlist-file',
        type=str,
        default='wishlist.json',
        help='Path to wishlist JSON file (default: wishlist.json)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=10.0,
        help='Delay between cards when scraping (default: 10.0 seconds)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=DEFAULT_PORT,
        help=f'Port to run server on (default: {DEFAULT_PORT})'
    )
    
    # Discovery-specific options
    parser.add_argument(
        '--min-avg30',
        type=float,
        default=10.0,
        help='Minimum AVG30 price for discovery (default: 10.0)'
    )
    
    parser.add_argument(
        '--max-avg30',
        type=float,
        default=500.0,
        help='Maximum AVG30 price for discovery (default: 500.0)'
    )
    
    parser.add_argument(
        '--max-candidates',
        type=int,
        default=10,
        help='Maximum candidates to scrape for discovery (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Run analyses (wishlist runs by default)
    if args.run_wishlist or args.run_discovery:
        print("🃏 MTG Card Binder Web UI - Running Analysis")
        print("=" * 60)
        
        if args.run_wishlist:
            print(f"📋 Running wishlist analysis for: {args.wishlist_file}")
            run_wishlist_analysis(args.wishlist_file, args.delay)
        
        if args.run_discovery:
            print(f"🔍 Running discovery analysis for: {args.wishlist_file}")
            run_discovery_analysis(
                wishlist_file=args.wishlist_file,
                min_avg30=args.min_avg30,
                max_avg30=args.max_avg30,
                max_candidates=args.max_candidates,
                delay=args.delay
            )
        
        print("\n" + "=" * 60)
    
    # Start web server
    print("\n" + "=" * 60)
    print("🃏 MTG Card Binder Web UI")
    print("=" * 60)
    print(f"Starting server on http://localhost:{args.port}")
    print(f"Results directory: {RESULTS_DIR}")
    print("\nOpen your browser to view the binder interface!")
    print("=" * 60)
    
    try:
        # When using reload=True, uvicorn needs the app as an import string
        # This allows it to reload the module when code changes
        uvicorn.run(
            "web_ui:app",  # Import string format: module:variable
            host="0.0.0.0", 
            port=args.port, 
            log_level="info", 
            reload=True  # Auto-reload on code changes
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Server stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\n\n❌ Error starting web server: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 Trying without reload mode...")
        try:
            # Fallback: run without reload if string format fails
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=args.port,
                log_level="info",
                reload=False
            )
        except Exception as e2:
            print(f"❌ Failed to start server even without reload: {e2}")
            sys.exit(1)


if __name__ == '__main__':
    main()
