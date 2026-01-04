# Unified Website Deployment Guide - playmagic.now

Complete guide for deploying the MTG Cards Unified Manager to `playmagic.now` domain. This includes:
- **Collection Manager** (`/collection`)
- **Wishlist Manager** (`/wishlist`)
- **Market Scanner** (`/market`)
- **Games** (`/games`)

All services run as subpaths of the main domain.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Server Setup](#server-setup)
4. [Application Setup](#application-setup)
5. [Production Build](#production-build)
6. [systemd Services](#systemd-services)
7. [Caddy Configuration](#caddy-configuration)
8. [Environment Variables](#environment-variables)
9. [Testing & Verification](#testing--verification)
10. [Troubleshooting](#troubleshooting)
11. [Maintenance](#maintenance)

---

## Overview

The unified website consists of three main components:

1. **Unified Website** (FastAPI) - Port 5010
   - Main application serving Collection, Wishlist, Market Scanner
   - Routes: `/`, `/collection`, `/wishlist`, `/market`, `/games`
   - File: `cards_binders/main_app.py`

2. **Game Backend** (FastAPI) - Port 9000
   - WebSocket server for real-time game state
   - Card database and game logic
   - File: `backend/backend_server.py`

3. **Game Frontend** (React/Vite) - Port 5173 (dev) or static build (prod)
   - React application for game lobby and gameplay
   - Served as static files in production

**Architecture:**
```
playmagic.now
├── /                    → Unified Website (main_app.py)
├── /collection          → Unified Website (main_app.py)
├── /wishlist            → Unified Website (main_app.py)
├── /market              → Unified Website (main_app.py)
├── /games               → Game Frontend (static build)
├── /api/*               → Game Backend (backend_server.py)
└── /ws/*                → Game Backend WebSocket (backend_server.py)
```

---

## Prerequisites

- Ubuntu 22.04+ VPS
- Root or sudo access
- Domain `playmagic.now` configured with DNS pointing to your server
- SSH access to server

---

## Server Setup

### 1. Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Core Dependencies

```bash
sudo apt install -y \
    git \
    python3 \
    python3-venv \
    python3-pip \
    nodejs \
    npm \
    redis-server \
    caddy \
    build-essential
```

### 3. Start and Enable Redis

```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 4. Verify Installations

```bash
python3 --version  # Should be 3.9+
node --version     # Should be 18+
npm --version       # Should be 9+
redis-cli ping     # Should return PONG
caddy version      # Should show version
```

---

## Application Setup

### 1. Clone Repository

```bash
# Recommended location
cd /opt
sudo git clone https://github.com/YourUsername/magicworkstation.git
sudo chown -R $USER:$USER magicworkstation
cd magicworkstation
```

### 2. Unified Website Setup (cards_binders)

```bash
cd cards_binders

# Create virtual environment
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Deactivate venv
deactivate

cd ..
```

### 3. Game Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Deactivate venv
deactivate

cd ..
```

### 4. Game Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

cd ..
```

### 5. Create Required Directories

```bash
# Create logs directory
mkdir -p logs

# Create card images directories (if they don't exist)
mkdir -p cards_binders/card_images
mkdir -p cards_binders/card_images_sets

# Set permissions
chmod -R 755 logs
chmod -R 755 cards_binders/card_images
chmod -R 755 cards_binders/card_images_sets
```

---

## Production Build

### 1. Build Game Frontend

The game frontend needs to be built for production and served as static files.

```bash
cd frontend

# Set production environment variables
export VITE_API_URL="https://playmagic.now/api"
export VITE_WS_URL="wss://playmagic.now"

# Build for production
npm run build

# Verify build
ls -la dist/

cd ..
```

**Note:** The built files will be in `frontend/dist/` and served by Caddy.

---

## systemd Services

Create systemd service files to run all three components as daemons.

### 1. Unified Website Service

Create `/etc/systemd/system/unified-website.service`:

```bash
sudo nano /etc/systemd/system/unified-website.service
```

```ini
[Unit]
Description=MTG Cards Unified Website
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/magicworkstation/cards_binders
Environment="PATH=/opt/magicworkstation/cards_binders/venv/bin"
Environment="GAME_FRONTEND_URL=https://playmagic.now/games"
Environment="GAME_BACKEND_URL=https://playmagic.now/api"
ExecStart=/opt/magicworkstation/cards_binders/venv/bin/python main_app.py --host 0.0.0.0 --port 5010
Restart=always
RestartSec=10
StandardOutput=append:/opt/magicworkstation/logs/unified_website.log
StandardError=append:/opt/magicworkstation/logs/unified_website.log

[Install]
WantedBy=multi-user.target
```

**Replace `YOUR_USERNAME` with your actual username.**

### 2. Game Backend Service

Create `/etc/systemd/system/game-backend.service`:

```bash
sudo nano /etc/systemd/system/game-backend.service
```

```ini
[Unit]
Description=MTG Game Backend Server
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/magicworkstation/backend
Environment="PATH=/opt/magicworkstation/backend/.venv/bin"
Environment="REDIS_URL=redis://localhost:6379"
ExecStart=/opt/magicworkstation/backend/.venv/bin/python backend_server.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/magicworkstation/logs/game_backend.log
StandardError=append:/opt/magicworkstation/logs/game_backend.log

[Install]
WantedBy=multi-user.target
```

### 3. Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable unified-website.service
sudo systemctl enable game-backend.service

# Start services
sudo systemctl start unified-website.service
sudo systemctl start game-backend.service

# Check status
sudo systemctl status unified-website.service
sudo systemctl status game-backend.service
```

### 4. Verify Services Are Running

```bash
# Check if ports are listening
sudo lsof -i :5010  # Unified website
sudo lsof -i :9000  # Game backend

# Check logs
tail -f /opt/magicworkstation/logs/unified_website.log
tail -f /opt/magicworkstation/logs/game_backend.log
```

---

## Caddy Configuration

Caddy will handle HTTPS, routing, and serve static files.

### 1. Create Caddyfile

```bash
sudo nano /etc/caddy/Caddyfile
```

```caddyfile
playmagic.now {
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
        root * /opt/magicworkstation/cards_binders
        header Cache-Control "public, max-age=31536000"
        file_server
    }
    
    handle /card_images_sets/* {
        root * /opt/magicworkstation/cards_binders
        header Cache-Control "public, max-age=31536000"
        file_server
    }
    
    # Game Frontend (static build) - served at /games
    handle /games/* {
        root * /opt/magicworkstation/frontend/dist
        header Cache-Control "public, max-age=3600"
        try_files {path} /index.html
        file_server
    }
    
    # Game Frontend root path
    handle /games {
        rewrite /games /games/
        handle {
            root * /opt/magicworkstation/frontend/dist
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
```

**Key Points:**
- Routes are processed **in order** - most specific first
- `/api/*` and `/ws/*` go to game backend
- `/games` and `/games/*` serve static frontend build
- `/card_images/*` serve card images
- Everything else goes to unified website

### 2. Validate and Reload Caddy

```bash
# Test configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Reload Caddy
sudo systemctl reload caddy

# Check status
sudo systemctl status caddy
```

### 3. Check Caddy Logs

```bash
sudo tail -f /var/log/caddy/access.log
```

---

## Environment Variables

### Unified Website Environment

The unified website reads these environment variables (set in systemd service):

- `GAME_FRONTEND_URL` - URL for game frontend (default: `http://localhost:5173`)
- `GAME_BACKEND_URL` - URL for game backend API (default: `http://localhost:9000`)

### Game Frontend Environment

Set during build (already done above):

- `VITE_API_URL` - Backend API URL
- `VITE_WS_URL` - WebSocket URL

### Game Backend Environment

Set in systemd service:

- `REDIS_URL` - Redis connection URL (default: `redis://localhost:6379`)

---

## Testing & Verification

### 1. Test All Routes

```bash
# Test unified website home
curl -I https://playmagic.now/

# Test collection
curl -I https://playmagic.now/collection

# Test wishlist
curl -I https://playmagic.now/wishlist

# Test market scanner
curl -I https://playmagic.now/market

# Test games
curl -I https://playmagic.now/games

# Test game backend API
curl https://playmagic.now/api/health
```

### 2. Verify HTTPS

All routes should redirect to HTTPS automatically. Check:

```bash
curl -I http://playmagic.now/
# Should redirect to https://playmagic.now/
```

### 3. Test Game Functionality

1. Visit `https://playmagic.now/games`
2. Create a game lobby
3. Verify WebSocket connection works
4. Test creating/joining games

### 4. Check Service Logs

```bash
# Unified website logs
sudo journalctl -u unified-website.service -f

# Game backend logs
sudo journalctl -u game-backend.service -f

# Caddy logs
sudo tail -f /var/log/caddy/access.log
```

---

## Troubleshooting

### Services Won't Start

**Check service status:**
```bash
sudo systemctl status unified-website.service
sudo systemctl status game-backend.service
```

**Check logs:**
```bash
sudo journalctl -u unified-website.service -n 50
sudo journalctl -u game-backend.service -n 50
```

**Common issues:**
- Port already in use: `sudo lsof -i :5010` or `sudo lsof -i :9000`
- Python path incorrect: Verify venv path in service file
- Missing dependencies: Check `requirements.txt` installed
- Permission issues: Check file ownership and permissions

### Caddy Won't Start

**Check Caddy configuration:**
```bash
sudo caddy validate --config /etc/caddy/Caddyfile
```

**Check Caddy logs:**
```bash
sudo journalctl -u caddy -n 50
```

**Common issues:**
- DNS not configured: Verify `playmagic.now` points to server IP
- Port conflicts: Check if ports 80/443 are in use
- Certificate issues: Caddy should auto-generate, check logs

### Games Not Working

**Check WebSocket connection:**
- Open browser console on `/games` page
- Look for WebSocket connection errors
- Verify `VITE_WS_URL` is set correctly in frontend build

**Check game backend:**
```bash
curl https://playmagic.now/api/health
# Should return JSON response
```

**Verify Redis:**
```bash
redis-cli ping
# Should return PONG
```

### Static Files Not Loading

**Check file permissions:**
```bash
ls -la /opt/magicworkstation/frontend/dist/
ls -la /opt/magicworkstation/cards_binders/card_images/
```

**Check Caddy routing:**
- Verify `/games/*` route comes before catch-all
- Check file_server directive is present
- Verify root paths are correct

---

## Daily Market Scans

The Market Scanner automatically loads the **newest scan results** by default. To keep the data fresh, you should run daily market scans.

### Running Market Scans

There are several ways to run market scans:

#### Option 1: Using the Scan Script (Recommended)

```bash
cd /opt/magicworkstation/cards_binders

# Run scan with default settings (10 second delay)
./run_market_scan.sh

# Run scan with custom delay (15 seconds between cards)
./run_market_scan.sh 15

# Run scan with custom wishlist file
./run_market_scan.sh 10 my_custom_wishlist.json
```

#### Option 2: Using Python Directly

```bash
cd /opt/magicworkstation/cards_binders
source venv/bin/activate

# Run scan using the simple_version script
python simple_version/wishlist_deals.py

# With custom delay
python simple_version/wishlist_deals.py --delay 15

deactivate
```

#### Option 3: Using main_app.py (Scan + Start Server)

```bash
cd /opt/magicworkstation/cards_binders
source venv/bin/activate

# Run scan then start server
python main_app.py --scan

# With custom delay
python main_app.py --scan --delay 15

deactivate
```

### Automated Daily Scans (Cron)

Set up a cron job to run scans automatically every day:

```bash
# Edit crontab
crontab -e

# Add this line to run scan daily at 2 AM
0 2 * * * cd /opt/magicworkstation/cards_binders && /opt/magicworkstation/cards_binders/venv/bin/python simple_version/wishlist_deals.py >> /opt/magicworkstation/logs/market_scan.log 2>&1

# Or using the shell script
0 2 * * * /opt/magicworkstation/cards_binders/run_market_scan.sh >> /opt/magicworkstation/logs/market_scan.log 2>&1
```

**Cron Schedule Examples:**
- `0 2 * * *` - Daily at 2:00 AM
- `0 */6 * * *` - Every 6 hours
- `0 2 * * 1` - Every Monday at 2:00 AM
- `0 2,14 * * *` - Twice daily at 2:00 AM and 2:00 PM

### Scan Results Location

Scan results are saved to:
```
/opt/magicworkstation/cards_binders/results/wishlist_deals_YYYYMMDD_HHMMSS.json
```

The Market Scanner web interface automatically loads the **newest file** (by modification time) when you visit `/market`.

### Monitoring Scans

Check scan logs:
```bash
# View scan log
tail -f /opt/magicworkstation/logs/market_scan.log

# List all scan results
ls -lth /opt/magicworkstation/cards_binders/results/

# View latest scan result summary
cat /opt/magicworkstation/cards_binders/results/wishlist_deals_*.json | jq '.summary' | tail -1
```

### Scan Performance

- **Typical scan time:** ~10-15 seconds per card (with delay)
- **100 cards:** ~15-25 minutes
- **Delay recommendation:** 10-15 seconds to avoid rate limiting
- **Results:** Automatically saved with timestamp

---

## Maintenance

### Updating the Application

**Option 1: Using the update script (Recommended)**

```bash
cd /opt/magicworkstation
./deploy/update.sh
```

This script will:
- Pull latest code from git
- Update all dependencies
- Rebuild the frontend
- Restart all services

**Option 2: Manual update**

```bash
cd /opt/magicworkstation

# Pull latest changes
git pull

# Update unified website
cd cards_binders
source venv/bin/activate
pip install -r requirements.txt --upgrade
deactivate

# Update game backend
cd ../backend
source .venv/bin/activate
pip install -r requirements.txt --upgrade
deactivate

# Update game frontend
cd ../frontend
npm install
npm run build

# Restart services
sudo systemctl restart unified-website.service
sudo systemctl restart game-backend.service
sudo systemctl reload caddy
```

### Initial Deployment

For first-time deployment, use the automated deployment script:

```bash
# Clone repository first (if not already cloned)
cd /opt
sudo git clone https://github.com/YourUsername/magicworkstation.git
cd magicworkstation

# Run deployment script
sudo ./deploy/deploy_unified_website.sh
```

The deployment script will:
- Install all system dependencies
- Set up Python virtual environments
- Install Node.js dependencies
- Build the frontend
- Create systemd services
- Configure Caddy
- Start all services

**Note:** Make sure to set the `REPO_URL` environment variable if using a different repository:

```bash
export REPO_URL="https://github.com/YourUsername/your-repo.git"
sudo ./deploy/deploy_unified_website.sh
```

### Viewing Logs

```bash
# Unified website
sudo journalctl -u unified-website.service -f

# Game backend
sudo journalctl -u game-backend.service -f

# All logs
tail -f /opt/magicworkstation/logs/*.log
```

### Restarting Services

```bash
# Restart unified website
sudo systemctl restart unified-website.service

# Restart game backend
sudo systemctl restart game-backend.service

# Reload Caddy (no downtime)
sudo systemctl reload caddy
```

### Backup

**Important files to backup:**
- `cards_binders/collection.json`
- `cards_binders/wishlist.json`
- `cards_binders/card_images/` (if large, consider separate backup)
- `cards_binders/results/` (market scanner results)
- Redis data (if using persistence)

**Backup script:**
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/magicworkstation"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup data files
tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" \
    /opt/magicworkstation/cards_binders/*.json \
    /opt/magicworkstation/cards_binders/results/

# Backup Redis (if using persistence)
redis-cli SAVE
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

echo "Backup completed: $BACKUP_DIR"
```

---

## Quick Reference

### Service Management

```bash
# Start services
sudo systemctl start unified-website.service
sudo systemctl start game-backend.service

# Stop services
sudo systemctl stop unified-website.service
sudo systemctl stop game-backend.service

# Restart services
sudo systemctl restart unified-website.service
sudo systemctl restart game-backend.service

# Check status
sudo systemctl status unified-website.service
sudo systemctl status game-backend.service
```

### Important Paths

- **Unified Website:** `/opt/magicworkstation/cards_binders/main_app.py`
- **Game Backend:** `/opt/magicworkstation/backend/backend_server.py`
- **Game Frontend Build:** `/opt/magicworkstation/frontend/dist/`
- **Logs:** `/opt/magicworkstation/logs/`
- **Caddy Config:** `/etc/caddy/Caddyfile`
- **Service Files:** `/etc/systemd/system/unified-website.service`, `/etc/systemd/system/game-backend.service`

### URLs

- **Home:** `https://playmagic.now/`
- **Collection:** `https://playmagic.now/collection`
- **Wishlist:** `https://playmagic.now/wishlist`
- **Market Scanner:** `https://playmagic.now/market`
- **Games:** `https://playmagic.now/games`
- **Game API:** `https://playmagic.now/api/`

---

## Next Steps

After deployment:

1. ✅ Verify all routes work correctly
2. ✅ Test game creation and joining
3. ✅ Set up monitoring (optional)
4. ✅ Configure backups
5. ✅ Set up log rotation
6. ✅ Document any custom configurations

For issues or questions, check the logs first, then refer to the troubleshooting section above.

