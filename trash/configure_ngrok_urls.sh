#!/bin/bash
# Configure frontend to use ngrok backend URL

echo "🔧 Configure Frontend for ngrok Backend"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -z "$1" ]; then
    echo "Usage: ./configure_ngrok_urls.sh <backend-ngrok-url>"
    echo ""
    echo "Example:"
    echo "  ./configure_ngrok_urls.sh https://abc123.ngrok-free.app"
    echo ""
    echo "This will update:"
    echo "  - frontend/src/api/gameApi.ts (REST API)"
    echo "  - frontend/src/context/GameStateWebSocket.tsx (WebSocket)"
    echo ""
    exit 1
fi

BACKEND_URL="$1"

# Remove trailing slash if present
BACKEND_URL="${BACKEND_URL%/}"

# Convert https:// to wss:// for WebSocket
WS_URL="${BACKEND_URL/https:/wss:}"
WS_URL="${WS_URL/http:/ws:}"

echo "Backend URL: $BACKEND_URL"
echo "WebSocket URL: $WS_URL"
echo ""

# Backup files
echo "📦 Creating backups..."
cp frontend/src/api/gameApi.ts frontend/src/api/gameApi.ts.backup
cp frontend/src/context/GameStateWebSocket.tsx frontend/src/context/GameStateWebSocket.tsx.backup
echo "  ✓ Backups created (.backup files)"
echo ""

# Update gameApi.ts
echo "🔄 Updating frontend/src/api/gameApi.ts..."
# Use regex to match any existing URL assignment
sed -i.tmp "s|const API_BASE = '.*';|const API_BASE = '${BACKEND_URL}/api';|g" frontend/src/api/gameApi.ts
rm -f frontend/src/api/gameApi.ts.tmp
echo "  ✓ API endpoint updated"

# Update GameStateWebSocket.tsx
echo "🔄 Updating frontend/src/context/GameStateWebSocket.tsx..."
# Use regex to match any existing wsUrl assignment
sed -i.tmp "s|const wsUrl = \`.*\`;|const wsUrl = \`${WS_URL}/ws/\${gId}/\${pId}\`;|g" frontend/src/context/GameStateWebSocket.tsx
rm -f frontend/src/context/GameStateWebSocket.tsx.tmp
echo "  ✓ WebSocket URL updated"

echo ""
echo "✅ Configuration complete!"
echo ""
echo "Next steps:"
echo "  1. Restart your frontend (Ctrl+C and ./start_frontend.sh)"
echo "  2. Access via ngrok URLs:"
echo "     - Frontend: https://your-frontend.ngrok-free.app"
echo "     - Backend: $BACKEND_URL"
echo ""
echo "To revert changes, run:"
echo "  ./restore_localhost.sh"
echo ""
