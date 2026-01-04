#!/bin/bash

# Unified Website Deployment Script for playmagic.now
# Based on docs/UNIFIED_WEBSITE_DEPLOYMENT.md
# Usage: ./deploy/deploy_unified_website.sh

set -e  # Exit on error

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

# Configuration
DOMAIN="playmagic.now"
PROJECT_ROOT="/opt/magicworkstation"
REPO_URL="${REPO_URL:-https://github.com/YourUsername/magicworkstation.git}"  # Override with env var
USERNAME="${SUDO_USER:-$USER}"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    error "Please run as root or with sudo"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "🎴 MTG Cards Unified Website Deployment Script"
log "Domain: $DOMAIN"
log "Project Root: $PROJECT_ROOT"
log "User: $USERNAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: Server Setup
log "Step 1: Installing system dependencies..."
apt update && apt upgrade -y
apt install -y \
    git \
    python3 \
    python3-venv \
    python3-pip \
    nodejs \
    npm \
    redis-server \
    caddy \
    build-essential \
    jq

success "System dependencies installed"

# Step 2: Start and Enable Redis
log "Step 2: Starting Redis..."
systemctl start redis-server
systemctl enable redis-server
success "Redis started and enabled"

# Step 3: Clone Repository
log "Step 3: Setting up application..."
if [ -d "$PROJECT_ROOT" ]; then
    warn "Project directory already exists at $PROJECT_ROOT"
    read -p "Continue with existing directory? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Deployment cancelled"
        exit 1
    fi
    cd "$PROJECT_ROOT"
    log "Pulling latest changes..."
    git pull || warn "Git pull failed, continuing..."
else
    log "Cloning repository..."
    mkdir -p "$(dirname $PROJECT_ROOT)"
    git clone "$REPO_URL" "$PROJECT_ROOT"
    success "Repository cloned"
fi

# Change ownership
chown -R "$USERNAME:$USERNAME" "$PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Step 4: Unified Website Setup
log "Step 4: Setting up unified website (cards_binders)..."
cd cards_binders

if [ ! -d "venv" ]; then
    log "Creating virtual environment..."
    sudo -u "$USERNAME" python3 -m venv venv
fi

log "Installing Python dependencies..."
sudo -u "$USERNAME" bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
success "Unified website dependencies installed"
cd ..

# Step 5: Game Backend Setup
log "Step 5: Setting up game backend..."
cd backend

if [ ! -d ".venv" ]; then
    log "Creating virtual environment..."
    sudo -u "$USERNAME" python3 -m venv .venv
fi

log "Installing Python dependencies..."
sudo -u "$USERNAME" bash -c "source .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
success "Game backend dependencies installed"
cd ..

# Step 6: Game Frontend Setup
log "Step 6: Setting up game frontend..."
cd frontend
log "Installing Node.js dependencies..."
sudo -u "$USERNAME" npm install
success "Frontend dependencies installed"
cd ..

# Step 7: Create Required Directories
log "Step 7: Creating required directories..."
mkdir -p logs
mkdir -p cards_binders/card_images
mkdir -p cards_binders/card_images_sets
chmod -R 755 logs
chmod -R 755 cards_binders/card_images
chmod -R 755 cards_binders/card_images_sets
chown -R "$USERNAME:$USERNAME" logs cards_binders/card_images cards_binders/card_images_sets
success "Directories created"

# Step 8: Build Frontend
log "Step 8: Building game frontend for production..."
cd frontend
export VITE_API_URL="https://$DOMAIN/api"
export VITE_WS_URL="wss://$DOMAIN"
sudo -u "$USERNAME" npm run build
success "Frontend built successfully"
cd ..

# Step 9: Create systemd Services
log "Step 9: Creating systemd services..."

# Unified Website Service
log "Creating unified-website.service..."
cat > /etc/systemd/system/unified-website.service << EOF
[Unit]
Description=MTG Cards Unified Website
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$PROJECT_ROOT/cards_binders
Environment="PATH=$PROJECT_ROOT/cards_binders/venv/bin"
Environment="GAME_FRONTEND_URL=https://$DOMAIN/games"
Environment="GAME_BACKEND_URL=https://$DOMAIN/api"
ExecStart=$PROJECT_ROOT/cards_binders/venv/bin/python main_app.py --host 0.0.0.0 --port 5010
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_ROOT/logs/unified_website.log
StandardError=append:$PROJECT_ROOT/logs/unified_website.log

[Install]
WantedBy=multi-user.target
EOF
success "unified-website.service created"

# Game Backend Service
log "Creating game-backend.service..."
cat > /etc/systemd/system/game-backend.service << EOF
[Unit]
Description=MTG Game Backend Server
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$PROJECT_ROOT/backend
Environment="PATH=$PROJECT_ROOT/backend/.venv/bin"
Environment="REDIS_URL=redis://localhost:6379"
ExecStart=$PROJECT_ROOT/backend/.venv/bin/python backend_server.py
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_ROOT/logs/game_backend.log
StandardError=append:$PROJECT_ROOT/logs/game_backend.log

[Install]
WantedBy=multi-user.target
EOF
success "game-backend.service created"

# Reload systemd and enable services
log "Reloading systemd..."
systemctl daemon-reload
systemctl enable unified-website.service
systemctl enable game-backend.service
success "Services enabled"

# Step 10: Configure Caddy
log "Step 10: Configuring Caddy..."

# Backup existing Caddyfile if it exists
if [ -f /etc/caddy/Caddyfile ]; then
    log "Backing up existing Caddyfile..."
    cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.backup.$(date +%Y%m%d_%H%M%S)
fi

log "Creating Caddyfile..."
cat > /etc/caddy/Caddyfile << EOF
$DOMAIN {
    # Enable automatic HTTPS
    encode zstd gzip
    
    # Logging
    log {
        output file /var/log/caddy/access.log
        format json
    }
    
    # Game Backend API (MUST come first - most specific routes)
    handle /api/* {
        reverse_proxy localhost:9000 {
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
        }
    }
    
    # Game Backend WebSocket
    handle /ws/* {
        reverse_proxy localhost:9000 {
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
            header_up Connection {>Connection}
            header_up Upgrade {>Upgrade}
        }
    }
    
    # Serve card images from unified website
    handle /card_images/* {
        root * $PROJECT_ROOT/cards_binders
        header Cache-Control "public, max-age=31536000"
        file_server
    }
    
    handle /card_images_sets/* {
        root * $PROJECT_ROOT/cards_binders
        header Cache-Control "public, max-age=31536000"
        file_server
    }
    
    # Game Frontend (static build) - served at /games
    handle /games/* {
        root * $PROJECT_ROOT/frontend/dist
        header Cache-Control "public, max-age=3600"
        try_files {path} /index.html
        file_server
    }
    
    # Game Frontend root path
    handle /games {
        rewrite /games /games/
        handle {
            root * $PROJECT_ROOT/frontend/dist
            try_files /index.html
            file_server
        }
    }
    
    # Unified Website (main_app.py) - all other routes
    handle {
        reverse_proxy localhost:5010 {
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
            header_up Host {host}
        }
    }
}
EOF
success "Caddyfile created"

# Validate Caddy configuration
log "Validating Caddy configuration..."
if caddy validate --config /etc/caddy/Caddyfile; then
    success "Caddy configuration is valid"
else
    error "Caddy configuration validation failed!"
    exit 1
fi

# Step 11: Start Services
log "Step 11: Starting services..."

log "Starting unified website..."
systemctl start unified-website.service
sleep 2

log "Starting game backend..."
systemctl start game-backend.service
sleep 2

log "Reloading Caddy..."
systemctl reload caddy || systemctl restart caddy
sleep 2

# Step 12: Verify Services
log "Step 12: Verifying services..."

# Check if ports are listening
if lsof -i :5010 > /dev/null 2>&1; then
    success "Unified website is running on port 5010"
else
    warn "Unified website port 5010 not listening"
fi

if lsof -i :9000 > /dev/null 2>&1; then
    success "Game backend is running on port 9000"
else
    warn "Game backend port 9000 not listening"
fi

# Check service status
if systemctl is-active --quiet unified-website.service; then
    success "unified-website.service is active"
else
    error "unified-website.service is not active"
    systemctl status unified-website.service --no-pager
fi

if systemctl is-active --quiet game-backend.service; then
    success "game-backend.service is active"
else
    error "game-backend.service is not active"
    systemctl status game-backend.service --no-pager
fi

if systemctl is-active --quiet caddy; then
    success "Caddy is active"
else
    error "Caddy is not active"
    systemctl status caddy --no-pager
fi

# Step 13: Test URLs
log "Step 13: Testing URLs..."
sleep 3

echo ""
log "Testing endpoints:"
echo ""

# Test unified website
if curl -s -o /dev/null -w "%{http_code}" "http://localhost:5010/" | grep -q "200"; then
    success "Unified website responding"
else
    warn "Unified website not responding"
fi

# Test game backend
if curl -s "http://localhost:9000/api/health" > /dev/null 2>&1; then
    success "Game backend API responding"
else
    warn "Game backend API not responding"
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "🎴 Deployment Complete!"
echo ""
log "Services Status:"
systemctl status unified-website.service --no-pager -l | head -3
systemctl status game-backend.service --no-pager -l | head -3
systemctl status caddy --no-pager -l | head -3
echo ""
log "URLs:"
echo "   Home:           https://$DOMAIN/"
echo "   Collection:     https://$DOMAIN/collection"
echo "   Wishlist:       https://$DOMAIN/wishlist"
echo "   Market Scanner: https://$DOMAIN/market"
echo "   Games:          https://$DOMAIN/games"
echo "   Game API:       https://$DOMAIN/api/"
echo ""
log "Logs:"
echo "   Unified Website: $PROJECT_ROOT/logs/unified_website.log"
echo "   Game Backend:    $PROJECT_ROOT/logs/game_backend.log"
echo "   Caddy:           /var/log/caddy/access.log"
echo ""
log "Useful Commands:"
echo "   View logs:       sudo journalctl -u unified-website.service -f"
echo "   Restart:         sudo systemctl restart unified-website.service"
echo "   Status:          sudo systemctl status unified-website.service"
echo ""
warn "⚠️  Make sure DNS is configured: $DOMAIN should point to this server's IP"
warn "⚠️  HTTPS certificates will be automatically generated by Caddy"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

