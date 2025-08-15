#!/bin/bash

# Video Chat Application Startup Script
# This script starts both the Flask backend and React frontend

echo "🚀 Starting Video Chat Application..."

# Function to cleanup background processes
cleanup() {
    echo "🛑 Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "❌ Backend directory not found. Please ensure the backend folder exists."
    exit 1
fi

# Check if frontend directory exists
if [ ! -d "chat-link-stream" ]; then
    echo "❌ Frontend directory not found. Please ensure the chat-link-stream folder exists."
    exit 1
fi

echo "📦 Installing backend dependencies..."
cd backend
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

echo "🌐 Starting Flask backend..."
python run.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

echo "📦 Installing frontend dependencies..."
cd ../chat-link-stream
npm install

echo "🎨 Starting React frontend..."
npm run dev &
FRONTEND_PID=$!

echo "✅ Application started successfully!"
echo "📡 Backend running on: http://localhost:8081"
echo "🎨 Frontend running on: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for background processes
wait
