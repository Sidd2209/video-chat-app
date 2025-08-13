# Video Chat Application - Complete Setup Guide

A real-time video and text chat application similar to Omegle, built with React frontend and Flask backend.

## 🚀 Quick Start (Recommended)

### Prerequisites
- **Python 3.8+** installed
- **Node.js 16+** installed
- **npm** or **yarn** package manager

### Automated Setup
1. **Clone and navigate to the project**:
   ```bash
   cd Online-website
   ```

2. **Make the startup script executable and run it**:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

3. **Access the application**:
   - Frontend: http://localhost:8080
   - Backend API: http://localhost:8081

### Manual Setup (Alternative)

#### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

#### Frontend Setup
```bash
cd chat-link-stream
npm install
npm run dev
```

## 🧪 Testing the Application

Run the test script to verify everything is working:
```bash
python3 test_app.py
```

## 🎯 How to Use

### Video Chat
1. Open http://localhost:8080 in your browser
2. Click "Video Chat"
3. Allow camera and microphone permissions when prompted
4. Click "Start" to begin searching for a partner
5. Once matched, you'll see your partner's video
6. Use the chat panel to send text messages
7. Use control buttons to mute/unmute or stop/start video

### Text Chat
1. Open http://localhost:8080 in your browser
2. Click "Text Chat"
3. Click "Start Chat" to begin searching for a partner
4. Once matched, you can start sending messages
5. Click "Disconnect" to end the chat

### Testing with Yourself
1. Open http://localhost:8080 in one browser tab
2. Open http://localhost:8080 in another browser tab (or incognito window)
3. Start a chat session in both tabs
4. You should be matched with yourself for testing

## 🛠️ Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **Socket.IO Client** for real-time communication
- **WebRTC** for peer-to-peer video streaming
- **Shadcn/ui** for UI components

### Backend
- **Flask** web framework
- **Flask-SocketIO** for WebSocket support
- **Eventlet** for async networking
- **Python 3.8+** for modern Python features

## 📁 Project Structure

```
Online-website/
├── backend/                 # Flask backend
│   ├── app.py              # Main Flask application
│   ├── config.py           # Configuration settings
│   ├── run.py              # Startup script
│   ├── requirements.txt    # Python dependencies
│   └── venv/              # Python virtual environment
├── chat-link-stream/        # React frontend
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── pages/         # Page components
│   │   ├── lib/           # Services and utilities
│   │   └── ...
│   ├── package.json       # Node.js dependencies
│   └── ...
├── start.sh               # Startup script for both servers
├── test_app.py           # Test script to verify functionality
└── README_IMPROVED.md    # This file
```

## 🔧 Configuration

### Environment Variables (Optional)

Create a `.env` file in the backend directory for custom configuration:

```env
SECRET_KEY=your-super-secret-key-here
FLASK_DEBUG=True
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8081
```

### Frontend Configuration

The frontend automatically connects to `http://localhost:8081` for the backend API. To change this, set environment variables:

```env
VITE_API_URL=http://your-backend-url:8081
VITE_SOCKET_URL=http://your-backend-url:8081
```

## 🔌 API Endpoints

### REST API
- `GET /` - Health check
- `POST /start` - Start text chat session
- `POST /start_video` - Start video chat session
- `POST /send` - Send message
- `POST /receive` - Receive messages
- `POST /disconnect` - Disconnect from session

### WebSocket Events
- `connect` - Client connects
- `disconnect` - Client disconnects
- `user_id` - User ID assigned to client
- `matched` - User matched with partner
- `new_message` - New message received
- `partner_disconnected` - Partner left the chat
- `webrtc_signal` - WebRTC signaling data
- `join_session` - Join chat session
- `leave_session` - Leave chat session

## 🐛 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using the ports
lsof -i :8080
lsof -i :8081

# Kill processes if needed
kill -9 <PID>
```

#### 2. Python/Node.js Not Found
```bash
# Check Python version
python3 --version

# Check Node.js version
node --version

# Install if missing
# Python: https://www.python.org/downloads/
# Node.js: https://nodejs.org/
```

#### 3. Permission Denied
```bash
# Make startup script executable
chmod +x start.sh
```

#### 4. Dependencies Not Installed
```bash
# Backend dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend dependencies
cd chat-link-stream
npm install
```

#### 5. WebSocket Connection Failed
- Check if backend is running on port 8081
- Verify CORS settings in `backend/config.py`
- Check browser console for errors

#### 6. Camera/Microphone Not Working
- Ensure HTTPS in production (required for media access)
- Check browser permissions
- Try refreshing the page

### Debug Mode

Enable debug mode for detailed error messages:

```bash
# Backend debug
export FLASK_DEBUG=True
export LOG_LEVEL=DEBUG

# Frontend debug
# Check browser console (F12)
```

### Browser Compatibility

- **Chrome/Edge**: Full support ✅
- **Firefox**: Full support ✅
- **Safari**: Full support ✅
- **Mobile browsers**: Limited WebRTC support ⚠️

## 🚀 Deployment

### Production Backend
```bash
# Using Gunicorn
pip install gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8081 app:app

# Using Docker
docker build -t video-chat-backend .
docker run -p 8081:8081 video-chat-backend
```

### Production Frontend
```bash
# Build for production
npm run build

# Serve with a static server
npm install -g serve
serve -s dist -l 8080
```

## 🔒 Security Considerations

- **CORS**: Configured for development, restrict in production
- **Session Management**: Secure session handling
- **Input Validation**: All inputs are validated
- **Rate Limiting**: Consider adding rate limiting for production
- **HTTPS**: Use HTTPS in production for WebRTC
- **WebRTC**: Peer-to-peer connections are secure by default

## 📝 Development

### Adding New Features
1. Backend changes: Edit `backend/app.py`
2. Frontend changes: Edit files in `chat-link-stream/src/`
3. UI components: Use Shadcn/ui components in `chat-link-stream/src/components/ui/`

### Code Structure
- **Backend**: Flask app with Socket.IO for real-time communication
- **Frontend**: React app with TypeScript and Tailwind CSS
- **Communication**: REST API + WebSocket for real-time features
- **Video**: WebRTC for peer-to-peer video streaming

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **Omegle** for inspiration
- **WebRTC** for peer-to-peer video technology
- **Socket.IO** for real-time communication
- **React** and **Flask** communities for excellent documentation

---

## 🎉 Success!

If you've followed this guide and run `python3 test_app.py` successfully, your Video Chat Application is ready to use! 

**Next Steps:**
1. Open http://localhost:8080 in your browser
2. Test both Video Chat and Text Chat features
3. Try connecting with yourself using multiple browser tabs
4. Enjoy your new chat application! 🚀
