# VPS Deployment Guide - Magic Game Station

Complete guide for deploying a Node.js frontend + Python backend application on Ubuntu VPS with systemd, Caddy, and HTTPS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Server Setup](#initial-server-setup)
3. [Application Setup](#application-setup)
4. [systemd Services](#systemd-services)
5. [Frontend Production Build](#frontend-production-build)
6. [Caddy Configuration](#caddy-configuration)
7. [DNS Configuration](#dns-configuration)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance & Updates](#maintenance--updates)

---

## Prerequisites

- Ubuntu 22.04+ VPS
- Root or sudo access
- Domain name configured
- SSH access to server

---

## Initial Server Setup

### 1. Update System Packages

```bash
apt update && apt upgrade -y
```

### 2. Install Core Dependencies

```bash
apt install -y \
    git \
    python3 \
    python3-venv \
    python3-pip \
    nodejs \
    npm \
    redis-server \
    caddy
```

### 3. Start and Enable Redis

```bash
systemctl start redis-server
systemctl enable redis-server
```

### 4. Verify Installations

```bash
python3 --version  # Should be 3.9+
node --version     # Should be 18+
redis-cli ping     # Should return PONG
caddy version      # Should show version
```

---

## Application Setup

### 1. Clone Repository

```bash
# Recommended location
cd /opt
git clone https://github.com/YourUsername/your-repo.git magicgamestation
cd magicgamestation
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Deactivate venv
deactivate

cd ..
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

cd ..
```

### 4. Manual Verification (Important!)

**Terminal 1 - Backend:**
```bash
cd /opt/magicgamestation/backend
source .venv/bin/activate
python backend_server.py
# Should see: "Backend server starting" and "✓ Redis connected"
# Test: curl http://localhost:9000/api/games
```

**Terminal 2 - Frontend:**
```bash
cd /opt/magicgamestation/frontend
npm run dev
# Should see: "VITE ready" on port 5173
# Test: curl http://localhost:5173
```

**Terminal 3 - Test:**
```bash
curl http://localhost:9000/api/games
curl http://localhost:5173
```

If both work, proceed to systemd setup. **Stop manual processes** (Ctrl+C) before continuing.

---

## systemd Services

### 1. Create Service Files

Copy service files from `deploy/` directory:

```bash
cd /opt/magicgamestation
sudo cp deploy/magicgamestation-backend.service /etc/systemd/system/
sudo cp deploy/magicgamestation-frontend.service /etc/systemd/system/
```

### 2. Update Paths (if needed)

Edit service files if your repo is not in `/opt/magicgamestation`:

```bash
sudo nano /etc/systemd/system/magicgamestation-backend.service
sudo nano /etc/systemd/system/magicgamestation-frontend.service
```

Update:
- `WorkingDirectory`
- `ExecStart` paths
- `Environment PATH` (venv path)

### 3. Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable magicgamestation-backend
sudo systemctl enable magicgamestation-frontend

# Start services
sudo systemctl start magicgamestation-backend
sudo systemctl start magicgamestation-frontend

# Check status
sudo systemctl status magicgamestation-backend
sudo systemctl status magicgamestation-frontend
```

### 4. Verify Services

```bash
# Test endpoints
curl http://localhost:9000/api/games
curl http://localhost:5173

# View logs if needed
journalctl -u magicgamestation-backend -n 50 --no-pager
journalctl -u magicgamestation-frontend -n 50 --no-pager
```

---

## Frontend Production Build

### 1. Set Environment Variables

```bash
cd /opt/magicgamestation/frontend

# Replace YOUR_DOMAIN with your actual domain
export VITE_API_URL="https://YOUR_DOMAIN/api"
export VITE_WS_URL="wss://YOUR_DOMAIN"
```

### 2. Build Static Files

```bash
npm run build

# Verify dist/ was created
ls -la dist/
```

### 3. Handle Static Assets

**Important:** If your app downloads files at runtime (like card images), ensure Caddy serves them from the `public/` directory, not just `dist/`. See Caddy configuration below.

---

## Caddy Configuration

### 1. Create Caddyfile

```bash
sudo nano /etc/caddy/Caddyfile
```

### 2. Basic Configuration Template

```caddyfile
# Replace YOUR_DOMAIN with your actual domain

YOUR_DOMAIN {
    # Proxy API requests to backend (MUST come first)
    handle /api/* {
        reverse_proxy localhost:9000
    }
    
    # Proxy WebSocket connections to backend
    handle /ws/* {
        reverse_proxy localhost:9000 {
            header_up X-Real-IP {remote_host}
        }
    }
    
    # Serve dynamic content from public/ (if app downloads files at runtime)
    handle /card_images/* {
        root * /opt/magicgamestation/frontend/public
        header Content-Type image/jpeg
        header Cache-Control "public, max-age=31536000"
        header Access-Control-Allow-Origin "*"
        file_server
    }
    
    handle /cards/* {
        root * /opt/magicgamestation/frontend/public
        header Content-Type image/jpeg
        header Cache-Control "public, max-age=31536000"
        header Access-Control-Allow-Origin "*"
        file_server
    }
    
    handle /data/* {
        root * /opt/magicgamestation/frontend/public
        header Content-Type application/json
        header Access-Control-Allow-Origin "*"
        file_server
    }
    
    handle /decks/* {
        root * /opt/magicgamestation/frontend/public
        header Content-Type application/json
        header Access-Control-Allow-Origin "*"
        file_server
    }
    
    # Serve static frontend files (comes last - catch-all)
    handle {
        root * /opt/magicgamestation/frontend/dist
        file_server
        try_files {path} /index.html
    }
}
```

**Key Points:**
- `handle` blocks are processed **in order** - more specific routes first
- API and WebSocket routes **must** come before `file_server`
- Dynamic content directories should be served from `public/` if files are added at runtime
- Static build files are served from `dist/`

### 3. Validate and Reload

```bash
# Validate configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Reload Caddy
sudo systemctl reload caddy

# Check status
sudo systemctl status caddy
```

### 4. Test Configuration

```bash
# Test API
curl -I https://YOUR_DOMAIN/api/games

# Test frontend
curl -I https://YOUR_DOMAIN/

# Test static assets
curl -I https://YOUR_DOMAIN/card_images/some_image.jpg
```

---

## DNS Configuration

### 1. Configure DNS Records

In your domain registrar (e.g., Porkbun, Cloudflare):

- **Type:** A
- **Name:** @ (or blank for root domain)
- **Value:** YOUR_VPS_IP
- **TTL:** 300 (or default)

### 2. Wait for Propagation

DNS changes can take 5-60 minutes to propagate. Check with:

```bash
dig YOUR_DOMAIN +short
# Should show your VPS IP
```

### 3. Caddy Will Auto-Obtain SSL

Once DNS points to your VPS, Caddy will automatically:
- Obtain SSL certificate from Let's Encrypt
- Enable HTTPS
- Set up HTTP→HTTPS redirects

Check certificate status:
```bash
journalctl -u caddy -n 50 --no-pager | grep -E "(certificate|tls|obtained)"
```

---

## Troubleshooting

### Port Conflicts

**Problem:** Service can't start because port is in use.

**Solution:**
```bash
# Find what's using the port
lsof -i :9000  # Backend
lsof -i :5173  # Frontend

# Kill the process
kill <PID>

# Or kill by name
pkill -f "python.*backend_server.py"
pkill -f "npm.*dev"
```

### Case Sensitivity Issues

**Problem:** Files exist but requests fail (Linux is case-sensitive).

**Solution:**
```bash
# Rename files to lowercase
cd /opt/magicgamestation/frontend/dist/card_images/
find . -type f -name "*.jpg" | while read file; do
    dir=$(dirname "$file")
    filename=$(basename "$file")
    lowercase=$(echo "$filename" | tr '[:upper:]' '[:lower:]')
    if [ "$filename" != "$lowercase" ]; then
        mv "$file" "$dir/$lowercase"
    fi
done
```

### Images Not Loading After Fetch

**Problem:** Backend saves images to `public/` but frontend serves from `dist/`.

**Solution:** Configure Caddy to serve dynamic content directories from `public/` (see Caddy configuration above).

### API Returns HTML Instead of JSON

**Problem:** Caddy routing order is wrong.

**Solution:** Ensure API routes (`handle /api/*`) come **before** `file_server` in Caddyfile.

### SSL Certificate Not Obtaining

**Problem:** DNS not pointing to VPS, or port 80/443 blocked.

**Solution:**
```bash
# Check DNS
dig YOUR_DOMAIN +short

# Check ports are open
sudo netstat -tulpn | grep -E ':(80|443)'

# Check Caddy logs
journalctl -u caddy -n 100 --no-pager | grep -i "certificate\|tls\|error"
```

### Service Won't Start

**Problem:** Check logs for errors.

**Solution:**
```bash
# View service logs
journalctl -u magicgamestation-backend -n 100 --no-pager
journalctl -u magicgamestation-frontend -n 100 --no-pager

# Common issues:
# - Missing dependencies (check requirements.txt)
# - Wrong paths in service file
# - Missing environment variables
# - Redis not running (for backend)
```

---

## Maintenance & Updates

### Quick Restart

```bash
cd /opt/magicgamestation
./deploy/restart.sh
```

### Full Update (Pull Code + Rebuild + Restart)

```bash
cd /opt/magicgamestation
./deploy/update.sh
```

### Manual Update Steps

```bash
# 1. Pull latest code
cd /opt/magicgamestation
git pull

# 2. Update backend dependencies (if needed)
cd backend
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

# 3. Rebuild frontend (if frontend code changed)
cd frontend
export VITE_API_URL="https://YOUR_DOMAIN/api"
export VITE_WS_URL="wss://YOUR_DOMAIN"
npm run build
cd ..

# 4. Restart services
systemctl restart magicgamestation-backend
systemctl restart magicgamestation-frontend  # Only if enabled
```

### Viewing Logs

```bash
# Backend logs (follow)
journalctl -u magicgamestation-backend -f

# Frontend logs (follow)
journalctl -u magicgamestation-frontend -f

# Caddy logs (follow)
journalctl -u caddy -f

# All services status
systemctl status magicgamestation-backend magicgamestation-frontend caddy redis-server
```

### Disable Frontend Dev Server (Optional)

If using static build only:

```bash
systemctl stop magicgamestation-frontend
systemctl disable magicgamestation-frontend
```

---

## Architecture Summary

```
┌─────────────────────────────────────────┐
│           Internet / Users              │
└─────────────────┬───────────────────────┘
                  │ HTTPS (443)
                  │
         ┌────────▼────────┐
         │   Caddy (443)   │  ← SSL Termination, Reverse Proxy
         └────────┬────────┘
                  │
     ┌────────────┼────────────┐
     │            │            │
┌────▼────┐  ┌────▼────┐  ┌───▼────┐
│ Frontend│  │  API    │  │ WebSocket│
│  (dist) │  │ /api/*  │  │  /ws/*   │
└─────────┘  └────┬────┘  └────┬────┘
                  │            │
         ┌────────▼────────────▼──┐
         │  Backend (port 9000)   │
         │  FastAPI + Python      │
         └────────┬───────────────┘
                  │
         ┌────────▼────────┐
         │  Redis (6379)   │  ← Game State Persistence
         └─────────────────┘
```

**Key Components:**
- **Caddy:** Reverse proxy, SSL, static file serving
- **Backend:** FastAPI on port 9000, systemd service
- **Frontend:** Static build in `dist/`, served by Caddy
- **Redis:** State persistence (optional but recommended)
- **systemd:** Service management, auto-start on boot

---

## Checklist for New Deployment

- [ ] Server packages installed (git, python3, nodejs, npm, redis, caddy)
- [ ] Repository cloned to `/opt/`
- [ ] Backend venv created and dependencies installed
- [ ] Frontend dependencies installed
- [ ] Manual verification passed (both services work)
- [ ] systemd service files created and enabled
- [ ] Frontend built for production with correct env vars
- [ ] Caddyfile configured with correct domain
- [ ] DNS A record points to VPS IP
- [ ] SSL certificate obtained (check Caddy logs)
- [ ] API endpoints working (test with curl)
- [ ] Frontend accessible via HTTPS
- [ ] Static assets loading correctly
- [ ] WebSocket connections working
- [ ] Services auto-start on reboot (test with `sudo reboot`)

---

## Notes

- **File Paths:** All paths assume `/opt/magicgamestation` - adjust if different
- **Ports:** Backend uses 9000, Frontend dev uses 5173 (if enabled)
- **Case Sensitivity:** Linux filesystems are case-sensitive - ensure filenames match
- **Dynamic Content:** Files added at runtime should be served from `public/`, not `dist/`
- **Caddy Order:** Route handlers are processed in order - specific routes first
- **SSL:** Caddy automatically obtains and renews certificates

---

## Additional Resources

- [Caddy Documentation](https://caddyserver.com/docs/)
- [systemd Service Files](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Vite Production Build](https://vitejs.dev/guide/build.html)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

---

**Last Updated:** January 2026
**Tested On:** Ubuntu 22.04, Python 3.10+, Node.js 18+

