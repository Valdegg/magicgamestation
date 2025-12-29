/**
 * Backend Data Structures
 * These match the .to_dict() output from the Python backend.
 */

export interface BackendCard {
  id: string;
  name: string;
  owner_id: string;
  tapped: boolean;
  face_down: boolean;
  attached_to_id?: string; // ID of the card this card is attached to
  data: {
    card_id?: string;
    set?: string;
    type?: string;
    image?: string;
    mana_cost?: string;
    cmc?: number;
    oracle_text?: string;
    x?: number;
    y?: number;
    [key: string]: any; // For other arbitrary metadata
  };
}

export interface BackendZone {
  zone_type: string;
  player_id: string;
  cards: BackendCard[];
}

export interface BackendPlayer {
  id: string;
  name: string;
  life_total: number;
  zones: Record<string, BackendZone>;
}

export interface BackendTargetingArrow {
  cardId: string;
  targetCardId?: string;
  targetPlayerId?: string;
  ownerPlayerId: string;
}

export interface BackendChatMessage {
  playerId: string;
  playerName: string;
  message: string;
  timestamp: string;
}

export interface BackendGameState {
  players: Record<string, BackendPlayer>;
  active_player_id: string | null;
  turn_number: number;
  current_phase: string;
  dice_tokens?: Array<{
    id: string;
    x: number;
    y: number;
    value: number | null;
    ownerPlayerId: string;
    dieType: string;
    lastRolledAt?: number | null;
  }>;
  targeting_arrows?: BackendTargetingArrow[];
  chat_messages?: BackendChatMessage[];
}

