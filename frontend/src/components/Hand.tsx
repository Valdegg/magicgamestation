import React, { useState } from 'react';
import { motion } from 'framer-motion';
import Card from './Card';
import ContextMenu from './ContextMenu';
import { CardData } from '../types';
import { useGameState } from '../context/GameStateWebSocket';
import { useCardScale } from '../context/CardScaleContext';

interface HandProps {
  cards: CardData[];
  height?: number;
}

const Hand: React.FC<HandProps> = ({ cards, height = 240 }) => {
  const { moveCard, reorderHand } = useGameState();
  const { hoverZoomValue } = useCardScale();
  const hoverZoomEnabled = hoverZoomValue > 1.0;
  const [draggingCardId, setDraggingCardId] = useState<string | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; cardId: string } | null>(null);
  
  // Calculate card size based on hand height (maintain aspect ratio)
  // Magic cards are ~2.5" x 3.5" = 5:7 ratio
  const cardHeight = Math.max(100, Math.min(300, height - 40)); // Leave padding
  const cardWidth = (cardHeight * 5) / 7;

  const handleCardDoubleClick = (cardId: string) => {
    console.log('🎴 Double-clicked card in hand, playing to battlefield:', cardId);
    // Play card to center of battlefield
    const battlefieldElement = document.getElementById('battlefield');
    if (battlefieldElement) {
      const rect = battlefieldElement.getBoundingClientRect();
      const centerX = rect.width / 2 - 75; // Offset by half card width
      const centerY = rect.height / 2 - 105; // Offset by half card height
      moveCard(cardId, 'battlefield', centerX, centerY);
    }
  };

  const handleDragStart = (e: React.DragEvent, cardId: string) => {
    console.log('🎴 Drag started from hand:', cardId);
    setDraggingCardId(cardId);
    e.dataTransfer.setData('cardId', cardId);
    e.dataTransfer.setData('text/plain', cardId); // For player targeting
    e.dataTransfer.setData('sourceZone', 'hand');
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnd = (e: React.DragEvent, cardId: string) => {
    console.log('🎴 Drag ended from hand:', {
      cardId,
      clientX: e.clientX,
      clientY: e.clientY,
      dragOverIndex
    });
    
    // Check if we're reordering within the hand
    if (dragOverIndex !== null && draggingCardId === cardId) {
      const currentIndex = cards.findIndex(c => c.id === cardId);
      if (currentIndex !== -1 && currentIndex !== dragOverIndex) {
        console.log(`🔄 Reordering hand: moving card from index ${currentIndex} to ${dragOverIndex}`);
        reorderHand(cardId, dragOverIndex);
      }
    } else {
      // Check library first (before other zones)
      const libraryElement = document.getElementById('library-zone');
      if (libraryElement) {
        const rect = libraryElement.getBoundingClientRect();
        if (
          e.clientX >= rect.left &&
          e.clientX <= rect.right &&
          e.clientY >= rect.top &&
          e.clientY <= rect.bottom
        ) {
          console.log('✅ Dropped on library!');
          moveCard(cardId, 'library');
    setDraggingCardId(null);
          setDragOverIndex(null);
          return;
        }
      }

      // Check graveyard
    const graveyardElement = document.getElementById('graveyard-zone');
    if (graveyardElement) {
      const rect = graveyardElement.getBoundingClientRect();

      
      if (
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom
      ) {
        console.log('✅ Dropped on graveyard!');
        moveCard(cardId, 'graveyard');
          setDraggingCardId(null);
          setDragOverIndex(null);
        return;
      }
    }

    // Check exile
    const exileElement = document.getElementById('exile-zone');
    if (exileElement) {
      const rect = exileElement.getBoundingClientRect();
      if (
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom
      ) {
        console.log('✅ Dropped on exile!');
        moveCard(cardId, 'exile');
          setDraggingCardId(null);
          setDragOverIndex(null);
        return;
      }
    }

    // Check battlefield
    const battlefieldElement = document.getElementById('battlefield');
    if (battlefieldElement) {
      const rect = battlefieldElement.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
        console.log('✅ Dropped on battlefield at', x, y);
        moveCard(cardId, 'battlefield', x, y);
          setDraggingCardId(null);
          setDragOverIndex(null);
        return;
      }
    }

    console.log('❌ No valid drop target found');
    }
    
    setDraggingCardId(null);
    setDragOverIndex(null);
  };

  // Calculate overlap based on card width
  const overlapAmount = Math.max(-cardWidth * 0.6, -60);

  // Drag over state for visual feedback
  const [isDragOver, setIsDragOver] = React.useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
    
    // If dragging a card from hand, allow reordering
    if (draggingCardId) {
      const currentIndex = cards.findIndex(c => c.id === draggingCardId);
      if (currentIndex !== -1) {
        // Check if mouse is near the start or end
        const containerRect = (e.currentTarget as HTMLElement).getBoundingClientRect();
        const mouseX = e.clientX;
        const startThreshold = containerRect.left + 50;
        const endThreshold = containerRect.right - 50;
        
        if (mouseX < startThreshold) {
          setDragOverIndex(0);
        } else if (mouseX > endThreshold) {
          setDragOverIndex(cards.length - 1);
        }
      }
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    // Only clear if we're actually leaving the hand container (not just moving to a child)
    const relatedTarget = e.relatedTarget as HTMLElement;
    const currentTarget = e.currentTarget as HTMLElement;
    
    if (!currentTarget.contains(relatedTarget)) {
    setIsDragOver(false);
      setDragOverIndex(null);
    }
  };

  const handleCardDragOver = (e: React.DragEvent, index: number) => {
    if (draggingCardId) {
      e.preventDefault();
      e.stopPropagation();
      const currentIndex = cards.findIndex(c => c.id === draggingCardId);
      
      // Don't show indicator if dragging over itself
      if (currentIndex === index) {
        return;
      }
      
      // Calculate insertion point based on mouse position relative to card center
      const cardElement = e.currentTarget as HTMLElement;
      const rect = cardElement.getBoundingClientRect();
      const mouseX = e.clientX;
      const cardCenterX = rect.left + rect.width / 2;
      
      // If mouse is on the right half, insert after this card
      // If mouse is on the left half, insert before this card
      let insertIndex = mouseX > cardCenterX ? index + 1 : index;
      
      // Clamp to valid range (accounting for the fact that we'll remove the card first)
      const maxIndex = currentIndex < index ? cards.length - 1 : cards.length - 1;
      insertIndex = Math.max(0, Math.min(insertIndex, maxIndex));
      
      setDragOverIndex(insertIndex);
    }
  };

  const handleCardDragLeave = () => {
    // Don't clear dragOverIndex immediately - wait for drop or drag end
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    console.log('✋ Hand zone received drop event');
    
    // Get the dragged card ID from the data transfer
    const cardId = e.dataTransfer.getData('cardId');
    const sourceZone = e.dataTransfer.getData('sourceZone');
    
    console.log('✋ Drop data:', { cardId, sourceZone, draggingCardId });
    
    // Handle drops from other zones (battlefield, library, etc.)
    if (cardId && sourceZone !== 'hand') {
      console.log('✅ Moving card to hand from', sourceZone, ':', cardId);
      moveCard(cardId, 'hand');
      setDraggingCardId(null);
      setDragOverIndex(null);
      return;
    }
    
    // Handle reordering within hand
    if (draggingCardId && dragOverIndex !== null) {
      const currentIndex = cards.findIndex(c => c.id === draggingCardId);
      if (currentIndex !== -1 && currentIndex !== dragOverIndex) {
        console.log(`🔄 Reordering hand: moving card from index ${currentIndex} to ${dragOverIndex}`);
        reorderHand(draggingCardId, dragOverIndex);
      }
    }
    
    setDraggingCardId(null);
    setDragOverIndex(null);
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
        label: '☠️ Move to Graveyard',
        onClick: () => {
          moveCard(cardId, 'graveyard');
        },
      },
    ];
  };

  return (
    <div 
      id="hand-zone"
      className="flex items-center justify-center transition-all rounded-lg px-4 mx-auto pointer-events-auto"
      style={{ 
        height: `${height}px`,
        width: 'fit-content',
        minWidth: '200px',
        overflowX: 'visible',
        overflowY: 'visible',
        background: isDragOver 
          ? 'linear-gradient(to top, rgba(40, 20, 20, 0.9) 0%, rgba(60, 15, 15, 0.6) 100%)'
          : 'linear-gradient(to top, rgba(40, 20, 20, 0.6) 0%, rgba(60, 15, 15, 0.0) 100%)',
        backdropFilter: isDragOver ? 'blur(4px)' : undefined,
        boxShadow: isDragOver 
          ? '0 0 30px rgba(212, 179, 107, 0.6), inset 0 0 30px rgba(212, 179, 107, 0.3)'
          : undefined,
        borderTop: isDragOver ? '2px solid #f4d589' : '1px solid rgba(212, 179, 107, 0.1)'
      }}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex gap-2 px-4" style={{ overflow: 'visible' }}>
        {cards.length === 0 ? (
          <div className="text-fantasy-gold/50 text-sm">
            Hand is empty
          </div>
        ) : (
          cards.map((card, index) => {
            const isDraggingThis = draggingCardId === card.id;
            const currentIndex = cards.findIndex(c => c.id === draggingCardId);
            const showInsertBefore = dragOverIndex === index && draggingCardId && currentIndex !== index;
            const showInsertAfter = dragOverIndex === index + 1 && draggingCardId && currentIndex !== index;
            
            return (
            <motion.div
              key={card.id}
              data-card-id={card.id}
              initial={{ opacity: 0, y: 50 }}
                animate={{ 
                  opacity: isDraggingThis ? 0.5 : 1, 
                  y: 0,
                  scale: (showInsertBefore || showInsertAfter) ? 1.05 : 1,
                }}
                transition={{ delay: index * 0.05, duration: 0.2 }}
                // Round transform values to prevent subpixel blur on high-DPI displays
                style={{
                  transform: 'translateZ(0)',
                }}
              style={{ 
                marginLeft: index > 0 ? `${overlapAmount}px` : '0',
                  overflow: 'visible',
                  position: 'relative',
                  zIndex: (showInsertBefore || showInsertAfter) ? 100 : isDraggingThis ? 50 : 1,
              }}
                onDragOver={(e) => handleCardDragOver(e, index)}
                onDragLeave={handleCardDragLeave}
                whileHover={!isDraggingThis && draggingCardId === null && hoverZoomEnabled ? { 
                scale: hoverZoomValue,
                y: -80,
                zIndex: 1000,
                transition: { duration: 0.2, delay: 0.8 }
              } : undefined}
              onDoubleClick={() => handleCardDoubleClick(card.id)}
            >
                {showInsertBefore && (
                  <div
                    style={{
                      position: 'absolute',
                      left: '-8px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      width: '4px',
                      height: '70%',
                      background: '#f4d589',
                      borderRadius: '2px',
                      boxShadow: '0 0 12px rgba(244, 213, 137, 0.9)',
                      zIndex: 1001,
                      pointerEvents: 'none'
                    }}
                  />
                )}
                {showInsertAfter && (
                  <div
                    style={{
                      position: 'absolute',
                      right: '-8px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      width: '4px',
                      height: '70%',
                      background: '#f4d589',
                      borderRadius: '2px',
                      boxShadow: '0 0 12px rgba(244, 213, 137, 0.9)',
                      zIndex: 1001,
                      pointerEvents: 'none'
                    }}
                  />
                )}
              <Card
                card={card}
                onTap={() => {}} // Cards in hand cannot be tapped
                  onContextMenu={(e) => handleContextMenu(e, card.id)}
                onDragStart={(e) => handleDragStart(e, card.id)}
                onDragEnd={(e) => handleDragEnd(e, card.id)}
                inHand
                cardWidth={cardWidth}
                cardHeight={cardHeight}
              />
            </motion.div>
            );
          })
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

export default Hand;

