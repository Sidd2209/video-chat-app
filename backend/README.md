# Video Chat Backend

A Flask-based backend for real-time video and text chat functionality, similar to Omegle.

## Features

- **Real-time Video Chat**: WebRTC-based peer-to-peer video streaming
- **Text Chat**: Real-time text messaging with Socket.IO
- **User Matching**: Automatic pairing of users for chat sessions
- **Session Management**: Robust session handling with cleanup
- **WebSocket Support**: Real-time bidirectional communication
- **CORS Support**: Cross-origin resource sharing enabled
- **Scalable Architecture**: Ready for production deployment

## Tech Stack

- **Flask**: Web framework
- **Flask-SocketIO**: WebSocket support for real-time communication
- **WebRTC**: Peer-to-peer video streaming
- **Eventlet**: Async networking library
- **Python 3.8+**: Modern Python features

## Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone <your-repo-url>
   cd backend
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional):
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Configuration

Create a `.env` file in the backend directory:

```env
SECRET_KEY=your-super-secret-key-here
FLASK_DEBUG=True
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=5000
REDIS_URL=redis://localhost:6379  # Optional, for production
```

## Running the Backend

### Development Mode
```bash
python run.py
```

### Production Mode
```bash
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

The server will start on `http://localhost:5000`

## API Endpoints

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

## Architecture

### Components

1. **Session Manager**: Handles user matching and session creation
2. **Message Handler**: Processes and routes chat messages
3. **WebRTC Signaling**: Manages peer-to-peer video connections
4. **Cleanup Service**: Removes inactive sessions

### Data Flow

1. User requests to start chat
2. Backend matches with waiting user or adds to waiting list
3. When matched, both users receive session details
4. WebRTC signaling establishes peer-to-peer connection
5. Messages are relayed through WebSocket
6. Session cleanup on disconnect

## Development

### Project Structure
```
backend/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── run.py              # Startup script
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── .env               # Environment variables (create this)
```

### Adding New Features

1. **New API Endpoints**: Add routes in `app.py`
2. **WebSocket Events**: Add handlers in the Socket.IO section
3. **Configuration**: Update `config.py` and `.env`

## Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

### Using Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "run.py"]
```

### Environment Variables for Production
```env
SECRET_KEY=your-production-secret-key
FLASK_DEBUG=False
LOG_LEVEL=WARNING
REDIS_URL=redis://your-redis-server:6379
```

## Monitoring and Logging

The application includes comprehensive logging:

- **Connection events**: User connections/disconnections
- **Session events**: Chat session creation and cleanup
- **Error handling**: Detailed error logs with stack traces
- **Performance metrics**: Session duration and message counts

## Security Considerations

- **CORS**: Configured for development, restrict in production
- **Session Management**: Secure session handling
- **Input Validation**: All inputs are validated
- **Rate Limiting**: Consider adding rate limiting for production
- **HTTPS**: Use HTTPS in production

## Troubleshooting

### Common Issues

1. **Port already in use**: Change port in `.env` or kill existing process
2. **CORS errors**: Check CORS configuration in `config.py`
3. **WebSocket connection failed**: Ensure Socket.IO client is configured correctly
4. **Video not working**: Check WebRTC support and camera permissions

### Debug Mode

Enable debug mode for detailed error messages:
```env
FLASK_DEBUG=True
LOG_LEVEL=DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.
