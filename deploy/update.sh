#!/bin/bash
# Update and restart Magic Game Station
# Usage: ./deploy/update.sh

set -e  # Exit on error

cd "$(dirname "$0")/.."

echo "📥 Pulling latest code..."
git pull

echo "📦 Updating backend dependencies (if needed)..."
cd backend
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate
cd ..

echo "🏗️  Rebuilding frontend..."
cd frontend
export VITE_API_URL="https://playmagic.now/api"
export VITE_WS_URL="wss://playmagic.now"
npm run build
cd ..

echo "🔄 Restarting services..."
./deploy/restart.sh

echo ""
echo "✅ Update complete!"
echo "🧪 Testing API..."
sleep 2
curl -s https://playmagic.now/api/games | jq . 2>/dev/null || curl -s https://playmagic.now/api/games | head -3

