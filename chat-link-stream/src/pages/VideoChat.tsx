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

  useEffect(() => {
    document.title = "Video Chat — Chat with a Stranger";
  }, []);

  const start = async () => {
    try {
      setConnecting(true);
      
      // Connect to WebSocket first
      console.log('Connecting to WebSocket...');
      await socketService.connect();
      
      // Check if we already have a cached user_id
      const cachedUserId = socketService.getCachedUserId();
      if (cachedUserId) {
        console.log('Using cached user_id:', cachedUserId);
        setUserId(cachedUserId);
        await setupVideoChat(cachedUserId);
        return;
      }
      
      // Wait for user_id with timeout
      console.log('Waiting for user_id...');
      const userId = await new Promise<string>((resolve, reject) => {
        const timeout = setTimeout(() => {
          console.error('Timeout waiting for user_id');
          reject(new Error('Timeout waiting for user_id'));
        }, 15000); // Increased timeout
        
        let userIdReceived = false;
        
        const handleUserId = (userId: string) => {
          if (userIdReceived) return;
          console.log('VideoChat received user_id:', userId);
          userIdReceived = true;
          clearTimeout(timeout);
          socketService.offUserId(handleUserId);
          setUserId(userId);
          resolve(userId);
        };
        
        socketService.onUserId(handleUserId);
        
        // Request user_id immediately if socket is connected
        if (socketService.isSocketConnected) {
          console.log('Socket is connected, requesting user_id...');
          socketService.emit('request_user_id');
        } else {
          console.log('Socket not connected yet, waiting...');
        }
      });
      
      await setupVideoChat(userId);
    } catch (e: any) {
      console.error('Error in start:', e);
      toast({ title: "Connection error", description: e?.message || "Failed to connect" });
    } finally {
      setConnecting(false);
    }
  };

  const setupVideoChat = async (userId: string) => {
    try {
      // Get user media
      const media = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      });
      
      streamRef.current = media;
      
      // Display local video
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = media;
        await localVideoRef.current.play().catch(() => {});
      }
      
      // Set up matched event listener BEFORE making the API call
      setupMatchedListener(userId, media);
      
      // Start video chat session
      console.log('Making API call to start video chat with userId:', userId);
      const response = await startVideoChat(userId);
      console.log('Video chat response:', response);
      const { session_id, status } = response;
      
      if (status === 'matched') {
        setSessionId(session_id);
        setIsMatched(true);
        setWaiting(false);
        toast({ title: "Matched!", description: "You've been connected with a stranger" });
        await setupRealTimeCommunication(session_id, media, false); // User who just joined is not initiator
      } else {
        setWaiting(true);
        setSessionId(null);
        toast({ title: "Connected", description: "Waiting for a partner..." });
      }
    } catch (e: any) {
      toast({ title: "Camera/Mic error", description: e?.message || "Permission needed" });
    }
  };

  const setupMatchedListener = (userId: string, media: MediaStream) => {
    // Listen for matched event from WebSocket
    socketService.on('matched', (data) => {
      console.log('Received matched event:', data);
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
      
      socketService.joinSession(sessionId);
      
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
      
      window.addEventListener('remoteStream', (event: any) => {
        if (remoteVideoRef.current) {
          remoteVideoRef.current.srcObject = event.detail;
          remoteVideoRef.current.play().catch(() => {});
        }
      });
      
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
      socketService.leaveSession(sessionId);
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
          <Button onClick={start} size="lg" className="bg-green-600 hover:bg-green-700">
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
