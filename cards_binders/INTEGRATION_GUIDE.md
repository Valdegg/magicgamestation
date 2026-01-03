# MTG Cards Unified Website - Integration Guide

## Overview

This document describes the integration of the Magic Gamestation (game lobby + games) into the unified MTG Cards website. Previously, the game system ran as a separate application. Now it's integrated as part of a unified website that includes Collection Management, Wishlist Management, Market Scanner, and Games.

## Architecture Changes

### Before Integration

- **Magic Gamestation**: Separate React app (port 5173) + FastAPI backend (port 9000)
- **Cards Binders**: Separate FastAPI app (port 5010) with Collection, Wishlist, and Market Scanner
- Two separate applications, no unified navigation

### After Integration

- **Unified Website**: Single FastAPI app (port 5010) serving:
  - Home page (`/`)
  - Collection Manager (`/collection`)
  - Wishlist Manager (`/wishlist`)
  - Market Scanner (`/market`)
  - Games (`/games` - redirects to game frontend)
- **Game Services**: Still run separately but integrated into unified navigation:
  - Game Backend: FastAPI (port 9000)
  - Game Frontend: React app (port 5173)

## File Structure

```
magicworkstation/
├── cards_binders/              # Unified website (main entry point)
│   ├── main_app.py            # Main FastAPI app with all routes
│   ├── start_website.sh        # Startup script for all services
│   ├── collection_ui.py       # Collection management routes
│   ├── wishlist_ui.py         # Wishlist management routes
│   ├── web_ui.py              # Market scanner routes
│   └── ...
├── backend/                    # Game backend (still separate)
│   ├── backend_server.py      # Game logic & WebSocket server
│   └── start_backend.sh
├── frontend/                   # Game frontend (still separate)
│   ├── src/                   # React app for games/lobby
│   └── start_frontend.sh
└── logs/                       # Log files for all services
```

## Running the Unified Website

### Quick Start

```bash
cd cards_binders
./start_website.sh
```

This script starts:
1. Redis (if available) - for game state persistence
2. Game Backend (port 9000)
3. Game Frontend (port 5173)
4. Unified Website (port 5010)

### Manual Start (if needed)

If you need to start services individually:

```bash
# Terminal 1: Game Backend
cd backend
./start_backend.sh

# Terminal 2: Game Frontend
cd frontend
./start_frontend.sh

# Terminal 3: Unified Website
cd cards_binders
python main_app.py
```

## URL Structure

### Unified Website (Port 5010)

- **Home**: `http://localhost:5010/`
- **Collection**: `http://localhost:5010/collection`
- **Wishlist**: `http://localhost:5010/wishlist`
- **Market Scanner**: `http://localhost:5010/market`
- **Games**: `http://localhost:5010/games` → Redirects to `http://localhost:5173`

### Game Services

- **Game Backend API**: `http://localhost:9000/api`
- **Game Frontend**: `http://localhost:5173` (full screen games/lobby)

## Server Deployment Configuration

### For Production Deployment

When deploying to a domain, you'll want to:

1. **Set the unified website as the main entry point** (port 5010)
2. **Configure reverse proxy** to route:
   - Main domain → Unified website (port 5010)
   - `/games` → Redirects to game frontend (port 5173)
   - Game backend API → Port 9000 (for WebSocket connections)

### Example Nginx Configuration

```nginx
# Main unified website
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:5010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Game frontend (if you want it on a subdomain)
server {
    listen 80;
    server_name games.yourdomain.com;

    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# Game backend API (for WebSocket connections)
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:9000;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Environment Variables

The unified website uses these environment variables (optional):

- `GAME_BACKEND_URL`: Game backend URL (default: `http://localhost:9000`)
- `GAME_FRONTEND_URL`: Game frontend URL (default: `http://localhost:5173`)

Set these in production to match your domain:

```bash
export GAME_BACKEND_URL="https://api.yourdomain.com"
export GAME_FRONTEND_URL="https://games.yourdomain.com"
```

## Key Changes Made

### 1. Navigation Integration

Added "Games" link to the unified navigation bar in `main_app.py`:
- Navigation bar appears on all pages (Home, Collection, Wishlist, Market Scanner)
- "Games" link redirects to the game frontend for full-screen experience

### 2. Games Route

The `/games` route in `main_app.py`:
- Redirects directly to the game frontend (port 5173)
- No iframe embedding - full screen experience
- Users can use browser back button to return to unified site

### 3. Startup Script

Created `start_website.sh` that:
- Starts all required services (Redis, game backend, game frontend, unified website)
- Checks if services are running correctly
- Provides status output with all URLs
- Handles cleanup on exit (Ctrl+C)

### 4. Home Page Update

Updated home page to include:
- Games card alongside Collection, Wishlist, and Market Scanner
- Consistent styling and navigation

## Service Dependencies

### Required Services

1. **Redis** (optional but recommended)
   - Used for game state persistence
   - If not available, games run in memory-only mode
   - Install: `brew install redis` (macOS) or `apt-get install redis-server` (Linux)

2. **Python 3.11+**
   - Required for all Python services
   - Virtual environments are created automatically

3. **Node.js & npm**
   - Required for game frontend
   - Dependencies installed automatically

### Port Requirements

Make sure these ports are available:
- **5010**: Unified website
- **9000**: Game backend API
- **5173**: Game frontend
- **6379**: Redis (if using)

## Log Files

All services log to `logs/` directory:
- `logs/unified_website.log` - Unified website (main_app.py)
- `logs/game_backend.log` - Game backend server
- `logs/game_frontend.log` - Game frontend (Vite dev server)

## Troubleshooting

### Games Page Shows "Connection Refused"

- Ensure game backend (port 9000) is running
- Ensure game frontend (port 5173) is running
- Check `logs/game_backend.log` and `logs/game_frontend.log`

### Unified Website Won't Start

- Check if port 5010 is already in use: `lsof -ti:5010`
- Check Python dependencies: `pip install -r requirements.txt`
- Check logs: `logs/unified_website.log`

### Games Don't Persist

- Ensure Redis is running: `redis-cli ping`
- Check Redis connection in game backend logs
- Games will work without Redis but state is lost on restart

## Migration Notes

If you're migrating from the old setup:

1. **No changes needed to game backend/frontend** - they still work the same
2. **New unified entry point** - Use `cards_binders/main_app.py` instead of just the game frontend
3. **Navigation** - Users can now access Collection, Wishlist, Market Scanner from the same site
4. **Games redirect** - Clicking "Games" redirects to the full-screen game experience

## Summary

The unified website now provides a single entry point for all MTG card management features:
- **Collection Management**: Track cards you own
- **Wishlist Management**: Track cards you want
- **Market Scanner**: Find deals on wishlist cards
- **Games**: Play Magic: The Gathering online

All accessible from one navigation bar, with the games experience remaining full-screen when accessed.

