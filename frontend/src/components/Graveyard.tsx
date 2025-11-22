import React, { useState } from 'react';
import { motion } from 'framer-motion';
import ContextMenu from './ContextMenu';
import { CardData } from '../types';
import { useCardDatabase } from '../context/CardDatabaseContext';
import { getCardImagePaths } from '../utils/cardDatabase';
import { useGameState } from '../context/GameStateWebSocket';

interface GraveyardProps {
  cards: CardData[];
}

const Graveyard: React.FC<GraveyardProps> = ({ cards }) => {
  const { getCard } = useCardDatabase();
  const { moveCard } = useGameState();
  const [draggingCardId, setDraggingCardId] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; cardId: string } | null>(null);
  
  // Show up to 5 cards with stacking - most recent on top
  const visibleCards = cards.slice(-5);
  const cardHeight = 158;
  const stackOffset = 24; // Fixed 24px visible per card
  
  const handleDragStart = (e: React.DragEvent, cardId: string) => {
    console.log('🎴 Drag started from graveyard:', cardId);
    setDraggingCardId(cardId);
    e.dataTransfer.setData('cardId', cardId);
    e.dataTransfer.setData('sourceZone', 'graveyard');
  };
  
  const handleDragEnd = (e: React.DragEvent, cardId: string) => {
    setDraggingCardId(null);
    const targetElement = document.elementFromPoint(e.clientX, e.clientY);
    
    // Check if dropped on library
    const libraryElement = document.getElementById('library-zone') || targetElement?.closest('#library-zone');
    if (libraryElement) {
      console.log('Moving card from graveyard to library:', cardId);
      moveCard(cardId, 'library');
      return;
    }
    
    // Check if dropped on hand
    const handElement = document.getElementById('hand-zone') || targetElement?.closest('#hand-zone');
    if (handElement) {
      console.log('Moving card from graveyard to hand:', cardId);
      moveCard(cardId, 'hand', 0, 0);
      return;
    }
    
    // Check if dropped on battlefield
    const battlefieldElement = document.getElementById('battlefield') || targetElement?.closest('#battlefield');
    if (battlefieldElement) {
      const rect = battlefieldElement.getBoundingClientRect();
      const x = e.clientX - rect.left - 75;
      const y = e.clientY - rect.top - 105;
      console.log('Moving card from graveyard to battlefield:', cardId, x, y);
      moveCard(cardId, 'battlefield', x, y);
      return;
    }
  };

  // Drag over state for visual feedback
  const [isDragOver, setIsDragOver] = React.useState(false);

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
    
    console.log('📦 Graveyard zone received drop event');
    
    // Get the dragged card ID from the data transfer
    const cardId = e.dataTransfer.getData('cardId');
    const sourceZone = e.dataTransfer.getData('sourceZone');
    
    console.log('📦 Drop data:', { cardId, sourceZone });
    
    if (cardId && sourceZone !== 'graveyard') {
      console.log('✅ Moving card to graveyard:', cardId);
      moveCard(cardId, 'graveyard', 0, 0);
    }
  };

  const handleContextMenu = (e: React.MouseEvent, cardId: string) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, cardId });
  };

  const getContextMenuOptions = (cardId: string) => {
    return [
      {
        label: '🚫 Move to Exile',
        onClick: () => {
          moveCard(cardId, 'exile');
        },
      },
      {
        label: '✋ Return to Hand',
        onClick: () => {
          moveCard(cardId, 'hand');
        },
      },
      {
        label: '🎴 Return to Battlefield',
        onClick: () => {
          // Place in center of battlefield
          const battlefieldElement = document.getElementById('battlefield');
          if (battlefieldElement) {
            const rect = battlefieldElement.getBoundingClientRect();
            const centerX = rect.width / 2 - 75;
            const centerY = rect.height / 2 - 105;
            moveCard(cardId, 'battlefield', centerX, centerY);
          }
        },
      },
    ];
  };

  return (
    <div className="fantasy-panel p-2 h-full flex flex-col">
      <div className="zone-label text-center text-sm mb-2 uppercase tracking-wider">Graveyard</div>
      <div
        id="graveyard-zone"
        className="flex-1 fantasy-border rounded-lg relative overflow-visible transition-all"
        style={{
          background: cards.length > 0 
            ? 'linear-gradient(135deg, #2a1810 0%, #1a100a 100%)'
            : 'linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%)',
          boxShadow: isDragOver ? '0 0 30px rgba(212, 179, 107, 0.6), inset 0 0 30px rgba(212, 179, 107, 0.3)' : undefined,
          border: isDragOver ? '3px solid #f4d589' : undefined
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {cards.length > 0 ? (
          <div className="absolute inset-0 flex items-start justify-center pt-2">
            <div 
              className="relative" 
              style={{ 
                height: `${cardHeight + (visibleCards.length - 1) * stackOffset}px`,
                width: '113px'
              }}
            >
              {visibleCards.map((card, index) => {
                const metadata = card.cardId ? getCard(card.cardId) : null;
                const displayName = metadata?.name || card.name;
                const imagePaths = getCardImagePaths(
                  displayName,
                  metadata?.set && metadata.set !== 'UNK' ? metadata.set : undefined
                );

                // Bottom card is index 0, top card is index visibleCards.length - 1
                const stackPosition = index;
                const zIndex = index + 1;

                return (
                  <motion.div
                    key={card.id}
                    className="absolute top-0 left-0 w-full rounded-lg overflow-hidden shadow-xl card-frame cursor-grab active:cursor-grabbing"
                    style={{
                      height: `${cardHeight}px`,
                      y: stackPosition * stackOffset,
                      zIndex: zIndex,
                    }}
                    whileHover={draggingCardId !== card.id ? { 
                      scale: 1.7,
                      y: -80,
                      zIndex: 1000,
                      transition: { duration: 0.2, delay: 0.8 }
                    } : undefined}
                  >
                    <div
                      draggable
                      onDragStart={(e) => handleDragStart(e, card.id)}
                      onDragEnd={(e) => handleDragEnd(e, card.id)}
                      onContextMenu={(e) => handleContextMenu(e, card.id)}
                      className="w-full h-full"
                    >
                      <img
                        src={imagePaths[0]}
                        alt={card.name}
                        className="w-full h-full object-cover"
                        style={{ imageRendering: 'crisp-edges' }}
                      />
                    </div>
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

      {/* Context Menu */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          options={getContextMenuOptions(contextMenu.cardId)}
          onClose={() => setContextMenu(null)}
        />
      )}
    </div>
  );
};

export default Graveyard;

