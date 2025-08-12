import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-this-in-production'
    CORS_HEADERS = 'Content-Type'
    
    # Redis configuration (optional, for production)
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379'
    
    # SocketIO configuration
    SOCKETIO_ASYNC_MODE = 'eventlet'
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
    
    # Session configuration
    SESSION_TIMEOUT = 3600  # 1 hour in seconds
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    
    # Development settings
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Server settings
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT') or 8081)
