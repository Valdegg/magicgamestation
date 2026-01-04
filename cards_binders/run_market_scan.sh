#!/bin/bash

# Market Scanner Daily Update Script
# Runs a market scan and saves results without starting the web server
# Usage: ./run_market_scan.sh [delay] [wishlist_file]

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
DELAY=${1:-10.0}  # Default delay: 10 seconds between cards
WISHLIST_FILE=${2:-"wishlist.json"}  # Default wishlist file

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERR]${NC} $1"; }

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    warn "Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    log "Installing dependencies..."
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

# Check if wishlist file exists
if [ ! -f "$WISHLIST_FILE" ]; then
    error "Wishlist file not found: $WISHLIST_FILE"
    error "Please create a wishlist.json file or specify a different file."
    exit 1
fi

log "Starting market scan..."
log "Wishlist file: $WISHLIST_FILE"
log "Delay between cards: ${DELAY}s"
echo ""

# Create a temporary Python script to run the scan
TEMP_SCRIPT=$(mktemp)
cat > "$TEMP_SCRIPT" << EOF
import sys
import os

# Get the script directory (cards_binders)
SCRIPT_DIR = "$SCRIPT_DIR"

# Add simple_version to path
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'simple_version'))

# Change to script directory
os.chdir(SCRIPT_DIR)

from wishlist_deals import check_wishlist_deals, save_results

deals = check_wishlist_deals(
    wishlist_file='$WISHLIST_FILE',
    delay_between_cards=$DELAY,
    use_historical=True
)

if deals:
    output_file = save_results(deals, None)  # Auto-generate filename
    print(f'\n✅ Scan complete! Results saved to: {output_file}')
    print(f'📊 Found {len(deals)} deals')
    
    # Count by category
    excellent = len([d for d in deals if d.get('category') == 'excellent'])
    good = len([d for d in deals if d.get('category') == 'good'])
    fair = len([d for d in deals if d.get('category') == 'fair'])
    expensive = len([d for d in deals if d.get('category') == 'expensive'])
    
    print(f'   Excellent: {excellent}')
    print(f'   Good: {good}')
    print(f'   Fair: {fair}')
    print(f'   Expensive: {expensive}')
    sys.exit(0)
else:
    print('\n⚠️  No deals found')
    sys.exit(1)
EOF

# Run the temporary script
python3 "$TEMP_SCRIPT"
SCAN_EXIT_CODE=$?

# Clean up
rm -f "$TEMP_SCRIPT"

if [ $SCAN_EXIT_CODE -eq 0 ]; then
    success "Market scan completed successfully!"
    log "The newest results will automatically appear in the Market Scanner web interface."
else
    error "Market scan failed. Check the output above for errors."
    exit 1
fi

deactivate

