#!/bin/bash

# EduComic Development Server Launcher
# Starts both backend and frontend simultaneously

set -e

echo "🚀 Starting EduComic Development Servers..."
echo "============================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to cleanup on exit
cleanup() {
    echo -e "\n${RED}Shutting down servers...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Start Backend
echo -e "${BLUE}📦 Setting up backend...${NC}"
cd backend
uv sync --locked
cd src

echo -e "${GREEN}✓ Backend dependencies installed${NC}"
echo -e "${BLUE}🔧 Starting backend server on http://localhost:8000${NC}"
uv run uvicorn main:app --reload > ../../backend.log 2>&1 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}✗ Backend failed to start. Check backend.log for errors.${NC}"
    exit 1
fi

# Return to root
cd ../..

# Start Frontend
echo -e "${BLUE}📦 Setting up frontend...${NC}"
cd frontend

echo -e "${BLUE}Installing locked frontend dependencies...${NC}"
npm ci

echo -e "${GREEN}✓ Frontend dependencies ready${NC}"
echo -e "${BLUE}🎨 Starting frontend server...${NC}"
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!

# Return to root
cd ..

# Wait a moment for frontend to start
sleep 3

echo ""
echo "============================================"
echo -e "${GREEN}✅ Both servers are running!${NC}"
echo "============================================"
echo -e "${BLUE}Backend:${NC}  http://localhost:8000"
echo -e "${BLUE}API Docs:${NC} http://localhost:8000/docs"
echo -e "${BLUE}Frontend:${NC} http://localhost:5173"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo -e "${RED}Press Ctrl+C to stop both servers${NC}"
echo "============================================"

# Keep script running and wait for Ctrl+C
wait
