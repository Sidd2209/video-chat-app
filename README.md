# Video Chat Application

A real-time video and text chat application similar to Omegle, built with React frontend and Flask backend.

## 🚀 Features

- **Real-time Video Chat**: WebRTC-based peer-to-peer video streaming
- **Text Chat**: Real-time text messaging with Socket.IO
- **User Matching**: Automatic pairing of users for chat sessions
- **Modern UI**: Beautiful, responsive interface with Tailwind CSS

## 🛠️ Tech Stack

### Frontend
- React 18 with TypeScript
- Vite for development
- Tailwind CSS for styling
- Socket.IO Client for real-time communication
- WebRTC for peer-to-peer video streaming

### Backend
- Flask web framework
- Flask-SocketIO for WebSocket support
- Python 3.8+

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+

### Start the Application

1. **Clone and navigate to the project**:
   ```bash
   git clone <your-repo-url>
   cd Online-website
   ```

2. **Run the startup script**:
   ```bash
   ./start.sh
   ```

3. **Access the application**:
   - Frontend: http://localhost:8080
   - Backend: http://localhost:8081

## 📁 Project Structure

```
Online-website/
├── backend/                 # Flask backend
│   ├── app.py              # Main Flask application
│   ├── config.py           # Configuration settings
│   ├── run.py              # Startup script
│   └── requirements.txt    # Python dependencies
├── chat-link-stream/        # React frontend
│   ├── src/                # Source code
│   ├── package.json        # Node.js dependencies
│   └── ...
├── start.sh                # Startup script
└── README.md              # This file
```

## 🎯 How to Use

1. Open http://localhost:8080 in your browser
2. Click "Start Video Chat" or "Start Text Chat"
3. Allow camera/microphone permissions
4. Wait for a partner to join
5. Start chatting!

## 🐛 Troubleshooting

- **WebSocket connection issues**: Make sure both backend and frontend are running
- **Camera not working**: Check browser permissions
- **No partner found**: Wait a few seconds or refresh the page
