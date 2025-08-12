#!/usr/bin/env python3
"""
Test script for the improved Omegle-like chat backend
"""

import requests
import json
import time

def test_backend_health():
    """Test backend health endpoint"""
    try:
        print("Testing backend health...")
        response = requests.get('http://localhost:8081/', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend is healthy!")
            print(f"📊 Stats: {data.get('stats', {})}")
            print(f"✨ Features: {data.get('features', [])}")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing backend: {e}")
        return False

def test_user_profile():
    """Test user profile endpoint"""
    try:
        print("\nTesting user profile endpoint...")
        
        # Test creating a profile
        profile_data = {
            'interests': ['music', 'technology', 'travel'],
            'language': 'en',
            'country': 'US',
            'age_group': '25-35',
            'gender': 'prefer_not_to_say'
        }
        
        response = requests.put(
            'http://localhost:8081/profile?user_id=test_user_123',
            json=profile_data,
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ Profile updated successfully")
            
            # Test getting the profile
            response = requests.get(
                'http://localhost:8081/profile?user_id=test_user_123',
                timeout=5
            )
            
            if response.status_code == 200:
                profile = response.json()
                print(f"✅ Profile retrieved: {profile}")
                return True
            else:
                print(f"❌ Failed to get profile: {response.status_code}")
                return False
        else:
            print(f"❌ Failed to update profile: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing profile: {e}")
        return False

def test_chat_session():
    """Test chat session creation"""
    try:
        print("\nTesting chat session creation...")
        
        # Test starting a text chat
        response = requests.post(
            'http://localhost:8081/start',
            headers={'X-User-ID': 'test_user_123'},
            json={},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat session created: {data}")
            return True
        else:
            print(f"❌ Failed to create chat session: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing chat session: {e}")
        return False

def test_message_sending():
    """Test message sending"""
    try:
        print("\nTesting message sending...")
        
        # First create a session
        session_response = requests.post(
            'http://localhost:8081/start',
            headers={'X-User-ID': 'test_user_123'},
            json={},
            timeout=5
        )
        
        if session_response.status_code == 200:
            session_data = session_response.json()
            session_id = session_data.get('session_id')
            
            # Send a message
            message_data = {
                'session_id': session_id,
                'message': 'Hello, this is a test message!',
                'user_id': 'test_user_123'
            }
            
            response = requests.post(
                'http://localhost:8081/send',
                json=message_data,
                timeout=5
            )
            
            if response.status_code == 200:
                print("✅ Message sent successfully")
                return True
            else:
                print(f"❌ Failed to send message: {response.status_code}")
                return False
        else:
            print(f"❌ Failed to create session for message test: {session_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing message sending: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Improved Omegle-like Chat Backend")
    print("=" * 50)
    
    tests = [
        test_backend_health,
        test_user_profile,
        test_chat_session,
        test_message_sending
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Backend is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the backend logs for issues.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
