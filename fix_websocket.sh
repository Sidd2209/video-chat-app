#!/bin/bash

echo "🔧 Fixing WebSocket Connection Issues..."

# Kill any existing processes
echo "🛑 Stopping existing processes..."
pkill -f "vite" 2>/dev/null || true
pkill -f "python.*run.py" 2>/dev/null || true
sleep 2

# Start backend on port 8081
echo "🌐 Starting backend on port 8081..."
cd backend
source venv/bin/activate
python3 run.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Test backend
echo "🧪 Testing backend..."
python3 test_backend.py
if [ $? -ne 0 ]; then
    echo "❌ Backend failed to start"
    exit 1
fi

# Start frontend on port 8080
echo "🎨 Starting frontend on port 8080..."
cd chat-link-stream
PORT=8080 npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
sleep 5

# Test frontend
echo "🧪 Testing frontend..."
curl -s http://localhost:8080/ > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Frontend is running on port 8080"
else
    echo "❌ Frontend failed to start"
    exit 1
fi

echo ""
echo "🎉 SUCCESS! Both services are running:"
echo "📡 Backend: http://localhost:8081"
echo "🎨 Frontend: http://localhost:8080"
echo ""
echo "🌐 Open your browser and go to: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for background processes
wait
