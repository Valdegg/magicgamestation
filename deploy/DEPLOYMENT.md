# Magic Game Station - VPS Deployment Guide

## Quick Setup Commands

### 1. Copy systemd service files
```bash
sudo cp deploy/magicgamestation-backend.service /etc/systemd/system/
sudo cp deploy/magicgamestation-frontend.service /etc/systemd/system/
```

### 2. Update paths in service files (if needed)
```bash
sudo nano /etc/systemd/system/magicgamestation-backend.service
sudo nano /etc/systemd/system/magicgamestation-frontend.service
# Change /opt/magicgamestation to your actual path
```

### 3. Build frontend for production
```bash
cd /opt/magicgamestation/frontend

# Set environment variables for build
# Replace YOUR_DOMAIN with your actual domain
export VITE_API_URL="https://YOUR_DOMAIN/api"
export VITE_WS_URL="wss://YOUR_DOMAIN"

# Build static files
npm run build

# This creates dist/ directory with static files
```

### 4. Configure Caddy
```bash
# Copy example Caddyfile
sudo cp deploy/Caddyfile.example /etc/caddy/Caddyfile

# Edit with your domain
sudo nano /etc/caddy/Caddyfile
# Replace YOUR_DOMAIN with your actual domain

# Test configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Reload Caddy
sudo systemctl reload caddy
```

### 5. Enable and start services
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

### 6. Check logs
```bash
# Backend logs
sudo journalctl -u magicgamestation-backend -f

# Frontend logs
sudo journalctl -u magicgamestation-frontend -f

# Caddy logs
sudo journalctl -u caddy -f
```

## Alternative: Static Frontend (Recommended)

Instead of running the Vite dev server, build static files and serve via Caddy:

1. Build frontend:
```bash
cd /opt/magicgamestation/frontend
export VITE_API_URL="https://YOUR_DOMAIN/api"
export VITE_WS_URL="wss://YOUR_DOMAIN"
npm run build
```

2. Disable frontend service (Caddy serves static files):
```bash
sudo systemctl stop magicgamestation-frontend
sudo systemctl disable magicgamestation-frontend
```

3. Update Caddyfile to serve from `frontend/dist` directory.

## Troubleshooting

### Backend won't start
- Check Redis: `sudo systemctl status redis-server`
- Check logs: `sudo journalctl -u magicgamestation-backend -n 50`
- Verify venv: `ls -la /opt/magicgamestation/backend/.venv`

### Frontend won't start
- Check Node: `node --version` (needs 18+)
- Check logs: `sudo journalctl -u magicgamestation-frontend -n 50`
- Verify dependencies: `cd /opt/magicgamestation/frontend && npm list`

### Caddy issues
- Check config: `sudo caddy validate --config /etc/caddy/Caddyfile`
- Check logs: `sudo journalctl -u caddy -n 50`
- Verify DNS: `dig YOUR_DOMAIN` (should point to VPS IP)

### Port conflicts
- Check what's using ports: `sudo netstat -tulpn | grep -E ':(9000|5173|80|443)'`
- Backend uses 9000, Frontend dev uses 5173

## Environment Variables

If you need to set environment variables for the backend, edit the service file:
```bash
sudo nano /etc/systemd/system/magicgamestation-backend.service
```

Add under `[Service]`:
```
Environment="REDIS_HOST=localhost"
Environment="REDIS_PORT=6379"
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart magicgamestation-backend
```

