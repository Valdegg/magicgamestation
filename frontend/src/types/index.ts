export type ZoneType = 'hand' | 'battlefield' | 'graveyard' | 'exile' | 'library' | 'sideboard';

export interface CardData {
  id: string; // Unique instance ID for this physical card
  cardId?: string; // Reference to card database (e.g., "lightning_bolt_A25")
  name: string;
  tapped: boolean;
  faceDown: boolean;
  zone: ZoneType;
  attachedToId?: string; // ID of the card this card is attached to (e.g. Aura/Equipment)
  x?: number;
  y?: number;
  scale?: number; // Scale factor for opponent cards (used for fitting in smaller battlefield)
  data?: Record<string, any>;
}

export interface PlayerState {
  id: string;
  name: string;
  life: number;
}

export interface GameState {
  player: PlayerState;
  cards: CardData[];
  libraryCount: number;
}
