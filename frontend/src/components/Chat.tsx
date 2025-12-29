import React, { useState, useRef, useEffect } from 'react';
import { useGameState } from '../context/GameStateWebSocket';

interface ChatMessage {
  playerId: string;
  playerName: string;
  message: string;
  timestamp: string;
}

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { sendChatMessage, playerId, chatMessages } = useGameState();

  // Sync persisted messages from context - this is the source of truth
  useEffect(() => {
    if (chatMessages) {
      console.log('💬 Chat component: syncing', chatMessages.length, 'messages from context');
      setMessages([...chatMessages]);
    } else {
      console.log('💬 Chat component: no messages in context');
    }
  }, [chatMessages]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();

    const message = newMessage.trim();
    if (!message) return;

    // Validate message length
    if (message.length > 500) {
      alert('Message too long! Maximum 500 characters.');
      return;
    }

    sendChatMessage(message);
    setNewMessage('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSendMessage(e);
    }
  };

  // Listen for new real-time messages via custom event
  React.useEffect(() => {
    const handleChatMessage = (event: CustomEvent<ChatMessage>) => {
      const newMsg = event.detail;
      // Only add if not already in messages (avoid duplicates from context sync)
      setMessages(prev => {
        const exists = prev.some(m => 
          m.playerId === newMsg.playerId && 
          m.message === newMsg.message && 
          m.timestamp === newMsg.timestamp
        );
        if (exists) return prev;
        return [...prev, newMsg];
      });
    };

    window.addEventListener('chatMessage', handleChatMessage as EventListener);

    return () => {
      window.removeEventListener('chatMessage', handleChatMessage as EventListener);
    };
  }, []);

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Chat Toggle Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="bg-fantasy-brown border-2 border-fantasy-gold text-fantasy-gold px-4 py-2 rounded-lg shadow-lg hover:bg-fantasy-brown/80 transition-colors"
      >
        💬 Chat ({messages.length})
      </button>

      {/* Chat Panel */}
      {isExpanded && (
        <div className="absolute bottom-12 right-0 w-80 h-96 bg-fantasy-dark bg-opacity-95 border-2 border-fantasy-gold rounded-lg shadow-2xl flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-3 border-b border-fantasy-gold/50">
            <h3 className="text-fantasy-gold font-bold">Game Chat</h3>
            <button
              onClick={() => setIsExpanded(false)}
              className="text-fantasy-gold hover:text-white text-xl"
            >
              ×
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {messages.length === 0 ? (
              <div className="text-fantasy-gold/60 text-center italic">
                No messages yet. Start the conversation!
              </div>
            ) : (
              messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex flex-col ${
                    msg.playerId === playerId ? 'items-end' : 'items-start'
                  }`}
                >
                  <div className="text-xs text-fantasy-gold/70 mb-1">
                    {msg.playerName}
                  </div>
                  <div
                    className={`max-w-xs px-3 py-2 rounded-lg text-sm ${
                      msg.playerId === playerId
                        ? 'bg-fantasy-gold text-fantasy-dark'
                        : 'bg-fantasy-brown text-fantasy-gold'
                    }`}
                  >
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
                placeholder="Type a message..."
                className="flex-1 bg-fantasy-brown border border-fantasy-gold/50 rounded px-3 py-2 text-fantasy-gold placeholder-fantasy-gold/50 focus:outline-none focus:border-fantasy-gold"
                maxLength={500}
              />
              <button
                type="submit"
                disabled={!newMessage.trim()}
                className="bg-fantasy-gold text-fantasy-dark px-4 py-2 rounded hover:bg-fantasy-gold/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Send
              </button>
            </div>
            <div className="text-xs text-fantasy-gold/50 mt-1">
              Press Enter to send • Max 500 characters
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
