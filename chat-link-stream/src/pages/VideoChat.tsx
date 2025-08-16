import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { startVideoChat } from "@/lib/chatApi";
import socketService from "@/lib/socketService";
import webrtcService from "@/lib/webrtcService";
import { useNavigate } from "react-router-dom";

const VideoChat = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const [isMatched, setIsMatched] = useState(false);
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const [isVideoEnabled, setIsVideoEnabled] = useState(true);

  const localVideoRef = useRef<HTMLVideoElement | null>(null);
  const remoteVideoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  
  // CRITICAL: Use refs to prevent cleanup on every render
  const isInitializedRef = useRef(false);
  const isConnectedRef = useRef(false);
  const cleanupRef = useRef(false);

  useEffect(() => {
    // Prevent multiple initializations
    if (isInitializedRef.current) {
      console.log('⚠️ Component already initialized, skipping...');
      return;
    }
    
    isInitializedRef.current = true;
    document.title = "Video Chat — Chat with a Stranger";
    
    // Clear any existing user_id from localStorage to prevent conflicts
    localStorage.removeItem('user_id');
    console.log('🧹 Cleared localStorage user_id to prevent conflicts');
    
    const handleMatched = (data: any) => {
      console.log('🎯 Received matched event:', data);
      setSessionId(data.session_id);
      setIsMatched(true);
      setWaiting(false);
      isConnectedRef.current = true;
      toast({ title: "Matched!", description: "You've been connected with a stranger" });
    };

    const handlePartnerDisconnected = (data: any) => {
      console.log('👋 Partner disconnected:', data);
      setIsMatched(false);
      setSessionId(null);
      isConnectedRef.current = false;
      toast({ title: "Partner disconnected", description: "Your chat partner has left the session." });
    };

    const handleSessionEnded = (data: any) => {
      console.log('🔚 Session ended:', data);
      setIsMatched(false);
      setSessionId(null);
      isConnectedRef.current = false;
      toast({ title: "Session ended", description: "The chat session has ended." });
    };

    // Register event listeners (only once)
    socketService.onMatched(handleMatched);
    socketService.on('partner_disconnected', handlePartnerDisconnected);
    socketService.on('session_ended', handleSessionEnded);

    // Cleanup function - ONLY on component unmount
    return () => {
      if (cleanupRef.current) return; // Prevent multiple cleanups
      cleanupRef.current = true;
      
      console.log('🧹 Component unmounting - performing cleanup...');
      socketService.offMatched(handleMatched);
      socketService.off('partner_disconnected', handlePartnerDisconnected);
      socketService.off('session_ended', handleSessionEnded);
      
      // Cleanup: clear localStorage when component unmounts
      localStorage.removeItem('user_id');
      console.log('🧹 Cleanup: cleared localStorage user_id');
    };
  }, []); // Empty dependency array to prevent re-registration

  // Separate useEffect for connection initialization
  useEffect(() => {
    // Only initialize if not already connected and not already initialized
    if (isConnectedRef.current || isInitializedRef.current) {
      return;
    }

    // Don't auto-initialize - wait for user to click button
    console.log('🚀 Component mounted, waiting for user to click Start Video Chat...');
  }, []); // Empty dependency array to prevent re-registration

  // CRITICAL: Add useEffect for remote stream handling
  useEffect(() => {
    const handleRemoteStream = (event: CustomEvent) => {
      console.log('🎥 Remote stream received in VideoChat component:', event.detail);
      if (remoteVideoRef.current && event.detail) {
        remoteVideoRef.current.srcObject = event.detail;
        console.log('✅ Remote video element updated with stream');
      }
    };

    // Listen for remote stream events
    window.addEventListener('remoteStream', handleRemoteStream as EventListener);

    return () => {
      window.removeEventListener('remoteStream', handleRemoteStream as EventListener);
    };
  }, []); // Empty dependency array

  // Manual start function for the button
  const startVideoChatManual = async () => {
    if (isConnectedRef.current || isInitializedRef.current) {
      console.log('⚠️ Already connected or initializing, skipping...');
      return;
    }

    try {
      setConnecting(true);
      console.log('🚀 Starting video chat manually...');
      
      // CRITICAL: Set up user_id listener BEFORE connecting to WebSocket
      console.log('Setting up user_id listener BEFORE connecting...');
      let userIdReceived = false;
      let userId: string | null = null;
      
      const handleUserId = (receivedUserId: string) => {
        if (userIdReceived) return;
        console.log('VideoChat received user_id:', receivedUserId);
        userIdReceived = true;
        userId = receivedUserId;
        setUserId(receivedUserId);
      };
      
      // Register listener BEFORE connecting
      socketService.onUserId(handleUserId);
      
      // Connect to WebSocket AFTER setting up listener
      console.log('Connecting to WebSocket...');
      await socketService.connect();
      console.log('WebSocket connected successfully');

      // CRITICAL: Request user_id manually if not received within 2 seconds
      setTimeout(async () => {
        if (!userIdReceived) {
          console.log('🔄 Requesting user_id manually...');
          try {
            // Request user_id from server
            socketService.emit('request_user_id');
            
            // Also try to get it via API
            const response = await fetch('http://localhost:8081/start_video', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_id: 'temp' })
            });
            
            if (response.ok) {
              const data = await response.json();
              console.log('API response:', data);
            }
          } catch (e) {
            console.error('Error requesting user_id:', e);
          }
        }
      }, 2000);
      
      // Wait for user_id with timeout
      const timeout = setTimeout(() => {
        if (!userIdReceived) {
          console.error('Timeout waiting for user_id');
          throw new Error('Timeout waiting for user_id');
        }
      }, 10000); // 10 second timeout
      
      // Wait for user_id to be received
      while (!userIdReceived) {
        await new Promise(resolve => setTimeout(resolve, 100)); // Wait 100ms
      }
      
      clearTimeout(timeout);
      socketService.offUserId(handleUserId);
      
      if (!userId) {
        throw new Error('Failed to receive user_id');
      }
      
      // CRITICAL: Add delay to ensure server has fully registered the user
      console.log('⏳ Waiting 2 seconds for server to fully register user...');
      await new Promise(resolve => setTimeout(resolve, 2000));
      console.log('✅ Server registration delay completed');
      
      await setupVideoChat(userId);
      setConnecting(false);
    } catch (error) {
      console.error('Error in startVideoChatManual:', error);
      setConnecting(false);
      toast({ title: "Connection error", description: error?.message || "Failed to connect" });
    }
  };

  const setupVideoChat = async (userId: string) => {
    try {
      // Get user media
      console.log('🎥 Requesting camera/microphone permissions...');
      
      // Enhanced constraints for better localhost compatibility
      const constraints = {
        video: {
          width: { ideal: 1280, min: 640 },
          height: { ideal: 720, min: 480 },
          frameRate: { ideal: 30, min: 15 },
          facingMode: 'user'
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: { ideal: 48000 },
          channelCount: { ideal: 2 }
        }
      };
      
      const media = await navigator.mediaDevices.getUserMedia(constraints);
      console.log('✅ Camera/microphone access granted');
      console.log('📹 Stream tracks:', media.getTracks().map(t => `${t.kind}: ${t.enabled}`));
      
      streamRef.current = media;
      
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = media;
        await localVideoRef.current.play().catch(() => {});
      }
      
      setupMatchedListener(userId, media);
      
      console.log('Making API call to start video chat with userId:', userId);
      
      // Add retry mechanism for API call
      let retryCount = 0;
      const maxRetries = 3;
      let response;
      
      while (retryCount < maxRetries) {
        try {
          response = await startVideoChat(userId);
          console.log('✅ Video chat API success:', response);
          break; // Success, exit retry loop
        } catch (apiError: any) {
          retryCount++;
          console.error(`❌ startVideoChat API failed (attempt ${retryCount}/${maxRetries}):`, apiError);
          
          // Check if it's a "User not connected" error
          if (apiError.message.includes('User not connected via WebSocket')) {
            if (retryCount < maxRetries) {
              console.log(`⏳ User not connected, waiting 1 second before retry ${retryCount + 1}...`);
              await new Promise(resolve => setTimeout(resolve, 1000));
              continue; // Retry
            } else {
              console.error('❌ Max retries reached for "User not connected" error');
              toast({ 
                title: "Connection Error", 
                description: "Failed to connect to video chat server after multiple attempts" 
              });
              return;
            }
          } else {
            // For other errors, don't retry
            console.error('❌ Non-retryable API error:', apiError);
            toast({ 
              title: "Connection Error", 
              description: apiError.message || "Failed to start video chat" 
            });
            return;
          }
        }
      }
      
      // Validate response structure
      if (!response || !response.hasOwnProperty('status')) {
        throw new Error('Invalid API response structure');
      }
      
      const { session_id, status } = response;
      
      if (status === 'matched') {
        console.log('🎯 User already matched, setting up session:', session_id);
        setSessionId(session_id);
        setIsMatched(true);
        setWaiting(false);
        toast({ title: "Matched!", description: "You've been connected with a stranger" });
        
        // Set up real-time communication for existing session
        if (streamRef.current) {
          setupRealTimeCommunication(session_id, streamRef.current, false);
        }
      } else {
        console.log('⏳ User added to waiting room, session:', session_id);
        setSessionId(session_id);
        setWaiting(true);
        setIsMatched(false);
        toast({ title: "Connected", description: "Waiting for a partner..." });
      }
      
    } catch (e: any) {
      console.error('❌ Camera/Mic error:', e);
      toast({ title: "Camera/Mic error", description: e?.message || "Permission needed" });
    }
  };

  const setupMatchedListener = (userId: string, media: MediaStream) => {
    // Listen for matched event from WebSocket
    console.log('Setting up matched event listener for user:', userId);
    socketService.on('matched', (data) => {
      console.log('🎯 Received matched event:', data);
      console.log('Current user ID:', userId);
      console.log('Matched session ID:', data.session_id);
      
      setIsMatched(true);
      setWaiting(false);
      setSessionId(data.session_id);
      toast({ title: "Matched!", description: "You've been connected with a stranger" });
      setupRealTimeCommunication(data.session_id, media, data.is_initiator);
    });
  };

  const setupRealTimeCommunication = async (sessionId: string, media: MediaStream, isInitiator: boolean = false) => {
    try {
      await webrtcService.initialize(sessionId, isInitiator);
      await webrtcService.setLocalStream(media);
      
      socketService.emit('join_session', { session_id: sessionId });
      
      // Only create offer if this user is the initiator
      if (isInitiator) {
        await webrtcService.createOffer();
      }
      
      socketService.on('partner_disconnected', (data) => {
        if (data.session_id === sessionId) {
          toast({ title: "Partner left", description: "Returning to home" });
          disconnect();
          navigate("/");
        }
      });
      
      // window.addEventListener('remoteStream', (event: any) => {
      //   if (remoteVideoRef.current) {
      //     remoteVideoRef.current.srcObject = event.detail;
      //     remoteVideoRef.current.play().catch(() => {});
      //   }
      // });
      
    } catch (error) {
      console.error('Error setting up real-time communication:', error);
      toast({ title: "Connection error", description: "Failed to establish connection" });
    }
  };

  const disconnect = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (sessionId) {
      webrtcService.cleanup();
      socketService.emit('leave_session', { session_id: sessionId });
    }
    
    socketService.disconnect();
    setSessionId(null);
    setUserId(null);
    setWaiting(false);
    setIsMatched(false);
    setConnecting(false);
    
    navigate("/");
  };

  const toggleAudio = () => {
    if (streamRef.current) {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsAudioEnabled(audioTrack.enabled);
      }
    }
  };

  const toggleVideo = () => {
    if (streamRef.current) {
      const videoTrack = streamRef.current.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setIsVideoEnabled(videoTrack.enabled);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 p-4 flex justify-between items-center">
        <h1 className="text-white text-xl font-bold">Video Chat</h1>
        <Button onClick={disconnect} variant="destructive">
          Disconnect
        </Button>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row gap-4 p-4">
        {/* Video Area */}
        <div className="flex-1 flex flex-col lg:flex-row gap-4">
          {/* Local Video */}
          <div className="flex-1 relative">
            <video
              ref={localVideoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover rounded-lg bg-gray-800"
            />
            <div className="absolute bottom-4 left-4 text-white bg-black bg-opacity-50 px-2 py-1 rounded">
              You
            </div>
          </div>

          {/* Remote Video */}
          <div className="flex-1 relative">
            <video
              ref={remoteVideoRef}
              autoPlay
              playsInline
              className="w-full h-full object-cover rounded-lg bg-gray-800"
            />
            <div className="absolute bottom-4 left-4 text-white bg-black bg-opacity-50 px-2 py-1 rounded">
              Stranger
            </div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-gray-800 p-4 flex justify-center gap-4">
        {!connecting && !waiting && !isMatched && (
          <Button size="lg" className="bg-green-600 hover:bg-green-700" onClick={startVideoChatManual}>
            Start Video Chat
          </Button>
        )}
        
        {connecting && (
          <Button disabled size="lg">
            Connecting...
          </Button>
        )}
        
        {waiting && (
          <Button disabled size="lg">
            Waiting for partner...
          </Button>
        )}
        
        {isMatched && (
          <>
            <Button onClick={toggleAudio} variant={isAudioEnabled ? "default" : "secondary"}>
              {isAudioEnabled ? "Mute" : "Unmute"}
            </Button>
            <Button onClick={toggleVideo} variant={isVideoEnabled ? "default" : "secondary"}>
              {isVideoEnabled ? "Stop Video" : "Start Video"}
            </Button>
          </>
        )}
      </div>
    </div>
  );
};

export default VideoChat;
