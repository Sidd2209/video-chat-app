#!/usr/bin/env python3
"""
Test script to verify the Video Chat backend setup
"""

import requests
import json
import time
import sys

def test_backend_health():
    """Test if the backend is running and healthy"""
    try:
        response = requests.get('http://localhost:5000/', timeout=5)
        if response.status_code == 200:
            print("✅ Backend health check passed")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend not accessible: {e}")
        return False

def test_text_chat_endpoints():
    """Test text chat API endpoints"""
    print("\n🧪 Testing text chat endpoints...")
    
    # Test starting a text chat
    try:
        response = requests.post('http://localhost:5000/start', 
                               json={}, 
                               timeout=5)
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            print(f"✅ Text chat started: {session_id}")
            
            # Test sending a message
            if session_id:
                msg_response = requests.post('http://localhost:5000/send',
                                           json={'session_id': session_id, 'message': 'Hello!'},
                                           timeout=5)
                if msg_response.status_code == 200:
                    print("✅ Message sent successfully")
                else:
                    print(f"❌ Failed to send message: {msg_response.status_code}")
                
                # Test disconnecting
                disconnect_response = requests.post('http://localhost:5000/disconnect',
                                                  json={'session_id': session_id},
                                                  timeout=5)
                if disconnect_response.status_code == 200:
                    print("✅ Disconnected successfully")
                else:
                    print(f"❌ Failed to disconnect: {disconnect_response.status_code}")
            
            return True
        else:
            print(f"❌ Failed to start text chat: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Text chat test failed: {e}")
        return False

def test_video_chat_endpoints():
    """Test video chat API endpoints"""
    print("\n🎥 Testing video chat endpoints...")
    
    try:
        response = requests.post('http://localhost:5000/start_video', 
                               json={}, 
                               timeout=5)
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            print(f"✅ Video chat started: {session_id}")
            
            # Test disconnecting
            if session_id:
                disconnect_response = requests.post('http://localhost:5000/disconnect',
                                                  json={'session_id': session_id},
                                                  timeout=5)
                if disconnect_response.status_code == 200:
                    print("✅ Video chat disconnected successfully")
                else:
                    print(f"❌ Failed to disconnect video chat: {disconnect_response.status_code}")
            
            return True
        else:
            print(f"❌ Failed to start video chat: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Video chat test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Video Chat Backend Test Suite")
    print("=" * 40)
    
    # Test backend health
    if not test_backend_health():
        print("\n❌ Backend is not running. Please start the backend first:")
        print("   cd backend && python run.py")
        sys.exit(1)
    
    # Test text chat
    text_success = test_text_chat_endpoints()
    
    # Test video chat
    video_success = test_video_chat_endpoints()
    
    print("\n" + "=" * 40)
    if text_success and video_success:
        print("🎉 All tests passed! Backend is working correctly.")
        print("\n📝 Next steps:")
        print("   1. Start the frontend: cd chat-link-stream && npm run dev")
        print("   2. Open http://localhost:5173 in your browser")
        print("   3. Test the video and text chat functionality")
    else:
        print("❌ Some tests failed. Please check the backend logs.")
        sys.exit(1)

if __name__ == '__main__':
    main()
