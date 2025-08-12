#!/usr/bin/env python3
"""
Simple test script to verify backend functionality
"""

import socket
import sys

def test_backend():
    """Test if backend is running and responding"""
    try:
        print("Testing backend connection...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 8081))
        sock.close()
        
        if result == 0:
            print("✅ Backend is running on port 8081!")
            return True
        else:
            print("❌ Backend is not running on port 8081")
            return False
    except Exception as e:
        print(f"❌ Error testing backend: {e}")
        return False

if __name__ == "__main__":
    if test_backend():
        print("\n🎉 Backend test passed!")
        sys.exit(0)
    else:
        print("\n💥 Backend test failed!")
        sys.exit(1)
