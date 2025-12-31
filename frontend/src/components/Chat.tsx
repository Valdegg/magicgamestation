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
  const hasInitializedRef = useRef(false);
  const { sendChatMessage, playerId, chatMessages } = useGameState();

  // Initialize lastReadOpponentMessageCount - start at 0, will be set when messages load
  const [lastReadOpponentMessageCount, setLastReadOpponentMessageCount] = useState(0);

  // Sync persisted messages from context - this is the source of truth
  useEffect(() => {
    if (chatMessages && playerId) {
      console.log('💬 Chat component: syncing', chatMessages.length, 'messages from context');
      const newMessages = [...chatMessages];
      const opponentCount = newMessages.filter(msg => msg.playerId !== playerId).length;
      
      console.log('💬 Chat: Current opponent message count:', opponentCount);
      console.log('💬 Chat: Last read count (state):', lastReadOpponentMessageCount);
      console.log('💬 Chat: Has initialized:', hasInitializedRef.current);
      
      setMessages(newMessages);
      
      // On initial load (first time messages sync after page load/refresh), 
      // mark ALL existing messages as read to prevent glow on refresh
      if (!hasInitializedRef.current) {
        console.log('💬 Chat: First initialization after page load - marking all', opponentCount, 'existing messages as read');
        console.log('💬 Chat: This prevents glow on refresh - only NEW messages after this will glow');
        setLastReadOpponentMessageCount(opponentCount);
        localStorage.setItem('chat_last_read_count', opponentCount.toString());
        hasInitializedRef.current = true;
      }
      // After initialization, lastReadCount only updates when:
      // 1. User opens chat (handleToggleChat)
      // 2. Chat is open and new messages arrive (useEffect below)
    } else {
      console.log('💬 Chat component: no messages in context or no playerId');
    }
  }, [chatMessages, playerId]); // Removed lastReadOpponentMessageCount from deps to avoid loops

  // Calculate unread count (only messages from other players)
  const currentOpponentMessageCount = messages.filter(msg => msg.playerId !== playerId).length;
  const unreadCount = Math.max(0, currentOpponentMessageCount - lastReadOpponentMessageCount);
  
  console.log('💬 Chat: Render - currentOpponentCount:', currentOpponentMessageCount, 'lastRead:', lastReadOpponentMessageCount, 'unreadCount:', unreadCount, 'willGlow:', unreadCount > 0 && !isExpanded);

  // If chat is open and new messages arrive, mark them as read automatically
  useEffect(() => {
    if (isExpanded && currentOpponentMessageCount > lastReadOpponentMessageCount) {
      console.log('💬 Chat: Chat is open, marking', currentOpponentMessageCount, 'messages as read');
      setLastReadOpponentMessageCount(currentOpponentMessageCount);
      localStorage.setItem('chat_last_read_count', currentOpponentMessageCount.toString());
    }
  }, [isExpanded, currentOpponentMessageCount, lastReadOpponentMessageCount]);

  // When chat is opened, mark all messages as read
  const handleToggleChat = () => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    if (newExpanded) {
      console.log('💬 Chat: Opening chat, marking all', currentOpponentMessageCount, 'messages as read');
      setLastReadOpponentMessageCount(currentOpponentMessageCount);
      localStorage.setItem('chat_last_read_count', currentOpponentMessageCount.toString());
    }
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Scroll to bottom when chat is opened
  useEffect(() => {
    if (isExpanded) {
      // Small delay to ensure the chat panel is rendered
      setTimeout(() => {
        scrollToBottom();
      }, 100);
    }
  }, [isExpanded]);

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
    <div className="fixed bottom-4 right-4 z-[150]">
      {/* Chat Toggle Button */}
      <button
        onClick={handleToggleChat}
        className="bg-fantasy-brown border-2 border-fantasy-gold text-fantasy-gold px-4 py-2 rounded-lg shadow-lg hover:bg-fantasy-brown/80 transition-all"
        style={{
          animation: unreadCount > 0 && !isExpanded ? 'blink 1s ease-in-out infinite' : undefined,
          boxShadow: unreadCount > 0 && !isExpanded 
            ? '0 0 10px rgba(244, 213, 137, 0.8), 0 0 20px rgba(244, 213, 137, 0.4)' 
            : undefined
        }}
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
