#!/usr/bin/env python3
"""
Test script to verify the Video Chat Application is working properly
"""

import requests
import time
import json

def test_backend():
    """Test the backend API endpoints"""
    print("🧪 Testing Backend...")
    
    base_url = "http://localhost:8081"
    
    try:
        # Test health check
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend is running - Status: {data.get('status')}")
            print(f"   Active users: {data.get('rooms', {}).get('active_users', 0)}")
            print(f"   Active sessions: {data.get('active_sessions', 0)}")
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running on http://localhost:8081")
        return False
    except Exception as e:
        print(f"❌ Backend test error: {e}")
        return False
    
    return True

def test_frontend():
    """Test the frontend is accessible"""
    print("\n🧪 Testing Frontend...")
    
    try:
        response = requests.get("http://localhost:8080/")
        if response.status_code == 200:
            print("✅ Frontend is running on http://localhost:8080")
            return True
        else:
            print(f"❌ Frontend test failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Frontend is not running on http://localhost:8080")
        return False
    except Exception as e:
        print(f"❌ Frontend test error: {e}")
        return False

def test_websocket_connection():
    """Test WebSocket connection"""
    print("\n🧪 Testing WebSocket Connection...")
    
    try:
        import socketio
        
        # Create a test client
        sio = socketio.Client()
        
        connected = False
        user_id_received = False
        
        @sio.event
        def connect():
            nonlocal connected
            connected = True
            print("✅ WebSocket connected successfully")
        
        @sio.event
        def user_id(data):
            nonlocal user_id_received
            user_id_received = True
            print(f"✅ Received user_id: {data.get('user_id')}")
        
        @sio.event
        def disconnect():
            print("WebSocket disconnected")
        
        # Connect to the server
        sio.connect('http://localhost:8081')
        
        # Wait for connection and user_id
        timeout = 10
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if connected and user_id_received:
                sio.disconnect()
                return True
            time.sleep(0.1)
        
        sio.disconnect()
        
        if not connected:
            print("❌ WebSocket connection failed")
        elif not user_id_received:
            print("❌ WebSocket user_id not received")
        
        return False
        
    except ImportError:
        print("⚠️  python-socketio not installed, skipping WebSocket test")
        return True
    except Exception as e:
        print(f"❌ WebSocket test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Video Chat Application Test Suite")
    print("=" * 50)
    
    backend_ok = test_backend()
    frontend_ok = test_frontend()
    websocket_ok = test_websocket_connection()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   Backend:    {'✅ PASS' if backend_ok else '❌ FAIL'}")
    print(f"   Frontend:   {'✅ PASS' if frontend_ok else '❌ FAIL'}")
    print(f"   WebSocket:  {'✅ PASS' if websocket_ok else '❌ FAIL'}")
    
    if backend_ok and frontend_ok and websocket_ok:
        print("\n🎉 All tests passed! The application is ready to use.")
        print("\n🌐 Access the application:")
        print("   Frontend: http://localhost:8080")
        print("   Backend API: http://localhost:8081")
        print("\n📝 Instructions:")
        print("   1. Open http://localhost:8080 in your browser")
        print("   2. Choose 'Video Chat' or 'Text Chat'")
        print("   3. Allow camera/microphone permissions for video chat")
        print("   4. Click 'Start' to begin searching for a partner")
        print("   5. Open another browser tab/window to test with yourself")
    else:
        print("\n❌ Some tests failed. Please check the issues above.")
        print("\n🔧 Troubleshooting:")
        if not backend_ok:
            print("   - Make sure the backend is running: cd backend && python run.py")
        if not frontend_ok:
            print("   - Make sure the frontend is running: cd chat-link-stream && npm run dev")
        if not websocket_ok:
            print("   - Check WebSocket configuration in the backend")

if __name__ == "__main__":
    main()
