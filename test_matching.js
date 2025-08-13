const io = require('socket.io-client');

console.log('Testing matching system with two users...');

// Create two socket connections
const socket1 = io('http://localhost:8081');
const socket2 = io('http://localhost:8081');

let user1Id = null;
let user2Id = null;

// User 1
socket1.on('connect', () => {
  console.log('✅ User 1 connected');
});

socket1.on('user_id', (data) => {
  user1Id = data.user_id;
  console.log('✅ User 1 received user_id:', user1Id);
  
  // Start text chat for user 1
  startTextChat(user1Id, 'User 1');
});

socket1.on('matched', (data) => {
  console.log('🎉 User 1 matched!', data);
});

// User 2
socket2.on('connect', () => {
  console.log('✅ User 2 connected');
});

socket2.on('user_id', (data) => {
  user2Id = data.user_id;
  console.log('✅ User 2 received user_id:', user2Id);
  
  // Start text chat for user 2
  startTextChat(user2Id, 'User 2');
});

socket2.on('matched', (data) => {
  console.log('🎉 User 2 matched!', data);
});

async function startTextChat(userId, userLabel) {
  try {
    console.log(`${userLabel} starting text chat...`);
    
    const response = await fetch('http://localhost:8081/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId
      },
      body: JSON.stringify({})
    });
    
    const data = await response.json();
    console.log(`${userLabel} API Response:`, data);
    
    if (data.status === 'waiting') {
      console.log(`${userLabel} is waiting for a partner`);
    } else if (data.status === 'matched') {
      console.log(`${userLabel} was matched with a partner`);
    }
    
  } catch (error) {
    console.error(`${userLabel} API call failed:`, error.message);
  }
}

// Cleanup after 15 seconds
setTimeout(() => {
  console.log('Cleaning up...');
  socket1.disconnect();
  socket2.disconnect();
  process.exit(0);
}, 15000);
