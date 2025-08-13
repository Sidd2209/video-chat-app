import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { disconnectChat, sendMessage, startChat } from "@/lib/chatApi";
import socketService from "@/lib/socketService";
import { useNavigate } from "react-router-dom";

interface ChatMsg {
  id: string;
  from: "You" | "Stranger";
  text: string;
  time: number;
}

const TextChat = () => {
  const { toast } = useToast();
  const navigate = useNavigate();

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const [isMatched, setIsMatched] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");

  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    document.title = "Text Chat — Chat with a Stranger";
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

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
        await setupTextChat(cachedUserId);
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
          console.log('TextChat received user_id:', userId);
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
      await setupTextChat(userId);
    } catch (e: any) {
      toast({ title: "Start failed", description: e?.message || "" });
    } finally {
      setConnecting(false);
    }
  };

  const setupTextChat = async (userId: string) => {
    try {
      console.log('Got user_id:', userId);
      
      // Then start the chat
      console.log('Making API call to start chat...');
      const response = await startChat(userId);
      console.log('Chat response:', response);
      const { session_id, status } = response;
      
      if (status === 'matched') {
        // Already matched with someone
        setSessionId(session_id);
        setIsMatched(true);
        setWaiting(false);
        toast({ title: "Matched!", description: "You've been connected with a stranger" });
        
        // Set up Socket.IO event handlers
        await setupSocketConnection(session_id);
      } else {
        // Waiting for a partner
        setWaiting(true);
        
        // Set up Socket.IO event handlers
        await setupSocketConnection(session_id);
        
        toast({ title: "Connecting", description: "Waiting for partner..." });
      }
    } catch (e: any) {
      toast({ title: "Start failed", description: e?.message || "" });
    }
  };

  const setupSocketConnection = async (sessionId: string) => {
    try {
      // Join the session room
      socketService.joinSession(sessionId);
      
      // Set up event handlers
      socketService.on('matched', (data) => {
        // Handle both waiting user_id and actual session_id
        if (data.session_id === sessionId || data.session_id === userId) {
          setIsMatched(true);
          setWaiting(false);
          setSessionId(data.session_id);
          toast({ title: "Matched!", description: "You've been connected with a stranger" });
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
      
    } catch (error) {
      console.error('Error setting up socket connection:', error);
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
        socketService.leaveSession(sessionId);
      }
    } catch (error) {
      console.error('Error disconnecting:', error);
    }
    
    setSessionId(null);
    setIsMatched(false);
    setWaiting(false);
    setMessages([]);
  };

  useEffect(() => {
    return () => {
      socketService.disconnect();
    };
  }, []);

  return (
    <main className="min-h-screen bg-background">
      <section className="container py-6 md:py-10">
        <header className="mb-6">
          <h1 className="text-3xl md:text-4xl font-bold">Text Chat</h1>
          <p className="text-muted-foreground">Simple, clean, and instant messaging with a random partner.</p>
        </header>

        <div className="flex flex-wrap gap-3 mb-4">
          <Button onClick={start} disabled={connecting || !!sessionId} size="lg">
            {connecting ? "Starting..." : "Start Chat"}
          </Button>
          <Button onClick={disconnect} variant="destructive" disabled={!sessionId} size="lg">
            Disconnect
          </Button>
        </div>

        {waiting && !isMatched && (
          <div className="mb-3 text-sm text-muted-foreground">Connecting... Waiting for partner...</div>
        )}
        {isMatched && (
          <div className="mb-3 text-sm text-green-600">Connected with a stranger!</div>
        )}

        <article className="rounded-lg border bg-card p-0 overflow-hidden">
          <div className="h-[55vh] md:h-[60vh] overflow-y-auto p-4 space-y-4 bg-secondary">
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
            <div ref={endRef} />
          </div>

          <div className="p-3 border-t bg-card">
            <div className="flex items-center gap-2">
              <Input
                placeholder="Type a message"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") onSend(); }}
                disabled={!sessionId}
              />
              <Button onClick={onSend} disabled={!canSend}>Send</Button>
            </div>
          </div>
        </article>
      </section>
    </main>
  );
};

export default TextChat;
