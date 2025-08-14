#!/bin/bash

echo "🚀 Starting Video Chat Application..."

# Set environment variables
export VITE_API_URL=http://localhost:8081
export VITE_SOCKET_URL=http://localhost:8081

# Check if backend is running
echo "📡 Checking backend status..."
if curl -s http://localhost:8081 > /dev/null; then
    echo "✅ Backend is already running on port 8081"
else
    echo "🔧 Starting backend..."
    cd backend
    python run.py &
    BACKEND_PID=$!
    echo "Backend started with PID: $BACKEND_PID"
    cd ..
    
    # Wait for backend to be ready
    echo "⏳ Waiting for backend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8081 > /dev/null; then
            echo "✅ Backend is ready!"
            break
        fi
        echo "Waiting... ($i/30)"
        sleep 1
    done
fi

# Start frontend
echo "🌐 Starting frontend..."
cd chat-link-stream
npm run dev &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"
cd ..

echo "🎉 Application started!"
echo "📱 Frontend: http://localhost:8080"
echo "🔧 Backend: http://localhost:8081"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user to stop
wait
