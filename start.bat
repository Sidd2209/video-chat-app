@echo off
echo 🚀 Starting Video Chat Application...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.8+ first.
    exit /b 1
)

:: Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed. Please install Node.js first.
    exit /b 1
)

:: Check if directories exist
if not exist "backend" (
    echo ❌ Backend directory not found. Please ensure the backend folder exists.
    exit /b 1
)

if not exist "chat-link-stream" (
    echo ❌ Frontend directory not found. Please ensure the chat-link-stream folder exists.
    exit /b 1
)

:: Setup and start backend
echo 📦 Installing backend dependencies...
cd backend
if not exist "venv" (
    echo 🔧 Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate
pip install -r requirements.txt

echo 🌐 Starting Flask backend...
start "Flask Backend" python run.py

:: Wait a moment for backend to start
timeout /t 3 /nobreak >nul

:: Setup and start frontend
echo 📦 Installing frontend dependencies...
cd ..\chat-link-stream
call npm install

echo 🎨 Starting React frontend...
start "React Frontend" npm run dev

echo ✅ Application started successfully!
echo 📡 Backend running on: http://localhost:5000
echo 🎨 Frontend running on: http://localhost:5173
echo.
echo Press Ctrl+C in the respective windows to stop the servers
pause
