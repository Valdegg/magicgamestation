#!/bin/bash
# Start ngrok tunnel for the backend (port 9000)

echo "🌐 Starting ngrok tunnel for Backend (port 9000)..."
echo ""
echo "Make sure your backend is already running:"
echo "  ./start_backend.sh"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok not found!"
    echo "Please install ngrok from https://ngrok.com/download"
    exit 1
fi

echo "Starting ngrok on port 9000 (Backend API)..."
ngrok http 9000

