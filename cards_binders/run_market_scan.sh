#!/bin/bash

# Market Scanner Daily Update Script
# Runs a market scan and saves results without starting the web server
# Usage: ./run_market_scan.sh [wishlist|collection] [delay] [--source json|db|all]
#   Examples:
#     ./run_market_scan.sh                         # Scan wishlist.json with 10s delay (default: source=all)
#     ./run_market_scan.sh 15                      # Scan wishlist.json with 15s delay (default: source=all)
#     ./run_market_scan.sh collection              # Scan collection.json with 10s delay (default: source=all)
#     ./run_market_scan.sh wishlist 5.0            # Scan wishlist.json with 5s delay (default: source=all)
#     ./run_market_scan.sh --source json           # Scan only JSON files (wishlist.json or collection.json)
#     ./run_market_scan.sh --source db             # Scan all users' wishlists from database only
#     ./run_market_scan.sh --source all            # Scan JSON + all database wishlists combined (default)
#     ./run_market_scan.sh wishlist 10 --source db # Scan database with custom settings

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Parse arguments
SOURCE_TYPE="wishlist"
DELAY=15.0
DATA_SOURCE="all"  # Default: all (or can be "json" or "db")

# Parse positional and named arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --source)
            DATA_SOURCE="$2"
            shift 2
            ;;
        --source=*)
            DATA_SOURCE="${1#*=}"
            shift
            ;;
        *)
            # Positional arguments
            # Check if argument is numeric (delay) or string (source type)
            if [[ "$1" =~ ^[0-9]+\.?[0-9]*$ ]]; then
                # Numeric argument = delay
                DELAY="$1"
            elif [[ -z "$POSITIONAL_SET" ]]; then
                # First non-numeric argument = source type
                SOURCE_TYPE="$1"
                POSITIONAL_SET=1
            else
                # Second non-numeric argument = delay (fallback)
                DELAY="$1"
            fi
            shift
            ;;
    esac
done

# Validate DATA_SOURCE
if [[ "$DATA_SOURCE" != "json" && "$DATA_SOURCE" != "db" && "$DATA_SOURCE" != "all" ]]; then
    echo "Error: Invalid --source value '$DATA_SOURCE'. Must be 'json', 'db', or 'all'."
    exit 1
fi

# Determine the file to scan based on source type
if [[ "$SOURCE_TYPE" == "collection" ]]; then
    WISHLIST_FILE="collection.json"
elif [[ "$SOURCE_TYPE" == "wishlist" ]]; then
    WISHLIST_FILE="wishlist.json"
elif [[ -f "$SOURCE_TYPE" ]]; then
    # If it's a valid file path, use it directly
    WISHLIST_FILE="$SOURCE_TYPE"
else
    # Default to wishlist.json
    WISHLIST_FILE="wishlist.json"
fi

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

# Check if source file exists (only required for source=json or source=all)
if [[ "$DATA_SOURCE" == "json" || "$DATA_SOURCE" == "all" ]]; then
    if [ ! -f "$WISHLIST_FILE" ]; then
        error "Source file not found: $WISHLIST_FILE"
        error "Please create the file or specify a different source type (wishlist/collection)."
        if [[ "$DATA_SOURCE" == "json" ]]; then
            error "Or use --source db to scan all users' wishlists from database."
        fi
        exit 1
    fi
fi

log "Starting market scan..."
log "Source type: $SOURCE_TYPE"
log "Data source: $DATA_SOURCE"
if [[ "$DATA_SOURCE" == "json" || "$DATA_SOURCE" == "all" ]]; then
    log "Source file: $WISHLIST_FILE"
fi
if [[ "$DATA_SOURCE" == "db" || "$DATA_SOURCE" == "all" ]]; then
    log "Database: All users' wishlists"
fi
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

# Configuration from shell script
wishlist_file = '$WISHLIST_FILE'
delay = $DELAY
source = '$DATA_SOURCE'

print(f'📋 Data source: {source}')
if source in ('json', 'all'):
    print(f'📄 JSON file: {wishlist_file}')
if source in ('db', 'all'):
    print(f'🗄️  Database: all users')

deals = check_wishlist_deals(
    wishlist_file=wishlist_file,
    delay_between_cards=delay,
    use_historical=True,
    source=source
)

if deals:
    output_file = save_results(deals, None, wishlist_file, source=source)  # Save based on source
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

