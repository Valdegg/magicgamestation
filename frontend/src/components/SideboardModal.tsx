import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CardData } from '../types';
import { useCardDatabase } from '../context/CardDatabaseContext';
import { getCardImagePaths } from '../utils/cardDatabase';
import { useGameState } from '../context/GameStateWebSocket';

interface SideboardModalProps {
  libraryCards: CardData[];
  sideboardCards: CardData[];
  onClose: () => void;
}

const SideboardModal: React.FC<SideboardModalProps> = ({ libraryCards, sideboardCards, onClose }) => {
  const { getCard } = useCardDatabase();
  const { moveCard } = useGameState();
  const hoverZoomEnabled = false; // Disable hover zoom in sideboard modal
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

  const filteredLibraryCards = useMemo(() => {
    if (!searchTerm) return libraryCards;
    return libraryCards.filter(card => {
      const metadata = card.cardId ? getCard(card.cardId) : null;
      const displayName = metadata?.name || card.name;
      return displayName.toLowerCase().includes(searchTerm.toLowerCase());
    });
  }, [libraryCards, searchTerm, getCard]);

  const handleDragStart = (e: React.DragEvent, cardId: string, sourceZone: 'library' | 'sideboard') => {
    setDraggingCard(cardId);
    e.dataTransfer.setData('cardId', cardId);
    e.dataTransfer.setData('sourceZone', sourceZone);
  };

  const handleDragEnd = () => {
    setDraggingCard(null);
  };

  const handleMoveToSideboard = (cardId: string) => {
    moveCard(cardId, 'sideboard');
  };

  const handleMoveToLibrary = (cardId: string) => {
    moveCard(cardId, 'library');
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
              <h2 className="text-fantasy-gold text-2xl font-bold">Sideboard</h2>
              <p className="text-fantasy-gold/60 text-sm">
                {sideboardCards.length} sideboard • {libraryCards.length} library
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-fantasy-gold hover:text-white text-2xl"
            >
              ✕
            </button>
          </div>

          {/* Sideboard Section - Row on Top */}
          <div className="mb-6">
            <h3 className="text-fantasy-gold text-lg font-bold mb-2">
              Sideboard ({sideboardCards.length})
            </h3>
            <div className="flex gap-2 overflow-x-auto pb-2" style={{ scrollbarWidth: 'thin' }}>
              {sideboardCards.length === 0 ? (
                <div className="text-fantasy-gold/50 text-sm italic py-8 px-4">
                  No cards in sideboard
                </div>
              ) : (
                sideboardCards.map((card) => {
                  const metadata = card.cardId ? getCard(card.cardId) : null;
                  const displayName = metadata?.name || card.name;
                  const imagePaths = getCardImagePaths(
                    displayName,
                    metadata?.set && metadata.set !== 'UNK' ? metadata.set : undefined
                  );

                  return (
                    <motion.div
                      key={card.id}
                      className="flex-shrink-0 rounded overflow-hidden shadow-lg cursor-grab active:cursor-grabbing relative group"
                      style={{ 
                        width: '120px',
                        aspectRatio: '2.5/3.5',
                        opacity: draggingCard === card.id ? 0.5 : 1,
                        willChange: 'auto',
                      }}
                    >
                      <div
                        draggable
                        onDragStart={(e: React.DragEvent) => handleDragStart(e, card.id, 'sideboard')}
                        onDragEnd={handleDragEnd}
                        className="absolute inset-0"
                      >
                      <img
                        src={imagePaths[0]}
                        alt={displayName}
                        className="w-full h-full object-cover"
                        style={{ borderRadius: '0.5rem' }}
                      />
                      
                      {/* Quick Action Button */}
                      <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <button
                          onClick={() => handleMoveToLibrary(card.id)}
                          className="w-full mx-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded"
                        >
                          → Library
                        </button>
                      </div>
                      </div>
                    </motion.div>
                  );
                })
              )}
            </div>
          </div>

          {/* Library Section - Grid Below */}
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-fantasy-gold text-lg font-bold">
                Library ({filteredLibraryCards.length})
              </h3>
            </div>

            {/* Search Input */}
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search library..."
              className="w-full px-4 py-2 mb-4 bg-fantasy-dark/50 border border-fantasy-gold/30 rounded text-fantasy-gold placeholder-fantasy-gold/30"
              autoFocus
            />

            {/* Instructions */}
            <div className="text-fantasy-gold/70 text-sm mb-4 p-3 bg-fantasy-dark/30 rounded">
              <strong>💡 Tip:</strong> Click cards to move between sideboard and library. Drag cards to move them.
            </div>

            {/* Library Cards Grid */}
            <div className="flex-1 overflow-y-auto mb-4">
              {filteredLibraryCards.length === 0 ? (
                <div className="text-fantasy-gold/50 text-sm italic py-8 text-center">
                  {searchTerm ? 'No cards match your search' : 'No cards in library'}
                </div>
              ) : (
                <div className="grid grid-cols-5 gap-3">
                  {filteredLibraryCards.map((card) => {
                    const metadata = card.cardId ? getCard(card.cardId) : null;
                    const displayName = metadata?.name || card.name;
                    const imagePaths = getCardImagePaths(
                      displayName,
                      metadata?.set && metadata.set !== 'UNK' ? metadata.set : undefined
                    );

                    return (
                      <motion.div
                        key={card.id}
                        className="rounded overflow-hidden shadow-lg cursor-grab active:cursor-grabbing relative group"
                        style={{ 
                          aspectRatio: '2.5/3.5',
                          opacity: draggingCard === card.id ? 0.5 : 1,
                          willChange: 'auto',
                        }}
                      >
                        <div
                          draggable
                          onDragStart={(e: React.DragEvent) => handleDragStart(e, card.id, 'library')}
                          onDragEnd={handleDragEnd}
                          className="absolute inset-0"
                        >
                        <img
                          src={imagePaths[0]}
                          alt={displayName}
                          className="w-full h-full object-cover"
                          style={{ borderRadius: '0.5rem' }}
                        />
                        
                        {/* Quick Action Button */}
                        <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                          <button
                            onClick={() => handleMoveToSideboard(card.id)}
                            className="w-full mx-2 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded"
                          >
                            → Sideboard
                          </button>
                        </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 py-3 bg-fantasy-gold/20 hover:bg-fantasy-gold/30 text-fantasy-gold rounded transition-colors font-bold"
            >
              Done Sideboarding
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default SideboardModal;

