const { io } = require('socket.io-client');

console.log('🧪 Testing WebSocket connection...');

const socket = io('http://localhost:8081', {
  transports: ['websocket', 'polling'],
  timeout: 5000
});

socket.on('connect', () => {
  console.log('✅ WebSocket connected successfully!');
  console.log('🆔 Socket ID:', socket.id);
  
  // Wait for user_id
  socket.on('user_id', (data) => {
    console.log('🆔 Received user_id:', data.user_id);
    console.log('🎉 WebSocket test passed!');
    socket.disconnect();
    process.exit(0);
  });
  
  // Timeout after 10 seconds
  setTimeout(() => {
    console.log('⏰ Timeout waiting for user_id');
    socket.disconnect();
    process.exit(1);
  }, 10000);
});

socket.on('connect_error', (error) => {
  console.log('❌ WebSocket connection failed:', error.message);
  process.exit(1);
});

socket.on('disconnect', () => {
  console.log('🔌 WebSocket disconnected');
});
