#!/bin/bash

# MTG Cards Unified Website Launcher
# Starts all services locally (no ngrok): Game backend, game frontend, and unified website
# All services run on localhost only
# Usage: ./start_website.sh

# Get script directory (absolute path)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Get project root (one level up from cards_binders)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Use logs directory in project root (magicworkstation/logs)
LOG_DIR="$PROJECT_ROOT/logs"

# Validate paths
if [ -z "$SCRIPT_DIR" ] || [ ! -d "$SCRIPT_DIR" ]; then
    echo "Error: Could not determine script directory"
    exit 1
fi
if [ -z "$PROJECT_ROOT" ] || [ ! -d "$PROJECT_ROOT" ]; then
    echo "Error: Could not determine project root (expected at: $SCRIPT_DIR/..)"
    exit 1
fi
if [ -z "$LOG_DIR" ]; then
    echo "Error: Could not determine log directory"
    exit 1
fi

# --- Colors ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# --- Helpers ---
log() { echo -e "${BLUE}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERR]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }

# --- Cleanup Function ---
cleanup() {
    echo ""
    log "Stopping all servers..."
    
    # Kill child processes
    pkill -P $$ 2>/dev/null
    
    # Kill processes on specific ports
    lsof -ti:5010 | xargs kill -9 2>/dev/null
    lsof -ti:9000 | xargs kill -9 2>/dev/null
    lsof -ti:5173 | xargs kill -9 2>/dev/null
    
    success "Cleanup complete."
    exit
}

trap cleanup SIGINT SIGTERM EXIT

# --- Pre-flight Checks ---
# Ensure LOG_DIR exists and is writable
if [ -z "$LOG_DIR" ] || [ "$LOG_DIR" = "/logs" ] || [ "$LOG_DIR" = "logs" ]; then
    # Fallback to script directory if PROJECT_ROOT resolution failed
    LOG_DIR="$SCRIPT_DIR/../logs"
    LOG_DIR="$(cd "$(dirname "$LOG_DIR")" && pwd)/$(basename "$LOG_DIR")"
fi
mkdir -p "$LOG_DIR" || {
    error "Failed to create log directory: $LOG_DIR"
    exit 1
}

# Check Redis (optional but recommended for games)
if ! command -v redis-server &> /dev/null; then
    warn "Redis not found. Games will run in memory-only mode (state lost on restart)."
    warn "Install redis-server for persistent game state."
else
    # Check if Redis is running
    if ! redis-cli ping &> /dev/null; then
        log "Starting Redis..."
        redis-server --daemonize yes 2>/dev/null || warn "Could not start Redis. Games will use memory-only mode."
        sleep 1
    else
        success "Redis is already running"
    fi
fi

# --- Cleanup existing processes ---
log "Cleaning up any existing processes on ports 5010, 9000, 5173..."
lsof -ti:5010 | xargs kill -9 2>/dev/null
lsof -ti:9000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
sleep 1

# --- Start Game Backend ---
if [ ! -d "$PROJECT_ROOT/backend" ]; then
    warn "Backend directory not found at $PROJECT_ROOT/backend"
    warn "Skipping game backend. Games will not be available."
    GAME_BACKEND_PID=""
else
    log "Starting Game Backend (port 9000)..."
    cd "$PROJECT_ROOT/backend"
    if [ ! -f "start_backend.sh" ]; then
        error "start_backend.sh not found in backend directory"
        cleanup
    fi
    bash start_backend.sh > "$LOG_DIR/game_backend.log" 2>&1 &
    GAME_BACKEND_PID=$!
    cd "$SCRIPT_DIR"
    
    # Wait for backend to start and check if port is listening
    sleep 3
    PORT_CHECK_COUNT=0
    while [ $PORT_CHECK_COUNT -lt 10 ]; do
        if lsof -ti:9000 > /dev/null 2>&1; then
            success "Game Backend started (PID: $GAME_BACKEND_PID, port 9000 listening)"
            break
        fi
        PORT_CHECK_COUNT=$((PORT_CHECK_COUNT + 1))
        sleep 1
    done
    
    if [ $PORT_CHECK_COUNT -ge 10 ]; then
        warn "Game backend port 9000 not listening. Check logs/game_backend.log"
        tail -n 20 "$LOG_DIR/game_backend.log"
        warn "Continuing without game backend..."
        GAME_BACKEND_PID=""
    fi
fi

# --- Start Game Frontend ---
if [ ! -d "$PROJECT_ROOT/frontend" ]; then
    warn "Frontend directory not found at $PROJECT_ROOT/frontend"
    warn "Skipping game frontend. Games will not be available."
    GAME_FRONTEND_PID=""
else
    log "Starting Game Frontend (port 5173)..."
    cd "$PROJECT_ROOT/frontend"
    if [ ! -f "start_frontend.sh" ]; then
        error "start_frontend.sh not found in frontend directory"
        cleanup
    fi
    bash start_frontend.sh > "$LOG_DIR/game_frontend.log" 2>&1 &
    GAME_FRONTEND_PID=$!
    cd "$SCRIPT_DIR"
    
    # Wait for frontend to start and check if port is listening
    sleep 3
    PORT_CHECK_COUNT=0
    while [ $PORT_CHECK_COUNT -lt 10 ]; do
        if lsof -ti:5173 > /dev/null 2>&1; then
            success "Game Frontend started (PID: $GAME_FRONTEND_PID, port 5173 listening)"
            break
        fi
        PORT_CHECK_COUNT=$((PORT_CHECK_COUNT + 1))
        sleep 1
    done
    
    if [ $PORT_CHECK_COUNT -ge 10 ]; then
        warn "Game frontend port 5173 not listening. Check logs/game_frontend.log"
        tail -n 20 "$LOG_DIR/game_frontend.log"
        warn "Continuing without game frontend..."
        GAME_FRONTEND_PID=""
    fi
fi

# --- Start Unified Website ---
log "Starting Unified Website (port 5010)..."
cd "$SCRIPT_DIR"

# Check for virtual environment
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install/update dependencies
log "Checking dependencies..."
pip install -q -r requirements.txt

# Start main_app.py
python main_app.py > "$LOG_DIR/unified_website.log" 2>&1 &
UNIFIED_WEBSITE_PID=$!

# Wait for website to start and check if port is listening
sleep 2
PORT_CHECK_COUNT=0
while [ $PORT_CHECK_COUNT -lt 10 ]; do
    if lsof -ti:5010 > /dev/null 2>&1; then
        success "Unified Website started (PID: $UNIFIED_WEBSITE_PID, port 5010 listening)"
        break
    fi
    PORT_CHECK_COUNT=$((PORT_CHECK_COUNT + 1))
    sleep 1
done

if [ $PORT_CHECK_COUNT -ge 10 ]; then
    error "Unified website port 5010 not listening. Check logs/unified_website.log"
    tail -n 20 "$LOG_DIR/unified_website.log"
    cleanup
fi

# --- Status Display ---
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "🎴 MTG CARDS UNIFIED WEBSITE RUNNING!"
echo ""
echo -e "🌐 ${GREEN}Unified Website:${NC}  http://localhost:5010"
echo ""
echo -e "   📍 ${BLUE}Home:${NC}           http://localhost:5010/"
echo -e "   🗂️  ${BLUE}Collection:${NC}     http://localhost:5010/collection"
echo -e "   📋 ${BLUE}Wishlist:${NC}        http://localhost:5010/wishlist"
echo -e "   📊 ${BLUE}Market Scanner:${NC}  http://localhost:5010/market"
echo -e "   🎮 ${BLUE}Games:${NC}           http://localhost:5010/games"
echo ""
echo -e "🎮 ${GREEN}Game Services:${NC}"
echo -e "   🔧 ${BLUE}Game Backend:${NC}    http://localhost:9000"
echo -e "   🎨 ${BLUE}Game Frontend:${NC}   http://localhost:5173"
echo ""
echo -e "📝 ${GREEN}Log Files:${NC}"
echo -e "   📄 ${BLUE}Unified Website:${NC} logs/unified_website.log"
echo -e "   📄 ${BLUE}Game Backend:${NC}    logs/game_backend.log"
echo -e "   📄 ${BLUE}Game Frontend:${NC}   logs/game_frontend.log"
echo ""
echo -e "${RED}Press Ctrl+C to stop all servers.${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Wait for any process to exit
if [ ! -z "$GAME_BACKEND_PID" ] && [ ! -z "$GAME_FRONTEND_PID" ]; then
    wait $UNIFIED_WEBSITE_PID $GAME_BACKEND_PID $GAME_FRONTEND_PID 2>/dev/null
elif [ ! -z "$GAME_BACKEND_PID" ]; then
    wait $UNIFIED_WEBSITE_PID $GAME_BACKEND_PID 2>/dev/null
elif [ ! -z "$GAME_FRONTEND_PID" ]; then
    wait $UNIFIED_WEBSITE_PID $GAME_FRONTEND_PID 2>/dev/null
else
    wait $UNIFIED_WEBSITE_PID 2>/dev/null
fi

