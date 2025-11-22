#!/bin/bash
# Restore frontend to use localhost backend

echo "🔄 Restoring localhost configuration..."
echo ""

if [ -f "frontend/src/api/gameApi.ts.backup" ]; then
    mv frontend/src/api/gameApi.ts.backup frontend/src/api/gameApi.ts
    echo "  ✓ Restored frontend/src/api/gameApi.ts"
fi

if [ -f "frontend/src/context/GameStateWebSocket.tsx.backup" ]; then
    mv frontend/src/context/GameStateWebSocket.tsx.backup frontend/src/context/GameStateWebSocket.tsx
    echo "  ✓ Restored frontend/src/context/GameStateWebSocket.tsx"
fi

echo ""
echo "✅ Restored to localhost configuration"
echo ""
echo "Restart your frontend to apply changes:"
echo "  ./start_frontend.sh"
echo ""

