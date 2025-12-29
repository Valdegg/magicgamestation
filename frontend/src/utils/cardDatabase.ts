/**
 * Card Database Utilities
 * 
 * Provides functions for loading card metadata and normalizing card IDs.
 */

export interface CardMetadata {
  id: string;
  name: string;
  set: string;
  image: string;
  type: string;
  mana_cost?: string;
  cmc?: number;
  oracle_text?: string;
  power?: string;
  toughness?: string;
  colors?: string[];
}

export interface CardDatabase {
  [key: string]: CardMetadata;
}

/**
 * Normalize a card name and set code to create a consistent card ID.
 * 
 * Rules:
 * - Convert to lowercase
 * - Replace spaces with underscores
 * - Remove special characters (except underscores)
 * - Append set code
 * 
 * @param name - Card name (e.g., "Lightning Bolt")
 * @param set - Set code (e.g., "A25")
 * @returns Normalized ID (e.g., "lightning_bolt_A25")
 */
export function normalizeCardId(name: string, set: string): string {
  const normalized = name
    .toLowerCase()
    .replace(/[',]/g, '') // Remove apostrophes and commas
    .replace(/[^a-z0-9]/g, '_') // Replace non-alphanumeric with underscore
    .replace(/_+/g, '_') // Collapse multiple underscores
    .replace(/^_|_$/g, ''); // Trim leading/trailing underscores
  
  return `${normalized}_${set}`;
}

/**
 * Convert card name to filename format (with underscores).
 * Preserves capitalization to match actual image filenames.
 * 
 * @param name - Card name
 * @returns Filename-safe name (e.g., "Lightning_Bolt")
 */
export function normalizeCardName(name: string): string {
  // Simple normalization: lowercase, underscores, remove special chars
  // No set codes or suffixes
  const normalized = name
    .replace(/[',]/g, '') // Remove apostrophes and commas  
    .replace(/[^a-zA-Z0-9]/g, '_') // Replace non-alphanumeric with underscore
    .replace(/_+/g, '_') // Collapse multiple underscores
    .replace(/^_|_$/g, ''); // Trim leading/trailing underscores
  
  return normalized;
}

/**
 * Get all possible image paths for a card, in order of preference.
 * 
 * This allows fallback when images don't have set codes in filenames.
 * 
 * @param cardName - Card name
 * @param setCode - Set code (optional)
 * @returns Array of possible image paths to try
 */
export function getCardImagePaths(cardName: string, _setCode?: string): string[] {
  // Strip _UNK or other set code suffixes from the card name if present
  // This handles cases where card IDs like "wild_mongrel_UNK" are passed
  let cleanName = cardName;
  const setCodeMatch = cardName.match(/^(.+)_([A-Z0-9]{2,4})$/i);
  if (setCodeMatch) {
    const suffix = setCodeMatch[2].toUpperCase();
    // If it's a set code suffix (UNK or 2-4 letter code), strip it
    if (suffix === 'UNK' || /^[A-Z0-9]{2,4}$/.test(suffix)) {
      cleanName = setCodeMatch[1];
    }
  }
  
  // Create lowercase filename: card_name.jpg
  const filename = cleanName
    .toLowerCase()
    .replace(/[',]/g, '')
    .replace(/[^a-z0-9]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '');
    
  const paths: string[] = [];
  
  // All images are lowercase
  paths.push(`/card_images/${filename}.jpg`);
  
  // Fallback
  paths.push('/cards/card-back.jpg');
  
  return paths;
}

/**
 * Load card database from JSON file.
 * 
 * @returns Promise with card database
 */
export async function loadCardDatabase(): Promise<CardDatabase> {
  try {
    // Add timestamp to prevent caching
    const response = await fetch(`/data/cards.json?t=${Date.now()}`);
    if (!response.ok) {
      throw new Error(`Failed to load cards.json: ${response.statusText}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error loading card database:', error);
    return {};
  }
}

/**
 * Get card metadata by ID.
 * Tries multiple lookup strategies:
 * 1. Exact match
 * 2. Strip _UNK suffix and try base name
 * 3. Strip any set code suffix (_XXX) and try base name
 * 
 * @param database - Card database
 * @param cardId - Card ID (e.g., "lightning_bolt_A25" or "lightning_bolt_UNK")
 * @returns Card metadata or null if not found
 */
export function getCardMetadata(
  database: CardDatabase,
  cardId: string
): CardMetadata | null {
  // 1. Try exact match first
  if (database[cardId]) {
    return database[cardId];
  }
  
  // 2. If ID ends with _UNK, strip it and try base name
  if (cardId.endsWith('_UNK')) {
    const baseName = cardId.slice(0, -4); // Remove '_UNK'
    if (database[baseName]) {
      return database[baseName];
    }
  }
  
  // 3. Strip any set code suffix (e.g., _A25, _UNK, _ODY) and try base name
  // Set codes are typically 2-4 uppercase letters/numbers at the end
  const setCodeMatch = cardId.match(/^(.+)_([A-Z0-9]{2,4})$/i);
  if (setCodeMatch) {
    const baseName = setCodeMatch[1];
    if (database[baseName]) {
      return database[baseName];
    }
  }
  
  return null;
}

/**
 * Search cards by name (case-insensitive).
 * 
 * @param database - Card database
 * @param searchTerm - Search term
 * @returns Array of matching cards
 */
export function searchCardsByName(
  database: CardDatabase,
  searchTerm: string
): CardMetadata[] {
  const term = searchTerm.toLowerCase();
  return Object.values(database).filter(card =>
    card.name.toLowerCase().includes(term)
  );
}

/**
 * Get all unique card names (ignoring sets).
 * 
 * @param database - Card database
 * @returns Array of unique card names
 */
export function getUniqueCardNames(database: CardDatabase): string[] {
  const names = new Set<string>();
  Object.values(database).forEach(card => names.add(card.name));
  return Array.from(names).sort();
}

/**
 * Get all cards of a specific type.
 * 
 * @param database - Card database
 * @param type - Card type (e.g., "Creature", "Instant")
 * @returns Array of matching cards
 */
export function getCardsByType(
  database: CardDatabase,
  type: string
): CardMetadata[] {
  return Object.values(database).filter(card =>
    card.type.includes(type)
  );
}

/**
 * Create a fallback image path for missing cards.
 * 
 * @param cardName - Card name
 * @returns Fallback image path
 */
export function getFallbackImage(): string {
  return '/card_images/card-back.jpg';
}
