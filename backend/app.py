# CRITICAL: Eventlet monkey patch must be the very first import
import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_cors import CORS
import os
import uuid
import json
import time
from datetime import datetime
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['CORS_HEADERS'] = 'Content-Type'

# Initialize SocketIO with CORS
socketio = SocketIO(
    app, 
    cors_allowed_origins=["http://localhost:8080", "http://127.0.0.1:8080", "*"], 
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e8,
    allow_upgrades=True,
    transports=['websocket', 'polling'],
    always_connect=True,
    cookie=None
)
CORS(app, origins=["http://localhost:8080", "http://127.0.0.1:8080", "*"])

# Global state management
class UserManager:
    def __init__(self):
        # Room management for Omegle-like functionality
        self.active_users = set()  # All users who are online
        self.connected_users = set()  # Users currently in chat sessions
        self.waiting_rooms = {
            'video': [],  # Users waiting for video chat
            'text': []    # Users waiting for text chat
        }
        self.active_sessions = {}  # session_id -> ChatSession
        self.user_sessions = {}  # user_id -> session_id
        self.socket_user_map = {}  # socket_id -> user_id
        self.user_rooms = {}  # user_id -> room_id
        self.lock = eventlet.Lock()
    
    def add_active_user(self, user_id):
        """Add user to active users (online)"""
        with self.lock:
            self.active_users.add(user_id)
            logger.info(f"User {user_id} added to active users")
    
    def remove_active_user(self, user_id):
        """Remove user from active users"""
        with self.lock:
            self.active_users.discard(user_id)
            logger.info(f"User {user_id} removed from active users")
    
    def add_waiting_user(self, user_id, chat_type):
        """Add user to waiting room"""
        with self.lock:
            if user_id not in self.waiting_rooms[chat_type]:
                self.waiting_rooms[chat_type].append(user_id)
                logger.info(f"User {user_id} added to {chat_type} waiting room")
                return True
            return False
    
    def get_waiting_partner(self, chat_type):
        """Get next waiting user for matching"""
        with self.lock:
            if self.waiting_rooms[chat_type]:
                return self.waiting_rooms[chat_type].pop(0)
            return None
    
    def add_connected_user(self, user_id):
        """Add user to connected users (in chat session)"""
        with self.lock:
            self.connected_users.add(user_id)
            logger.info(f"User {user_id} added to connected users")
    
    def remove_connected_user(self, user_id):
        """Remove user from connected users"""
        with self.lock:
            self.connected_users.discard(user_id)
            # Remove from waiting rooms
            for chat_type in ['video', 'text']:
                if user_id in self.waiting_rooms[chat_type]:
                    self.waiting_rooms[chat_type].remove(user_id)
                    logger.info(f"Removed {user_id} from {chat_type} waiting room")
            logger.info(f"User {user_id} removed from connected users")
    
    def create_session(self, user1_id, user2_id, chat_type):
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        chat_session = ChatSession(session_id, user1_id, user2_id, chat_type)
        
        with self.lock:
            self.active_sessions[session_id] = chat_session
            self.user_sessions[user1_id] = session_id
            self.user_sessions[user2_id] = session_id
            
            # Add both users to connected users
            self.add_connected_user(user1_id)
            self.add_connected_user(user2_id)
        
        logger.info(f"Created session {session_id} between {user1_id} and {user2_id}")
        return chat_session
    
    def get_user_session(self, user_id):
        """Get session for a user"""
        return self.user_sessions.get(user_id)
    
    def get_session(self, session_id):
        """Get session by ID"""
        return self.active_sessions.get(session_id)
    
    def remove_session(self, session_id):
        """Remove a session and clean up"""
        with self.lock:
            session = self.active_sessions.pop(session_id, None)
            if session:
                self.user_sessions.pop(session.user1_id, None)
                self.user_sessions.pop(session.user2_id, None)
                logger.info(f"Removed session {session_id}")
            return session
    

    
    def get_waiting_count(self, chat_type):
        """Get number of waiting users"""
        return len(self.waiting_rooms[chat_type])
    
    def get_active_sessions_count(self):
        """Get number of active sessions"""
        return len(self.active_sessions)

# Initialize user manager
user_manager = UserManager()

class ChatSession:
    def __init__(self, session_id, user1_id, user2_id, chat_type):
        self.session_id = session_id
        self.user1_id = user1_id
        self.user2_id = user2_id
        self.chat_type = chat_type
        self.messages = []
        self.created_at = datetime.now()
        self.is_active = True
        self.last_activity = datetime.now()
        
    def add_message(self, user_id, message):
        """Add a message to the session"""
        msg = {
            'id': str(uuid.uuid4()),
            'from': 'you' if user_id == self.user1_id else 'stranger',
            'text': message,
            'timestamp': datetime.now().isoformat()
        }
        self.messages.append(msg)
        self.last_activity = datetime.now()
        return msg
    
    def get_messages(self, since_timestamp=None):
        """Get messages since a timestamp"""
        if since_timestamp:
            return [msg for msg in self.messages if msg['timestamp'] > since_timestamp]
        return self.messages
    
    def get_partner_id(self, user_id):
        """Get partner's user ID"""
        return self.user2_id if user_id == self.user1_id else self.user1_id
    
    def is_user_in_session(self, user_id):
        """Check if user is part of this session"""
        return user_id in [self.user1_id, self.user2_id]

def cleanup_inactive_sessions():
    """Clean up inactive sessions periodically"""
    current_time = datetime.now()
    inactive_sessions = []
    
    for session_id, session in user_manager.active_sessions.items():
        # Remove sessions inactive for more than 30 minutes
        if (current_time - session.last_activity).total_seconds() > 1800:
            inactive_sessions.append(session_id)
    
    for session_id in inactive_sessions:
        session = user_manager.remove_session(session_id)
        if session:
            # Notify both users that session ended
            socketio.emit('session_ended', {
                'session_id': session_id,
                'reason': 'inactivity'
            }, room=session.user1_id)
            socketio.emit('session_ended', {
                'session_id': session_id,
                'reason': 'inactivity'
            }, room=session.user2_id)
            logger.info(f"Cleaned up inactive session: {session_id}")

# Start cleanup thread
def start_cleanup_thread():
    while True:
        time.sleep(300)  # Run every 5 minutes
        cleanup_inactive_sessions()

# Use eventlet greenthread instead of threading
eventlet.spawn(start_cleanup_thread)

@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'message': 'Video Chat Backend is running',
        'rooms': {
            'active_users': len(user_manager.active_users),
            'connected_users': len(user_manager.connected_users),
            'waiting_video': len(user_manager.waiting_rooms['video']),
            'waiting_text': len(user_manager.waiting_rooms['text'])
        },
        'active_sessions': user_manager.get_active_sessions_count(),
        'debug_info': {
            'active_users': list(user_manager.active_users),
            'connected_users': list(user_manager.connected_users),
            'waiting_rooms': user_manager.waiting_rooms,
            'user_sessions': user_manager.user_sessions,
            'active_session_ids': list(user_manager.active_sessions.keys())
        }
    })



@app.route('/start', methods=['POST'])
def start_text_chat():
    """Start a text chat session"""
    try:
        # Get user_id from request headers or query params
        user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        # Verify user is active (connected via WebSocket)
        if user_id not in user_manager.active_users:
            return jsonify({'error': 'User not connected via WebSocket'}), 400
        
        # Check if there's a waiting user
        partner_id = user_manager.get_waiting_partner('text')
        
        if partner_id:
            # Match with waiting user
            chat_session = user_manager.create_session(user_id, partner_id, 'text')
            
            # Notify both users
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'text',
                'partner_id': partner_id
            }, room=user_id)
            
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'text',
                'partner_id': user_id
            }, room=partner_id)
            
            logger.info(f"Text chat matched: {user_id} with {partner_id}")
            
            return jsonify({
                'session_id': chat_session.session_id,
                'status': 'matched',
                'partner_id': partner_id
            })
        else:
            # Add to waiting list
            user_manager.add_waiting_user(user_id, 'text')
            logger.info(f"User {user_id} waiting for text chat")
            
            return jsonify({
                'session_id': None,
                'status': 'waiting'
            })
        
    except Exception as e:
        logger.error(f"Error starting text chat: {str(e)}")
        return jsonify({'error': 'Failed to start chat'}), 500

@app.route('/start_video', methods=['POST'])
def start_video_chat():
    """Start a video chat session"""
    try:
        # Get user_id from request headers or query params
        user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
        logger.info(f"Received video chat request - Headers: {dict(request.headers)}, Args: {dict(request.args)}, user_id: {user_id}")
        
        if not user_id:
            logger.error("No user_id provided in request")
            return jsonify({'error': 'User ID required'}), 400
        
        # Verify user is active (connected via WebSocket)
        logger.info(f"Checking if user {user_id} is in active_users: {user_id in user_manager.active_users}")
        logger.info(f"Active users: {list(user_manager.active_users)}")
        
        if user_id not in user_manager.active_users:
            logger.error(f"User {user_id} not found in active_users")
            return jsonify({'error': 'User not connected via WebSocket'}), 400
        
        # Check if there's a waiting user
        partner_id = user_manager.get_waiting_partner('video')
        logger.info(f"Video chat request from {user_id}, waiting users: {user_manager.waiting_rooms['video']}, partner_id: {partner_id}")
        
        if partner_id:
            # Match with waiting user
            logger.info(f"Creating session between {user_id} and {partner_id}")
            chat_session = user_manager.create_session(user_id, partner_id, 'video')
            
            # Notify both users
            logger.info(f"Emitting matched event to {user_id}")
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'video',
                'partner_id': partner_id,
                'is_initiator': False  # The user who just joined is not the initiator
            }, room=user_id)
            
            logger.info(f"Emitting matched event to {partner_id}")
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'video',
                'partner_id': user_id,
                'is_initiator': True  # The user who was waiting is the initiator
            }, room=partner_id)
            
            logger.info(f"Video chat matched: {user_id} with {partner_id}, session: {chat_session.session_id}")
            
            return jsonify({
                'session_id': chat_session.session_id,
                'status': 'matched',
                'partner_id': partner_id
            })
        else:
            # Add to waiting list
            user_manager.add_waiting_user(user_id, 'video')
            logger.info(f"User {user_id} waiting for video chat. Total waiting: {user_manager.get_waiting_count('video')}")
            
            return jsonify({
                'session_id': None,
                'status': 'waiting'
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
        user_id = data.get('user_id')
        
        if not session_id or not message or not user_id:
            return jsonify({'error': 'Missing session_id, message, or user_id'}), 400
        
        chat_session = user_manager.get_session(session_id)
        if not chat_session or not chat_session.is_user_in_session(user_id):
            return jsonify({'error': 'Session not found or user not in session'}), 404
        
        # Add message to session
        msg = chat_session.add_message(user_id, message)
        
        # Get partner ID
        partner_id = chat_session.get_partner_id(user_id)
        
        # Emit message to partner
        socketio.emit('new_message', {
            'session_id': session_id,
            'message': msg
        }, room=partner_id)
        
        return jsonify({'ok': True, 'message_id': msg['id']})
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({'error': 'Failed to send message'}), 500

@app.route('/receive', methods=['POST'])
def receive_messages():
    """Receive messages from a chat session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        
        if not session_id or not user_id:
            return jsonify({'error': 'Missing session_id or user_id'}), 400
        
        chat_session = user_manager.get_session(session_id)
        if not chat_session or not chat_session.is_user_in_session(user_id):
            return jsonify({'error': 'Session not found or user not in session'}), 404
        
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
        user_id = data.get('user_id')
        
        if not session_id or not user_id:
            return jsonify({'error': 'Missing session_id or user_id'}), 400
        
        chat_session = user_manager.get_session(session_id)
        if not chat_session or not chat_session.is_user_in_session(user_id):
            return jsonify({'error': 'Session not found or user not in session'}), 404
        
        # Mark session as inactive
        chat_session.is_active = False
        
        # Get partner ID
        partner_id = chat_session.get_partner_id(user_id)
        
        # Notify partner
        socketio.emit('partner_disconnected', {
            'session_id': session_id,
            'reason': 'partner_left'
        }, room=partner_id)
        
        # Remove session
        user_manager.remove_session(session_id)
        
        logger.info(f"User {user_id} disconnected from session {session_id}")
        
        return jsonify({'ok': True})
        
    except Exception as e:
        logger.error(f"Error disconnecting: {str(e)}")
        return jsonify({'error': 'Failed to disconnect'}), 500

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    try:
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id
        
        # Join user's personal room
        join_room(user_id)
        
        # Add to active users (online)
        user_manager.add_active_user(user_id)
        
        # Map socket to user
        user_manager.socket_user_map[request.sid] = user_id
        
        # Emit the user_id to the client immediately
        logger.info(f"Emitting user_id {user_id} to client {request.sid}")
        try:
            emit('user_id', {'user_id': user_id})
            logger.info(f"Successfully emitted user_id to client")
        except Exception as e:
            logger.error(f"Error emitting user_id: {str(e)}")
        
        logger.info(f"Client connected: {user_id} (socket: {request.sid})")
    except Exception as e:
        logger.error(f"Error in handle_connect: {str(e)}")
        raise

@socketio.on('request_user_id')
def handle_request_user_id():
    """Handle user_id request from client"""
    user_id = user_manager.socket_user_map.get(request.sid)
    if user_id:
        logger.info(f"Re-sending user_id {user_id} to client {request.sid}")
        emit('user_id', {'user_id': user_id})
    else:
        logger.warning(f"Client {request.sid} requested user_id but not found in mapping")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    try:
        user_id = user_manager.socket_user_map.get(request.sid)
        if user_id:
            logger.info(f"Client disconnecting: {user_id} (socket: {request.sid})")
            
            # Remove from active users
            user_manager.remove_active_user(user_id)
            
            # Remove from connected users if in session
            user_manager.remove_connected_user(user_id)
            
            # Remove socket mapping
            user_manager.socket_user_map.pop(request.sid, None)
            
            # Handle active session disconnection
            session_id = user_manager.get_user_session(user_id)
            if session_id:
                chat_session = user_manager.get_session(session_id)
                if chat_session:
                    partner_id = chat_session.get_partner_id(user_id)
                    try:
                        socketio.emit('partner_disconnected', {
                            'session_id': session_id,
                            'reason': 'partner_disconnected'
                        }, room=partner_id)
                    except Exception as e:
                        logger.error(f"Error emitting partner_disconnected: {str(e)}")
                    
                    # Remove session
                    user_manager.remove_session(session_id)
            
            logger.info(f"Client disconnected: {user_id} (socket: {request.sid})")
        else:
            logger.warning(f"Disconnect event for unknown socket: {request.sid}")
    except Exception as e:
        logger.error(f"Error in handle_disconnect: {str(e)}")

@socketio.on('join_session')
def handle_join_session(data):
    """Handle joining a chat session"""
    session_id = data.get('session_id')
    user_id = user_manager.socket_user_map.get(request.sid)
    
    if session_id and user_id:
        join_room(session_id)
        user_manager.user_rooms[user_id] = session_id
        logger.info(f"User {user_id} joined session {session_id}")

@socketio.on('leave_session')
def handle_leave_session(data):
    """Handle leaving a chat session"""
    session_id = data.get('session_id')
    user_id = user_manager.socket_user_map.get(request.sid)
    
    if session_id and user_id:
        leave_room(session_id)
        user_manager.user_rooms.pop(user_id, None)
        logger.info(f"User {user_id} left session {session_id}")

@socketio.on('webrtc_signal')
def handle_webrtc_signal(data):
    """Handle WebRTC signaling"""
    session_id = data.get('session_id')
    signal = data.get('signal')
    user_id = user_manager.socket_user_map.get(request.sid)
    
    if session_id and signal and user_id:
        chat_session = user_manager.get_session(session_id)
        if chat_session and chat_session.is_user_in_session(user_id):
            # Forward signal to partner
            partner_id = chat_session.get_partner_id(user_id)
            socketio.emit('webrtc_signal', {
                'session_id': session_id,
                'signal': signal,
                'from': user_id
            }, room=partner_id)

@socketio.on('user_typing')
def handle_user_typing(data):
    """Handle user typing indicator"""
    session_id = data.get('session_id')
    user_id = user_manager.socket_user_map.get(request.sid)
    is_typing = data.get('is_typing', False)
    
    if session_id and user_id:
        chat_session = user_manager.get_session(session_id)
        if chat_session and chat_session.is_user_in_session(user_id):
            partner_id = chat_session.get_partner_id(user_id)
            socketio.emit('partner_typing', {
                'session_id': session_id,
                'is_typing': is_typing
            }, room=partner_id)

if __name__ == '__main__':
    logger.info("Starting Video Chat Backend...")
    socketio.run(app, host='0.0.0.0', port=8081, debug=True)
