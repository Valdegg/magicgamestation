import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getAvailableDecks } from '../utils/deckLoader';
import { useGameState } from '../context/GameStateWebSocket';

interface DeckSelectorProps {
  onClose: () => void;
}

const DeckSelector: React.FC<DeckSelectorProps> = ({ onClose }) => {
  const [decks, setDecks] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { loadDeckByName } = useGameState();

  useEffect(() => {
    loadAvailableDecks();
  }, []);

  // Handle ESC key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const loadAvailableDecks = async () => {
    try {
      const availableDecks = await getAvailableDecks();
      setDecks(availableDecks);
    } catch (err) {
      setError('Failed to load deck list');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDeck = async (deckName: string) => {
    try {
      setLoading(true);
      await loadDeckByName(deckName);
      onClose();
    } catch (err) {
      setError(`Failed to load deck: ${deckName}`);
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000]">
        <motion.div
          className="fantasy-panel max-w-md w-full mx-4"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
        >
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold text-fantasy-gold">Select Deck</h2>
            <button
              onClick={onClose}
              className="text-fantasy-gold hover:text-fantasy-parchment text-2xl"
            >
              ×
            </button>
          </div>

          {loading && (
            <div className="text-center text-fantasy-gold/70 py-8">
              Loading decks...
            </div>
          )}

          {error && (
            <div className="text-center text-red-400 py-4 mb-4 bg-red-900/20 rounded">
              {error}
            </div>
          )}

          {!loading && !error && (
            <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
              {decks.length === 0 ? (
                <div className="text-center text-fantasy-gold/50 py-8">
                  No decks found
                </div>
              ) : (
                decks.map((deckName) => (
                  <motion.button
                    key={deckName}
                    className="w-full fantasy-button text-left"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleSelectDeck(deckName)}
                  >
                    {deckName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </motion.button>
                ))
              )}
            </div>
          )}

          <div className="mt-4 text-xs text-fantasy-gold/50 text-center">
            Decks are loaded from /public/decks/
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default DeckSelector;

