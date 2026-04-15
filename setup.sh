#!/bin/bash

# Webhook Setup Script - Start ngrok and FastAPI server
# Usage: bash setup.sh

echo "🚀 Starting agentic-review-gate webhook setup..."

# Activate virtual environment
echo -e "\n📦 Activating virtual environment..."
source venv/bin/activate

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed. Install it from: https://ngrok.com/download"
    exit 1
fi

# Start ngrok in background
echo -e "\n🌐 Starting ngrok on port 8000..."
ngrok http 8000 &
NGROK_PID=$!

# Wait for ngrok to start
sleep 3

# Get ngrok public URL
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | cut -d'"' -f4 | head -1)

if [ -n "$NGROK_URL" ]; then
    echo "✅ ngrok is running at: $NGROK_URL"
    echo -e "\n📝 Update your GitHub webhook with:"
    echo "   Payload URL: $NGROK_URL/webhook/github"
else
    echo "⚠️  Could not retrieve ngrok URL automatically. Check http://127.0.0.1:4040"
fi

# Start FastAPI server
echo -e "\n🔧 Starting FastAPI server..."
echo "📍 Server running at: http://127.0.0.1:8000"
echo "📊 Docs at: http://127.0.0.1:8000/docs"

python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000

# Cleanup on exit
echo -e "\n🛑 Shutting down ngrok..."
kill $NGROK_PID 2>/dev/null
echo "✅ Cleanup complete"
