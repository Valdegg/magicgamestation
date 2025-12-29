import React, { useState, useRef, useEffect } from 'react';

interface LobbyChatMessage {
  playerName: string;
  message: string;
  timestamp: string;
}

interface LobbyChatProps {
  userName: string;
}

export const LobbyChat: React.FC<LobbyChatProps> = ({ userName }) => {
  const [messages, setMessages] = useState<LobbyChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isExpanded, setIsExpanded] = useState(true); // Expanded by default in lobby
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // WebSocket connection for lobby chat
  useEffect(() => {
    let reconnectTimeout: NodeJS.Timeout | null = null;
    let isMounted = true;
    
    const connect = () => {
      if (!isMounted) return;
      
      // Determine WebSocket URL - handle both http/https and ws/wss
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = import.meta.env.VITE_WS_URL 
        ? import.meta.env.VITE_WS_URL.replace(/^https?:\/\//, '').replace(/^wss?:\/\//, '')
        : window.location.host;
      const wsUrl = `${protocol}//${host}/ws/lobby`;
      
      console.log('🔌 Connecting to lobby WebSocket:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('✅ Lobby WebSocket connected');
        if (isMounted) {
          setIsConnected(true);
        }
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout);
          reconnectTimeout = null;
        }
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'lobby_chat_history') {
            // Load existing messages
            if (isMounted) {
              setMessages(data.messages || []);
            }
          } else if (data.type === 'lobby_chat_message') {
            // Add new message
            if (isMounted) {
              setMessages(prev => [...prev, {
                playerName: data.playerName,
                message: data.message,
                timestamp: data.timestamp
              }]);
            }
          } else if (data.type === 'ping') {
            // Respond to keepalive ping
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'pong' }));
            }
          }
        } catch (error) {
          console.error('Failed to parse lobby WebSocket message:', error);
        }
      };
      
      ws.onerror = (error) => {
        console.error('❌ Lobby WebSocket error:', error);
        if (isMounted) {
          setIsConnected(false);
        }
      };
      
      ws.onclose = (event) => {
        console.log('🔌 Lobby WebSocket disconnected', event.code, event.reason);
        if (isMounted) {
          setIsConnected(false);
        }
        
        // Attempt to reconnect after 3 seconds if component is still mounted
        if (isMounted && event.code !== 1000) { // Don't reconnect on normal close
          reconnectTimeout = setTimeout(() => {
            if (isMounted) {
              console.log('🔄 Attempting to reconnect lobby WebSocket...');
              connect();
            }
          }, 3000);
        }
      };
      
      wsRef.current = ws;
    };
    
    connect();
    
    return () => {
      isMounted = false;
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, []);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();

    const message = newMessage.trim();
    if (!message) return;

    // Validate message length
    if (message.length > 500) {
      alert('Message too long! Maximum 500 characters.');
      return;
    }

    if (!userName.trim()) {
      alert('Please enter your name before sending a message');
      return;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'lobby_chat',
        data: {
          message: message,
          playerName: userName.trim()
        }
      }));
      setNewMessage('');
    } else {
      alert('Not connected to lobby chat. Please wait...');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSendMessage(e);
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 w-80">
      {/* Chat Panel */}
      <div className="bg-fantasy-dark bg-opacity-95 border-2 border-fantasy-gold rounded-lg shadow-2xl flex flex-col" style={{ maxHeight: '500px' }}>
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-fantasy-gold/50">
          <div className="flex items-center gap-2">
            <h3 className="text-fantasy-gold font-bold">Lobby Chat</h3>
            {isConnected ? (
              <span className="text-xs text-green-400">●</span>
            ) : (
              <span className="text-xs text-red-400">●</span>
            )}
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-fantasy-gold hover:text-white text-xl"
          >
            {isExpanded ? '−' : '+'}
          </button>
        </div>

        {isExpanded && (
          <>
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2" style={{ maxHeight: '300px' }}>
              {messages.length === 0 ? (
                <div className="text-fantasy-gold/60 text-center italic text-sm">
                  No messages yet. Start the conversation!
                </div>
              ) : (
                messages.map((msg, index) => (
                  <div
                    key={index}
                    className="flex flex-col"
                  >
                    <div className="text-xs text-fantasy-gold/70 mb-1">
                      {msg.playerName}
                    </div>
                    <div className="max-w-xs px-3 py-2 rounded-lg text-sm bg-fantasy-brown text-fantasy-gold">
                      {msg.message}
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <form onSubmit={handleSendMessage} className="p-3 border-t border-fantasy-gold/50">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={userName.trim() ? "Type a message..." : "Enter your name first..."}
                  className="flex-1 bg-fantasy-brown border border-fantasy-gold/50 rounded px-3 py-2 text-fantasy-gold placeholder-fantasy-gold/50 focus:outline-none focus:border-fantasy-gold"
                  maxLength={500}
                />
                <button
                  type="submit"
                  disabled={!newMessage.trim() || !userName.trim() || !isConnected}
                  className="bg-fantasy-gold text-fantasy-dark px-4 py-2 rounded hover:bg-fantasy-gold/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Send
                </button>
              </div>
              <div className="text-xs text-fantasy-gold/50 mt-1">
                {!isConnected && <span className="text-red-400">Not connected • </span>}
                {!userName.trim() && <span className="text-yellow-400">Enter your name first • </span>}
                Press Enter to send • Max 500 characters
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

