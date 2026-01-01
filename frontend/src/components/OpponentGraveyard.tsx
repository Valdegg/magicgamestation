import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CardData } from '../types';
import { useCardDatabase } from '../context/CardDatabaseContext';
import { getCardImagePaths } from '../utils/cardDatabase';
import { useCardScale } from '../context/CardScaleContext';

interface OpponentGraveyardProps {
  cards: CardData[];
  opponentName: string;
}

const OpponentGraveyard: React.FC<OpponentGraveyardProps> = ({ cards, opponentName }) => {
  const { getCard } = useCardDatabase();
  const { cardScale, hoverZoomValue } = useCardScale();
  const hoverZoomEnabled = hoverZoomValue > 1.0;
  const [showExpanded, setShowExpanded] = useState(false);
  const [draggingCardId] = useState<string | null>(null);

  // Handle ESC key to close expanded modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showExpanded) {
        setShowExpanded(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showExpanded]);
  
  // Show up to 3 cards with stacking - most recent on top (half size)
  const visibleCards = cards.slice(-3);
  const baseCardHeight = 105;
  const cardHeight = Math.round(baseCardHeight * cardScale);
  const cardWidth = Math.round((cardHeight * 5) / 7);
  const stackOffset = Math.round(16 * cardScale);

  return (
    <>
      <div className="fantasy-panel p-2 h-full flex flex-col">
        <div className="zone-label text-center text-sm mb-2 uppercase tracking-wider">
          {opponentName}'s Graveyard
        </div>
        <div
          className="flex-1 fantasy-border rounded-lg relative overflow-visible transition-all"
          style={{
            background: cards.length > 0 
              ? 'linear-gradient(135deg, #2a1810 0%, #1a100a 100%)'
              : 'linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%)'
          }}
        >
          {cards.length > 0 ? (
            <div className="absolute inset-0 flex items-start justify-center pt-2">
              <div 
                className="relative" 
                style={{ 
                  height: `${cardHeight + (visibleCards.length - 1) * stackOffset}px`,
                  width: `${cardWidth}px`
                }}
              >
                {visibleCards.map((card, index) => {
                  const metadata = card.cardId ? getCard(card.cardId) : null;
                  const displayName = metadata?.name || card.name;
                  const imagePaths = getCardImagePaths(displayName);

                  // Bottom card is index 0, top card is index visibleCards.length - 1
                  const stackPosition = index;
                  const zIndex = index + 1;

                  return (
                    <motion.div
                      key={card.id}
                      className="absolute top-0 left-0 w-full rounded-lg overflow-hidden shadow-xl card-frame cursor-pointer"
                      style={{
                        height: `${cardHeight}px`,
                        y: stackPosition * stackOffset,
                        zIndex: zIndex,
                      }}
                      whileHover={draggingCardId !== card.id && hoverZoomEnabled ? { 
                        scale: hoverZoomValue,
                        y: -80,
                        zIndex: 1000,
                        transition: { duration: 0.2, delay: 0.8 }
                      } : undefined}
                      onClick={() => setShowExpanded(true)}
                    >
                      <img
                        src={imagePaths[0]}
                        alt={card.name}
                        className="w-full h-full object-cover"
                        style={{ imageRendering: 'crisp-edges' }}
                      />
                    </motion.div>
                  );
                })}
                
                {/* Card count badge */}
                {cards.length > 1 && (
                  <div className="absolute top-1 right-1 bg-fantasy-gold text-fantasy-dark px-2 py-1 rounded-full font-bold text-xs shadow-lg z-50">
                    {cards.length}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-fantasy-gold/30 text-sm">Empty</div>
            </div>
          )}
        </div>
      </div>

      {/* Expanded Modal */}
      <AnimatePresence>
        {showExpanded && (
          <>
            <div
              className="fixed inset-0 bg-black/60 z-[200]"
              onClick={() => setShowExpanded(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: -20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: -20 }}
              className="fixed top-4 left-1/2 -translate-x-1/2 z-[201] fantasy-panel p-4 max-w-2xl max-h-[80vh] overflow-y-auto"
            >
              <div className="text-center mb-4">
                <h3 className="text-fantasy-gold text-lg font-bold">{opponentName}'s Graveyard</h3>
                <p className="text-fantasy-gold/60 text-sm">{cards.length} cards</p>
              </div>
              
              <div className="grid grid-cols-4 gap-2">
                {cards.map((card) => {
                  const metadata = card.cardId ? getCard(card.cardId) : getCard(card.name);
                  const displayName = metadata?.name || card.name;
                  const imagePaths = getCardImagePaths(displayName);
                  
                  return (
                    <div
                      key={card.id}
                      className="rounded overflow-hidden shadow-lg"
                      style={{ aspectRatio: '2.5/3.5' }}
                    >
                      <img
                        src={imagePaths[0]}
                        alt={displayName || 'Card'}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  );
                })}
              </div>
              
              <button
                onClick={() => setShowExpanded(false)}
                className="mt-4 w-full py-2 bg-fantasy-gold/20 hover:bg-fantasy-gold/30 text-fantasy-gold rounded transition-colors"
              >
                Close
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
};

export default OpponentGraveyard;
