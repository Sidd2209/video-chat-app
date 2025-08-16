# Video Chat Application

A modern, real-time video chat application built with React, TypeScript, and Flask. Connect with strangers instantly through your browser with video and audio capabilities.

## 🚀 Features

- **Real-time Video Chat**: Connect with random strangers instantly
- **WebRTC Technology**: Peer-to-peer video and audio streaming
- **Modern UI**: Built with React, TypeScript, and Tailwind CSS
- **Responsive Design**: Works on desktop and mobile devices
- **Auto-matching**: Automatic pairing of users for video chat
- **Persistent Sessions**: User IDs are maintained across reconnections

## 🏗️ Project Structure

```
Online-website/
├── backend/                 # Flask backend server
│   ├── app.py              # Main Flask application
│   ├── requirements.txt    # Python dependencies
│   └── venv/              # Python virtual environment
├── chat-link-stream/       # React frontend
│   ├── src/
│   │   ├── components/ui/  # UI components (Button, Toast, etc.)
│   │   ├── hooks/         # Custom React hooks
│   │   ├── lib/           # Services (WebSocket, WebRTC, API)
│   │   ├── pages/         # Page components
│   │   └── main.tsx       # React entry point
│   ├── package.json       # Node.js dependencies
│   └── vite.config.ts     # Vite configuration
└── README.md              # This file
```

## 🛠️ Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **Socket.IO Client** for real-time communication
- **WebRTC** for peer-to-peer video/audio

### Backend
- **Flask** web framework
- **Flask-SocketIO** for WebSocket support
- **Eventlet** for async operations
- **Python 3.12+**

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Python 3.12+
- Modern browser with camera/microphone support

### 1. Start the Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

The backend will start on `http://localhost:8081`

### 2. Start the Frontend
```bash
cd chat-link-stream
npm install
npm run dev
```

The frontend will start on `http://localhost:8080`

### 3. Test the Application
1. Open `http://localhost:8080` in your browser
2. Click "Start Video Chat"
3. Allow camera and microphone permissions
4. Wait to be matched with another user

## 🧪 Testing

### Single User Test
1. Open the application in one browser window
2. Click "Start Video Chat"
3. You should see your camera feed and be placed in the waiting room

### Multi-User Test
1. Open the application in two different browser windows
2. Click "Start Video Chat" in both
3. Allow camera/microphone permissions in both
4. Users should be automatically matched and see each other's video

## 🔧 Development

### Key Files
- `backend/app.py` - Main Flask server with Socket.IO events
- `chat-link-stream/src/pages/VideoChat.tsx` - Main video chat component
- `chat-link-stream/src/lib/socketService.ts` - WebSocket connection management
- `chat-link-stream/src/lib/webrtcService.ts` - WebRTC peer connection handling

### Adding Features
1. Backend events are handled in `app.py`
2. Frontend components are in `src/pages/`
3. Services and utilities are in `src/lib/`
4. UI components are in `src/components/ui/`

## 🐛 Troubleshooting

### Common Issues
1. **"Timeout waiting for user_id"** - Check if backend is running on port 8081
2. **Camera not working** - Ensure HTTPS or localhost, check browser permissions
3. **Users not matching** - Check backend logs for connection issues
4. **WebSocket errors** - Verify both frontend and backend are running

### Debug Mode
- Backend logs are verbose and show connection events
- Frontend console shows WebSocket and WebRTC events
- Check browser Network tab for WebSocket connections

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues and questions, please check the troubleshooting section above or create an issue in the repository.
