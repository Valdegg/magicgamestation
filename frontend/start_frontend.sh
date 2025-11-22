#!/bin/bash
# Start the Magic Workstation frontend

cd "$(dirname "$0")"

echo "🎨 Frontend: Starting..."

# Dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Frontend: Installing dependencies..."
    npm install --silent
fi

echo "✅ Frontend: Ready on http://localhost:5173"
npm run dev
