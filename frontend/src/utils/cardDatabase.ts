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
export function getCardImagePaths(cardName: string): string[] {
  // Create filename format: Card_Name (Cap words, underscores)
  const filename = cardName
    .replace(/[',]/g, '')
    .replace(/[^a-zA-Z0-9]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '');
    
  const paths: string[] = [];
  
  // 1. Try filename format (Card_Name.jpg)
  paths.push(`/card_images/${filename}.jpg`);
  
  // 2. Try ID format (card_name.jpg) - legacy support
  paths.push(`/card_images/${filename.toLowerCase()}.jpg`);
  
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
 * 
 * @param database - Card database
 * @param cardId - Card ID (e.g., "lightning_bolt_A25")
 * @returns Card metadata or null if not found
 */
export function getCardMetadata(
  database: CardDatabase,
  cardId: string
): CardMetadata | null {
  return database[cardId] || null;
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
