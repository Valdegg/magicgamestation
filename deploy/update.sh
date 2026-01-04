#!/bin/bash
# Update and restart Unified Website
# Usage: ./deploy/update.sh

set -e  # Exit on error

cd "$(dirname "$0")/.."

echo "📥 Pulling latest code..."
git pull

echo "📦 Updating unified website dependencies..."
cd cards_binders
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -q -r requirements.txt --upgrade
    deactivate
else
    echo "⚠️  Virtual environment not found. Run deploy/deploy_unified_website.sh first."
fi
cd ..

echo "📦 Updating game backend dependencies..."
cd backend
if [ -d ".venv" ]; then
    source .venv/bin/activate
    pip install -q -r requirements.txt --upgrade
    deactivate
else
    echo "⚠️  Virtual environment not found. Run deploy/deploy_unified_website.sh first."
fi
cd ..

echo "🏗️  Rebuilding frontend..."
cd frontend
export VITE_API_URL="https://playmagic.now/api"
export VITE_WS_URL="wss://playmagic.now"
npm install
npm run build
cd ..

echo "🔄 Restarting services..."
if systemctl is-active --quiet unified-website.service 2>/dev/null; then
    echo "   Restarting unified-website.service..."
    sudo systemctl restart unified-website.service
else
    echo "   ⚠️  unified-website.service not found. Run deploy/deploy_unified_website.sh first."
fi

if systemctl is-active --quiet game-backend.service 2>/dev/null; then
    echo "   Restarting game-backend.service..."
    sudo systemctl restart game-backend.service
else
    echo "   ⚠️  game-backend.service not found. Run deploy/deploy_unified_website.sh first."
fi

echo "   Reloading Caddy..."
sudo systemctl reload caddy || sudo systemctl restart caddy

echo ""
echo "✅ Update complete!"
echo "🧪 Testing services..."
sleep 2

# Test unified website
if curl -s -o /dev/null -w "%{http_code}" "https://playmagic.now/" | grep -q "200"; then
    echo "   ✅ Unified website responding"
else
    echo "   ⚠️  Unified website not responding"
fi

# Test game backend API
if curl -s "https://playmagic.now/api/health" > /dev/null 2>&1; then
    echo "   ✅ Game backend API responding"
else
    echo "   ⚠️  Game backend API not responding"
fi

