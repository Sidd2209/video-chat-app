const io = require('socket.io-client');

console.log('Testing WebSocket connection...');

const socket = io('http://localhost:8081', {
  transports: ['websocket', 'polling'],
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
});

let userIdReceived = false;

socket.on('connect', () => {
  console.log('✅ Connected to WebSocket server');
  console.log('Socket ID:', socket.id);
});

socket.on('user_id', (data) => {
  console.log('✅ Received user_id:', data.user_id);
  userIdReceived = true;
  
  // Test API call
  testApiCall(data.user_id);
});

socket.on('disconnect', () => {
  console.log('❌ Disconnected from WebSocket server');
});

socket.on('connect_error', (error) => {
  console.error('❌ Connection error:', error.message);
});

// Test API call after receiving user_id
async function testApiCall(userId) {
  try {
    console.log('Testing API call with user_id:', userId);
    
    const response = await fetch('http://localhost:8081/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId
      },
      body: JSON.stringify({})
    });
    
    const data = await response.json();
    console.log('✅ API Response:', data);
    
    if (data.status === 'waiting') {
      console.log('✅ User is waiting for a partner');
    } else if (data.status === 'matched') {
      console.log('✅ User was matched with a partner');
    }
    
  } catch (error) {
    console.error('❌ API call failed:', error.message);
  }
}

// Timeout after 10 seconds
setTimeout(() => {
  if (!userIdReceived) {
    console.log('❌ Timeout: user_id not received within 10 seconds');
  }
  socket.disconnect();
  process.exit(0);
}, 10000);
