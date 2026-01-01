import React, { useState, useRef } from 'react';
import Card from './Card';
import ContextMenu from './ContextMenu';
import DiceToken from './DiceToken';
import { CardData } from '../types';
import { useGameState } from '../context/GameStateWebSocket';

interface BattlefieldProps {
  cards: CardData[];
}

const Battlefield: React.FC<BattlefieldProps> = ({ cards }) => {
  const { tapCard, moveCard, toggleFaceDown, playerId, attachCard, unattachCard, addCounter, createDie, diceTokens } = useGameState();
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    cardId: string;
  } | null>(null);
  const [draggedCard, setDraggedCard] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const battlefieldRef = useRef<HTMLDivElement>(null);
  
  // Multi-select state
  const [selectedCards, setSelectedCards] = useState<Set<string>>(new Set());
  const [selectionBox, setSelectionBox] = useState<{
    startX: number;
    startY: number;
    currentX: number;
    currentY: number;
  } | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const [attachingCardId, setAttachingCardId] = useState<string | null>(null);

  // Filter cards into hosts and attachments
  const hostCards = cards.filter(c => !c.attachedToId);
  const getAttachedCards = (hostId: string) => cards.filter(c => c.attachedToId === hostId);

  const handleCardClick = (e: React.MouseEvent, cardId: string) => {
    // Handle Attachment Mode
    if (attachingCardId) {
      if (attachingCardId === cardId) {
        setAttachingCardId(null); // Cancel if clicked self
        return;
      }
      
      console.log(`🔗 Attaching card ${attachingCardId} to ${cardId}`);
      attachCard(attachingCardId, cardId);
      
      setAttachingCardId(null);
      return;
    }

    if (e.ctrlKey || e.metaKey) {
      // Toggle selection with Ctrl/Cmd
      e.preventDefault();
      e.stopPropagation();
      setSelectedCards(prev => {
        const newSet = new Set(prev);
        if (newSet.has(cardId)) {
          newSet.delete(cardId);
        } else {
          newSet.add(cardId);
        }
        console.log('🎯 Selected cards:', Array.from(newSet));
        return newSet;
      });
    }
  };

  const handleCardContextMenu = (e: React.MouseEvent, cardId: string) => {
    e.preventDefault();
    // If card is not in selection, select only this card
    if (!selectedCards.has(cardId)) {
      setSelectedCards(new Set([cardId]));
    }
    setContextMenu({ x: e.clientX, y: e.clientY, cardId });
  };

  const handleDragStart = (e: React.DragEvent, card: CardData) => {
    // Check if this card is part of a selection
    const isSelected = selectedCards.has(card.id);
    const cardsToDrag = isSelected && selectedCards.size > 1 
      ? Array.from(selectedCards) 
      : [card.id];
    
    console.log('🎴 Drag started from battlefield:', card.id, isSelected ? `(with ${cardsToDrag.length} selected cards)` : '');
    setDraggedCard(card.id);
    
    // Set data for other zones to read
    e.dataTransfer.setData('cardId', card.id); // Primary card for compatibility
    e.dataTransfer.setData('text/plain', card.id); // For player targeting
    e.dataTransfer.setData('sourceZone', 'battlefield');
    
    // Store multiple card IDs if dragging selection
    if (cardsToDrag.length > 1) {
      e.dataTransfer.setData('multipleCardIds', JSON.stringify(cardsToDrag));
      
      // Calculate and store relative positions of all selected cards
      // Use the dragged card as the reference point
      const cardPositions: Record<string, { x: number; y: number }> = {};
      const referenceCard = cards.find(c => c.id === card.id);
      
      if (referenceCard && referenceCard.x !== undefined && referenceCard.y !== undefined) {
        const refX = referenceCard.x;
        const refY = referenceCard.y;
        
        cardsToDrag.forEach(cardId => {
          const cardData = cards.find(c => c.id === cardId);
          if (cardData && cardData.x !== undefined && cardData.y !== undefined) {
            // Store relative offset from the reference card
            cardPositions[cardId] = {
              x: cardData.x - refX,
              y: cardData.y - refY
            };
          }
        });
        
        e.dataTransfer.setData('cardRelativePositions', JSON.stringify(cardPositions));
        console.log('📍 Stored relative positions:', cardPositions);
      }
    }
    
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const handleDragEnd = () => {
    // Always clear dragged card when drag ends, regardless of where it was dropped
    setDraggedCard(null);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    

    const dropX = e.clientX;
    const dropY = e.clientY;
    
    if (!battlefieldRef.current) {
      console.log('⚠️ Battlefield handleDrop: No battlefield ref');
      return;
    }

    // Check if this is a die drop
    const dragType = e.dataTransfer.getData('dragType');
    console.log('🎯 dragType:', dragType);
    if (dragType === 'lifeDie') {
      const rect = battlefieldRef.current.getBoundingClientRect();
      const x = dropX - rect.left;
      const y = dropY - rect.top;
      const dieType = e.dataTransfer.getData('dieType') || 'd20';
      console.log('🎲 Dropped die on battlefield at', x, y);
      createDie(x, y, dieType);
      return;
    }

    // Check if this is an external drag (from hand, library, etc.)
    const externalCardId = e.dataTransfer.getData('cardId');
    const sourceZone = e.dataTransfer.getData('sourceZone');
    const multipleCardIdsData = e.dataTransfer.getData('multipleCardIds');
    
    // Check if we're dragging multiple cards (from selection)
    let cardIdsToMove: string[] = [];
    if (multipleCardIdsData) {
      try {
        cardIdsToMove = JSON.parse(multipleCardIdsData);
        console.log('🎴 Dragging multiple cards:', cardIdsToMove.length);
      } catch (e) {
        console.error('Failed to parse multipleCardIds:', e);
        cardIdsToMove = [];
      }
    }
    
    // If no multiple cards, use single card
    if (cardIdsToMove.length === 0) {
      const cardId = draggedCard || externalCardId;
      if (!cardId) {
        console.log('⚠️ Battlefield handleDrop: No card ID');
        return;
      }
      cardIdsToMove = [cardId];
    }
    
    console.log('🎴 Drop event on battlefield:', {
      cardIds: cardIdsToMove,
      sourceZone: sourceZone,
      dropX,
      dropY
    });

    // Get the element at the drop point
    const elementAtPoint = document.elementFromPoint(dropX, dropY);
    console.log('🎯 Element at drop point:', elementAtPoint?.id, elementAtPoint?.className);

    // Check if dropped on graveyard
    const graveyardElement = document.getElementById('graveyard-zone');
    if (graveyardElement) {
      const graveyardRect = graveyardElement.getBoundingClientRect();

      
      // Check if dropped on graveyard or if the element at drop point is inside graveyard
      const isOnGraveyard = (dropX >= graveyardRect.left && dropX <= graveyardRect.right && dropY >= graveyardRect.top && dropY <= graveyardRect.bottom) ||
                            graveyardElement.contains(elementAtPoint);
      
      if (isOnGraveyard) {
        console.log('✅ Dropped', cardIdsToMove.length, 'card(s) on graveyard!');
        cardIdsToMove.forEach(cardId => moveCard(cardId, 'graveyard'));
        setDraggedCard(null);
        setSelectedCards(new Set()); // Clear selection after moving
        return;
      }
    }

    // Check if dropped on library
    const libraryElement = document.getElementById('library-zone');
    if (libraryElement) {
      const libraryRect = libraryElement.getBoundingClientRect();
      
      // Check if dropped on library or if the element at drop point is inside library
      const isOnLibrary = (dropX >= libraryRect.left && dropX <= libraryRect.right && dropY >= libraryRect.top && dropY <= libraryRect.bottom) ||
                          libraryElement.contains(elementAtPoint);
      
      if (isOnLibrary) {
        console.log('✅ Dropped', cardIdsToMove.length, 'card(s) on library!');
        cardIdsToMove.forEach(cardId => moveCard(cardId, 'library'));
        setDraggedCard(null);
        setSelectedCards(new Set()); // Clear selection after moving
        return;
      }
    }

    // Check if dropped on exile
    // Exile zone removed - cards are now shown in graveyard face down
    // This check is kept for backwards compatibility but won't trigger
    const exileElement = document.getElementById('exile-zone');
    if (exileElement) {
      const exileRect = exileElement.getBoundingClientRect();
      const isOnExile = (dropX >= exileRect.left && dropX <= exileRect.right && dropY >= exileRect.top && dropY <= exileRect.bottom) ||
                        exileElement.contains(elementAtPoint);
      
      if (isOnExile) {
        console.log('✅ Dropped', cardIdsToMove.length, 'card(s) to exile (graveyard + face down)!');
        cardIdsToMove.forEach(cardId => {
          moveCard(cardId, 'graveyard');
          toggleFaceDown(cardId);
        });
        setDraggedCard(null);
        setSelectedCards(new Set());
        return;
      }
    }

    // Otherwise, place on battlefield
    const rect = battlefieldRef.current.getBoundingClientRect();
    // For external drops, use the drop position directly
    // For internal moves, use the drag offset
    // Adjusted centering for 150x210 cards (75, 105)
    const baseX = draggedCard ? e.clientX - rect.left - dragOffset.x : e.clientX - rect.left - 75;
    const baseY = draggedCard ? e.clientY - rect.top - dragOffset.y : e.clientY - rect.top - 105;

    // Check if we have relative positions stored (for multiple card drag)
    const relativePositionsData = e.dataTransfer.getData('cardRelativePositions');
    let relativePositions: Record<string, { x: number; y: number }> = {};
    
    if (relativePositionsData && cardIdsToMove.length > 1) {
      try {
        relativePositions = JSON.parse(relativePositionsData);
        console.log('📍 Using stored relative positions:', relativePositions);
      } catch (e) {
        console.error('Failed to parse cardRelativePositions:', e);
      }
    }

    // Move all cards, preserving relative positions if available
    cardIdsToMove.forEach((cardId) => {
      if (relativePositions[cardId] && Object.keys(relativePositions).length > 0) {
        // Use stored relative position
        const newX = Math.round(baseX + relativePositions[cardId].x);
        const newY = Math.round(baseY + relativePositions[cardId].y);
        console.log(`📍 Moving card ${cardId} to (${newX}, ${newY}) with offset (${relativePositions[cardId].x}, ${relativePositions[cardId].y})`);
        moveCard(cardId, 'battlefield', newX, newY);
      } else {
        // Single card or no relative positions - use base position
        moveCard(cardId, 'battlefield', Math.round(baseX), Math.round(baseY));
      }
    });
    
    setDraggedCard(null);
    if (cardIdsToMove.length > 1) {
      setSelectedCards(new Set()); // Clear selection after moving multiple cards
    }
  };

  // Box selection handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    // Only start selection on empty battlefield area (not on cards)
    if (e.button !== 0 || e.target !== e.currentTarget) return;
    
    const rect = battlefieldRef.current?.getBoundingClientRect();
    if (!rect) return;

    setIsSelecting(true);
    setSelectionBox({
      startX: e.clientX - rect.left,
      startY: e.clientY - rect.top,
      currentX: e.clientX - rect.left,
      currentY: e.clientY - rect.top,
    });
    
    // Clear selection if not holding Ctrl/Cmd
    if (!e.ctrlKey && !e.metaKey) {
      setSelectedCards(new Set());
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isSelecting || !selectionBox) return;
    
    const rect = battlefieldRef.current?.getBoundingClientRect();
    if (!rect) return;

    setSelectionBox({
      ...selectionBox,
      currentX: e.clientX - rect.left,
      currentY: e.clientY - rect.top,
    });

    // Calculate selection box bounds
    const minX = Math.min(selectionBox.startX, e.clientX - rect.left);
    const maxX = Math.max(selectionBox.startX, e.clientX - rect.left);
    const minY = Math.min(selectionBox.startY, e.clientY - rect.top);
    const maxY = Math.max(selectionBox.startY, e.clientY - rect.top);

    // Check which cards are in the selection box
    const newSelection = new Set<string>();
    cards.forEach(card => {
      const cardX = card.x ?? 0;
      const cardY = card.y ?? 0;
      const cardWidth = 119; // Updated to match new Card size (10% larger)
      const cardHeight = 166; // Updated to match new Card size

      // Check if card overlaps with selection box
      if (
        cardX < maxX &&
        cardX + cardWidth > minX &&
        cardY < maxY &&
        cardY + cardHeight > minY
      ) {
        newSelection.add(card.id);
      }
    });

    setSelectedCards(newSelection);
  };

  const handleMouseUp = () => {
    setIsSelecting(false);
    setSelectionBox(null);
  };

  // addCounter is now from useGameState

  const getContextMenuOptions = (cardId: string) => {
    const targetCards = selectedCards.has(cardId) ? Array.from(selectedCards) : [cardId];
    const isMultiple = targetCards.length > 1;
    const card = cards.find(c => c.id === cardId);
    
    const options = [
      {
        label: isMultiple ? `⚡ Tap/Untap (${targetCards.length} cards)` : '⚡ Tap/Untap',
        onClick: () => {
          console.log('⚡ Tapping cards via context menu:', targetCards);
          targetCards.forEach(id => tapCard(id));
          setSelectedCards(new Set());
        },
      },
      {
        label: isMultiple ? `🎭 Flip Face Down/Up (${targetCards.length} cards)` : '🎭 Flip Face Down/Up',
        onClick: () => {
          targetCards.forEach(id => toggleFaceDown(id));
          setSelectedCards(new Set());
        },
      },
    ];

    // Only show Attach option for single card selection
    if (!isMultiple) {
      options.push({
        label: '🔗 Attach to...',
        onClick: () => {
          setAttachingCardId(cardId);
          setSelectedCards(new Set());
          // Show a toast or some indicator?
        },
      });

      // If card is already attached, show Unattach
      if (card?.attachedToId) {
        options.push({
          label: '💔 Unattach',
          onClick: () => {
            unattachCard(cardId);
          },
        });
      }
    }

    options.push(
      {
        label: '➕ Add +1/+1 Counter',
        onClick: () => {
          targetCards.forEach(id => addCounter(id, '+1/+1', 1));
          setSelectedCards(new Set());
        },
      },
      {
        label: '➖ Remove +1/+1 Counter',
        onClick: () => {
          targetCards.forEach(id => addCounter(id, '+1/+1', -1));
          setSelectedCards(new Set());
        },
      },
      {
        label: isMultiple ? `☠️ Move to Graveyard (${targetCards.length} cards)` : '☠️ Move to Graveyard',
        onClick: () => {
          console.log('☠️ Moving to graveyard via context menu:', targetCards);
          targetCards.forEach(id => moveCard(id, 'graveyard'));
          setSelectedCards(new Set());
        },
      },
      {
        label: isMultiple ? `🚫 Move to Exile (${targetCards.length} cards)` : '🚫 Move to Exile',
        onClick: () => {
          targetCards.forEach(id => {
            moveCard(id, 'graveyard');
            toggleFaceDown(id);
          });
          setSelectedCards(new Set());
        },
      },
      {
        label: isMultiple ? `✋ Return to Hand (${targetCards.length} cards)` : '✋ Return to Hand',
        onClick: () => {
          targetCards.forEach(id => moveCard(id, 'hand'));
          setSelectedCards(new Set());
        },
      },
    );
    
    return options;
  };

  return (
    <div
      id="battlefield"
      ref={battlefieldRef}
      className="relative w-full h-full bg-gradient-to-br from-fantasy-dark/80 to-fantasy-burgundy/40 overflow-visible"
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{
        backgroundImage: `
          radial-gradient(circle at 20% 30%, rgba(212, 179, 107, 0.03) 0%, transparent 50%),
          radial-gradient(circle at 80% 70%, rgba(107, 26, 26, 0.05) 0%, transparent 50%)
        `,
        cursor: isSelecting ? 'crosshair' : 'default',
      }}
    >

      {/* Attaching Indicator */}
      {attachingCardId && (
        <div className="absolute top-12 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-4 py-2 rounded-full shadow-lg z-50 animate-pulse border-2 border-white font-bold">
          Select target card to attach...
          <button 
            onClick={(e) => { e.stopPropagation(); setAttachingCardId(null); }}
            className="ml-3 text-blue-200 hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {/* Cards */}
      {hostCards.map((card) => (
        <div
          key={card.id}
          data-card-id={card.id}
          className="absolute"
          style={{
            left: Math.round(card.x ?? 0),
            top: Math.round(card.y ?? 0),
            zIndex: card.tapped ? 1 : 10, // Tapped cards lower z-index? No, maybe higher? Default is fine.
          }}
          onClick={(e) => handleCardClick(e, card.id)}
        >
          {/* Render Attached Cards - Rendered first so they appear behind */}
          {getAttachedCards(card.id).map((attachedCard, index) => (
            <div
              key={attachedCard.id}
              className="absolute"
              style={{
                // Offset attached cards slightly more to be visible
                top: 30 + (index * 15),
                left: 30 + (index * 15),
                zIndex: index, // Explicit positive stack order among attachments
                pointerEvents: 'auto', // Allow interactions
              }}
              onClick={(e) => {
                e.stopPropagation();
                handleCardClick(e, attachedCard.id);
              }}
            >
              <Card
                card={attachedCard}
                onTap={() => tapCard(attachedCard.id)}
                onContextMenu={(e) => handleCardContextMenu(e, attachedCard.id)}
                onDragStart={(e) => handleDragStart(e, attachedCard)}
                onDragEnd={handleDragEnd}
                disableHover={draggedCard === attachedCard.id}
                // Make attached cards same size or slightly smaller?
                cardWidth={119}
                cardHeight={166}
              />
               {/* Selection indicator for attached card */}
              {selectedCards.has(attachedCard.id) && (
                <div
                  className="absolute inset-0 pointer-events-none rounded-lg"
                  style={{
                    border: '3px solid rgba(59, 130, 246, 0.8)',
                    boxShadow: '0 0 12px rgba(59, 130, 246, 0.6), inset 0 0 12px rgba(59, 130, 246, 0.3)',
                  }}
                />
              )}
            </div>
          ))}

          {/* Render Host Card - Rendered last so it appears on top */}
          <div style={{ position: 'relative', zIndex: 100 }}>
          <Card
            card={card}
            onTap={() => tapCard(card.id)}
            onContextMenu={(e) => handleCardContextMenu(e, card.id)}
            onDragStart={(e) => handleDragStart(e, card)}
            onDragEnd={handleDragEnd}
            disableHover={draggedCard === card.id}
          />
            {/* Selection indicator for host card */}
          {selectedCards.has(card.id) && (
            <div
              className="absolute inset-0 pointer-events-none rounded-lg"
              style={{
                border: '3px solid rgba(59, 130, 246, 0.8)',
                boxShadow: '0 0 12px rgba(59, 130, 246, 0.6), inset 0 0 12px rgba(59, 130, 246, 0.3)',
              }}
            />
          )}
        </div>
        </div>
      ))}

      {/* Dice Tokens - Only show dice owned by this player */}
      {diceTokens
        .filter(die => die.ownerPlayerId === playerId)
        .map((die) => (
          <DiceToken
            key={die.id}
            id={die.id}
            x={die.x}
            y={die.y}
            value={die.value}
            ownerPlayerId={die.ownerPlayerId}
            dieType={die.dieType}
            isRolling={die.value === null}
          />
        ))}

      {/* Selection box */}
      {isSelecting && selectionBox && (
        <div
          className="absolute pointer-events-none"
          style={{
            left: Math.min(selectionBox.startX, selectionBox.currentX),
            top: Math.min(selectionBox.startY, selectionBox.currentY),
            width: Math.abs(selectionBox.currentX - selectionBox.startX),
            height: Math.abs(selectionBox.currentY - selectionBox.startY),
            border: '2px dashed rgba(59, 130, 246, 0.8)',
            background: 'rgba(59, 130, 246, 0.1)',
            zIndex: 1000,
          }}
        />
      )}

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

export default Battlefield;

