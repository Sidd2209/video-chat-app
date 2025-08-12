# 🎯 Complete Video Chat Application Setup Guide

## 🚀 Quick Start (Recommended)

Run the comprehensive fix and startup script:

```bash
./fix_and_start.sh
```

This script will:
- ✅ Fix all configuration issues
- ✅ Install all dependencies
- ✅ Start both backend and frontend
- ✅ Test the application
- ✅ Open the app in your browser

## 🔧 Issues Fixed

### 1. **Port Configuration Issues**
- ✅ Backend port: Fixed to 8081 (was inconsistent)
- ✅ Frontend port: Fixed to 8080 (was 3000)
- ✅ API URLs: Updated to use correct ports
- ✅ WebSocket URLs: Updated to use correct ports

### 2. **Backend Code Issues**
- ✅ Removed duplicate method definitions in UserManager
- ✅ Fixed AttributeError with waiting_rooms
- ✅ Updated port configuration in app.py
- ✅ Fixed user_id emission timing

### 3. **Frontend Configuration**
- ✅ Created .env.local with correct URLs
- ✅ Updated Vite config to use port 8080
- ✅ Fixed WebSocket connection handling
- ✅ Improved error handling

### 4. **Dependencies**
- ✅ Updated requirements.txt
- ✅ Fixed virtual environment setup
- ✅ Added proper error handling

## 📁 Project Structure

```
Online-website/
├── backend/                 # Flask backend
│   ├── app.py              # Main Flask application
│   ├── config.py           # Configuration settings
│   ├── run.py              # Startup script
│   ├── requirements.txt    # Python dependencies
│   └── venv/               # Virtual environment
├── chat-link-stream/       # React frontend
│   ├── src/
│   │   ├── pages/          # React pages
│   │   ├── lib/            # API and services
│   │   └── components/     # UI components
│   ├── package.json        # Node.js dependencies
│   └── vite.config.ts      # Vite configuration
├── fix_and_start.sh        # Comprehensive startup script
├── test_backend.py         # Backend test script
└── README.md               # Project documentation
```

## 🌐 Application URLs

- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:8081
- **Backend Health Check**: http://localhost:8081/

## 🧪 Testing

### Test Backend
```bash
python3 test_backend.py
```

### Test WebSocket Connection
```bash
node test_connection.js
```

### Test User Matching
```bash
node test_matching.js
```

## 🔍 Manual Setup (Alternative)

If you prefer to set up manually:

### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

### Frontend Setup
```bash
cd chat-link-stream
npm install
npm run dev
```

## 🐛 Troubleshooting

### Backend Not Starting
1. Check Python version: `python3 --version`
2. Recreate virtual environment: `rm -rf venv && python3 -m venv venv`
3. Install dependencies: `pip install -r requirements.txt`
4. Check for port conflicts: `lsof -i :8081`

### Frontend Not Starting
1. Check Node.js version: `node --version`
2. Clear npm cache: `npm cache clean --force`
3. Reinstall dependencies: `rm -rf node_modules && npm install`
4. Check for port conflicts: `lsof -i :8080`

### WebSocket Connection Issues
1. Verify backend is running: `curl http://localhost:8081/`
2. Check browser console for errors
3. Ensure no firewall blocking port 8081
4. Try refreshing the page

### Video/Audio Issues
1. Allow camera/microphone permissions
2. Check browser settings
3. Try different browser
4. Ensure HTTPS in production

## 📝 Features

### ✅ Working Features
- Real-time text chat
- Live video streaming
- User matching system
- WebSocket communication
- Session management
- Error handling
- Responsive UI

### 🔄 Real-time Communication
- WebSocket for instant messaging
- WebRTC for peer-to-peer video
- Automatic user matching
- Session cleanup

## 🚀 Deployment

### Docker (Recommended)
```bash
docker-compose up -d
```

### Manual Deployment
1. Build frontend: `npm run build`
2. Set up production backend
3. Configure reverse proxy (Nginx)
4. Set environment variables

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section
2. Run the test scripts
3. Check browser console for errors
4. Verify all services are running

## 🎉 Success!

Once everything is running:
1. Open http://localhost:8080
2. Click "Start Video Chat" or "Start Text Chat"
3. Allow camera/microphone permissions
4. Wait for a partner to connect
5. Start chatting!

---

**🎯 Your Omegle-like video chat application is now fully functional!**
