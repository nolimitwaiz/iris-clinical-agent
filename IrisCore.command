#!/bin/bash
# IrisCore Launcher — double-click to start the Iris Core web app
# Drag this file to your Dock or Desktop for quick access

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "==============================="
echo "  Iris Core — Heart Failure Care Agent"
echo "==============================="
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.11+."
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

# Install dependencies if streamlit is missing
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "Installing dependencies (first run only)..."
    pip3 install -r requirements.txt
    echo ""
fi

# Check API key status
if [ -f .env ]; then
    KEY=$(grep -E "^GEMINI_API_KEY=.+" .env | cut -d= -f2-)
    if [ -z "$KEY" ]; then
        echo "NOTE: No Gemini API key set. Running in demo mode."
        echo "      To enable AI responses, add your key to .env"
        echo "      Get a free key at: https://aistudio.google.com/apikey"
        echo ""
    else
        echo "Gemini API key found."
        echo ""
    fi
else
    echo "NOTE: No .env file found. Running in demo mode."
    echo ""
fi

echo "Starting Iris Core on http://localhost:8501 ..."
echo "Press Ctrl+C to stop."
echo ""

# Open browser after a short delay
(sleep 2 && open "http://localhost:8501") &

# Start Streamlit
python3 -m streamlit run app.py --server.headless true
