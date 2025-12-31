import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ContextMenu from './ContextMenu';
import { CardData } from '../types';
import { useCardDatabase } from '../context/CardDatabaseContext';
import { getCardImagePaths } from '../utils/cardDatabase';
import { useGameState } from '../context/GameStateWebSocket';
import { useCardScale } from '../context/CardScaleContext';

interface GraveyardProps {
  cards: CardData[];
}

const Graveyard: React.FC<GraveyardProps> = ({ cards }) => {
  const { getCard } = useCardDatabase();
  const { moveCard, toggleFaceDown } = useGameState();
  const { cardScale, hoverZoomValue } = useCardScale();
  const hoverZoomEnabled = hoverZoomValue > 1.0;
  const [draggingCardId, setDraggingCardId] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; cardId: string } | null>(null);
  const [showExpanded, setShowExpanded] = useState(false);

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
  
  // Separate cards into face-up and face-down (exiled) groups
  const faceUpCards = cards.filter(card => card.zone !== 'exile' && !card.faceDown);
  const faceDownCards = cards.filter(card => card.zone === 'exile' || card.faceDown);
  
  // Only show face-up cards in the main stack view (exiled cards are hidden)
  // Show up to 6 most recent face-up cards
  const maxVisible = 6;
  const visibleCards = faceUpCards.slice(-maxVisible);
  const baseCardHeight = 158;
  const cardHeight = Math.round(baseCardHeight * cardScale);
  const cardWidth = Math.round((cardHeight * 5) / 7); // Maintain aspect ratio
  const stackOffset = Math.round(24 * cardScale); // Scale stack offset too
  
  const handleDragStart = (e: React.DragEvent, cardId: string) => {
    console.log('🎴 Drag started from graveyard:', cardId);
    setDraggingCardId(cardId);
    e.dataTransfer.setData('cardId', cardId);
    e.dataTransfer.setData('sourceZone', 'graveyard');
  };
  
  const handleDragEnd = (e: React.DragEvent, cardId: string) => {
    setDraggingCardId(null);
    
    // First check if dropped back on graveyard itself - if so, do nothing
    const graveyardElement = document.getElementById('graveyard-zone');
    if (graveyardElement) {
      const graveyardRect = graveyardElement.getBoundingClientRect();
      if (
        e.clientX >= graveyardRect.left &&
        e.clientX <= graveyardRect.right &&
        e.clientY >= graveyardRect.top &&
        e.clientY <= graveyardRect.bottom
      ) {
        // Dropped back on graveyard, don't move
        return;
      }
    }
    
    // Check if dropped on library (with coordinate verification)
    const libraryElement = document.getElementById('library-zone');
    if (libraryElement) {
      const libraryRect = libraryElement.getBoundingClientRect();
      if (
        e.clientX >= libraryRect.left &&
        e.clientX <= libraryRect.right &&
        e.clientY >= libraryRect.top &&
        e.clientY <= libraryRect.bottom
      ) {
        console.log('Moving card from graveyard to library:', cardId);
        moveCard(cardId, 'library');
        return;
      }
    }
    
    // Check if dropped on hand
    const handElement = document.getElementById('hand-zone');
    if (handElement) {
      const handRect = handElement.getBoundingClientRect();
      if (
        e.clientX >= handRect.left &&
        e.clientX <= handRect.right &&
        e.clientY >= handRect.top &&
        e.clientY <= handRect.bottom
      ) {
        console.log('Moving card from graveyard to hand:', cardId);
        moveCard(cardId, 'hand', 0, 0);
        return;
      }
    }
    
    // Check if dropped on exile
    const exileElement = document.getElementById('exile-zone');
    if (exileElement) {
      const exileRect = exileElement.getBoundingClientRect();
      if (
        e.clientX >= exileRect.left &&
        e.clientX <= exileRect.right &&
        e.clientY >= exileRect.top &&
        e.clientY <= exileRect.bottom
      ) {
        console.log('Moving card from graveyard to exile (graveyard + face down):', cardId);
        moveCard(cardId, 'graveyard');
        toggleFaceDown(cardId);
        return;
      }
    }
    
    // Check if dropped on battlefield
    const battlefieldElement = document.getElementById('battlefield');
    if (battlefieldElement) {
      const rect = battlefieldElement.getBoundingClientRect();
      if (
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom
      ) {
        const x = e.clientX - rect.left - 75;
        const y = e.clientY - rect.top - 105;
        console.log('Moving card from graveyard to battlefield:', cardId, x, y);
        moveCard(cardId, 'battlefield', x, y);
        return;
      }
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
    
    
    // Get the dragged card ID from the data transfer
    const cardId = e.dataTransfer.getData('cardId');
    const sourceZone = e.dataTransfer.getData('sourceZone');
    const multipleCardIdsData = e.dataTransfer.getData('multipleCardIds');
    
    // Check if we're dragging multiple cards
    let cardIdsToMove: string[] = [];
    if (multipleCardIdsData) {
      try {
        cardIdsToMove = JSON.parse(multipleCardIdsData);
        console.log('📦 Dropping multiple cards to graveyard:', cardIdsToMove.length);
      } catch (e) {
        console.error('Failed to parse multipleCardIds:', e);
        cardIdsToMove = [];
      }
    }
    
    // If no multiple cards, use single card
    if (cardIdsToMove.length === 0 && cardId) {
      cardIdsToMove = [cardId];
    }
    
    console.log('📦 Drop data:', { cardIds: cardIdsToMove, sourceZone });
    
    if (cardIdsToMove.length > 0 && sourceZone !== 'graveyard') {
      console.log('✅ Moving', cardIdsToMove.length, 'card(s) to graveyard');
      cardIdsToMove.forEach(cardId => moveCard(cardId, 'graveyard', 0, 0));
    }
  };

  const handleContextMenu = (e: React.MouseEvent, cardId: string) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, cardId });
  };

  const getContextMenuOptions = (cardId: string) => {
    const card = cards.find(c => c.id === cardId);
    const isExiled = card?.zone === 'exile' || card?.faceDown;
    
    return [
      {
        label: isExiled ? '↩️ Return from Exile' : '🚫 Move to Exile',
        onClick: () => {
          if (isExiled) {
            // Return from exile: if in exile zone, move to graveyard; if faceDown, flip face up
            if (card?.zone === 'exile') {
              moveCard(cardId, 'graveyard');
            }
            if (card?.faceDown) {
              toggleFaceDown(cardId);
            }
          } else {
            // Move to exile: move to graveyard and flip face down
            moveCard(cardId, 'graveyard');
            if (!card?.faceDown) {
              toggleFaceDown(cardId);
            }
          }
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
        className="flex-1 fantasy-border rounded-lg relative overflow-visible transition-all cursor-pointer"
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
        onClick={(e) => {
          // Only open expanded view if clicking on the zone itself, not on cards
          if (e.target === e.currentTarget || (e.target as HTMLElement).closest('.graveyard-zone-background')) {
            setShowExpanded(true);
          }
        }}
      >
        {cards.length > 0 ? (
          <div className="absolute inset-0 flex items-start justify-center pt-2 graveyard-zone-background">
            <div 
              className="relative" 
              style={{ 
                height: `${cardHeight + (visibleCards.length - 1) * stackOffset}px`,
                width: `${cardWidth}px`
              }}
              onClick={(e) => {
                // Clicking on cards opens expanded view
                e.stopPropagation();
                setShowExpanded(true);
              }}
            >
              {visibleCards.map((card, index) => {
                const metadata = card.cardId ? getCard(card.cardId) : null;
                const displayName = metadata?.name || card.name;
                const imagePaths = getCardImagePaths(displayName);
                
                // Cards from exile zone or face-down cards should be shown upside down
                const isExiled = card.zone === 'exile' || card.faceDown;

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
                    whileHover={draggingCardId !== card.id && hoverZoomEnabled ? { 
                      scale: hoverZoomValue,
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
                      className="w-full h-full relative"
                    >
                      {isExiled ? (
                        <>
                          {/* Show card back for exiled/face-down cards */}
                          <img
                            src="/Magic_the_gathering-card_back.jpg"
                            alt="Card back"
                            className="w-full h-full object-cover"
                            style={{ imageRendering: 'crisp-edges' }}
                          />
                          {/* Show card name overlay */}
                          <div className="absolute bottom-2 left-0 right-0 text-center px-1">
                            <div className="bg-black/80 text-fantasy-gold text-xs font-bold px-2 py-1 rounded">
                              {displayName}
                            </div>
                          </div>
                        </>
                      ) : (
                        <img
                          src={imagePaths[0]}
                          alt={card.name}
                          className="w-full h-full object-cover"
                          style={{ imageRendering: 'crisp-edges' }}
                        />
                      )}
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
                <h3 className="text-fantasy-gold text-lg font-bold">Graveyard</h3>
                <p className="text-fantasy-gold/60 text-sm">{cards.length} cards</p>
              </div>
              
              <div className="grid grid-cols-4 gap-2">
                {[...faceUpCards, ...faceDownCards].map((card) => {
                  const metadata = card.cardId ? getCard(card.cardId) : getCard(card.name);
                  const displayName = metadata?.name || card.name;
                  const imagePaths = getCardImagePaths(displayName);
                  const isExiled = card.zone === 'exile' || card.faceDown;
                  
                  return (
                    <div
                      key={card.id}
                      className="rounded overflow-hidden shadow-lg cursor-pointer hover:scale-105 transition-transform relative group"
                      style={{ 
                        aspectRatio: '2.5/3.5'
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        // Click card to return to hand
                        moveCard(card.id, 'hand');
                        if (isExiled && card.faceDown) {
                          toggleFaceDown(card.id);
                        }
                        setShowExpanded(false);
                      }}
                      onContextMenu={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        // Right-click for context menu with more options
                        setContextMenu({ x: e.clientX, y: e.clientY, cardId: card.id });
                        setShowExpanded(false);
                      }}
                    >
                      {isExiled ? (
                        <>
                          <img
                            src="/Magic_the_gathering-card_back.jpg"
                            alt="Card back"
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute bottom-2 left-0 right-0 text-center px-1">
                            <div className="bg-black/80 text-fantasy-gold text-xs font-bold px-2 py-1 rounded">
                              {displayName}
                            </div>
                          </div>
                        </>
                      ) : (
                        <img
                          src={imagePaths[0]}
                          alt={displayName || 'Card'}
                          className="w-full h-full object-cover"
                        />
                      )}
                      {/* Hover overlay with quick actions */}
                      <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            moveCard(card.id, 'hand');
                            if (isExiled && card.faceDown) {
                              toggleFaceDown(card.id);
                            }
                            setShowExpanded(false);
                          }}
                          className="px-2 py-1 bg-fantasy-gold/80 hover:bg-fantasy-gold text-fantasy-dark text-xs font-bold rounded"
                          title="Return to Hand (or click card)"
                        >
                          ✋
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            const battlefieldElement = document.getElementById('battlefield');
                            if (battlefieldElement) {
                              const rect = battlefieldElement.getBoundingClientRect();
                              const centerX = rect.width / 2 - 75;
                              const centerY = rect.height / 2 - 105;
                              moveCard(card.id, 'battlefield', centerX, centerY);
                              if (isExiled && card.faceDown) {
                                toggleFaceDown(card.id);
                              }
                            }
                            setShowExpanded(false);
                          }}
                          className="px-2 py-1 bg-fantasy-gold/80 hover:bg-fantasy-gold text-fantasy-dark text-xs font-bold rounded"
                          title="Play to Battlefield"
                        >
                          🎴
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            moveCard(card.id, 'library');
                            if (isExiled && card.faceDown) {
                              toggleFaceDown(card.id);
                            }
                            setShowExpanded(false);
                          }}
                          className="px-2 py-1 bg-fantasy-gold/80 hover:bg-fantasy-gold text-fantasy-dark text-xs font-bold rounded"
                          title="Return to Library"
                        >
                          📚
                        </button>
                      </div>
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
    </div>
  );
};

export default Graveyard;

