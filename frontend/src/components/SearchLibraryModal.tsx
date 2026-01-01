import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CardData } from '../types';
import { useCardDatabase } from '../context/CardDatabaseContext';
import { getCardImagePaths } from '../utils/cardDatabase';
import { useGameState } from '../context/GameStateWebSocket';

interface SearchLibraryModalProps {
  cards: CardData[];
  onClose: () => void;
}

const SearchLibraryModal: React.FC<SearchLibraryModalProps> = ({ cards, onClose }) => {
  const { getCard } = useCardDatabase();
  const { moveCard } = useGameState();
  const hoverZoomEnabled = false; // Disable hover zoom in search library modal
  const [searchTerm, setSearchTerm] = useState('');
  const [draggingCard, setDraggingCard] = useState<string | null>(null);

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

  const filteredCards = cards.filter(card => {
    if (!searchTerm) return true;
    const metadata = card.cardId ? getCard(card.cardId) : null;
    const displayName = metadata?.name || card.name;
    return displayName.toLowerCase().includes(searchTerm.toLowerCase());
  });

  const handleDragStart = (e: React.DragEvent, cardId: string) => {
    setDraggingCard(cardId);
    e.dataTransfer.setData('cardId', cardId);
    e.dataTransfer.setData('sourceZone', 'library');
  };

  const handleDragEnd = () => {
    setDraggingCard(null);
  };

  const handleCardClick = (cardId: string, destination: 'hand' | 'graveyard' | 'battlefield') => {
    if (destination === 'battlefield') {
      const battlefieldElement = document.getElementById('battlefield');
      if (battlefieldElement) {
        const rect = battlefieldElement.getBoundingClientRect();
        const centerX = rect.width / 2 - 75;
        const centerY = rect.height / 2 - 105;
        moveCard(cardId, 'battlefield', centerX, centerY);
      }
    } else {
      moveCard(cardId, destination);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/70 z-[200] flex items-center justify-center" onClick={onClose}>
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          className="fantasy-panel p-6 max-w-6xl w-full max-h-[90vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-fantasy-gold text-2xl font-bold">Search Library</h2>
              <p className="text-fantasy-gold/60 text-sm">{filteredCards.length} cards</p>
            </div>
            <button
              onClick={onClose}
              className="text-fantasy-gold hover:text-white text-2xl"
            >
              ✕
            </button>
          </div>

          {/* Search Input */}
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search for a card..."
            className="w-full px-4 py-2 mb-4 bg-fantasy-dark/50 border border-fantasy-gold/30 rounded text-fantasy-gold placeholder-fantasy-gold/30"
            autoFocus
          />

          {/* Instructions */}
          <div className="text-fantasy-gold/70 text-sm mb-4 p-3 bg-fantasy-dark/30 rounded">
            <strong>💡 Tip:</strong> Drag cards to Hand, Graveyard, or Battlefield. Or click a card and then click a destination button below.
          </div>

          {/* Cards Grid */}
          <div className="flex-1 overflow-y-auto mb-4">
            <div className="grid grid-cols-5 gap-3">
              {filteredCards.map((card) => {
                const metadata = card.cardId ? getCard(card.cardId) : null;
                const displayName = metadata?.name || card.name;
                const imagePaths = getCardImagePaths(
                  displayName,
                  metadata?.set && metadata.set !== 'UNK' ? metadata.set : undefined
                );

                return (
                  <motion.div
                    key={card.id}
                    className="rounded overflow-hidden shadow-lg cursor-grab active:cursor-grabbing relative"
                    style={{ 
                      aspectRatio: '2.5/3.5',
                      opacity: draggingCard === card.id ? 0.5 : 1,
                      // Prevent GPU compositing blur
                      willChange: 'auto',
                    }}
                  >
                    <div
                      draggable
                      onDragStart={(e: React.DragEvent) => handleDragStart(e, card.id)}
                      onDragEnd={handleDragEnd}
                      className="absolute inset-0"
                    >
                    <img
                      src={imagePaths[0]}
                      alt={displayName}
                      className="w-full h-full object-cover"
                      style={{ 
                        // Removed crisp-edges - let browser use high-quality scaling
                        borderRadius: '0.5rem'
                      }}
                    />
                    
                    {/* Quick Action Buttons */}
                    <div className="absolute inset-0 bg-black/70 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center gap-2 flex-col p-2">
                      <button
                        onClick={() => handleCardClick(card.id, 'hand')}
                        className="w-full py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded"
                      >
                        → Hand
                      </button>
                      <button
                        onClick={() => handleCardClick(card.id, 'graveyard')}
                        className="w-full py-1 bg-red-600 hover:bg-red-700 text-white text-xs rounded"
                      >
                        → Graveyard
                      </button>
                      <button
                        onClick={() => handleCardClick(card.id, 'battlefield')}
                        className="w-full py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded"
                      >
                        → Battlefield
                      </button>
                    </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Footer */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 py-3 bg-fantasy-gold/20 hover:bg-fantasy-gold/30 text-fantasy-gold rounded transition-colors font-bold"
            >
              Done Searching
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default SearchLibraryModal;

