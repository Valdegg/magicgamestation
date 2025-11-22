import React, { createContext, useContext, useState, useEffect, ReactNode, useRef } from 'react';
import { CardData, GameState, ZoneType } from '../types';
import { BackendGameState, BackendPlayer, BackendCard } from '../types/backend';
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
  updateCardPosition: (cardId: string, x: number, y: number) => void;
  toggleFaceDown: (cardId: string) => void;
  loadDeckByName: (deckName: string) => void;
  initializeGame: () => Promise<void>;
  nextPhase: () => void;
  nextTurn: () => void;
  copyShareUrl: () => void;
  reorderHand: (cardId: string, newIndex: number) => void;
  attachCard: (cardId: string, targetCardId: string) => void;
  unattachCard: (cardId: string) => void;
  addCounter: (cardId: string, counterType: string, delta: number) => void;
  createToken: (name: string, power: string, toughness: string) => void;
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
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

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

    const baseUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:9000';
    const wsUrl = `${baseUrl}/ws/${gId}/${pId}`;
    console.log('🔌 Connecting to WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('✅ WebSocket connected');
      setIsConnected(true);
    };
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.type === 'game_state_update') {
          console.log('📨 Received game state update');
          syncStateFromBackend(message.state);
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
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('⚠️ WebSocket not connected, cannot send action:', action);
      return;
    }
    
    console.log(`📤 Sending action: ${action}`, data);
    wsRef.current.send(JSON.stringify({ action, data }));
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
      }
    }

    // Extract phase and turn
    if (backendState.current_phase) {
      setCurrentPhase(backendState.current_phase);
    }

    if (backendState.turn_number !== undefined) {
      setTurnNumber(backendState.turn_number);
    }
  };

  // Action functions using WebSocket
  const loadDeckByName = (deckName: string) => {
    sendAction('load_deck', { deckName });
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

  const nextPhase = () => {
    sendAction('next_phase');
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
    updateCardPosition,
    toggleFaceDown,
    loadDeckByName,
    initializeGame,
    nextPhase,
    nextTurn,
    copyShareUrl,
    reorderHand,
    attachCard,
    unattachCard,
    addCounter,
    createToken,
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

