#!/bin/bash

# Start development servers for EduComic
# This script starts both backend and frontend servers

set -e  # Exit on error

echo "🚀 Starting EduComic Development Servers..."
echo ""

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Install it with:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "After installation, restart your terminal and run this script again."
    exit 1
fi

# Check if Node.js is installed
if ! command -v npm &> /dev/null; then
    echo "❌ Node.js/npm is not installed."
    echo "   Install from: https://nodejs.org/"
    exit 1
fi

# Check if dependencies are installed
if [ ! -d "backend/.venv" ]; then
    echo "📦 Installing backend dependencies with UV..."
    cd backend
    uv sync --locked
    cd ..
    echo "✅ Backend dependencies installed"
    echo ""
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm ci
    cd ..
    echo "✅ Frontend dependencies installed"
    echo ""
fi

# Create log directory
mkdir -p .logs

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    
    # Kill backend
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    # Kill frontend
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Kill any remaining processes on the ports
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
    
    echo "✅ Servers stopped"
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup INT TERM

# Check if ports are already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use. Stopping existing process..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8080 is already in use. Stopping existing process..."
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Start backend
echo "📦 Starting Backend (FastAPI on port 8000)..."
cd backend/src
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../../.logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ../..

# Wait for backend to start
echo "   Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ Backend is running (PID: $BACKEND_PID)"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ❌ Backend failed to start. Check .logs/backend.log for details."
        cat .logs/backend.log
        cleanup
    fi
    sleep 0.5
done

# Start frontend
echo "🎨 Starting Frontend (Vite on port 8080)..."
cd frontend
npm run dev > ../.logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "   Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8080 > /dev/null 2>&1; then
        echo "   ✅ Frontend is running (PID: $FRONTEND_PID)"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ❌ Frontend failed to start. Check .logs/frontend.log for details."
        cat .logs/frontend.log
        cleanup
    fi
    sleep 0.5
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All servers are running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   🌐 Frontend:  http://localhost:8080"
echo "   🔧 Backend:   http://localhost:8000"
echo "   📚 API Docs:  http://localhost:8000/docs"
echo ""
echo "   📝 Logs:"
echo "      Backend:  .logs/backend.log"
echo "      Frontend: .logs/frontend.log"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for user interrupt
wait
