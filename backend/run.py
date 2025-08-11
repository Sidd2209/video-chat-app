#!/usr/bin/env python3
"""
Startup script for the Video Chat Backend
"""

import os
import sys
from app import app, socketio
from config import Config

def main():
    """Main entry point for the application"""
    print("🚀 Starting Video Chat Backend...")
    print(f"📡 Server will run on {Config.HOST}:{Config.PORT}")
    print(f"🔧 Debug mode: {Config.DEBUG}")
    print(f"📝 Log level: {Config.LOG_LEVEL}")
    
    try:
        socketio.run(
            app,
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG,
            use_reloader=Config.DEBUG
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
