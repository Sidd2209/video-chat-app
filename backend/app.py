from flask import Flask, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_cors import CORS
import uuid
import json
import time
from datetime import datetime
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['CORS_HEADERS'] = 'Content-Type'

# Initialize SocketIO with CORS
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
CORS(app)

# In-memory storage (in production, use Redis)
waiting_users = {
    'video': [],
    'text': []
}
active_sessions = {}
user_sessions = {}

class ChatSession:
    def __init__(self, session_id, user1_id, user2_id, chat_type):
        self.session_id = session_id
        self.user1_id = user1_id
        self.user2_id = user2_id
        self.chat_type = chat_type
        self.messages = []
        self.created_at = datetime.now()
        self.is_active = True
        
    def add_message(self, user_id, message):
        msg = {
            'id': str(uuid.uuid4()),
            'from': 'you' if user_id == self.user1_id else 'stranger',
            'text': message,
            'timestamp': datetime.now().isoformat()
        }
        self.messages.append(msg)
        return msg
    
    def get_messages(self, since_timestamp=None):
        if since_timestamp:
            return [msg for msg in self.messages if msg['timestamp'] > since_timestamp]
        return self.messages

def cleanup_inactive_sessions():
    """Clean up inactive sessions periodically"""
    current_time = datetime.now()
    inactive_sessions = []
    
    for session_id, session in active_sessions.items():
        # Remove sessions older than 1 hour
        if (current_time - session.created_at).total_seconds() > 3600:
            inactive_sessions.append(session_id)
    
    for session_id in inactive_sessions:
        session = active_sessions.pop(session_id, None)
        if session:
            # Notify users that session ended
            socketio.emit('session_ended', {'session_id': session_id}, room=session.user1_id)
            socketio.emit('session_ended', {'session_id': session_id}, room=session.user2_id)
            logger.info(f"Cleaned up inactive session: {session_id}")

# Start cleanup thread
def start_cleanup_thread():
    while True:
        time.sleep(300)  # Run every 5 minutes
        cleanup_inactive_sessions()

cleanup_thread = threading.Thread(target=start_cleanup_thread, daemon=True)
cleanup_thread.start()

@app.route('/')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Video Chat Backend is running'})

@app.route('/start', methods=['POST'])
def start_text_chat():
    """Start a text chat session"""
    try:
        user_id = str(uuid.uuid4())
        
        # Check if there's a waiting user
        if waiting_users['text']:
            # Match with waiting user
            partner_id = waiting_users['text'].pop(0)
            session_id = str(uuid.uuid4())
            
            # Create new session
            chat_session = ChatSession(session_id, user_id, partner_id, 'text')
            active_sessions[session_id] = chat_session
            user_sessions[user_id] = session_id
            user_sessions[partner_id] = session_id
            
            # Notify both users
            socketio.emit('matched', {
                'session_id': session_id,
                'chat_type': 'text'
            }, room=user_id)
            
            socketio.emit('matched', {
                'session_id': session_id,
                'chat_type': 'text'
            }, room=partner_id)
            
            logger.info(f"Text chat started: {session_id} between {user_id} and {partner_id}")
            
        else:
            # Add to waiting list
            waiting_users['text'].append(user_id)
            logger.info(f"User {user_id} waiting for text chat")
        
        return jsonify({
            'session_id': user_id,
            'status': 'waiting' if user_id in waiting_users['text'] else 'matched'
        })
        
    except Exception as e:
        logger.error(f"Error starting text chat: {str(e)}")
        return jsonify({'error': 'Failed to start chat'}), 500

@app.route('/start_video', methods=['POST'])
def start_video_chat():
    """Start a video chat session"""
    try:
        user_id = str(uuid.uuid4())
        
        # Check if there's a waiting user
        if waiting_users['video']:
            # Match with waiting user
            partner_id = waiting_users['video'].pop(0)
            session_id = str(uuid.uuid4())
            
            # Create new session
            chat_session = ChatSession(session_id, user_id, partner_id, 'video')
            active_sessions[session_id] = chat_session
            user_sessions[user_id] = session_id
            user_sessions[partner_id] = session_id
            
            # Notify both users
            socketio.emit('matched', {
                'session_id': session_id,
                'chat_type': 'video'
            }, room=user_id)
            
            socketio.emit('matched', {
                'session_id': session_id,
                'chat_type': 'video'
            }, room=partner_id)
            
            logger.info(f"Video chat started: {session_id} between {user_id} and {partner_id}")
            
        else:
            # Add to waiting list
            waiting_users['video'].append(user_id)
            logger.info(f"User {user_id} waiting for video chat")
        
        return jsonify({
            'session_id': user_id,
            'status': 'waiting' if user_id in waiting_users['video'] else 'matched'
        })
        
    except Exception as e:
        logger.error(f"Error starting video chat: {str(e)}")
        return jsonify({'error': 'Failed to start video chat'}), 500

@app.route('/send', methods=['POST'])
def send_message():
    """Send a message in a chat session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        message = data.get('message')
        
        if not session_id or not message:
            return jsonify({'error': 'Missing session_id or message'}), 400
        
        chat_session = active_sessions.get(session_id)
        if not chat_session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Add message to session
        msg = chat_session.add_message(session_id, message)
        
        # Emit message to both users
        socketio.emit('new_message', {
            'session_id': session_id,
            'message': msg
        }, room=chat_session.user1_id)
        
        socketio.emit('new_message', {
            'session_id': session_id,
            'message': msg
        }, room=chat_session.user2_id)
        
        return jsonify({'ok': True})
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({'error': 'Failed to send message'}), 500

@app.route('/receive', methods=['POST'])
def receive_messages():
    """Receive messages from a chat session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Missing session_id'}), 400
        
        chat_session = active_sessions.get(session_id)
        if not chat_session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Get messages since last check
        since_timestamp = data.get('since_timestamp')
        messages = chat_session.get_messages(since_timestamp)
        
        return jsonify({
            'messages': messages,
            'disconnected': not chat_session.is_active
        })
        
    except Exception as e:
        logger.error(f"Error receiving messages: {str(e)}")
        return jsonify({'error': 'Failed to receive messages'}), 500

@app.route('/disconnect', methods=['POST'])
def disconnect_chat():
    """Disconnect from a chat session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Missing session_id'}), 400
        
        chat_session = active_sessions.get(session_id)
        if not chat_session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Mark session as inactive
        chat_session.is_active = False
        
        # Notify partner
        partner_id = chat_session.user2_id if session_id == chat_session.user1_id else chat_session.user1_id
        socketio.emit('partner_disconnected', {
            'session_id': session_id
        }, room=partner_id)
        
        # Clean up
        active_sessions.pop(session_id, None)
        user_sessions.pop(chat_session.user1_id, None)
        user_sessions.pop(chat_session.user2_id, None)
        
        logger.info(f"User {session_id} disconnected from session {session_id}")
        
        return jsonify({'ok': True})
        
    except Exception as e:
        logger.error(f"Error disconnecting: {str(e)}")
        return jsonify({'error': 'Failed to disconnect'}), 500

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    join_room(user_id)
    logger.info(f"Client connected: {user_id}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    user_id = session.get('user_id')
    if user_id:
        # Remove from waiting lists
        if user_id in waiting_users['video']:
            waiting_users['video'].remove(user_id)
        if user_id in waiting_users['text']:
            waiting_users['text'].remove(user_id)
        
        # Handle active session disconnection
        session_id = user_sessions.get(user_id)
        if session_id:
            chat_session = active_sessions.get(session_id)
            if chat_session:
                partner_id = chat_session.user2_id if user_id == chat_session.user1_id else chat_session.user1_id
                socketio.emit('partner_disconnected', {
                    'session_id': session_id
                }, room=partner_id)
                
                # Clean up
                active_sessions.pop(session_id, None)
                user_sessions.pop(chat_session.user1_id, None)
                user_sessions.pop(chat_session.user2_id, None)
        
        logger.info(f"Client disconnected: {user_id}")

@socketio.on('join_session')
def handle_join_session(data):
    """Handle joining a chat session"""
    session_id = data.get('session_id')
    user_id = session.get('user_id')
    
    if session_id and user_id:
        join_room(session_id)
        logger.info(f"User {user_id} joined session {session_id}")

@socketio.on('leave_session')
def handle_leave_session(data):
    """Handle leaving a chat session"""
    session_id = data.get('session_id')
    user_id = session.get('user_id')
    
    if session_id and user_id:
        leave_room(session_id)
        logger.info(f"User {user_id} left session {session_id}")

@socketio.on('webrtc_signal')
def handle_webrtc_signal(data):
    """Handle WebRTC signaling"""
    session_id = data.get('session_id')
    signal = data.get('signal')
    user_id = session.get('user_id')
    
    if session_id and signal and user_id:
        chat_session = active_sessions.get(session_id)
        if chat_session:
            # Forward signal to partner
            partner_id = chat_session.user2_id if user_id == chat_session.user1_id else chat_session.user1_id
            socketio.emit('webrtc_signal', {
                'session_id': session_id,
                'signal': signal,
                'from': user_id
            }, room=partner_id)

if __name__ == '__main__':
    logger.info("Starting Video Chat Backend...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
