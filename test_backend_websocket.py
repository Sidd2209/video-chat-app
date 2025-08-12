#!/usr/bin/env python3
"""
Test backend WebSocket functionality
"""

import socketio
import time
import sys

def test_backend_websocket():
    """Test backend WebSocket connection and user_id emission"""
    print("🧪 Testing backend WebSocket...")
    
    # Create Socket.IO client
    sio = socketio.Client()
    
    user_id_received = False
    
    @sio.event
    def connect():
        print("✅ Connected to backend WebSocket")
    
    @sio.event
    def user_id(data):
        global user_id_received
        print(f"🆔 Received user_id: {data}")
        user_id_received = True
        sio.disconnect()
    
    @sio.event
    def disconnect():
        print("🔌 Disconnected from backend WebSocket")
    
    try:
        # Connect to backend
        sio.connect('http://localhost:8081')
        
        # Wait for user_id (max 10 seconds)
        timeout = 10
        start_time = time.time()
        
        while not user_id_received and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if user_id_received:
            print("🎉 Backend WebSocket test passed!")
            return True
        else:
            print("⏰ Timeout waiting for user_id")
            return False
            
    except Exception as e:
        print(f"❌ Error testing backend WebSocket: {e}")
        return False
    finally:
        if sio.connected:
            sio.disconnect()

if __name__ == "__main__":
    if test_backend_websocket():
        sys.exit(0)
    else:
        sys.exit(1)
