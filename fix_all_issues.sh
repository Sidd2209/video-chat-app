#!/bin/bash

# Video Chat Application - Comprehensive Fix Script
# This script fixes common issues and ensures the app runs properly

echo "🔧 Video Chat Application - Fix All Issues Script"
echo "=================================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to kill processes on a port
kill_port() {
    local port=$1
    echo "🔄 Killing processes on port $port..."
    lsof -ti :$port | xargs kill -9 2>/dev/null || true
    sleep 2
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists python3; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    echo "   Download from: https://www.python.org/downloads/"
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    echo "   Download from: https://nodejs.org/"
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Kill any existing processes
echo "🔄 Cleaning up existing processes..."
kill_port 8080
kill_port 8081

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "chat-link-stream" ]; then
    echo "❌ Please run this script from the project root directory (Online-website/)"
    exit 1
fi

# Fix backend issues
echo "🔧 Fixing backend issues..."

cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install/upgrade dependencies
echo "📦 Installing backend dependencies..."
pip install -r requirements.txt

# Check for missing dependencies
echo "🔍 Checking for missing dependencies..."
python3 -c "
import sys
required_packages = ['flask', 'flask_socketio', 'flask_cors', 'eventlet', 'python_dotenv']
missing = []
for package in required_packages:
    try:
        __import__(package.replace('-', '_'))
    except ImportError:
        missing.append(package)
if missing:
    print(f'Missing packages: {missing}')
    sys.exit(1)
else:
    print('All required packages are installed')
"

if [ $? -ne 0 ]; then
    echo "❌ Some required packages are missing. Installing them..."
    pip install flask flask-socketio flask-cors eventlet python-dotenv
fi

cd ..

# Fix frontend issues
echo "🔧 Fixing frontend issues..."

cd chat-link-stream

# Clear npm cache
echo "🧹 Clearing npm cache..."
npm cache clean --force

# Remove node_modules and package-lock.json if they exist
if [ -d "node_modules" ]; then
    echo "🗑️ Removing existing node_modules..."
    rm -rf node_modules
fi

if [ -f "package-lock.json" ]; then
    echo "🗑️ Removing existing package-lock.json..."
    rm package-lock.json
fi

# Install dependencies
echo "📦 Installing frontend dependencies..."
npm install

# Check for missing dependencies
echo "🔍 Checking for missing dependencies..."
npm ls --depth=0

cd ..

# Make startup script executable
echo "🔧 Making startup script executable..."
chmod +x start.sh

# Create a simple environment file for backend if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo "📝 Creating backend environment file..."
    cat > backend/.env << EOF
SECRET_KEY=your-secret-key-change-this-in-production
FLASK_DEBUG=True
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8081
EOF
fi

# Test the setup
echo "🧪 Testing the setup..."

# Test backend
echo "🔍 Testing backend..."
cd backend
source venv/bin/activate
python3 -c "
from app import app
print('✅ Backend app imports successfully')
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Backend test passed"
else
    echo "❌ Backend test failed"
    exit 1
fi

cd ..

# Test frontend
echo "🔍 Testing frontend..."
cd chat-link-stream
npm run build --silent >/dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Frontend test passed"
else
    echo "❌ Frontend test failed"
    exit 1
fi

cd ..

echo ""
echo "🎉 All issues have been fixed!"
echo ""
echo "🚀 To start the application:"
echo "   ./start.sh"
echo ""
echo "🧪 To test the application:"
echo "   python3 test_app.py"
echo ""
echo "🌐 Access the application:"
echo "   Frontend: http://localhost:8080"
echo "   Backend: http://localhost:8081"
echo ""
echo "📝 If you still encounter issues:"
echo "   1. Check the browser console (F12) for frontend errors"
echo "   2. Check the terminal output for backend errors"
echo "   3. Ensure your firewall allows connections on ports 8080 and 8081"
echo "   4. Try running the test script: python3 test_app.py"
