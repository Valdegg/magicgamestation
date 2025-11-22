#!/bin/bash
# Interactive script to help configure ngrok for Magic Workstation

echo "🎴 Magic Workstation - ngrok Setup Helper"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed!"
    echo ""
    echo "Please install ngrok first:"
    echo "  macOS:  brew install ngrok"
    echo "  Other:  https://ngrok.com/download"
    echo ""
    exit 1
fi

echo "✅ ngrok found!"
echo ""

# Check if services are running
echo "📊 Checking if services are running..."
echo ""

BACKEND_RUNNING=false
FRONTEND_RUNNING=false

if curl -s http://localhost:9000/docs > /dev/null 2>&1; then
    echo "✅ Backend is running on port 9000"
    BACKEND_RUNNING=true
else
    echo "❌ Backend is NOT running"
fi

if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "✅ Frontend is running on port 5173"
    FRONTEND_RUNNING=true
else
    echo "❌ Frontend is NOT running"
fi

echo ""

# Provide instructions based on what's running
if [ "$BACKEND_RUNNING" = false ] || [ "$FRONTEND_RUNNING" = false ]; then
    echo "⚠️  Please start the missing services first:"
    echo ""
    if [ "$BACKEND_RUNNING" = false ]; then
        echo "  Terminal 1: ./start_backend.sh"
    fi
    if [ "$FRONTEND_RUNNING" = false ]; then
        echo "  Terminal 2: ./start_frontend.sh"
    fi
    echo ""
    echo "Then run this script again."
    exit 0
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  IMPORTANT: For remote access, you need BOTH tunnels!"
echo ""
echo "Why? When remote users access your app, their browser tries to"
echo "connect to localhost:9000 - which is THEIR machine, not yours!"
echo ""
echo "Choose your setup:"
echo ""
echo "  1) Backend tunnel (Step 1 of 2)"
echo "     - Start this first"
echo "     - Then use configure_ngrok_urls.sh"
echo ""
echo "  2) Frontend tunnel (Step 2 of 2)"
echo "     - Run after configuring backend URL"
echo "     - Share this URL with friends!"
echo ""
echo "  3) Show full setup instructions"
echo ""
echo -n "Enter choice (1-3): "
read choice

echo ""

case $choice in
    1)
        echo "🚀 Starting ngrok for Backend (port 9000)..."
        echo ""
        echo "📝 After ngrok starts, you'll see a URL like:"
        echo "   https://abc123.ngrok-free.app"
        echo ""
        echo "COPY THAT URL! Then in another terminal:"
        echo ""
        echo "  ./configure_ngrok_urls.sh https://abc123.ngrok-free.app"
        echo "  ./start_frontend.sh"
        echo "  ./start_ngrok.sh"
        echo ""
        sleep 3
        ngrok http 9000
        ;;
    2)
        echo "🚀 Starting ngrok for Frontend (port 5173)..."
        echo ""
        echo "⚠️  Make sure you already:"
        echo "  1. Ran ./start_ngrok_backend.sh (in another terminal)"
        echo "  2. Ran ./configure_ngrok_urls.sh with backend URL"
        echo "  3. Restarted frontend"
        echo ""
        echo "After this starts, SHARE THE URL with your friends!"
        echo ""
        sleep 3
        ngrok http 5173
        ;;
    3)
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📚 FULL SETUP INSTRUCTIONS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "Terminal 1:"
        echo "  ./start_backend.sh"
        echo ""
        echo "Terminal 2:"
        echo "  ./start_frontend.sh"
        echo ""
        echo "Terminal 3:"
        echo "  ./start_ngrok_backend.sh"
        echo "  (Copy the URL, e.g., https://abc123.ngrok-free.app)"
        echo ""
        echo "Terminal 4:"
        echo "  ./configure_ngrok_urls.sh https://abc123.ngrok-free.app"
        echo ""
        echo "Terminal 2 (restart):"
        echo "  Ctrl+C"
        echo "  ./start_frontend.sh"
        echo ""
        echo "Terminal 5:"
        echo "  ./start_ngrok.sh"
        echo "  (Share this URL with friends!)"
        echo ""
        echo "When done:"
        echo "  ./restore_localhost.sh"
        echo ""
        echo "See NGROK_SETUP.md for detailed guide."
        echo "See NGROK_QUICK_START.txt for quick reference."
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

