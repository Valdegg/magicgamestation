import unittest
from backend.card_engine import Card, Zone, Player, Game, ZoneType, Phase

class TestCardEngine(unittest.TestCase):
    
    def test_card_initialization(self):
        card = Card("Lightning Bolt", "player1", {"mana_cost": "{R}"})
        self.assertEqual(card.name, "Lightning Bolt")
        self.assertEqual(card.owner_id, "player1")
        self.assertFalse(card.tapped)
        self.assertFalse(card.face_down)
        self.assertEqual(card.data["mana_cost"], "{R}")

    def test_card_state_toggling(self):
        card = Card("Mountain", "player1")
        
        card.tap()
        self.assertTrue(card.tapped)
        
        card.untap()
        self.assertFalse(card.tapped)
        
        card.toggle_tap()
        self.assertTrue(card.tapped)
        
        card.flip_face_down()
        self.assertTrue(card.face_down)
        
        card.toggle_face()
        self.assertFalse(card.face_down)

    def test_zone_operations(self):
        zone = Zone(ZoneType.HAND, "player1")
        c1 = Card("C1", "player1")
        c2 = Card("C2", "player1")
        
        zone.add(c1)
        zone.add(c2)
        self.assertEqual(len(zone), 2)
        self.assertEqual(zone.top(), c2)
        self.assertEqual(zone.bottom(), c1)
        
        found = zone.find_by_id(c1.id)
        self.assertEqual(found, c1)
        
        zone.remove(c1)
        self.assertEqual(len(zone), 1)
        self.assertEqual(zone.top(), c2)

    def test_player_draw(self):
        player = Player("Alice")
        library = player.zones[ZoneType.LIBRARY]
        
        # Add 3 cards to library
        for i in range(3):
            library.add(Card(f"Card {i}", player.id))
            
        self.assertEqual(len(library), 3)
        self.assertEqual(len(player.zones[ZoneType.HAND]), 0)
        
        # Draw 1
        drawn = player.draw(1)
        self.assertEqual(len(drawn), 1)
        self.assertEqual(len(library), 2)
        self.assertEqual(len(player.zones[ZoneType.HAND]), 1)
        
        # Draw more than available (should draw remaining 2)
        drawn = player.draw(5)
        self.assertEqual(len(drawn), 2)
        self.assertEqual(len(library), 0)
        self.assertEqual(len(player.zones[ZoneType.HAND]), 3)

    def test_game_turn_cycle(self):
        game = Game()
        p1 = Player("Alice")
        p2 = Player("Bob")
        game.add_player(p1)
        game.add_player(p2)
        
        self.assertEqual(game.active_player_id, p1.id)
        self.assertEqual(game.turn_number, 1)
        self.assertEqual(game.current_phase, Phase.UNTAP)
        
        # Advance phases until end of turn
        initial_phase = game.current_phase
        steps = len(Phase)
        
        # Go through all phases of P1
        for _ in range(steps):
            game.next_phase()
            
        # Should now be P2's turn, Upkeep (untap is skipped/automated in next_turn logic usually, 
        # but let's check how next_turn is implemented. 
        # Looking at card_engine.py: next_turn sets phase to UPKEEP)
        
        self.assertEqual(game.active_player_id, p2.id)
        self.assertEqual(game.turn_number, 1) # Turn number increments when back to P1
        self.assertEqual(game.current_phase, Phase.UPKEEP)
        
        # Cycle P2
        for _ in range(steps): # This will wrap around
            game.next_phase()
            
        # Back to P1, Turn 2
        self.assertEqual(game.active_player_id, p1.id)
        self.assertEqual(game.turn_number, 2)

    def test_move_card(self):
        game = Game()
        p1 = Player("Alice")
        game.add_player(p1)
        
        c1 = Card("Test", p1.id)
        p1.zones[ZoneType.HAND].add(c1)
        
        # Move Hand -> Battlefield
        success = game.move_card(c1.id, p1.id, ZoneType.BATTLEFIELD)
        self.assertTrue(success)
        self.assertEqual(len(p1.zones[ZoneType.HAND]), 0)
        self.assertEqual(len(p1.zones[ZoneType.BATTLEFIELD]), 1)
        
        # Verify position
        self.assertEqual(p1.zones[ZoneType.BATTLEFIELD].cards[0].id, c1.id)

if __name__ == '__main__':
    unittest.main()

