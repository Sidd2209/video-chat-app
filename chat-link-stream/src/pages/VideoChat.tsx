import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { disconnectChat, sendMessage, startVideoChat } from "@/lib/chatApi";
import socketService from "@/lib/socketService";
import webrtcService from "@/lib/webrtcService";
import { useNavigate } from "react-router-dom";

interface ChatMsg {
  id: string;
  from: "You" | "Stranger";
  text: string;
  time: number;
}

const VideoChat = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const [input, setInput] = useState("");
  const [isMatched, setIsMatched] = useState(false);
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const [isVideoEnabled, setIsVideoEnabled] = useState(true);

  const localVideoRef = useRef<HTMLVideoElement | null>(null);
  const remoteVideoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    document.title = "Video Chat — Chat with a Stranger";
  }, []);

  const canSend = useMemo(() => !!sessionId && input.trim().length > 0, [sessionId, input]);

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
        // Continue with the rest of the setup
        await setupVideoChat(cachedUserId);
        return;
      }
      
      // Wait for user_id with timeout
      console.log('Waiting for user_id...');
      const userId = await new Promise<string>((resolve, reject) => {
        const timeout = setTimeout(() => {
          console.error('Timeout waiting for user_id');
          reject(new Error('Timeout waiting for user_id'));
        }, 10000); // 10 second timeout
        
        let userIdReceived = false;
        
        const handleUserId = (userId: string) => {
          if (userIdReceived) return; // Prevent multiple calls
          console.log('VideoChat received user_id:', userId);
          userIdReceived = true;
          clearTimeout(timeout);
          socketService.offUserId(handleUserId);
          setUserId(userId);
          resolve(userId);
        };
        
        // Register for user_id events using the new callback system
        socketService.onUserId(handleUserId);
        
        // If we're already connected, the user_id might have been sent already
        // Let's check if we need to request it
        if (socketService.isSocketConnected) {
          console.log('Socket is connected, waiting for user_id...');
          // Give a small delay to ensure the listener is set up
          setTimeout(() => {
            if (!userIdReceived) {
              console.log('Requesting user_id from server...');
              // Emit a request for user_id if not received
              socketService.emit('request_user_id');
            }
          }, 100);
        }
      });
      
      // Continue with the rest of the setup
      await setupVideoChat(userId);
    } catch (e: any) {
      toast({ title: "Camera/Mic error", description: e?.message || "Permission needed" });
    } finally {
      setConnecting(false);
    }
  };

  const setupVideoChat = async (userId: string) => {
    try {
      // Get user media
      const media = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streamRef.current = media;
      
      // Set up local video
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = media;
        localVideoRef.current.muted = true;
        await localVideoRef.current.play().catch(() => {});
      }
      
      // Start video chat session
      console.log('Making API call to start video chat...');
      const response = await startVideoChat(userId);
      console.log('Video chat response:', response);
      const { session_id, status } = response;
      
      if (status === 'matched') {
        // Already matched with someone
        setSessionId(session_id);
        setIsMatched(true);
        setWaiting(false);
        toast({ title: "Matched!", description: "You've been connected with a stranger" });
        
        // Set up WebRTC and Socket.IO
        await setupRealTimeCommunication(session_id, media);
      } else {
        // Waiting for a partner
        setWaiting(true);
        
        // Set up WebRTC and Socket.IO
        await setupRealTimeCommunication(session_id, media);
        
        toast({ title: "Connected", description: "Waiting for a partner..." });
      }
    } catch (e: any) {
      toast({ title: "Camera/Mic error", description: e?.message || "Permission needed" });
    }
  };

  const setupRealTimeCommunication = async (sessionId: string, media: MediaStream) => {
    try {
      // Initialize WebRTC service
      await webrtcService.initialize(sessionId, true);
      await webrtcService.setLocalStream(media);
      
      // Join the session room
      socketService.joinSession(sessionId);
      
      // Set up Socket.IO event handlers
      socketService.on('matched', (data) => {
        // Handle both waiting user_id and actual session_id
        if (data.session_id === sessionId || data.session_id === userId) {
          setIsMatched(true);
          setWaiting(false);
          setSessionId(data.session_id);
          toast({ title: "Matched!", description: "You've been connected with a stranger" });
          
          // Create WebRTC offer when matched
          webrtcService.createOffer();
        }
      });
      
      socketService.on('new_message', (data) => {
        // Check if this message is for our current session
        const currentSessionId = sessionId || userId;
        if (data.session_id === currentSessionId) {
          setMessages(prev => [
            ...prev,
            {
              id: data.message.id,
              from: (data.message.from === "you" ? "You" : "Stranger") as "You" | "Stranger",
              text: data.message.text,
              time: Date.now(),
            },
          ]);
        }
      });
      
      socketService.on('partner_disconnected', (data) => {
        // Check if this disconnection is for our current session
        const currentSessionId = sessionId || userId;
        if (data.session_id === currentSessionId) {
          toast({ title: "Partner left", description: "Returning to home" });
          disconnect();
          navigate("/");
        }
      });
      
      // Set up remote stream handler
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

  const onSend = async () => {
    if (!sessionId || !userId || !input.trim()) return;
    const text = input.trim();
    setInput("");
    setMessages(prev => [...prev, { id: `${Date.now()}`, from: "You", text, time: Date.now() }]);
    try {
      await sendMessage(sessionId, text, userId);
    } catch (e: any) {
      toast({ title: "Send failed", description: e?.message || "" });
    }
  };

  const disconnect = async () => {
    try {
      if (sessionId && userId) {
        await disconnectChat(sessionId, userId);
        webrtcService.cleanup();
      }
    } catch (error) {
      console.error('Error disconnecting:', error);
    }
    
    setSessionId(null);
    setIsMatched(false);
    setWaiting(false);
    setMessages([]);
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    
    // Clean up video elements
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
    }
    if (remoteVideoRef.current) {
      remoteVideoRef.current.srcObject = null;
    }
  };

  const toggleMute = () => {
    const newState = !isAudioEnabled;
    setIsAudioEnabled(newState);
    webrtcService.toggleAudio(newState);
  };

  const toggleVideo = () => {
    const newState = !isVideoEnabled;
    setIsVideoEnabled(newState);
    webrtcService.toggleVideo(newState);
  };

  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
      webrtcService.cleanup();
      socketService.disconnect();
    };
  }, []);

  return (
    <main className="min-h-screen bg-background">
      <section className="container py-6 md:py-10">
        <header className="mb-6">
          <h1 className="text-3xl md:text-4xl font-bold">Video Chat</h1>
          <p className="text-muted-foreground">Connect instantly and chat while on video.</p>
        </header>

        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <article className="rounded-lg border bg-card p-3">
                <h2 className="text-sm font-medium mb-2">Your Video</h2>
                <div className="aspect-video rounded-md overflow-hidden bg-secondary">
                  <video ref={localVideoRef} className="w-full h-full object-cover" playsInline />
                </div>
              </article>
              <article className="rounded-lg border bg-card p-3 relative">
                <h2 className="text-sm font-medium mb-2">Stranger’s Video</h2>
                <div className="aspect-video rounded-md overflow-hidden bg-secondary grid place-items-center">
                  <video 
                    ref={remoteVideoRef} 
                    className={`w-full h-full object-cover ${isMatched ? '' : 'hidden'}`} 
                    playsInline 
                    autoPlay
                  />
                  {waiting && !isMatched && (
                    <span className="text-sm text-muted-foreground">Waiting for a partner...</span>
                  )}
                  {!waiting && !isMatched && (
                    <span className="text-sm text-muted-foreground">Click Start to begin</span>
                  )}
                </div>
              </article>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button onClick={start} disabled={connecting || !!sessionId} size="lg">
                {connecting ? "Starting..." : "Start"}
              </Button>
              <Button onClick={disconnect} variant="destructive" disabled={!sessionId} size="lg">
                Disconnect
              </Button>
              <Button onClick={toggleMute} variant="secondary" disabled={!sessionId} size="lg">
                {isAudioEnabled ? "Mute" : "Unmute"}
              </Button>
              <Button onClick={toggleVideo} variant="secondary" disabled={!sessionId} size="lg">
                {isVideoEnabled ? "Stop Video" : "Start Video"}
              </Button>
            </div>
          </div>

          <aside className="rounded-lg border bg-card p-3 flex flex-col max-h-[70vh]">
            <h2 className="text-sm font-medium mb-2">Chat</h2>
            <div className="flex-1 overflow-y-auto rounded-md bg-secondary p-3 space-y-3">
              {messages.map(m => (
                <div key={m.id} className="animate-fade-in">
                  <div className="text-xs text-muted-foreground mb-1">{m.from}</div>
                  <div className="inline-block px-3 py-2 rounded-lg bg-background border">
                    {m.text}
                  </div>
                </div>
              ))}
              {messages.length === 0 && (
                <p className="text-sm text-muted-foreground">No messages yet.</p>
              )}
            </div>
            <div className="mt-3 flex items-center gap-2">
              <Input
                placeholder="Type a message"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onSend();
                }}
                disabled={!sessionId}
              />
              <Button onClick={onSend} disabled={!canSend}>Send</Button>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
};

export default VideoChat;
