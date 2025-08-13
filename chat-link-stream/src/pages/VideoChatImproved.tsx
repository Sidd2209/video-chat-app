import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { disconnectChat, sendMessage, startVideoChat } from "@/lib/chatApi";
import socketService from "@/lib/socketService";
import webrtcService from "@/lib/webrtcService";
import { useNavigate } from "react-router-dom";
import { 
  Mic, 
  MicOff, 
  Video, 
  VideoOff, 
  Phone, 
  MessageSquare, 
  User, 
  Flag, 
  Settings,
  Heart,
  Star,
  Clock
} from "lucide-react";

interface ChatMsg {
  id: string;
  from: "You" | "Stranger";
  text: string;
  time: number;
  type?: "text" | "system";
}

interface UserProfile {
  user_id: string;
  interests: string[];
  language: string;
  country?: string;
  age_group?: string;
  gender?: string;
  total_sessions: number;
  connection_quality: string;
}

const VideoChatImproved = () => {
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
  const [partnerProfile, setPartnerProfile] = useState<UserProfile | null>(null);
  const [connectionQuality, setConnectionQuality] = useState<string>("unknown");
  const [sessionDuration, setSessionDuration] = useState<number>(0);
  const [showProfile, setShowProfile] = useState(false);
  const [estimatedWaitTime, setEstimatedWaitTime] = useState<number>(0);

  const localVideoRef = useRef<HTMLVideoElement | null>(null);
  const remoteVideoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const sessionTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    document.title = "Video Chat — Chat with a Stranger";
    
    // Start session timer when matched
    if (isMatched) {
      sessionTimerRef.current = setInterval(() => {
        setSessionDuration(prev => prev + 1);
      }, 1000);
    }

    return () => {
      if (sessionTimerRef.current) {
        clearInterval(sessionTimerRef.current);
      }
    };
  }, [isMatched]);

  const canSend = useMemo(() => !!sessionId && input.trim().length > 0, [sessionId, input]);

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const start = async () => {
    try {
      setConnecting(true);
      
      // Connect to WebSocket first
      console.log('Connecting to WebSocket...');
      await socketService.connect();
      
      // Wait for user_id with timeout
      console.log('Waiting for user_id...');
      const userId = await new Promise<string>((resolve, reject) => {
        const timeout = setTimeout(() => {
          console.error('Timeout waiting for user_id');
          reject(new Error('Timeout waiting for user_id'));
        }, 10000);
        
        const handleUserId = (data: { user_id: string }) => {
          console.log('Received user_id:', data.user_id);
          clearTimeout(timeout);
          socketService.off('user_id', handleUserId);
          setUserId(data.user_id);
          resolve(data.user_id);
        };
        
        socketService.on('user_id', handleUserId);
      });
      
      console.log('Got user_id:', userId);
      
      // Get user media
      const media = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 }
        }, 
        audio: { 
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
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
      const { session_id, status, estimated_wait_time } = response;
      
      if (status === 'matched') {
        setSessionId(session_id);
        setIsMatched(true);
        setWaiting(false);
        toast({ title: "Matched!", description: "You've been connected with a stranger" });
        await setupRealTimeCommunication(session_id, media);
      } else {
        setWaiting(true);
        setEstimatedWaitTime(estimated_wait_time || 0);
        await setupRealTimeCommunication(session_id, media);
        toast({ title: "Connected", description: `Waiting for a partner... (${estimated_wait_time}s)` });
      }
    } catch (e: any) {
      toast({ title: "Camera/Mic error", description: e?.message || "Permission needed" });
    } finally {
      setConnecting(false);
    }
  };

  const setupRealTimeCommunication = async (sessionId: string, media: MediaStream) => {
    try {
      await webrtcService.initialize(sessionId, true);
      await webrtcService.setLocalStream(media);
      
      socketService.joinSession(sessionId);
      
      socketService.on('matched', (data) => {
        if (data.session_id === sessionId || data.session_id === userId) {
          setIsMatched(true);
          setWaiting(false);
          setSessionId(data.session_id);
          setPartnerProfile(data.partner_profile);
          toast({ title: "Matched!", description: "You've been connected with a stranger" });
          webrtcService.createOffer();
        }
      });
      
      socketService.on('new_message', (data) => {
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
        const currentSessionId = sessionId || userId;
        if (data.session_id === currentSessionId) {
          toast({ title: "Partner left", description: "Returning to home" });
          disconnect();
          navigate("/");
        }
      });
      
      // Monitor connection quality
      setInterval(() => {
        if (webrtcService.getConnectionState() === 'connected') {
          const quality = webrtcService.getConnectionQuality();
          setConnectionQuality(quality);
          socketService.emit('connection_quality', { quality });
        }
      }, 5000);
      
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
    } finally {
      setSessionId(null);
      setIsMatched(false);
      setWaiting(false);
      setMessages([]);
      setSessionDuration(0);
      setPartnerProfile(null);
      if (sessionTimerRef.current) {
        clearInterval(sessionTimerRef.current);
      }
    }
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

  const blockUser = async () => {
    if (partnerProfile) {
      try {
        await fetch('/block', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            blocked_user_id: partnerProfile.user_id
          })
        });
        toast({ title: "User blocked", description: "This user has been blocked" });
        disconnect();
      } catch (error) {
        toast({ title: "Error", description: "Failed to block user" });
      }
    }
  };

  const reportUser = async () => {
    if (partnerProfile) {
      const reason = prompt("Please provide a reason for reporting this user:");
      if (reason) {
        try {
          await fetch('/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              reporter_id: userId,
              reported_user_id: partnerProfile.user_id,
              reason: reason
            })
          });
          toast({ title: "User reported", description: "Thank you for your report" });
          disconnect();
        } catch (error) {
          toast({ title: "Error", description: "Failed to report user" });
        }
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 text-white">
      <div className="container mx-auto p-4">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Video Chat</h1>
          <div className="flex items-center gap-4">
            {isMatched && (
              <>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>{formatDuration(sessionDuration)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Star className="w-4 h-4" />
                  <span className="capitalize">{connectionQuality}</span>
                </div>
              </>
            )}
            <Button variant="outline" onClick={() => navigate("/")}>
              Home
            </Button>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Video Section */}
          <div className="lg:col-span-2 space-y-4">
            {/* Remote Video */}
            <div className="relative bg-black rounded-lg overflow-hidden aspect-video">
              <video
                ref={remoteVideoRef}
                className="w-full h-full object-cover"
                autoPlay
                playsInline
              />
              {!isMatched && (
                <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
                    <p className="text-lg">
                      {waiting ? `Waiting for partner... (${estimatedWaitTime}s)` : "Connecting..."}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Local Video */}
            <div className="relative bg-black rounded-lg overflow-hidden w-48 h-32">
              <video
                ref={localVideoRef}
                className="w-full h-full object-cover"
                autoPlay
                playsInline
                muted
              />
            </div>

            {/* Controls */}
            <div className="flex justify-center gap-4">
              <Button
                onClick={toggleAudio}
                variant={isAudioEnabled ? "default" : "destructive"}
                size="lg"
                className="rounded-full w-12 h-12 p-0"
              >
                {isAudioEnabled ? <Mic className="w-6 h-6" /> : <MicOff className="w-6 h-6" />}
              </Button>
              
              <Button
                onClick={toggleVideo}
                variant={isVideoEnabled ? "default" : "destructive"}
                size="lg"
                className="rounded-full w-12 h-12 p-0"
              >
                {isVideoEnabled ? <Video className="w-6 h-6" /> : <VideoOff className="w-6 h-6" />}
              </Button>
              
              <Button
                onClick={disconnect}
                variant="destructive"
                size="lg"
                className="rounded-full w-12 h-12 p-0"
              >
                <Phone className="w-6 h-6" />
              </Button>
            </div>

            {/* Start Button */}
            {!isMatched && !waiting && (
              <div className="text-center">
                <Button
                  onClick={start}
                  disabled={connecting}
                  size="lg"
                  className="bg-green-600 hover:bg-green-700"
                >
                  {connecting ? "Connecting..." : "Start Video Chat"}
                </Button>
              </div>
            )}
          </div>

          {/* Chat Section */}
          <div className="space-y-4">
            {/* Partner Info */}
            {partnerProfile && (
              <div className="bg-white/10 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">Partner Info</h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowProfile(!showProfile)}
                  >
                    <User className="w-4 h-4" />
                  </Button>
                </div>
                
                {showProfile && (
                  <div className="space-y-2 text-sm">
                    <p><strong>Language:</strong> {partnerProfile.language}</p>
                    <p><strong>Country:</strong> {partnerProfile.country || "Unknown"}</p>
                    <p><strong>Sessions:</strong> {partnerProfile.total_sessions}</p>
                    {partnerProfile.interests.length > 0 && (
                      <div>
                        <strong>Interests:</strong>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {partnerProfile.interests.map((interest, index) => (
                            <span key={index} className="bg-blue-600 px-2 py-1 rounded text-xs">
                              {interest}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                <div className="flex gap-2 mt-3">
                  <Button
                    onClick={blockUser}
                    variant="outline"
                    size="sm"
                    className="flex-1"
                  >
                    Block
                  </Button>
                  <Button
                    onClick={reportUser}
                    variant="outline"
                    size="sm"
                    className="flex-1"
                  >
                    <Flag className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}

            {/* Chat Messages */}
            <div className="bg-white/10 rounded-lg p-4 h-96 flex flex-col">
              <h3 className="font-semibold mb-3">Chat</h3>
              
              <div className="flex-1 overflow-y-auto space-y-2 mb-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`p-2 rounded-lg ${
                      msg.from === "You"
                        ? "bg-blue-600 ml-auto max-w-xs"
                        : "bg-gray-600 mr-auto max-w-xs"
                    }`}
                  >
                    <p className="text-sm">{msg.text}</p>
                    <p className="text-xs opacity-70 mt-1">
                      {new Date(msg.time).toLocaleTimeString()}
                    </p>
                  </div>
                ))}
              </div>
              
              {/* Message Input */}
              <div className="flex gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && onSend()}
                  placeholder="Type a message..."
                  className="flex-1"
                  disabled={!isMatched}
                />
                <Button onClick={onSend} disabled={!canSend}>
                  <MessageSquare className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoChatImproved;
