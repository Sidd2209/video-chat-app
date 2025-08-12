#!/bin/bash

# Comprehensive fix and startup script for Video Chat Application
echo "🔧 Fixing and starting Video Chat Application..."

# Function to cleanup background processes
cleanup() {
    echo "🛑 Shutting down..."
    pkill -f "python.*run.py" 2>/dev/null
    pkill -f "npm.*dev" 2>/dev/null
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

echo "📦 Installing backend dependencies..."
cd backend

# Create fresh virtual environment
if [ -d "venv" ]; then
    echo "🗑️ Removing old virtual environment..."
    rm -rf venv
fi

echo "🔧 Creating new virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Test backend import
echo "🧪 Testing backend imports..."
python3 -c "from app import app; print('✅ Backend imports successfully')" || {
    echo "❌ Backend import failed"
    exit 1
}

echo "🌐 Starting Flask backend..."
python3 run.py &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Test backend
echo "🧪 Testing backend..."
python3 ../test_backend.py
if [ $? -ne 0 ]; then
    echo "❌ Backend test failed. Check the logs above."
    exit 1
fi

echo "📦 Installing frontend dependencies..."
cd ../chat-link-stream

# Install frontend dependencies
npm install

echo "🎨 Starting React frontend..."
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 5

echo "✅ Application started successfully!"
echo "📡 Backend running on: http://localhost:8081"
echo "🎨 Frontend running on: http://localhost:8080"
echo ""
echo "🌐 Open your browser and go to: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for background processes
wait
