/**
 * Deck Loader Utilities
 * 
 * Load and parse deck files for the Magic Gamestation.
 */

export interface DeckList {
  name: string;
  format?: string;
  description?: string;
  main: string[]; // Array of card IDs
  sideboard?: string[];
}

/**
 * Load a deck file from the decks directory.
 * 
 * @param deckName - Name of the deck file (without .json extension)
 * @returns Promise with deck list
 */
export async function loadDeck(deckName: string): Promise<DeckList> {
  try {
    const response = await fetch(`/decks/${deckName}.json`);
    if (!response.ok) {
      throw new Error(`Failed to load deck: ${response.statusText}`);
    }
    const deck = await response.json();
    return deck;
  } catch (error) {
    console.error('Error loading deck:', error);
    throw error;
  }
}

/**
 * Get list of available decks.
 * 
 * @returns Promise with array of deck names
 */
export async function getAvailableDecks(): Promise<string[]> {
  try {
    console.log('📂 Fetching /decks/index.json...');
    const response = await fetch('/decks/index.json');
    console.log('📂 Response status:', response.status, response.statusText);
    if (!response.ok) {
      console.warn('⚠️ Index.json not found or error:', response.status, response.statusText);
      // If index doesn't exist, return empty array
      return [];
    }
    const data = await response.json();
    console.log('📂 Parsed index.json:', data);
    return data.decks || [];
  } catch (error) {
    console.error('❌ Error loading deck index:', error);
    throw error; // Re-throw so the component can handle it
  }
}

/**
 * Parse a deck string in simple text format.
 * Format: "4 Lightning Bolt (A25)"
 * 
 * @param deckText - Deck list as text
 * @returns Array of card IDs
 */
export function parseDeckText(deckText: string): string[] {
  const lines = deckText.split('\n');
  const cardIds: string[] = [];
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('//')) continue; // Skip empty lines and comments
    
    // Match format: "4 Lightning Bolt (A25)" or "4x Lightning Bolt [A25]"
    const match = trimmed.match(/^(\d+)x?\s+(.+?)\s*[\(\[]([A-Z0-9]+)[\)\]]/i);
    if (match) {
      const count = parseInt(match[1], 10);
      const cardName = match[2].trim();
      const setCode = match[3].toUpperCase();
      
      // Normalize to card ID
      const cardId = cardName.toLowerCase().replace(/[',]/g, '').replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '') + '_' + setCode;
      
      // Add card multiple times based on count
      for (let i = 0; i < count; i++) {
        cardIds.push(cardId);
      }
    }
  }
  
  return cardIds;
}

/**
 * Validate a deck list against the card database.
 * 
 * @param deck - Deck list
 * @param cardDatabase - Card database
 * @returns Object with validation results
 */
export function validateDeck(deck: DeckList, cardDatabase: any): {
  valid: boolean;
  missingCards: string[];
  totalCards: number;
} {
  const missingCards: string[] = [];
  const allCards = [...deck.main, ...(deck.sideboard || [])];
  
  for (const cardId of allCards) {
    if (!cardDatabase[cardId]) {
      if (!missingCards.includes(cardId)) {
        missingCards.push(cardId);
      }
    }
  }
  
  return {
    valid: missingCards.length === 0,
    missingCards,
    totalCards: deck.main.length,
  };
}

/**
 * Shuffle an array (Fisher-Yates algorithm).
 * 
 * @param array - Array to shuffle
 * @returns Shuffled array (new array, original unchanged)
 */
export function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

