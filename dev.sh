#!/usr/bin/env bash
set -e

# Colors
ORANGE='\033[0;33m'
NC='\033[0m'

echo -e "${ORANGE}Starting Iris Core...${NC}"

# Start backend in background
echo -e "${ORANGE}[1/2] Starting FastAPI backend on :8000${NC}"
uvicorn api.main:app --reload --port 8000 &
BACKEND_PID=$!

# Cleanup on exit
trap "echo ''; echo -e '${ORANGE}Shutting down...${NC}'; kill $BACKEND_PID 2>/dev/null; exit 0" INT TERM

# Wait briefly for backend to start
sleep 2

# Start frontend in foreground
echo -e "${ORANGE}[2/2] Starting Vite frontend on :3000${NC}"
echo -e "${ORANGE}Open http://localhost:3000${NC}"
cd frontend && npm run dev
