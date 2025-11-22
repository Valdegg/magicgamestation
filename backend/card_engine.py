"""
Magic Workstation-Style Card Engine
A lightweight, rules-agnostic engine for playing card games.

This engine does NOT enforce game rules - it only manages state.
All game actions are manual and must be explicitly called.
"""

from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4
import random


class ZoneType(Enum):
    """Standard game zones for each player."""
    LIBRARY = "library"
    HAND = "hand"
    BATTLEFIELD = "battlefield"
    GRAVEYARD = "graveyard"
    EXILE = "exile"
    STACK = "stack"
    COMMAND = "command"


class Phase(Enum):
    """Magic: The Gathering turn phases."""
    UNTAP = "untap"
    UPKEEP = "upkeep"
    DRAW = "draw"
    MAIN_1 = "main_1"
    BEGIN_COMBAT = "begin_combat"
    DECLARE_ATTACKERS = "declare_attackers"
    DECLARE_BLOCKERS = "declare_blockers"
    DAMAGE = "damage"
    END_COMBAT = "end_combat"
    MAIN_2 = "main_2"
    END_STEP = "end_step"
    CLEANUP = "cleanup"


class Card:
    """
    A card is just data + state.
    No rules enforcement - cards are inert objects that can be manipulated.
    """
    
    def __init__(self, name: str, owner_id: str, data: Optional[Dict] = None):
        self.id = str(uuid4())
        self.name = name
        self.owner_id = owner_id
        self.tapped = False
        self.face_down = False
        self.attached_to_id: Optional[str] = None
        self.data = data or {}
    
    def tap(self): self.tapped = True
    def untap(self): self.tapped = False
    def toggle_tap(self): self.tapped = not self.tapped
    
    def flip_face_down(self): self.face_down = True
    def flip_face_up(self): self.face_down = False
    def toggle_face(self): self.face_down = not self.face_down
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "owner_id": self.owner_id,
            "tapped": self.tapped,
            "face_down": self.face_down,
            "attached_to_id": self.attached_to_id,
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Card':
        card = cls(data["name"], data["owner_id"], data.get("data", {}))
        card.id = data["id"]
        card.tapped = data.get("tapped", False)
        card.face_down = data.get("face_down", False)
        card.attached_to_id = data.get("attached_to_id")
        return card
    
    def __repr__(self):
        state = []
        if self.tapped: state.append("tapped")
        if self.face_down: state.append("face-down")
        state_str = f" ({', '.join(state)})" if state else ""
        return f"Card({self.name}{state_str})"


class Zone:
    """
    A zone is an ordered list of cards.
    Operations: add, remove, move, shuffle.
    """
    
    def __init__(self, zone_type: ZoneType, player_id: str):
        self.zone_type = zone_type
        self.player_id = player_id
        self.cards: List[Card] = []
    
    def add(self, card: Card, index: Optional[int] = None):
        if index is None:
            self.cards.append(card)
        else:
            self.cards.insert(index, card)
    
    def remove(self, card: Card) -> bool:
        try:
            self.cards.remove(card)
            return True
        except ValueError:
            return False
    
    def remove_by_id(self, card_id: str) -> Optional[Card]:
        for i, card in enumerate(self.cards):
            if card.id == card_id:
                return self.cards.pop(i)
        return None
    
    def find_by_id(self, card_id: str) -> Optional[Card]:
        for card in self.cards:
            if card.id == card_id:
                return card
        return None
    
    def shuffle(self): random.shuffle(self.cards)
    def top(self) -> Optional[Card]: return self.cards[-1] if self.cards else None
    def bottom(self) -> Optional[Card]: return self.cards[0] if self.cards else None
    def size(self) -> int: return len(self.cards)
    def is_empty(self) -> bool: return len(self.cards) == 0
    
    def to_dict(self) -> Dict:
        return {
            "zone_type": self.zone_type.value,
            "player_id": self.player_id,
            "cards": [card.to_dict() for card in self.cards]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Zone':
        zone = cls(ZoneType(data["zone_type"]), data["player_id"])
        zone.cards = [Card.from_dict(card_data) for card_data in data["cards"]]
        return zone
    
    def __repr__(self):
        return f"Zone({self.zone_type.value}, {len(self.cards)} cards)"
    
    def __len__(self):
        return len(self.cards)


class Player:
    """
    A player with zones and life total.
    """
    
    def __init__(self, name: str, starting_life: int = 20):
        self.id = str(uuid4())
        self.name = name
        self.life_total = starting_life
        self.zones: Dict[ZoneType, Zone] = {
            zone_type: Zone(zone_type, self.id) for zone_type in ZoneType
        }
    
    def draw(self, count: int = 1) -> List[Card]:
        drawn = []
        library = self.zones[ZoneType.LIBRARY]
        hand = self.zones[ZoneType.HAND]
        
        for _ in range(count):
            if library.is_empty(): break
            card = library.cards.pop()
            hand.add(card)
            drawn.append(card)
        return drawn
    
    def shuffle_library(self): self.zones[ZoneType.LIBRARY].shuffle()
    def change_life(self, delta: int): self.life_total += delta
    def set_life(self, amount: int): self.life_total = amount
    
    def find_card(self, card_id: str) -> Optional[tuple[Card, ZoneType]]:
        for zone_type, zone in self.zones.items():
            card = zone.find_by_id(card_id)
            if card: return (card, zone_type)
        return None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "life_total": self.life_total,
            "zones": {z_type.value: z.to_dict() for z_type, z in self.zones.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Player':
        player = cls(data["name"], data["life_total"])
        player.id = data["id"]
        player.zones = {
            ZoneType(z_type): Zone.from_dict(z_data)
            for z_type, z_data in data["zones"].items()
        }
        return player
    
    def __repr__(self):
        return f"Player({self.name}, life={self.life_total})"


class Game:
    """
    The game consists of players and manages game state.
    No rule checks are performed - the game simply updates state.
    """
    
    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.active_player_id: Optional[str] = None
        self.turn_number = 1
        self.current_phase = Phase.UNTAP
        self.phase_order = list(Phase)
    
    def add_player(self, player: Player):
        self.players[player.id] = player
        if self.active_player_id is None:
            self.active_player_id = player.id
    
    def remove_player(self, player_id: str) -> bool:
        if player_id in self.players:
            del self.players[player_id]
            if self.active_player_id == player_id:
                self.active_player_id = next(iter(self.players)) if self.players else None
            return True
        return False
    
    def next_phase(self):
        current_idx = self.phase_order.index(self.current_phase)
        next_idx = (current_idx + 1) % len(self.phase_order)
        if next_idx == 0: 
            self.next_turn()
            return
        self.current_phase = self.phase_order[next_idx]
    
    def next_turn(self):
        if not self.players: return
        
        p_ids = list(self.players.keys())
        if not self.active_player_id:
            self.active_player_id = p_ids[0]
            self.turn_number = 1
        else:
            curr_idx = p_ids.index(self.active_player_id)
            next_idx = (curr_idx + 1) % len(p_ids)
            self.active_player_id = p_ids[next_idx]
            if next_idx == 0: self.turn_number += 1
        
        self.current_phase = Phase.UPKEEP
        self.untap_all_permanents()
    
    def find_card(self, card_id: str) -> Optional[tuple[Card, Player, ZoneType]]:
        for player in self.players.values():
            result = player.find_card(card_id)
            if result: return (result[0], player, result[1])
        return None
    
    def move_card(self, card_id: str, to_player_id: str, to_zone_type: ZoneType, index: Optional[int] = None) -> bool:
        result = self.find_card(card_id)
        if not result: return False
        
        card, from_player, from_zone_type = result
        to_player = self.players.get(to_player_id)
        if not to_player: return False
        
        # If moving to a different zone/player, unattach it
        if card.attached_to_id:
            card.attached_to_id = None

        from_player.zones[from_zone_type].remove(card)
        to_player.zones[to_zone_type].add(card, index)
        return True
    
    def attach_card(self, card_id: str, target_card_id: str) -> bool:
        """Attach a card to another card (e.g., Aura/Equipment)."""
        result = self.find_card(card_id)
        if not result: return False
        card = result[0]
        
        # Verify target exists
        target_result = self.find_card(target_card_id)
        if not target_result: return False
        
        # Prevent circular attachment or self-attachment
        if card_id == target_card_id: return False
        
        card.attached_to_id = target_card_id
        return True
        
    def unattach_card(self, card_id: str) -> bool:
        """Remove attachment from a card."""
        result = self.find_card(card_id)
        if result:
            result[0].attached_to_id = None
            return True
        return False

    def toggle_tap_card(self, card_id: str) -> bool:
        result = self.find_card(card_id)
        if result:
            result[0].toggle_tap()
            return True
        return False
    
    def toggle_face_card(self, card_id: str) -> bool:
        result = self.find_card(card_id)
        if result:
            result[0].toggle_face()
            return True
        return False
    
    def untap_all_permanents(self) -> int:
        count = 0
        if self.active_player_id:
            player = self.players.get(self.active_player_id)
            if player:
                for card in player.zones[ZoneType.BATTLEFIELD].cards:
                    if card.tapped:
                        card.untap()
                        count += 1
        return count
    
    def to_dict(self) -> Dict:
        return {
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "active_player_id": self.active_player_id,
            "turn_number": self.turn_number,
            "current_phase": self.current_phase.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Game':
        game = cls()
        game.players = {pid: Player.from_dict(p_data) for pid, p_data in data["players"].items()}
        game.active_player_id = data.get("active_player_id")
        game.turn_number = data.get("turn_number", 0)
        game.current_phase = Phase(data.get("current_phase", "untap"))
        return game

    def __repr__(self):
        return f"Game(turn={self.turn_number}, players={len(self.players)})"
