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
 * Generate filename variations for a card name.
 * Handles apostrophes, special characters, and common naming variations.
 * 
 * @param name - Card name
 * @returns Array of possible filename variations (without extension)
 */
function generateFilenameVariations(name: string): string[] {
  const variations = new Set<string>();
  const debug = name.toLowerCase().includes('mishra');
  
  if (debug) {
    console.log(`[generateFilenameVariations] Input name: "${name}"`);
    // Log character codes to identify the apostrophe
    const apostropheIndex = name.toLowerCase().indexOf('mishra') + 6;
    if (apostropheIndex < name.length) {
      const apostropheChar = name[apostropheIndex];
      console.log(`[generateFilenameVariations] Apostrophe character code: U+${apostropheChar.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0')}, char: "${apostropheChar}"`);
    }
  }
  
  // Normalize: lowercase first
  const lowerName = name.toLowerCase();
  
  if (debug) {
    console.log(`[generateFilenameVariations] Lowercase: "${lowerName}"`);
  }
  
  // Variation 1: Remove apostrophes (including Unicode curly quotes) and commas, replace non-alphanumeric (except existing underscores) with underscore
  // This handles "mishra's_factory" -> "mishras_factory"
  // Use a comprehensive pattern: match any character that looks like an apostrophe
  // Match common apostrophe characters: U+0027 (') U+2018 (') U+2019 (') U+201A (‚) U+201B (‛) 
  // U+2032 (′) U+2035 (‵) U+0060 (`) U+00B4 (´) and modifier letters
  // Also match Unicode quotation mark ranges: U+2018-U+201F
  const apostrophePattern = /[\u0027\u0060\u00B4\u02BC\u02BB\u02BD\u02BE\u02BF\u2018-\u201F\u2032\u2035\u0301\u0313\u0314\u0315]/g;
  const step1 = lowerName.replace(apostrophePattern, '').replace(/,/g, '');
  const step2 = step1.replace(/[^a-z0-9_]/g, '_');
  const step3 = step2.replace(/_+/g, '_');
  const base = step3.replace(/^_|_$/g, '');
  
  if (debug) {
    console.log(`[generateFilenameVariations] Base variation steps:`, {
      original: lowerName,
      afterRemoveApostrophe: step1,
      afterReplaceNonAlpha: step2,
      afterCollapseUnderscores: step3,
      final: base
    });
  }
  
  if (base.length > 0) {
    variations.add(base);
  }
  
  // Variation 2: Replace apostrophe (including Unicode) with underscore (e.g., "mishra's" -> "mishra_s")
  // This handles "mishra's_factory" -> "mishra_s_factory"
  const withApostropheUnderscoreStep1 = lowerName.replace(apostrophePattern, '_');
  const withApostropheUnderscoreStep2 = withApostropheUnderscoreStep1.replace(/[^a-z0-9_]/g, '_');
  const withApostropheUnderscoreStep3 = withApostropheUnderscoreStep2.replace(/_+/g, '_');
  const withApostropheUnderscore = withApostropheUnderscoreStep3.replace(/^_|_$/g, '');
  
  if (debug) {
    console.log(`[generateFilenameVariations] Apostrophe->Underscore variation steps:`, {
      original: lowerName,
      afterReplaceApostrophe: withApostropheUnderscoreStep1,
      afterReplaceNonAlpha: withApostropheUnderscoreStep2,
      afterCollapseUnderscores: withApostropheUnderscoreStep3,
      final: withApostropheUnderscore
    });
  }
  
  if (withApostropheUnderscore.length > 0 && withApostropheUnderscore !== base) {
    variations.add(withApostropheUnderscore);
  }
  
  // Variation 3: Remove apostrophe but keep the 's' (same as base, but explicit)
  // This is already covered by base, but we ensure it's there
  
  // Variation 4: Handle possessive 's' separately (remove both apostrophe and 's')
  // This handles "mishra's factory" -> "mishra factory" -> "mishra_factory"
  // Handle Unicode apostrophes in possessive form
  const noPossessiveStep1 = lowerName.replace(new RegExp(`[${String.fromCharCode(0x0027, 0x2018, 0x2019, 0x201A, 0x201B, 0x2032, 0x2035, 0x0060, 0x00B4)}]s\\b`, 'g'), '');
  const noPossessiveStep2 = noPossessiveStep1.replace(apostrophePattern, '');
  const noPossessiveStep3 = noPossessiveStep2.replace(/[^a-z0-9_]/g, '_');
  const noPossessiveStep4 = noPossessiveStep3.replace(/_+/g, '_');
  const noPossessive = noPossessiveStep4.replace(/^_|_$/g, '');
  
  if (debug) {
    console.log(`[generateFilenameVariations] No possessive variation steps:`, {
      original: lowerName,
      afterRemovePossessive: noPossessiveStep1,
      afterRemoveApostrophe: noPossessiveStep2,
      afterReplaceNonAlpha: noPossessiveStep3,
      afterCollapseUnderscores: noPossessiveStep4,
      final: noPossessive
    });
  }
  
  if (noPossessive.length > 0 && noPossessive !== base && noPossessive !== withApostropheUnderscore) {
    variations.add(noPossessive);
  }
  
  const result = Array.from(variations);
  
  if (debug) {
    console.log(`[generateFilenameVariations] All variations:`, result);
  }
  
  return result;
}

/**
 * Get all possible image paths for a card, in order of preference.
 * 
 * This allows fallback when images don't have set codes in filenames.
 * Generates multiple filename variations to handle apostrophes and special characters.
 * 
 * @param cardName - Card name
 * @param setCode - Set code (optional)
 * @returns Array of possible image paths to try
 */
export function getCardImagePaths(cardName: string, _setCode?: string): string[] {
  const debug = cardName.toLowerCase().includes('mishra');
  
  if (debug) {
    console.log(`[getCardImagePaths] Input cardName: "${cardName}"`);
  }
  
  // Strip _UNK or other set code suffixes from the card name if present
  // This handles cases where card IDs like "wild_mongrel_UNK" are passed
  // Be conservative: only strip if it's clearly a set code (UNK, or 2-3 chars, or contains numbers)
  // Don't strip 4-letter words that might be part of the card name (like "kavu")
  let cleanName = cardName;
  const setCodeMatch = cardName.match(/^(.+)_([A-Z0-9]{2,4})$/i);
  if (setCodeMatch) {
    const suffix = setCodeMatch[2].toUpperCase();
    // Only strip if:
    // 1. It's "UNK" (unknown set)
    // 2. It's 2-3 characters (most set codes are 2-3 chars like "A25", "CMR", "M21")
    // 3. It contains numbers (like "A25", "2X2")
    // Don't strip 4-letter words that are likely part of the card name
    const isLikelySetCode = suffix === 'UNK' || 
                            suffix.length <= 3 || 
                            /\d/.test(suffix);
    
    if (isLikelySetCode) {
      cleanName = setCodeMatch[1];
      if (debug) {
        console.log(`[getCardImagePaths] Stripped set code "${suffix}", cleanName: "${cleanName}"`);
      }
    } else if (debug) {
      console.log(`[getCardImagePaths] NOT stripping "${suffix}" - likely part of card name (4+ letters, no numbers)`);
    }
  }
  
  // If the name already looks like a filename (lowercase with underscores, no spaces or special chars except apostrophes),
  // try it directly first, and also try with apostrophe removed
  // Allow both regular and Unicode apostrophes
  const lowerCleanName = cleanName.toLowerCase();
  const apostropheChars = /[\u0027\u0060\u00B4\u02BC\u02BB\u02BD\u02BE\u02BF\u2018-\u201F\u2032\u2035\u0301\u0313\u0314\u0315]/g;
  const looksLikeFilename = /^[a-z0-9_\u0027\u0060\u00B4\u02BC\u02BB\u02BD\u02BE\u02BF\u2018-\u201F\u2032\u2035\u0301\u0313\u0314\u0315]+$/.test(lowerCleanName);
  const paths: string[] = [];
  
  if (debug) {
    console.log(`[getCardImagePaths] looksLikeFilename check:`, {
      lowerCleanName,
      regexTest: /^[a-z0-9_']+$/.test(lowerCleanName),
      result: looksLikeFilename
    });
  }
  
  if (looksLikeFilename) {
    // Try the name directly as-is (already in filename format)
    const directPath = `/card_images/${lowerCleanName}.jpg`;
    paths.push(directPath);
    if (debug) {
      console.log(`[getCardImagePaths] Added direct path: ${directPath}`);
    }
    
    // Also try with apostrophe removed (common case: "mishra's_factory" -> "mishras_factory")
    // Handle both regular and Unicode apostrophes
    if (apostropheChars.test(lowerCleanName)) {
      const withoutApostrophe = lowerCleanName.replace(apostropheChars, '');
      const withoutApostrophePath = `/card_images/${withoutApostrophe}.jpg`;
      paths.push(withoutApostrophePath);
      if (debug) {
        console.log(`[getCardImagePaths] Added path without apostrophe: ${withoutApostrophePath}`);
      }
    }
  }
  
  // Generate multiple filename variations
  const filenameVariations = generateFilenameVariations(cleanName);
  
  if (debug) {
    console.log(`[getCardImagePaths] Generated ${filenameVariations.length} filename variations:`, filenameVariations);
  }
  
  // Add all variations (avoid duplicates)
  filenameVariations.forEach(filename => {
    const path = `/card_images/${filename}.jpg`;
    if (!paths.includes(path)) {
      paths.push(path);
      if (debug) {
        console.log(`[getCardImagePaths] Added variation path: ${path}`);
      }
    } else if (debug) {
      console.log(`[getCardImagePaths] Skipped duplicate path: ${path}`);
    }
  });
  
  // Fallback
  paths.push('/cards/card-back.jpg');
  
  if (debug) {
    console.log(`[getCardImagePaths] Final paths (${paths.length} total):`, paths);
  }
  
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
