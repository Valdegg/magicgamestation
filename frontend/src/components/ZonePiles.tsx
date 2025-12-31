import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CardData } from '../types';
import { useGameState } from '../context/GameStateWebSocket';

interface ZonePilesProps {
  exile: CardData[];
}

const ZonePiles: React.FC<ZonePilesProps> = ({ exile }) => {
  const [showExile, setShowExile] = useState(false);
  const { moveCard } = useGameState();
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    const cardId = e.dataTransfer.getData('cardId');
    const sourceZone = e.dataTransfer.getData('sourceZone');
    const multipleCardIdsData = e.dataTransfer.getData('multipleCardIds');
    
    // Check if we're dragging multiple cards
    let cardIdsToMove: string[] = [];
    if (multipleCardIdsData) {
      try {
        cardIdsToMove = JSON.parse(multipleCardIdsData);
        console.log('📦 Dropping multiple cards to exile:', cardIdsToMove.length);
      } catch (e) {
        console.error('Failed to parse multipleCardIds:', e);
        cardIdsToMove = [];
      }
    }
    
    // If no multiple cards, use single card
    if (cardIdsToMove.length === 0 && cardId) {
      cardIdsToMove = [cardId];
    }
    
    console.log('📦 Drop data on exile:', { cardIds: cardIdsToMove, sourceZone });
    
    if (cardIdsToMove.length > 0 && sourceZone !== 'exile') {
      console.log('✅ Moving', cardIdsToMove.length, 'card(s) to exile');
      cardIdsToMove.forEach(cardId => moveCard(cardId, 'exile', 0, 0));
    }
  };

  return (
    <div className="flex items-stretch">
      {/* Collapsed Button - Shows by default */}
      {!showExile && (
        <motion.button
          onClick={() => setShowExile(true)}
          className="px-3 flex flex-col items-center justify-center gap-1 cursor-pointer transition-colors relative rounded-lg pointer-events-auto"
          style={{ 
            minWidth: '50px',
            writingMode: 'horizontal-tb',
            background: 'linear-gradient(135deg, rgba(40, 20, 20, 0.4) 0%, rgba(60, 15, 15, 0.5) 100%)',
            backdropFilter: 'blur(8px)',
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.6), inset 0 1px 2px rgba(212, 179, 107, 0.1)',
            border: '2px solid rgba(212, 179, 107, 0.3)'
          }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {/* EX Label */}
          <div className="text-fantasy-gold font-bold text-lg tracking-wider">
            EX
          </div>
          
          {/* Card count badge */}
          {exile.length > 0 && (
            <div 
              className="bg-purple-900/60 text-fantasy-gold text-xs font-bold px-2 py-0.5 rounded-full border border-purple-700/50"
              style={{ boxShadow: '0 0 8px rgba(147, 51, 234, 0.3)' }}
            >
              {exile.length}
            </div>
          )}
          
          {/* Expand indicator */}
          <div className="text-fantasy-gold/40 text-xs mt-auto">
            ▶
          </div>
        </motion.button>
      )}

      {/* Expanded View */}
      <AnimatePresence>
        {showExile && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 200, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden rounded-lg pointer-events-auto"
            style={{
              background: 'linear-gradient(135deg, rgba(40, 20, 20, 0.4) 0%, rgba(60, 15, 15, 0.5) 100%)',
              backdropFilter: 'blur(8px)',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.6), inset 0 1px 2px rgba(212, 179, 107, 0.1)',
              border: '2px solid rgba(212, 179, 107, 0.3)'
            }}
          >
            <div className="p-2 h-full flex flex-col">
              {/* Header */}
              <div className="flex items-center justify-between mb-2">
                <div className="zone-label text-sm uppercase tracking-wider">Exile</div>
                <motion.button
                  className="px-2 py-1 bg-fantasy-burgundy/30 text-fantasy-gold rounded border border-fantasy-gold/30 text-xs hover:bg-fantasy-burgundy/50"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setShowExile(false)}
                >
                  ◀
                </motion.button>
              </div>

              {/* Exile Zone Content */}
              <div
                id="exile-zone"
                className="flex-1 fantasy-border rounded-lg flex items-center justify-center cursor-pointer hover:bg-purple-900/20 transition-colors"
                style={{
                  background: exile.length > 0
                    ? 'linear-gradient(135deg, #2a1028 0%, #1a101a 100%)'
                    : 'linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%)',
                  boxShadow: isDragOver ? '0 0 30px rgba(147, 51, 234, 0.6), inset 0 0 30px rgba(147, 51, 234, 0.3)' : undefined,
                  border: isDragOver ? '3px solid rgba(147, 51, 234, 0.8)' : undefined
                }}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                {exile.length > 0 ? (
                  <div className="text-center">
                    <div className="text-fantasy-gold text-3xl font-bold">
                      {exile.length}
                    </div>
                    <div className="text-fantasy-gold/70 text-xs mt-1 px-2">
                      {exile[exile.length - 1]?.name}
                    </div>
                  </div>
                ) : (
                  <div className="text-fantasy-gold/30 text-sm">Empty</div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ZonePiles;

