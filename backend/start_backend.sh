#!/bin/bash
# Start the Magic Gamestation backend server (FastAPI)

cd "$(dirname "$0")"

echo "🎴 Backend: Starting..."

# Virtual Environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Backend: Creating venv..."
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# Dependencies
echo "📦 Backend: Checking dependencies..."
pip install -q -r requirements.txt

# Checks
if [ ! -f "../frontend/public/data/cards.json" ]; then
    echo "⚠️  Backend: Card database missing at ../frontend/public/data/cards.json"
fi

echo "✅ Backend: Ready on http://localhost:9000"
python backend_server.py
