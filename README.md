# Video Chat Application

A real-time video and text chat application similar to Omegle, built with React frontend and Flask backend.

## 🚀 Features

- **Real-time Video Chat**: WebRTC-based peer-to-peer video streaming
- **Text Chat**: Real-time text messaging with Socket.IO
- **User Matching**: Automatic pairing of users for chat sessions
- **Session Management**: Robust session handling with cleanup
- **WebSocket Support**: Real-time bidirectional communication
- **Modern UI**: Beautiful, responsive interface with Tailwind CSS
- **Cross-platform**: Works on desktop and mobile browsers

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
│   └── README.md          # Backend documentation
├── chat-link-stream/        # React frontend
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── pages/         # Page components
│   │   ├── lib/           # Services and utilities
│   │   └── ...
│   ├── package.json       # Node.js dependencies
│   └── ...
├── start.sh               # Startup script for both servers
└── README.md             # This file
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** installed
- **Node.js 16+** installed
- **npm** or **yarn** package manager

### Option 1: Automated Setup (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd Online-website
   ```

2. **Run the startup script**:
   ```bash
   ./start.sh
   ```

   This script will:
   - Install backend dependencies
   - Create Python virtual environment
   - Install frontend dependencies
   - Start both servers automatically

3. **Access the application**:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:5000

### Option 2: Manual Setup

#### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the backend**:
   ```bash
   python run.py
   ```

#### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd chat-link-stream
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the frontend**:
   ```bash
   npm run dev
   ```

## 🎯 How to Use

### Video Chat
1. Click "Video Chat" on the home page
2. Allow camera and microphone permissions
3. Click "Start" to begin searching for a partner
4. Once matched, you'll see your partner's video
5. Use the chat panel to send text messages
6. Use the control buttons to mute/unmute or stop/start video

### Text Chat
1. Click "Text Chat" on the home page
2. Click "Start Chat" to begin searching for a partner
3. Once matched, you can start sending messages
4. Click "Disconnect" to end the chat

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
SECRET_KEY=your-super-secret-key-here
FLASK_DEBUG=True
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=5000
REDIS_URL=redis://localhost:6379  # Optional, for production
```

### Frontend Configuration

The frontend automatically connects to `http://localhost:5000` for the backend API. To change this, set the `VITE_API_URL` environment variable:

```env
VITE_API_URL=http://your-backend-url:5000
VITE_SOCKET_URL=http://your-backend-url:5000
```

## 🏗️ Architecture

### Backend Architecture

1. **Session Manager**: Handles user matching and session creation
2. **Message Handler**: Processes and routes chat messages
3. **WebRTC Signaling**: Manages peer-to-peer video connections
4. **Cleanup Service**: Removes inactive sessions

### Frontend Architecture

1. **Socket Service**: Manages WebSocket connections
2. **WebRTC Service**: Handles peer-to-peer video streaming
3. **Chat API**: REST API communication
4. **UI Components**: React components for user interface

### Data Flow

1. User requests to start chat
2. Backend matches with waiting user or adds to waiting list
3. When matched, both users receive session details via WebSocket
4. WebRTC signaling establishes peer-to-peer connection
5. Messages are relayed through WebSocket
6. Session cleanup on disconnect

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
- `matched` - User matched with partner
- `new_message` - New message received
- `partner_disconnected` - Partner left the chat
- `webrtc_signal` - WebRTC signaling data
- `join_session` - Join chat session
- `leave_session` - Leave chat session

## 🚀 Deployment

### Production Backend

```bash
# Using Gunicorn
pip install gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app

# Using Docker
docker build -t video-chat-backend .
docker run -p 5000:5000 video-chat-backend
```

### Production Frontend

```bash
# Build for production
npm run build

# Serve with a static server
npm install -g serve
serve -s dist -l 3000
```

## 🔒 Security Considerations

- **CORS**: Configured for development, restrict in production
- **Session Management**: Secure session handling
- **Input Validation**: All inputs are validated
- **Rate Limiting**: Consider adding rate limiting for production
- **HTTPS**: Use HTTPS in production
- **WebRTC**: Peer-to-peer connections are secure by default

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use**: Change port in `.env` or kill existing process
2. **CORS errors**: Check CORS configuration in `config.py`
3. **WebSocket connection failed**: Ensure Socket.IO client is configured correctly
4. **Video not working**: Check WebRTC support and camera permissions
5. **Backend not starting**: Check Python version and dependencies

### Debug Mode

Enable debug mode for detailed error messages:

```env
FLASK_DEBUG=True
LOG_LEVEL=DEBUG
```

### Browser Compatibility

- **Chrome/Edge**: Full support
- **Firefox**: Full support
- **Safari**: Full support
- **Mobile browsers**: Limited WebRTC support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **Omegle** for inspiration
- **WebRTC** for peer-to-peer video technology
- **Socket.IO** for real-time communication
- **React** and **Flask** communities for excellent documentation
