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
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['CORS_HEADERS'] = 'Content-Type'

# Initialize SocketIO with CORS
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
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
CORS(app, origins="*")

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
        self.lock = threading.Lock()
    
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
    
    def get_waiting_partner(self, chat_type, exclude_user_id=None):
        """Get next waiting user for matching"""
        with self.lock:
            if self.waiting_rooms[chat_type]:
                # Get the first user that's not the excluded user
                for i, user_id in enumerate(self.waiting_rooms[chat_type]):
                    if user_id != exclude_user_id:
                        return self.waiting_rooms[chat_type].pop(i)
                # If no other user found, return None
                return None
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
        eventlet.sleep(300)  # Run every 5 minutes
        cleanup_inactive_sessions()

# Use eventlet greenthread instead of threading
eventlet.spawn(start_cleanup_thread)

@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'message': 'Video Chat Backend is running - UPDATED',
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

@app.route('/force_match', methods=['POST'])
def force_match():
    """Force match two waiting users for testing"""
    try:
        # Get two users from waiting room
        waiting_users = user_manager.waiting_rooms['video']
        if len(waiting_users) >= 2:
            user1 = waiting_users.pop(0)
            user2 = waiting_users.pop(0)
            
            # Create session
            chat_session = user_manager.create_session(user1, user2, 'video')
            
            # Emit matched events
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'video',
                'partner_id': user2,
                'is_initiator': True
            }, room=user1)
            
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'video',
                'partner_id': user1,
                'is_initiator': False
            }, room=user2)
            
            return jsonify({
                'success': True,
                'session_id': chat_session.session_id,
                'user1': user1,
                'user2': user2
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Not enough users waiting. Need 2, have {len(waiting_users)}'
            })
    except Exception as e:
        logger.error(f"Error in force_match: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/test_emit', methods=['POST'])
def test_emit():
    """Test endpoint to verify emit functionality"""
    try:
        data = request.get_json()
        socket_id = data.get('socket_id')
        test_message = data.get('message', 'test')
        
        if socket_id:
            logger.info(f"Testing emit to socket {socket_id}")
            try:
                emit('test_event', {'message': test_message}, room=socket_id)
                logger.info(f"✅ Test emit successful to {socket_id}")
                return jsonify({'success': True, 'message': 'Test emit sent'})
            except Exception as e:
                logger.error(f"❌ Test emit failed: {str(e)}")
                return jsonify({'success': False, 'error': str(e)}), 500
        else:
            return jsonify({'success': False, 'error': 'No socket_id provided'}), 400
    except Exception as e:
        logger.error(f"Error in test_emit: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/auto_match_all', methods=['POST'])
def auto_match_all():
    """Automatically match all active users who are not in sessions"""
    try:
        # Get all active users who are not in sessions
        active_users = list(user_manager.active_users)
        sessioned_users = set(user_manager.user_sessions.keys())
        available_users = [user for user in active_users if user not in sessioned_users]
        
        logger.info(f"Auto matching: {len(available_users)} available users out of {len(active_users)} active users")
        
        matched_pairs = []
        
        # Match users in pairs
        while len(available_users) >= 2:
            user1 = available_users.pop(0)
            user2 = available_users.pop(0)
            
            # Create session
            chat_session = user_manager.create_session(user1, user2, 'video')
            
            # Emit matched events
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'video',
                'partner_id': user2,
                'is_initiator': True
            }, room=user1)
            
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'video',
                'partner_id': user1,
                'is_initiator': False
            }, room=user2)
            
            matched_pairs.append({
                'session_id': chat_session.session_id,
                'user1': user1,
                'user2': user2
            })
            
            logger.info(f"Auto matched: {user1} with {user2} in session {chat_session.session_id}")
        
        return jsonify({
            'success': True,
            'matched_pairs': matched_pairs,
            'remaining_users': available_users,
            'total_matched': len(matched_pairs) * 2
        })
        
    except Exception as e:
        logger.error(f"Error in auto_match_all: {str(e)}")
        return jsonify({'error': str(e)}), 500



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
            
            # Add a small delay to ensure both users are ready
            eventlet.sleep(0.5)
            
            # Notify both users
            logger.info(f"Emitting matched event to {user_id} with session {chat_session.session_id}")
            try:
                socketio.emit('matched', {
                    'session_id': chat_session.session_id,
                    'chat_type': 'video',
                    'partner_id': partner_id,
                    'is_initiator': False  # The user who just joined is not the initiator
                }, room=user_id)
                logger.info(f"✅ Successfully emitted matched event to {user_id}")
            except Exception as e:
                logger.error(f"❌ Failed to emit matched event to {user_id}: {str(e)}")
            
            logger.info(f"Emitting matched event to {partner_id} with session {chat_session.session_id}")
            try:
                socketio.emit('matched', {
                    'session_id': chat_session.session_id,
                    'chat_type': 'video',
                    'partner_id': user_id,
                    'is_initiator': True  # The user who was waiting is the initiator
                }, room=partner_id)
                logger.info(f"✅ Successfully emitted matched event to {partner_id}")
            except Exception as e:
                logger.error(f"❌ Failed to emit matched event to {partner_id}: {str(e)}")
            
            # Also broadcast to all users as a fallback
            logger.info("Broadcasting matched event to all users as fallback")
            try:
                socketio.emit('matched_broadcast', {
                    'session_id': chat_session.session_id,
                    'chat_type': 'video',
                    'user1_id': user_id,
                    'user2_id': partner_id,
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("✅ Successfully broadcasted matched event")
            except Exception as e:
                logger.error(f"❌ Failed to broadcast matched event: {str(e)}")
            
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
    logger.info(f"🎉 CONNECT EVENT TRIGGERED for socket {request.sid}")
    try:
        # Map early to prevent disconnect warnings
        user_id = str(uuid.uuid4())
        logger.info(f"Generated user_id: {user_id}")
        
        session['user_id'] = user_id
        logger.info(f"Set session user_id")
        
        user_manager.socket_user_map[request.sid] = user_id  # Map immediately
        logger.info(f"Mapped socket {request.sid} to user {user_id}")
        
        # Join user's personal room
        join_room(user_id)
        logger.info(f"Joined room: {user_id}")
        
        # Add to active users (online)
        user_manager.add_active_user(user_id)
        logger.info(f"Added to active users")
        
        logger.info(f"Client connected: {user_id} (socket: {request.sid})")
        
        # Emit the user_id to the client immediately (auto-send approach)
        logger.info(f"Auto-emitting user_id {user_id} to client {request.sid}")
        try:
            # Try direct emit first
            emit('user_id', {'user_id': user_id})
            logger.info(f"✅ Successfully auto-emitted user_id to client (direct)")
        except Exception as e:
            logger.error(f"❌ Error auto-emitting user_id (direct): {str(e)}")
            try:
                # Fallback: emit to room
                emit('user_id', {'user_id': user_id}, room=request.sid)
                logger.info(f"✅ Successfully auto-emitted user_id to client (room)")
            except Exception as e2:
                logger.error(f"❌ Error auto-emitting user_id (room): {str(e2)}")
                try:
                    # Last resort: emit to namespace
                    emit('user_id', {'user_id': user_id}, namespace='/')
                    logger.info(f"✅ Successfully auto-emitted user_id to client (namespace)")
                except Exception as e3:
                    logger.error(f"❌ Error auto-emitting user_id (namespace): {str(e3)}")
        
        # Auto-match with other waiting users (with delay to ensure user_id is sent first)
        logger.info(f"Starting auto-match for user {user_id}")
        eventlet.spawn(auto_match_user, user_id)
        
    except Exception as e:
        logger.error(f"Error in handle_connect: {str(e)}")
        # Clean up mapping on error
        user_manager.socket_user_map.pop(request.sid, None)
        raise

def auto_match_user(new_user_id):
    """Automatically match a new user with waiting users"""
    try:
        logger.info(f"🔍 Auto-match function called for user {new_user_id}")
        
        # Add user to waiting room
        user_manager.add_waiting_user(new_user_id, 'video')
        logger.info(f"✅ User {new_user_id} added to video waiting room")
        
        # Check if there's a waiting partner (excluding self)
        partner_id = user_manager.get_waiting_partner('video', exclude_user_id=new_user_id)
        logger.info(f"🔍 Looking for partner, found: {partner_id}")
        
        if partner_id and partner_id != new_user_id:
            logger.info(f"🎯 Auto-matching {new_user_id} with {partner_id}")
            
            # Create session
            chat_session = user_manager.create_session(new_user_id, partner_id, 'video')
            logger.info(f"✅ Created session {chat_session.session_id}")
            
            # Add delay to ensure both users are ready
            eventlet.sleep(1.0)
            
            # Emit matched events
            logger.info(f"📤 Emitting matched event to {new_user_id}")
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'video',
                'partner_id': partner_id,
                'is_initiator': False
            }, room=new_user_id)
            
            logger.info(f"📤 Emitting matched event to {partner_id}")
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'video',
                'partner_id': new_user_id,
                'is_initiator': True
            }, room=partner_id)
            
            logger.info(f"🎉 Auto-matched {new_user_id} with {partner_id} in session {chat_session.session_id}")
        else:
            logger.info(f"⏳ User {new_user_id} added to waiting room (no partner available)")
            logger.info(f"📊 Current waiting room: {user_manager.waiting_rooms['video']}")
            
    except Exception as e:
        logger.error(f"❌ Error in auto_match_user: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

@socketio.on('*')
def catch_all(event, data=None):
    """Catch all events for debugging"""
    logger.info(f"🔍 Received event: {event}, data: {data}")

@socketio.on('request_user_id')
def handle_request_user_id():
    """Handle user_id request from client"""
    logger.info(f"📞 REQUEST_USER_ID event triggered for socket {request.sid}")
    
    user_id = user_manager.socket_user_map.get(request.sid)
    if user_id:
        logger.info(f"Re-sending user_id {user_id} to client {request.sid}")
        try:
            emit('user_id', {'user_id': user_id}, room=request.sid, namespace='/')
            logger.info(f"✅ Successfully re-sent user_id to client {request.sid}")
        except Exception as e:
            logger.error(f"❌ Error re-sending user_id: {str(e)}")
    else:
        logger.warning(f"Client {request.sid} requested user_id but not found in mapping")
        # Generate new user_id if none exists
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id
        join_room(user_id)
        user_manager.add_active_user(user_id)
        user_manager.socket_user_map[request.sid] = user_id
        logger.info(f"Generated new user_id {user_id} for client {request.sid}")
        try:
            emit('user_id', {'user_id': user_id}, room=request.sid, namespace='/')
            logger.info(f"✅ Successfully sent new user_id to client {request.sid}")
        except Exception as e:
            logger.error(f"❌ Error sending new user_id: {str(e)}")
        
        # Also trigger auto-match for this user
        logger.info(f"Triggering auto-match for newly created user {user_id}")
        eventlet.spawn(auto_match_user, user_id)

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
            # Gracefully handle unknown socket disconnects (transport upgrades, etc.)
            logger.debug(f"Disconnect event for unknown socket: {request.sid} (likely transport upgrade)")
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
