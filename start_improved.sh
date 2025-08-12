#!/bin/bash

echo "🚀 Starting Improved Omegle-like Chat Application..."
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Kill all existing processes
print_status "Stopping all existing processes..."
pkill -f "vite" 2>/dev/null || true
pkill -f "python.*app_improved.py" 2>/dev/null || true
pkill -f "python.*run.py" 2>/dev/null || true
pkill -f "node.*vite" 2>/dev/null || true
sleep 3

# Check if ports are free
print_status "Checking port availability..."
if lsof -i :8080 > /dev/null 2>&1; then
    print_error "Port 8080 is still in use"
    lsof -i :8080
    exit 1
fi

if lsof -i :8081 > /dev/null 2>&1; then
    print_error "Port 8081 is still in use"
    lsof -i :8081
    exit 1
fi

print_success "Ports are available"

# Check if Python virtual environment exists
if [ ! -d "backend/venv" ]; then
    print_status "Creating Python virtual environment..."
    cd backend
    python3 -m venv venv
    cd ..
fi

# Activate virtual environment and install dependencies
print_status "Installing backend dependencies..."
cd backend
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..

# Start improved backend
print_status "Starting improved backend on port 8081..."
cd backend
source venv/bin/activate
python3 app_improved.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
print_status "Waiting for backend to start..."
sleep 5

# Test backend
print_status "Testing backend..."
curl -s http://localhost:8081/ > /dev/null
if [ $? -eq 0 ]; then
    print_success "Backend is running on port 8081"
else
    print_error "Backend failed to start"
    exit 1
fi

# Fix frontend dependencies
print_status "Fixing frontend dependencies..."
cd chat-link-stream

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    print_status "Creating .env.local file..."
    cat > .env.local << EOF
VITE_API_URL=http://localhost:8081
VITE_SOCKET_URL=http://localhost:8081
EOF
fi

# Start frontend with explicit port
print_status "Starting frontend on port 8080..."
PORT=8080 npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
print_status "Waiting for frontend to start..."
sleep 10

# Test frontend
print_status "Testing frontend..."
curl -s http://localhost:8080/ > /dev/null
if [ $? -eq 0 ]; then
    print_success "Frontend is running on port 8080"
else
    print_warning "Frontend failed to start on port 8080, trying alternative port..."
    curl -s http://localhost:5173/ > /dev/null
    if [ $? -eq 0 ]; then
        print_warning "Frontend is running on port 5173 (fallback)"
    else
        print_error "Frontend failed to start completely"
        exit 1
    fi
fi

# Test WebSocket connection
print_status "Testing WebSocket connection..."
node test_connection.js
if [ $? -eq 0 ]; then
    print_success "WebSocket connection test passed"
else
    print_warning "WebSocket connection test failed, but continuing..."
fi

echo ""
echo "🎉 SUCCESS! Improved Omegle-like Chat Application is running:"
echo "============================================================="
echo "📡 Backend: http://localhost:8081"
echo "🎨 Frontend: http://localhost:8080 (or http://localhost:5173)"
echo ""
echo "🌐 Open your browser and go to: http://localhost:8080"
echo ""
echo "✨ New Features Available:"
echo "   • Smart user matching based on interests and language"
echo "   • User profiles and preferences"
echo "   • Connection quality monitoring"
echo "   • User blocking and reporting"
echo "   • Multi-language support"
echo "   • Enhanced WebRTC with TURN servers"
echo "   • Session duration tracking"
echo "   • Partner information display"
echo ""
echo "🔧 To stop the application, press Ctrl+C"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    print_status "Stopping application..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    print_success "Application stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for background processes
wait
