import React, { createContext, useContext, useState, useEffect, ReactNode, useRef } from 'react';
import { CardData, GameState, ZoneType } from '../types';
import { BackendGameState, BackendPlayer, BackendCard, BackendChatMessage } from '../types/backend';
import { gameApi } from '../api/gameApi';

interface OpponentData {
  id: string;
  name: string;
  life: number;
  handCount: number;
  libraryCount: number;
  battlefieldCards: CardData[];
  graveyardCards: CardData[];
  exileCards: CardData[];
}

interface GameStateContextType extends GameState {
  gameId: string | null;
  playerId: string | null;
  currentPhase: string;
  turnNumber: number;
  isConnected: boolean;
  activePlayerId: string | null;
  opponent: OpponentData | null;
  drawCard: (count?: number) => void;
  moveCard: (cardId: string, toZone: ZoneType, x?: number, y?: number) => void;
  tapCard: (cardId: string) => void;
  untapAll: () => void;
  changeLife: (delta: number) => void;
  shuffleLibrary: () => void;
  mulligan: () => void;
  updateCardPosition: (cardId: string, x: number, y: number) => void;
  toggleFaceDown: (cardId: string) => void;
  loadDeckByName: (deckName: string) => void;
  initializeGame: () => Promise<void>;
  nextPhase: () => void;
  setPhase: (phase: string) => void;
  nextTurn: () => void;
  copyShareUrl: () => void;
  reorderHand: (cardId: string, newIndex: number) => void;
  attachCard: (cardId: string, targetCardId: string) => void;
  unattachCard: (cardId: string) => void;
  addCounter: (cardId: string, counterType: string, delta: number) => void;
  createToken: (name: string, power: string, toughness: string) => void;
  sendChatMessage: (message: string) => void;
  createDie: (x: number, y: number, dieType?: string) => void;
  moveDie: (dieId: string, x: number, y: number) => void;
  removeDie: (dieId: string) => void;
  diceTokens: Array<{
    id: string;
    x: number;
    y: number;
    value: number | null;
    ownerPlayerId: string;
    dieType: string;
    lastRolledAt?: number | null;
  }>;
  targetingArrows: Array<{
    cardId: string;
    targetCardId?: string;
    targetPlayerId?: string;
    ownerPlayerId: string;
  }>;
  setTargetingArrow: (cardId: string, targetCardId?: string, targetPlayerId?: string) => void;
  clearTargetingArrows: () => void;
  chatMessages: BackendChatMessage[];
}

const GameStateContext = createContext<GameStateContextType | undefined>(undefined);

export const GameStateProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [gameId, setGameId] = useState<string | null>(null);
  const [playerId, setPlayerId] = useState<string | null>(null);
  const [player, setPlayer] = useState({
    id: 'player-1',
    name: 'Player',
    life: 20,
  });
  const [cards, setCards] = useState<CardData[]>([]);
  const [libraryCount, setLibraryCount] = useState(0);
  const [currentPhase, setCurrentPhase] = useState<string>('untap');
  const [turnNumber, setTurnNumber] = useState<number>(1);
  const [isConnected, setIsConnected] = useState(false);
  const [activePlayerId, setActivePlayerId] = useState<string | null>(null);
  const [opponent, setOpponent] = useState<OpponentData | null>(null);
  const [targetingArrows, setTargetingArrows] = useState<Array<{
    cardId: string;
    targetCardId?: string;
    targetPlayerId?: string;
    ownerPlayerId: string;
  }>>([]);
  const [diceTokens, setDiceTokens] = useState<Array<{
    id: string;
    x: number;
    y: number;
    value: number | null;
    ownerPlayerId: string;
    dieType: string;
    lastRolledAt?: number | null;
  }>>([]);
  const [chatMessages, setChatMessages] = useState<BackendChatMessage[]>([]);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pendingActionsRef = useRef<Array<{ action: string; data: any }>>([]);

  // Initialize game on mount
  useEffect(() => {
    initializeGame();
    
    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  // Connect to WebSocket when gameId and playerId are available
  useEffect(() => {
    if (gameId && playerId) {
      connectWebSocket(gameId, playerId);
    }
  }, [gameId, playerId]);

  const connectWebSocket = (gId: string, pId: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    // @ts-ignore - Vite provides import.meta.env
    const baseUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:9000';
    const wsUrl = `${baseUrl}/ws/${gId}/${pId}`;
    console.log('🔌 Connecting to WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('✅ WebSocket connected');
      setIsConnected(true);
      
      // Send any pending actions that were queued before connection
      const pending = pendingActionsRef.current;
      if (pending.length > 0) {
        console.log(`📤 WebSocket connected! Sending ${pending.length} queued action(s):`, pending.map(p => p.action));
        pending.forEach(({ action, data }) => {
          ws.send(JSON.stringify({ action, data }));
        });
        pendingActionsRef.current = [];
      }
    };
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.type === 'game_state_update') {
          console.log('📨 Received game state update');
          syncStateFromBackend(message.state);
        } else if (message.type === 'chat_message') {
          console.log('💬 Received chat message:', message);
          // Dispatch custom event for chat component
          window.dispatchEvent(new CustomEvent('chatMessage', { detail: message }));
        } else if (message.type === 'error') {
          console.error('❌ WebSocket error:', message.message);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
    
    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
    };
    
    ws.onclose = () => {
      console.log('🔌 WebSocket disconnected');
      setIsConnected(false);
      
      // Attempt to reconnect after 3 seconds
      reconnectTimeoutRef.current = window.setTimeout(() => {
        console.log('🔄 Attempting to reconnect...');
        connectWebSocket(gId, pId);
      }, 3000);
    };
    
    wsRef.current = ws;
  };

  const sendAction = (action: string, data: any = {}) => {
    // Check if we're in a game
    if (!gameId || !playerId) {
      console.warn('⚠️ Not in a game yet. Please join or create a game first.');
      return;
    }
    
    // If WebSocket is open, send immediately
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log(`📤 Sending action: ${action}`, data);
      wsRef.current.send(JSON.stringify({ action, data }));
      return;
    }
    
    // If WebSocket is connecting or closed, queue the action
    // It will be sent automatically when the connection opens
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      const state = wsRef.current?.readyState;
      const stateName = state === WebSocket.CONNECTING ? 'connecting' : 'not connected';
      console.log(`⏳ WebSocket ${stateName}, queueing action: ${action}`);
      pendingActionsRef.current.push({ action, data });
    }
  };

  const initializeGame = async () => {
    try {
      // Check URL params for game ID and player ID
      const urlParams = new URLSearchParams(window.location.search);
      const urlGameId = urlParams.get('game');
      const urlPlayerId = urlParams.get('player');
      
      // Check localStorage for game ID
      const storedGameId = localStorage.getItem('mtg_game_id');
      const storedPlayerId = localStorage.getItem('mtg_player_id');
      
      // Only restore if URL specifically requests a game
      // This prevents auto-redirecting from root (Lobby) to a previous game
      const existingGameId = urlGameId;
      const existingPlayerId = urlPlayerId || (storedGameId === urlGameId ? storedPlayerId : null);
      
      if (existingGameId && existingPlayerId) {
        console.log('🔄 Restoring existing game:', existingGameId, 'player:', existingPlayerId);
        try {
          // Try to fetch existing game state
          const result = await gameApi.getGameState(existingGameId);
          if (result.success && result.state) {
            // Verify player exists in game
            if (result.state.players[existingPlayerId]) {
              setGameId(existingGameId);
              setPlayerId(existingPlayerId);
              syncStateFromBackend(result.state);
              
              // Update URL and localStorage
              const newUrl = new URL(window.location.href);
              newUrl.searchParams.set('game', existingGameId);
              newUrl.searchParams.set('player', existingPlayerId);
              window.history.replaceState({}, '', newUrl.toString());
              localStorage.setItem('mtg_game_id', existingGameId);
              localStorage.setItem('mtg_player_id', existingPlayerId);
              
              console.log('✅ Game restored successfully');
              return;
            }
          } else {
            console.warn('⚠️ Game not found or invalid state');
            // Clear URL and storage if game not found
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.delete('game');
            newUrl.searchParams.delete('player');
            window.history.replaceState({}, '', newUrl.toString());
            localStorage.removeItem('mtg_game_id');
            localStorage.removeItem('mtg_player_id');
          }
        } catch (error) {
          console.warn('⚠️ Failed to restore game:', error);
          // Clear URL and storage on 404
          if ((error as any)?.response?.status === 404 || (error as any)?.message?.includes('404')) {
        const newUrl = new URL(window.location.href);
             newUrl.searchParams.delete('game');
             newUrl.searchParams.delete('player');
        window.history.replaceState({}, '', newUrl.toString());
             localStorage.removeItem('mtg_game_id');
             localStorage.removeItem('mtg_player_id');
          }
        }
      }
      
      console.log('ℹ️ No active game found, waiting for user to join/create via Lobby');
    } catch (error) {
      console.error('Failed to initialize game:', error);
    }
  };

  const syncStateFromBackend = (backendState: BackendGameState) => {
    // Extract active player ID
    if (backendState.active_player_id) {
      setActivePlayerId(backendState.active_player_id);
    }

    // Extract my player info (the one controlled by this client)
    if (playerId && backendState.players[playerId]) {
      const playerData: BackendPlayer = backendState.players[playerId];
      
      setPlayer({
        id: playerId,
        name: playerData.name,
        life: playerData.life_total,
      });

      // Convert backend zones to frontend cards (only for this player)
      const allCards: CardData[] = [];
      
      for (const [zoneName, zoneData] of Object.entries(playerData.zones)) {
        const zone = zoneName as ZoneType;
        
        for (const backendCard of zoneData.cards) {
          const card: CardData = {
            id: backendCard.id,
            cardId: backendCard.data?.card_id,
            name: backendCard.name,
            tapped: backendCard.tapped,
            faceDown: backendCard.face_down,
            attachedToId: backendCard.attached_to_id,
            zone: zone,
            x: backendCard.data?.x,
            y: backendCard.data?.y,
            data: backendCard.data,
          };
          
          allCards.push(card);
        }
      }
      
      setCards(allCards);
      setLibraryCount(playerData.zones.library?.cards.length || 0);
    }

    // Extract opponent info
    if (playerId && backendState.players) {
      const opponentId = Object.keys(backendState.players).find(id => id !== playerId);
      
      if (opponentId) {
        const opponentData: BackendPlayer = backendState.players[opponentId];
        
        // Helper to convert cards
        const convertOpponentCards = (cards: BackendCard[], zone: ZoneType): CardData[] => {
          return cards.map(c => ({
            id: c.id,
            cardId: c.data?.card_id,
            name: c.name,
            tapped: c.tapped,
            faceDown: c.face_down,
            attachedToId: c.attached_to_id,
            zone: zone,
            x: c.data?.x,
            y: c.data?.y,
            data: c.data,
          }));
        };
        
        setOpponent({
          id: opponentId,
          name: opponentData.name,
          life: opponentData.life_total,
          handCount: opponentData.zones.hand?.cards.length || 0,
          libraryCount: opponentData.zones.library?.cards.length || 0,
          battlefieldCards: convertOpponentCards(opponentData.zones.battlefield?.cards || [], 'battlefield'),
          graveyardCards: convertOpponentCards(opponentData.zones.graveyard?.cards || [], 'graveyard'),
          exileCards: convertOpponentCards(opponentData.zones.exile?.cards || [], 'exile'),
        });
      } else {
        // No opponent found - clear opponent state (e.g., if opponent left)
        setOpponent(null);
      }
    }

    // Update dice tokens
    if (backendState.dice_tokens) {
      setDiceTokens(backendState.dice_tokens);
    }

    // Update targeting arrows
    if (backendState.targeting_arrows) {
      console.log('🎯 Received targeting arrows:', backendState.targeting_arrows);
      setTargetingArrows(backendState.targeting_arrows);
    }

    // Extract phase and turn
    if (backendState.current_phase) {
      setCurrentPhase(backendState.current_phase);
    }

    if (backendState.turn_number !== undefined) {
      setTurnNumber(backendState.turn_number);
    }

    // Update chat messages (persisted history)
    if (backendState.chat_messages) {
      console.log('💬 Received chat messages from backend:', backendState.chat_messages.length, 'messages');
      setChatMessages(backendState.chat_messages);
    } else {
      console.log('💬 No chat messages in backend state');
    }
  };

  // Action functions using WebSocket
  const loadDeckByName = async (deckName: string) => {
    console.log(`📂 loadDeckByName called with deckName: ${deckName}`);
    
    // Get gameId and playerId from state, URL, or localStorage (in that order of preference)
    // This handles cases where state hasn't updated yet
    let currentGameId = gameId;
    let currentPlayerId = playerId;
    
    if (!currentGameId || !currentPlayerId) {
      const urlParams = new URLSearchParams(window.location.search);
      currentGameId = currentGameId || urlParams.get('game') || localStorage.getItem('mtg_game_id');
      currentPlayerId = currentPlayerId || urlParams.get('player') || localStorage.getItem('mtg_player_id');
    }
    
    console.log(`📂 Current gameId: ${currentGameId}, playerId: ${currentPlayerId}`);
    
    if (!currentGameId) {
      console.error('⚠️ Cannot load deck: not in a game');
      throw new Error('Not in a game. Please join or create a game first.');
    }
    
    if (!currentPlayerId) {
      console.error('⚠️ Cannot load deck: player ID not found');
      throw new Error('Player ID not found. Please join or create a game first.');
    }
    
    // Use REST API instead of WebSocket - simpler and doesn't need connection
    console.log(`📂 Calling gameApi.loadDeck(${currentGameId}, ${deckName}, ${currentPlayerId})`);
    try {
      const response = await gameApi.loadDeck(currentGameId, deckName, currentPlayerId);
      console.log(`📂 API response received:`, response);
      if (response.success) {
        console.log(`✅ Deck loaded: ${deckName}`);
        // The WebSocket will receive a game state update automatically
      } else {
        console.error('❌ Failed to load deck:', response.error);
        throw new Error(response.error || 'Failed to load deck');
      }
    } catch (error) {
      console.error('❌ Error loading deck:', error);
      if (error instanceof Error) {
        console.error('❌ Error details:', error.message, error.stack);
      }
      throw error;
    }
  };

  const drawCard = (count: number = 1) => {
    sendAction('draw', { count });
  };

  const moveCard = (cardId: string, toZone: ZoneType, x?: number, y?: number) => {
    const data: any = { cardId, toZone };
    if (x !== undefined) data.x = x;
    if (y !== undefined) data.y = y;
    sendAction('move_card', data);
  };

  const tapCard = (cardId: string) => {
    sendAction('tap_card', { cardId });
  };

  const untapAll = () => {
    sendAction('untap_all');
  };

  const toggleFaceDown = (cardId: string) => {
    sendAction('toggle_face', { cardId });
  };

  const changeLife = (delta: number) => {
    sendAction('change_life', { delta });
  };

  const shuffleLibrary = () => {
    sendAction('shuffle');
  };

  const mulligan = () => {
    sendAction('mulligan');
  };

  const nextPhase = () => {
    sendAction('next_phase');
  };

  const setPhase = (phase: string) => {
    sendAction('set_phase', { phase });
  };

  const nextTurn = () => {
    sendAction('next_turn');
  };

  const updateCardPosition = (cardId: string, x: number, y: number) => {
    // Just update position via move_card
    sendAction('move_card', { cardId, toZone: 'battlefield', x, y });
  };

  const copyShareUrl = () => {
    if (!gameId || !playerId) {
      console.error('No game or player ID available');
      return;
    }
    
    // Find opponent ID
    const opponentId = opponent?.id;
    if (!opponentId) {
      console.error('No opponent found');
      return;
    }
    
    const shareUrl = `${window.location.origin}?game=${gameId}&player=${opponentId}`;
    navigator.clipboard.writeText(shareUrl).then(() => {
      console.log('✅ Share URL copied to clipboard!');
      alert('Opponent URL copied to clipboard!');
    }).catch(err => {
      console.error('Failed to copy URL:', err);
    });
  };

  const reorderHand = (cardId: string, newIndex: number) => {
    sendAction('reorder_hand', { cardId, newIndex });
  };

  const attachCard = (cardId: string, targetCardId: string) => {
    sendAction('attach_card', { cardId, targetCardId });
  };

  const unattachCard = (cardId: string) => {
    sendAction('unattach_card', { cardId });
  };

  const addCounter = (cardId: string, counterType: string, delta: number) => {
    sendAction('add_counter', { cardId, counterType, delta });
  };

  const createToken = (name: string, power: string, toughness: string) => {
    sendAction('create_token', { name, power, toughness });
  };

  const sendChatMessage = (message: string) => {
    sendAction('chat', { message });
  };

  const createDie = (x: number, y: number, dieType: string = 'd20') => {
    sendAction('create_die', { x, y, dieType });
  };

  const moveDie = (dieId: string, x: number, y: number) => {
    sendAction('move_die', { dieId, x, y });
  };

  const removeDie = (dieId: string) => {
    sendAction('remove_die', { dieId });
  };

  const setTargetingArrow = (cardId: string, targetCardId?: string, targetPlayerId?: string) => {
    sendAction('set_targeting_arrow', { cardId, targetCardId, targetPlayerId });
  };

  const clearTargetingArrows = () => {
    sendAction('clear_targeting_arrows', {});
  };

  const value: GameStateContextType = {
    player,
    cards,
    libraryCount,
    gameId,
    playerId,
    currentPhase,
    turnNumber,
    isConnected,
    activePlayerId,
    opponent,
    drawCard,
    moveCard,
    tapCard,
    untapAll,
    changeLife,
    shuffleLibrary,
    mulligan,
    updateCardPosition,
    toggleFaceDown,
    loadDeckByName,
    initializeGame,
    nextPhase,
    setPhase,
    nextTurn,
    copyShareUrl,
    reorderHand,
    attachCard,
    unattachCard,
    addCounter,
    createToken,
    sendChatMessage,
    createDie,
    moveDie,
    removeDie,
    diceTokens,
    targetingArrows,
    setTargetingArrow,
    clearTargetingArrows,
    chatMessages,
  };

  return (
    <GameStateContext.Provider value={value}>
      {children}
    </GameStateContext.Provider>
  );
};

export const useGameState = () => {
  const context = useContext(GameStateContext);
  if (!context) {
    throw new Error('useGameState must be used within GameStateProvider');
  }
  return context;
};

