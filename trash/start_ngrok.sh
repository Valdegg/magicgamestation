#!/bin/bash
# Start ngrok tunnels for Magic Workstation

echo "🌐 Starting ngrok tunnels for Magic Workstation..."
echo ""
echo "Make sure your backend and frontend are already running:"
echo "  - Backend: ./start_backend.sh (port 9000)"
echo "  - Frontend: ./start_frontend.sh (port 5173)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok not found!"
    echo "Please install ngrok from https://ngrok.com/download"
    exit 1
fi

echo "Starting ngrok on port 5173 (Frontend)..."
echo ""
echo "⚠️  IMPORTANT: After ngrok starts, you'll see a URL like:"
echo "   https://xxxx-xxxx.ngrok-free.app"
echo ""
echo "You'll need to update the backend CORS settings with this URL."
echo "See instructions below after starting..."
echo ""

# Start ngrok on the frontend port
# For multiple ports, you'd need ngrok paid plan or run multiple instances
ngrok http 5173

