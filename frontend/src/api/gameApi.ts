/**
 * Game API Client
 * 
 * Communicates with the Python backend server.
 * All game state is managed by the backend (card_engine.py).
 */

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
  async loadDeck(gameId: string, deckName: string): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE}/game/${gameId}/load-deck`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ deckName })
    });
    return response.json();
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
  }
};

