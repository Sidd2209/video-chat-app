from flask import Flask, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_cors import CORS
import uuid
import json
import time
from datetime import datetime, timedelta
import threading
import logging
from collections import defaultdict, deque
import random
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['CORS_HEADERS'] = 'Content-Type'

# Initialize SocketIO with CORS
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
CORS(app)

class UserProfile:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.interests = []
        self.language = "en"
        self.country = None
        self.age_group = None
        self.gender = None
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.total_sessions = 0
        self.blocked_users = set()
        self.reported_by = set()
        self.is_banned = False
        self.connection_quality = "unknown"
        
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'interests': self.interests,
            'language': self.language,
            'country': self.country,
            'age_group': self.age_group,
            'gender': self.gender,
            'total_sessions': self.total_sessions,
            'connection_quality': self.connection_quality
        }

class ChatSession:
    def __init__(self, session_id: str, user1_id: str, user2_id: str, chat_type: str):
        self.session_id = session_id
        self.user1_id = user1_id
        self.user2_id = user2_id
        self.chat_type = chat_type
        self.messages = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.is_active = True
        self.connection_quality = "unknown"
        self.user1_typing = False
        self.user2_typing = False
        self.user1_connected = True
        self.user2_connected = True
        
    def add_message(self, user_id: str, message: str, message_type: str = "text"):
        msg = {
            'id': str(uuid.uuid4()),
            'from': 'you' if user_id == self.user1_id else 'stranger',
            'text': message,
            'type': message_type,
            'timestamp': datetime.now().isoformat()
        }
        self.messages.append(msg)
        self.last_activity = datetime.now()
        return msg
    
    def get_messages(self, since_timestamp=None):
        if since_timestamp:
            return [msg for msg in self.messages if msg['timestamp'] > since_timestamp]
        return self.messages
    
    def get_partner_id(self, user_id: str):
        return self.user2_id if user_id == self.user1_id else self.user1_id
    
    def is_user_in_session(self, user_id: str):
        return user_id in [self.user1_id, self.user2_id]
    
    def update_connection_quality(self, quality: str):
        self.connection_quality = quality

class ImprovedUserManager:
    def __init__(self):
        self.active_users = {}  # user_id -> UserProfile
        self.connected_users = set()  # Users currently in chat sessions
        self.waiting_rooms = {
            'video': deque(),  # Users waiting for video chat
            'text': deque()    # Users waiting for text chat
        }
        self.active_sessions = {}  # session_id -> ChatSession
        self.user_sessions = {}  # user_id -> session_id
        self.socket_user_map = {}  # socket_id -> user_id
        self.user_rooms = {}  # user_id -> room_id
        self.lock = threading.Lock()
        self.session_stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'total_messages': 0
        }
        
    def add_active_user(self, user_id: str, profile_data: dict = None):
        """Add user to active users with profile"""
        with self.lock:
            if user_id not in self.active_users:
                profile = UserProfile(user_id)
                if profile_data:
                    profile.interests = profile_data.get('interests', [])
                    profile.language = profile_data.get('language', 'en')
                    profile.country = profile_data.get('country')
                    profile.age_group = profile_data.get('age_group')
                    profile.gender = profile_data.get('gender')
                self.active_users[user_id] = profile
                logger.info(f"User {user_id} added to active users with profile")
    
    def remove_active_user(self, user_id: str):
        """Remove user from active users"""
        with self.lock:
            if user_id in self.active_users:
                del self.active_users[user_id]
                logger.info(f"User {user_id} removed from active users")
    
    def add_waiting_user(self, user_id: str, chat_type: str):
        """Add user to waiting room with smart matching"""
        with self.lock:
            if user_id not in self.active_users:
                return False
                
            # Remove from other waiting rooms first
            for other_type in ['video', 'text']:
                if user_id in self.waiting_rooms[other_type]:
                    self.waiting_rooms[other_type].remove(user_id)
            
            # Add to current waiting room
            if user_id not in self.waiting_rooms[chat_type]:
                self.waiting_rooms[chat_type].append(user_id)
                logger.info(f"User {user_id} added to {chat_type} waiting room")
                return True
            return False
    
    def find_best_match(self, user_id: str, chat_type: str):
        """Find the best matching partner based on preferences"""
        with self.lock:
            if not self.waiting_rooms[chat_type]:
                return None
                
            user_profile = self.active_users.get(user_id)
            if not user_profile:
                return None
            
            # Try to find a match with similar interests/language
            best_match = None
            best_score = 0
            
            for waiting_user_id in list(self.waiting_rooms[chat_type]):
                if waiting_user_id == user_id:
                    continue
                    
                waiting_profile = self.active_users.get(waiting_user_id)
                if not waiting_profile:
                    continue
                
                # Check if users have blocked each other
                if (user_id in waiting_profile.blocked_users or 
                    waiting_user_id in user_profile.blocked_users):
                    continue
                
                # Calculate compatibility score
                score = self.calculate_compatibility(user_profile, waiting_profile)
                
                if score > best_score:
                    best_score = score
                    best_match = waiting_user_id
            
            # If no good match found, take the first available user
            if best_match is None and self.waiting_rooms[chat_type]:
                best_match = self.waiting_rooms[chat_type].popleft()
            elif best_match:
                self.waiting_rooms[chat_type].remove(best_match)
            
            return best_match
    
    def calculate_compatibility(self, profile1: UserProfile, profile2: UserProfile) -> int:
        """Calculate compatibility score between two users"""
        score = 0
        
        # Language compatibility (highest weight)
        if profile1.language == profile2.language:
            score += 50
        
        # Interest overlap
        common_interests = set(profile1.interests) & set(profile2.interests)
        score += len(common_interests) * 10
        
        # Age group compatibility
        if profile1.age_group == profile2.age_group:
            score += 20
        
        # Country proximity (if available)
        if profile1.country and profile2.country:
            if profile1.country == profile2.country:
                score += 15
        
        return score
    
    def create_session(self, user1_id: str, user2_id: str, chat_type: str):
        """Create a new chat session with improved logic"""
        session_id = str(uuid.uuid4())
        chat_session = ChatSession(session_id, user1_id, user2_id, chat_type)
        
        with self.lock:
            self.active_sessions[session_id] = chat_session
            self.user_sessions[user1_id] = session_id
            self.user_sessions[user2_id] = session_id
            
            # Update user stats
            if user1_id in self.active_users:
                self.active_users[user1_id].total_sessions += 1
            if user2_id in self.active_users:
                self.active_users[user2_id].total_sessions += 1
            
            # Add both users to connected users
            self.connected_users.add(user1_id)
            self.connected_users.add(user2_id)
            
            # Update session stats
            self.session_stats['total_sessions'] += 1
            self.session_stats['active_sessions'] += 1
        
        logger.info(f"Created session {session_id} between {user1_id} and {user2_id}")
        return chat_session
    
    def remove_connected_user(self, user_id: str):
        """Remove user from connected users"""
        with self.lock:
            self.connected_users.discard(user_id)
            # Remove from waiting rooms
            for chat_type in ['video', 'text']:
                if user_id in self.waiting_rooms[chat_type]:
                    self.waiting_rooms[chat_type].remove(user_id)
                    logger.info(f"Removed {user_id} from {chat_type} waiting room")
            logger.info(f"User {user_id} removed from connected users")
    
    def get_user_session(self, user_id: str):
        """Get session ID for a user"""
        return self.user_sessions.get(user_id)
    
    def get_session(self, session_id: str):
        """Get session by ID"""
        return self.active_sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """Remove a session"""
        with self.lock:
            session = self.active_sessions.get(session_id)
            if session:
                # Remove from user sessions
                self.user_sessions.pop(session.user1_id, None)
                self.user_sessions.pop(session.user2_id, None)
                
                # Remove from active sessions
                del self.active_sessions[session_id]
                
                # Update stats
                self.session_stats['active_sessions'] -= 1
                
                logger.info(f"Removed session {session_id}")
                return session
            return None
    
    def get_active_sessions_count(self):
        """Get count of active sessions"""
        return len(self.active_sessions)
    
    def block_user(self, user_id: str, blocked_user_id: str):
        """Block a user"""
        with self.lock:
            if user_id in self.active_users:
                self.active_users[user_id].blocked_users.add(blocked_user_id)
                logger.info(f"User {user_id} blocked {blocked_user_id}")
    
    def report_user(self, reporter_id: str, reported_user_id: str, reason: str):
        """Report a user"""
        with self.lock:
            if reported_user_id in self.active_users:
                self.active_users[reported_user_id].reported_by.add(reporter_id)
                logger.info(f"User {reported_user_id} reported by {reporter_id} for: {reason}")
                
                # Auto-ban if too many reports
                if len(self.active_users[reported_user_id].reported_by) >= 5:
                    self.active_users[reported_user_id].is_banned = True
                    logger.warning(f"User {reported_user_id} auto-banned due to multiple reports")

# Initialize improved user manager
user_manager = ImprovedUserManager()

def cleanup_inactive_sessions():
    """Clean up inactive sessions with improved logic"""
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

cleanup_thread = threading.Thread(target=start_cleanup_thread, daemon=True)
cleanup_thread.start()

@app.route('/')
def health_check():
    """Enhanced health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'message': 'Improved Omegle-like Chat Backend is running',
        'stats': {
            'active_users': len(user_manager.active_users),
            'connected_users': len(user_manager.connected_users),
            'waiting_video': len(user_manager.waiting_rooms['video']),
            'waiting_text': len(user_manager.waiting_rooms['text']),
            'active_sessions': len(user_manager.active_sessions),
            'total_sessions': user_manager.session_stats['total_sessions']
        },
        'features': [
            'Smart user matching',
            'User profiles and preferences',
            'Connection quality monitoring',
            'User blocking and reporting',
            'Multi-language support',
            'Interest-based matching'
        ]
    })

@app.route('/start', methods=['POST'])
def start_text_chat():
    """Start a text chat session with improved matching"""
    try:
        user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        if user_id not in user_manager.active_users:
            return jsonify({'error': 'User not connected via WebSocket'}), 400
        
        # Check if user is banned
        if user_manager.active_users[user_id].is_banned:
            return jsonify({'error': 'Account suspended'}), 403
        
        # Find best match
        partner_id = user_manager.find_best_match(user_id, 'text')
        
        if partner_id:
            # Match with partner
            chat_session = user_manager.create_session(user_id, partner_id, 'text')
            
            # Get user profiles for better context
            user_profile = user_manager.active_users[user_id]
            partner_profile = user_manager.active_users[partner_id]
            
            # Notify both users
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'text',
                'partner_id': partner_id,
                'partner_profile': partner_profile.to_dict()
            }, room=user_id)
            
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'text',
                'partner_id': user_id,
                'partner_profile': user_profile.to_dict()
            }, room=partner_id)
            
            logger.info(f"Text chat matched: {user_id} with {partner_id}")
            
            return jsonify({
                'session_id': chat_session.session_id,
                'status': 'matched',
                'partner_id': partner_id,
                'partner_profile': partner_profile.to_dict()
            })
        else:
            # Add to waiting list
            user_manager.add_waiting_user(user_id, 'text')
            logger.info(f"User {user_id} waiting for text chat")
            
            return jsonify({
                'session_id': user_id,
                'status': 'waiting',
                'estimated_wait_time': len(user_manager.waiting_rooms['text']) * 30  # 30 seconds per user
            })
        
    except Exception as e:
        logger.error(f"Error starting text chat: {str(e)}")
        return jsonify({'error': 'Failed to start chat'}), 500

@app.route('/start_video', methods=['POST'])
def start_video_chat():
    """Start a video chat session with improved matching"""
    try:
        user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        if user_id not in user_manager.active_users:
            return jsonify({'error': 'User not connected via WebSocket'}), 400
        
        # Check if user is banned
        if user_manager.active_users[user_id].is_banned:
            return jsonify({'error': 'Account suspended'}), 403
        
        # Find best match
        partner_id = user_manager.find_best_match(user_id, 'video')
        
        if partner_id:
            # Match with partner
            chat_session = user_manager.create_session(user_id, partner_id, 'video')
            
            # Get user profiles
            user_profile = user_manager.active_users[user_id]
            partner_profile = user_manager.active_users[partner_id]
            
            # Notify both users
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'video',
                'partner_id': partner_id,
                'partner_profile': partner_profile.to_dict()
            }, room=user_id)
            
            socketio.emit('matched', {
                'session_id': chat_session.session_id,
                'chat_type': 'video',
                'partner_id': user_id,
                'partner_profile': user_profile.to_dict()
            }, room=partner_id)
            
            logger.info(f"Video chat matched: {user_id} with {partner_id}")
            
            return jsonify({
                'session_id': chat_session.session_id,
                'status': 'matched',
                'partner_id': partner_id,
                'partner_profile': partner_profile.to_dict()
            })
        else:
            # Add to waiting list
            user_manager.add_waiting_user(user_id, 'video')
            logger.info(f"User {user_id} waiting for video chat")
            
            return jsonify({
                'session_id': user_id,
                'status': 'waiting',
                'estimated_wait_time': len(user_manager.waiting_rooms['video']) * 45  # 45 seconds per user
            })
        
    except Exception as e:
        logger.error(f"Error starting video chat: {str(e)}")
        return jsonify({'error': 'Failed to start video chat'}), 500

@app.route('/profile', methods=['GET', 'PUT'])
def user_profile():
    """Get or update user profile"""
    try:
        user_id = request.headers.get('X-User-ID') or request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        if user_id not in user_manager.active_users:
            return jsonify({'error': 'User not found'}), 404
        
        if request.method == 'GET':
            return jsonify(user_manager.active_users[user_id].to_dict())
        else:
            # Update profile
            data = request.get_json()
            profile = user_manager.active_users[user_id]
            
            if 'interests' in data:
                profile.interests = data['interests']
            if 'language' in data:
                profile.language = data['language']
            if 'country' in data:
                profile.country = data['country']
            if 'age_group' in data:
                profile.age_group = data['age_group']
            if 'gender' in data:
                profile.gender = data['gender']
            
            profile.last_activity = datetime.now()
            return jsonify({'message': 'Profile updated successfully'})
            
    except Exception as e:
        logger.error(f"Error handling profile: {str(e)}")
        return jsonify({'error': 'Failed to handle profile'}), 500

@app.route('/block', methods=['POST'])
def block_user():
    """Block a user"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        blocked_user_id = data.get('blocked_user_id')
        
        if not user_id or not blocked_user_id:
            return jsonify({'error': 'User ID and blocked user ID required'}), 400
        
        user_manager.block_user(user_id, blocked_user_id)
        return jsonify({'message': 'User blocked successfully'})
        
    except Exception as e:
        logger.error(f"Error blocking user: {str(e)}")
        return jsonify({'error': 'Failed to block user'}), 500

@app.route('/report', methods=['POST'])
def report_user():
    """Report a user"""
    try:
        data = request.get_json()
        reporter_id = data.get('reporter_id')
        reported_user_id = data.get('reported_user_id')
        reason = data.get('reason', 'No reason provided')
        
        if not reporter_id or not reported_user_id:
            return jsonify({'error': 'Reporter ID and reported user ID required'}), 400
        
        user_manager.report_user(reporter_id, reported_user_id, reason)
        return jsonify({'message': 'User reported successfully'})
        
    except Exception as e:
        logger.error(f"Error reporting user: {str(e)}")
        return jsonify({'error': 'Failed to report user'}), 500

@app.route('/send', methods=['POST'])
def send_message():
    """Send a message in a chat session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        message = data.get('message')
        user_id = data.get('user_id')
        
        if not all([session_id, message, user_id]):
            return jsonify({'error': 'Session ID, message, and user ID required'}), 400
        
        # Get the session
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
        
        # Update stats
        user_manager.session_stats['total_messages'] += 1
        
        return jsonify({'message': 'Message sent successfully'})
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({'error': 'Failed to send message'}), 500

@app.route('/disconnect', methods=['POST'])
def disconnect_chat():
    """Disconnect from a chat session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        
        if not all([session_id, user_id]):
            return jsonify({'error': 'Session ID and user ID required'}), 400
        
        # Get the session
        chat_session = user_manager.get_session(session_id)
        if not chat_session or not chat_session.is_user_in_session(user_id):
            return jsonify({'error': 'Session not found or user not in session'}), 404
        
        # Get partner ID before removing session
        partner_id = chat_session.get_partner_id(user_id)
        
        # Mark session as inactive
        chat_session.is_active = False
        
        # Remove session
        user_manager.remove_session(session_id)
        
        # Remove users from connected users
        user_manager.remove_connected_user(user_id)
        user_manager.remove_connected_user(partner_id)
        
        # Notify partner
        socketio.emit('partner_disconnected', {
            'session_id': session_id,
            'reason': 'partner_disconnected'
        }, room=partner_id)
        
        logger.info(f"User {user_id} disconnected from session {session_id}")
        
        return jsonify({'message': 'Disconnected successfully'})
        
    except Exception as e:
        logger.error(f"Error disconnecting: {str(e)}")
        return jsonify({'error': 'Failed to disconnect'}), 500

@app.route('/messages/<session_id>', methods=['GET'])
def get_messages(session_id):
    """Get messages for a session"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        chat_session = user_manager.get_session(session_id)
        if not chat_session or not chat_session.is_user_in_session(user_id):
            return jsonify({'error': 'Session not found or user not in session'}), 404
        
        messages = chat_session.get_messages()
        return jsonify({'messages': messages})
        
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        return jsonify({'error': 'Failed to get messages'}), 500

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection with improved logic"""
    user_id = str(uuid.uuid4())
    session['user_id'] = user_id
    
    # Join user's personal room
    join_room(user_id)
    
    # Add to active users with basic profile
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

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection with improved cleanup"""
    user_id = user_manager.socket_user_map.get(request.sid)
    if user_id:
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
                socketio.emit('partner_disconnected', {
                    'session_id': session_id,
                    'reason': 'partner_disconnected'
                }, room=partner_id)
                
                # Remove session
                user_manager.remove_session(session_id)
        
        logger.info(f"Client disconnected: {user_id} (socket: {request.sid})")

@socketio.on('update_profile')
def handle_update_profile(data):
    """Handle profile updates via WebSocket"""
    user_id = user_manager.socket_user_map.get(request.sid)
    if user_id and user_id in user_manager.active_users:
        profile = user_manager.active_users[user_id]
        
        if 'interests' in data:
            profile.interests = data['interests']
        if 'language' in data:
            profile.language = data['language']
        if 'country' in data:
            profile.country = data['country']
        if 'age_group' in data:
            profile.age_group = data['age_group']
        if 'gender' in data:
            profile.gender = data['gender']
        
        profile.last_activity = datetime.now()
        logger.info(f"Profile updated for user {user_id}")

@socketio.on('connection_quality')
def handle_connection_quality(data):
    """Handle connection quality updates"""
    user_id = user_manager.socket_user_map.get(request.sid)
    if user_id and user_id in user_manager.active_users:
        quality = data.get('quality', 'unknown')
        user_manager.active_users[user_id].connection_quality = quality
        
        # Update session quality if user is in a session
        session_id = user_manager.get_user_session(user_id)
        if session_id:
            chat_session = user_manager.get_session(session_id)
            if chat_session:
                chat_session.update_connection_quality(quality)

if __name__ == '__main__':
    logger.info("Starting Improved Omegle-like Chat Backend...")
    socketio.run(app, host='0.0.0.0', port=8081, debug=True)
