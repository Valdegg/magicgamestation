/**
 * Game API Client
 * 
 * Communicates with the Python backend server.
 * All game state is managed by the backend (card_engine.py).
 */

// @ts-ignore - Vite provides import.meta.env
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:9000/api';

export interface ApiResponse {
  success: boolean;
  state?: any;
  error?: string;
  gameId?: string;
}

export const gameApi = {
  /**
   * Create a new 2-player game.
   */
  async createGame(
    playerName: string = 'Player 1',
    opponentName: string = 'Player 2',
    deckName?: string,
    opponentDeckName?: string,
    startingLife = 20
  ): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playerName, opponentName, deckName, opponentDeckName, startingLife })
    });
    return response.json();
  },

  /**
   * Get current game state.
   */
  async getGameState(gameId: string): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/${gameId}/state`);
    return response.json();
  },

  /**
   * Load a deck for the player.
   */
  async loadDeck(gameId: string, deckName: string, playerId?: string): Promise<ApiResponse> {
    const body: any = { deckName };
    if (playerId) {
      body.playerId = playerId;
    }
    const url = `${API_BASE}/game/${gameId}/load-deck`;
    console.log(`📂 Making POST request to: ${url}`);
    console.log(`📂 Request body:`, body);
    
    try {
      const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
      console.log(`📂 Response status: ${response.status} ${response.statusText}`);
      
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        console.error(`❌ Load deck failed:`, errorData);
      return { success: false, error: errorData.detail || `Failed to load deck: ${response.statusText}` };
    }
      const result = await response.json();
      console.log(`📂 Load deck success:`, result);
      return result;
    } catch (error) {
      console.error(`❌ Fetch error loading deck:`, error);
      throw error;
    }
  },

  /**
   * Draw cards from library.
   */
  async drawCards(gameId: string, count = 1): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/${gameId}/draw`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count })
    });
    return response.json();
  },

  /**
   * Move a card between zones.
   */
  async moveCard(
    gameId: string,
    cardId: string,
    toZone: string,
    toPlayerId?: string,
    x?: number,
    y?: number
  ): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/${gameId}/move-card`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cardId, toZone, toPlayerId, x, y })
    });
    return response.json();
  },

  /**
   * Tap or untap a card.
   */
  async tapCard(gameId: string, cardId: string): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/${gameId}/tap-card`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cardId })
    });
    return response.json();
  },

  /**
   * Untap all cards on the battlefield.
   */
  async untapAll(gameId: string): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/${gameId}/untap-all`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return response.json();
  },

  /**
   * Toggle face-down state.
   */
  async toggleFace(gameId: string, cardId: string): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/${gameId}/toggle-face`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cardId })
    });
    return response.json();
  },

  /**
   * Change player's life total.
   */
  async changeLife(gameId: string, delta: number): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/${gameId}/change-life`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delta })
    });
    return response.json();
  },

  /**
   * Shuffle library.
   */
  async shuffleLibrary(gameId: string): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/${gameId}/shuffle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return response.json();
  },

  /**
   * Advance to next phase.
   */
  async nextPhase(gameId: string): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/${gameId}/next-phase`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return response.json();
  },

  /**
   * Advance to next turn.
   */
  async nextTurn(gameId: string): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/${gameId}/next-turn`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return response.json();
    },

  /**
   * Fetch a card image from Scryfall and download it.
   */
  async fetchCardImage(cardName: string): Promise<{ success: boolean; card?: any; error?: string }> {
    try {
      const response = await fetch(`${API_BASE}/cards/fetch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cardName })
      });
      const data = await response.json();
      if (!response.ok) {
        return { success: false, error: data.detail || 'Failed to fetch card' };
      }
      return { success: true, card: data.card };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  }
};

