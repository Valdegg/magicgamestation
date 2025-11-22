#!/bin/bash

# Magic Workstation - Server Launcher
# Usage: ./start_server.sh [-local]

# --- Configuration ---
MODE="remote"
STATIC_DOMAIN="magic.ngrok.dev"
LOG_DIR="logs"

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

cleanup() {
    echo ""
    log "Stopping servers..."
    pkill -P $$ # Kill child processes
    if [ ! -z "$NGROK_PID" ]; then kill $NGROK_PID 2>/dev/null; fi
    rm -f ngrok_temp.yml
    success "Cleanup complete."
    exit
}

trap cleanup SIGINT SIGTERM EXIT

# --- Parse Args ---
if [[ "$1" == "-local" || "$1" == "--local" ]]; then MODE="local"; fi

# --- Pre-flight Checks ---
mkdir -p "$LOG_DIR"
if ! command -v redis-server &> /dev/null; then
    error "Redis not found! Please install redis-server."
    exit 1
fi

# --- Mode: Remote (ngrok) ---
if [ "$MODE" == "remote" ]; then
    log "Mode: Remote Play (ngrok enabled)"
    
    if ! command -v ngrok &> /dev/null; then
        error "ngrok not found! Run with -local for offline mode."
        exit 1
    fi

    # Cleanup ports
    lsof -ti:9000 | xargs kill -9 2>/dev/null
    lsof -ti:5173 | xargs kill -9 2>/dev/null

    # Configure ngrok
    log "Generating ngrok config..."
    
    cat > ngrok_temp.yml << EOF
version: "2"
tunnels:
  backend:
    proto: http
    addr: 9000
  frontend:
    proto: http
    addr: 5173
EOF

    if [ ! -z "$STATIC_DOMAIN" ]; then
        log "Using static domain: $STATIC_DOMAIN"
        cat > ngrok_temp.yml << EOF
version: "2"
tunnels:
  backend:
    proto: http
    addr: 9000
  frontend:
    proto: http
    addr: 5173
    domain: $STATIC_DOMAIN
EOF
    fi
    
    # Debug: show the generated config
    log "Config generated:"
    cat ngrok_temp.yml

    # Start ngrok
    log "Starting ngrok..."
    # Kill any existing ngrok process first
    pkill -9 ngrok 2>/dev/null
    
    # Check for default config which contains the auth token
    DEFAULT_CONFIG="$HOME/Library/Application Support/ngrok/ngrok.yml"
    [ ! -f "$DEFAULT_CONFIG" ] && DEFAULT_CONFIG="$HOME/.ngrok2/ngrok.yml"
    
    # Explicitly include the auth config file
    if [ -f "$DEFAULT_CONFIG" ]; then
        log "Using auth config: $DEFAULT_CONFIG"
        ARGS="start --config=\"$DEFAULT_CONFIG\" --config=ngrok_temp.yml --log=stdout backend frontend"
    else
        warn "No default ngrok config found. Auth token might be missing."
        ARGS="start --config=ngrok_temp.yml --log=stdout backend frontend"
    fi
    
    log "Running: ngrok $ARGS"
    
    eval ngrok $ARGS > "$LOG_DIR/ngrok.log" 2>&1 &
    NGROK_PID=$!
    log "ngrok PID: $NGROK_PID"
    
    log "Waiting for tunnels..."
    sleep 8  # Increased wait time
    
    # Check if ngrok is still running
    if ! ps -p $NGROK_PID > /dev/null; then
        error "ngrok process died immediately. Check logs/ngrok.log:"
        tail -n 20 "$LOG_DIR/ngrok.log"
        cleanup
    fi

    # Get URLs
    if command -v jq &> /dev/null; then
        BACKEND_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[] | select(.config.addr | contains("9000")) | .public_url')
        FRONTEND_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[] | select(.config.addr | contains("5173")) | .public_url')
    else
        BACKEND_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*"' | grep -v "5173" | head -1 | cut -d'"' -f4)
        warn "jq not found, URL parsing might be flaky."
    fi

    [ -z "$BACKEND_URL" ] && { error "Failed to get Backend URL. Check logs/ngrok.log"; exit 1; }

    success "Backend:  $BACKEND_URL"
    success "Frontend: $FRONTEND_URL"

    # Set Env Vars
    WS_URL="${BACKEND_URL/https:/wss:}"
    WS_URL="${WS_URL/http:/ws:}"
    export VITE_API_URL="${BACKEND_URL}/api"
    export VITE_WS_URL="${WS_URL%/}"

else
    log "Mode: Local Server (Offline)"
fi

# --- Start Services ---
log "Starting Backend..."
backend/start_backend.sh > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

sleep 2

log "Starting Frontend..."
frontend/start_frontend.sh > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

# --- Status ---
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$MODE" == "remote" ]; then
    success "SERVER RUNNING!"
    echo -e "📤 SHARE: ${GREEN}$FRONTEND_URL${NC}"
else
    success "LOCAL SERVER RUNNING!"
    echo -e "🏠 Access: ${GREEN}http://localhost:5173${NC}"
fi
echo "📝 Logs: logs/{backend,frontend,ngrok}.log"
echo -e "${RED}Press Ctrl+C to stop.${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

wait $BACKEND_PID
