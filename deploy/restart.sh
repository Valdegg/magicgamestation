#!/bin/bash
# Restart Magic Game Station services

echo "🔄 Restarting Magic Game Station services..."

# Restart backend
echo "📦 Restarting backend..."
systemctl restart magicgamestation-backend

# Check if frontend service exists and is enabled
if systemctl is-enabled magicgamestation-frontend &>/dev/null; then
    echo "🎨 Restarting frontend..."
    systemctl restart magicgamestation-frontend
else
    echo "ℹ️  Frontend service not running (using static build)"
fi

# Wait a moment for services to start
sleep 2

# Check status
echo ""
echo "📊 Service Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
systemctl status magicgamestation-backend --no-pager | head -5

if systemctl is-enabled magicgamestation-frontend &>/dev/null; then
    echo ""
    systemctl status magicgamestation-frontend --no-pager | head -5
fi

echo ""
echo "✅ Restart complete!"

