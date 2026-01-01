import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useGameState } from '../context/GameStateWebSocket';
import { useCardScale, MIN_SCALE, MAX_SCALE, DEFAULT_SCALE, HOVER_ZOOM_VALUES, HOVER_ZOOM_LABELS, HoverZoomOption, OPPONENT_CARD_SIZE_VALUES, OPPONENT_CARD_SIZE_LABELS, OpponentCardSizeOption } from '../context/CardScaleContext';
import Battlefield from './Battlefield';
import Hand from './Hand';
import ControlPanel from './ControlPanel';
import OpponentPanel from './OpponentPanel';
import OpponentGraveyard from './OpponentGraveyard';
import Graveyard from './Graveyard';
import PhaseTracker from './PhaseTracker';
import OpponentCard from './OpponentCard';
import { Chat } from './Chat';
import DiceToken from './DiceToken';

interface GameViewProps {
  onBackToLobby?: () => void;
}

export default function GameView({ onBackToLobby }: GameViewProps) {
  const { 
    cards, 
    currentPhase, 
    nextPhase,
    setPhase,
    drawCard,
    turnNumber, 
    nextTurn,
    isConnected,
    playerId,
    activePlayerId,
    opponent,
    copyShareUrl,
    moveCard,
    targetingArrows,
    setTargetingArrow,
    clearTargetingArrows,
    diceTokens
  } = useGameState();
  const { cardScale, setCardScale, resetScale, hoverZoom, setHoverZoom, opponentCardSize, setOpponentCardSize, opponentCardSizeValue } = useCardScale();

  // Keep prop for backwards-compat; component currently navigates via URL/localStorage.
  void onBackToLobby;

  const handCards = cards.filter(card => card.zone === 'hand');
  const battlefieldCards = cards.filter(card => card.zone === 'battlefield');
  // Combine graveyard and exile cards - exile cards will be shown face down in graveyard
  const graveyardCards = cards.filter(card => card.zone === 'graveyard' || card.zone === 'exile');

  const leftPanelWidth = 220;
  const [handHeight, setHandHeight] = useState(180);
  const [opponentBattlefieldHeight, setOpponentBattlefieldHeight] = useState(220);
  const [isLeftPanelOpen, setIsLeftPanelOpen] = useState(true);
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(true);
  const rightPanelWidth = 180;

  const isDraggingRef = useRef<'bottom' | 'battlefield' | 'opponent' | null>(null);
  const [measuredOpponentWidth, setMeasuredOpponentWidth] = useState(0);
  const [measuredOpponentHeight, setMeasuredOpponentHeight] = useState(0);
  const opponentBattlefieldContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!opponentBattlefieldContainerRef.current) return;
    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        setMeasuredOpponentWidth(entry.contentRect.width);
        setMeasuredOpponentHeight(entry.contentRect.height);
      }
    });
    observer.observe(opponentBattlefieldContainerRef.current);
    return () => observer.disconnect();
  }, [opponent]); // Re-run when opponent changes (container becomes available)

  const mappedOpponentCards = React.useMemo(() => {
    if (!opponent || !opponent.battlefieldCards || opponent.battlefieldCards.length === 0) {
      if (opponent && opponent.battlefieldCards && opponent.battlefieldCards.length === 0) {
        // Only log once when cards array is empty (not on every render)
        const logKey = 'opponent-empty-battlefield';
        if (!(window as any)[logKey]) {
          console.log('[GameView] Opponent has no battlefield cards');
          (window as any)[logKey] = true;
        }
      }
      return [];
    }
    if (measuredOpponentWidth === 0 || measuredOpponentHeight === 0) {
      // Return cards without mapping if container not measured yet
      return opponent.battlefieldCards;
    }

    const cards = opponent.battlefieldCards;
    // Use current opponent card base dimensions (matches OpponentCard.tsx)
    const cardWidth = 156;
    const cardHeight = 217;
    const padding = 16; // Extra padding to keep cards away from borders
    
    // Account for global card scale and opponent card size multiplier
    // These are applied in OpponentCard.tsx, so we need to account for them here
    const finalCardWidth = cardWidth * cardScale * opponentCardSizeValue;
    const finalCardHeight = cardHeight * cardScale * opponentCardSizeValue;
    
    // Reference battlefield size - assume player's battlefield is approximately this size
    const REFERENCE_WIDTH = 1200;
    const REFERENCE_HEIGHT = 600;
    
    // Available space in opponent view
    const availableWidth = Math.max(0, measuredOpponentWidth - (padding * 2));
    const availableHeight = Math.max(0, measuredOpponentHeight - (padding * 2));
    
    // Helper to check if two cards overlap
    const checkOverlap = (x1: number, y1: number, x2: number, y2: number, w: number, h: number) => {
      const overlapMargin = 5; // Small margin to allow slight overlap
      return !(x1 + w - overlapMargin < x2 || x2 + w - overlapMargin < x1 || 
               y1 + h - overlapMargin < y2 || y2 + h - overlapMargin < y1);
    };
    
    // Check which cards overlap in their original positions (intentional overlaps)
    // Use base card dimensions to check original overlaps
    const originalCardWidth = 156; // Base card width
    const originalCardHeight = 217; // Base card height
    const intentionalOverlaps = new Set<string>();
    for (let i = 0; i < cards.length; i++) {
      for (let j = i + 1; j < cards.length; j++) {
        const card1 = cards[i];
        const card2 = cards[j];
        const x1 = card1.x || 0;
        const y1 = card1.y || 0;
        const x2 = card2.x || 0;
        const y2 = card2.y || 0;
        if (checkOverlap(x1, y1, x2, y2, originalCardWidth, originalCardHeight)) {
          // Store as a pair key (smaller index first for consistency)
          const pairKey = `${Math.min(i, j)}-${Math.max(i, j)}`;
          intentionalOverlaps.add(pairKey);
        }
      }
    }
    
    // Find actual Y range to utilize full vertical space
    const ys = cards.map(c => c.y || 0);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const rangeY = maxY - minY || 1;
    
    // Helper to calculate positions at a given layout scale
    // The layout scale is applied on top of the final card dimensions
    const calculatePositions = (layoutScale: number) => {
      const scaledCardWidth = finalCardWidth * layoutScale;
      const scaledCardHeight = finalCardHeight * layoutScale;
      
      // First, calculate initial positions
      const initialPositions = cards.map(card => {
        const cardX = card.x || 0;
        const cardY = card.y || 0;
        
        // Convert X to percentage of reference battlefield width
        const percentX = cardX / REFERENCE_WIDTH;
        
        // Convert Y to percentage of actual card range (0 to 1)
        // This ensures we use the full vertical space
        const percentY = rangeY > 0 ? (cardY - minY) / rangeY : 0.5;
        
        // Apply percentage to opponent view area with flipping
        const mappedX = padding + (1 - percentX) * (availableWidth - scaledCardWidth);
        // Flip Y: cards with highest Y (near player's hand) appear at top (low mappedY)
        const mappedY = padding + (1 - percentY) * (availableHeight - scaledCardHeight);

        return { 
          ...card, 
          x: mappedX, 
          y: mappedY,
          scale: layoutScale 
        };
      });
      
      // Compute bounding box of all cards
      const xs = initialPositions.map(p => p.x || 0);
      const ys = initialPositions.map(p => p.y || 0);
      const minX = Math.min(...xs);
      const maxX = Math.max(...xs.map(x => x + scaledCardWidth));
      const minYPos = Math.min(...ys);
      const maxYPos = Math.max(...ys.map(y => y + scaledCardHeight));
      
      const boundingBoxWidth = maxX - minX;
      const boundingBoxHeight = maxYPos - minYPos;
      
      // Calculate offset to center the bounding box
      const centerX = (availableWidth + padding * 2) / 2;
      const centerY = (availableHeight + padding * 2) / 2;
      const boundingBoxCenterX = minX + boundingBoxWidth / 2;
      const boundingBoxCenterY = minYPos + boundingBoxHeight / 2;
      const offsetX = centerX - boundingBoxCenterX;
      const offsetY = centerY - boundingBoxCenterY;
      
      // Apply offset and clamp positions to keep cards within bounds
      return initialPositions.map(pos => {
        const newX = pos.x + offsetX;
        const newY = pos.y + offsetY;
        
        // Clamp positions to keep cards fully within the opponent battlefield area
        const clampedX = Math.max(padding, Math.min(newX, availableWidth - scaledCardWidth + padding));
        const clampedY = Math.max(padding, Math.min(newY, availableHeight - scaledCardHeight + padding));

        return { 
          ...pos, 
          x: clampedX, 
          y: clampedY
        };
      });
    };
    
    // Helper to check if any cards overlap (excluding intentional overlaps)
    const hasOverlaps = (positions: typeof cards, layoutScale: number) => {
      const w = finalCardWidth * layoutScale;
      const h = finalCardHeight * layoutScale;
      for (let i = 0; i < positions.length; i++) {
        for (let j = i + 1; j < positions.length; j++) {
          // Skip if this overlap was intentional (present in original positions)
          const pairKey = `${Math.min(i, j)}-${Math.max(i, j)}`;
          if (intentionalOverlaps.has(pairKey)) {
            continue; // Allow intentional overlaps
          }
          // Only flag new overlaps that weren't in the original layout
          if (checkOverlap(positions[i].x || 0, positions[i].y || 0, 
                          positions[j].x || 0, positions[j].y || 0, w, h)) {
            return true;
          }
        }
      }
      return false;
    };
    
    // Start with ideal layout scale and reduce if overlaps detected
    // Layout scale is applied on top of the final card dimensions
    const widthScale = availableWidth / REFERENCE_WIDTH;
    const heightScale = availableHeight / REFERENCE_HEIGHT;
    // Base layout scale calculation - this is applied on top of finalCardWidth/Height
    let layoutScale = Math.max(0.25, Math.min(0.8, Math.min(widthScale, heightScale)));
    
    let positions = calculatePositions(layoutScale);
    
    // Reduce layout scale until no overlaps or minimum reached
    const MIN_SCALE = 0.15;
    const SCALE_STEP = 0.05;
    while (hasOverlaps(positions, layoutScale) && layoutScale > MIN_SCALE) {
      layoutScale -= SCALE_STEP;
      positions = calculatePositions(layoutScale);
    }
    
    return positions;
  }, [opponent, measuredOpponentWidth, measuredOpponentHeight, cardScale, opponentCardSizeValue]);

  const opponentPanelRef = useRef<HTMLDivElement>(null);
  const playerPanelRef = useRef<HTMLDivElement>(null);
  
  // Local arrows for immediate display + synced arrows from other players
  const [localArrows, setLocalArrows] = useState<Array<{ cardId: string; targetPlayerId?: string; targetCardId?: string; }>>([]);
  
  // Combine local arrows with synced arrows from opponent (but filter out our own arrows from synced to avoid duplicates)
  const allArrows = [
    ...localArrows,
    ...targetingArrows.filter(a => a.ownerPlayerId !== playerId)
  ];

  const handleCardTargetPlayer = (cardId: string, targetPlayerId: string) => {
    // Set locally for immediate display
    setLocalArrows(prev => [...prev.filter(a => a.cardId !== cardId), { cardId, targetPlayerId }]);
    // Also sync to backend for opponent
    setTargetingArrow(cardId, undefined, targetPlayerId);
  };

  const handleCardTargetCard = (cardId: string, targetCardId: string) => {
    // Set locally for immediate display
    setLocalArrows(prev => [...prev.filter(a => a.cardId !== cardId), { cardId, targetCardId }]);
    // Also sync to backend for opponent
    setTargetingArrow(cardId, targetCardId, undefined);
  };

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      // Don't clear on drag events or if target is a card
      const target = e.target as HTMLElement;
      if (target.closest('[data-card-id]') || target.closest('[draggable]')) return;
      if (localArrows.length > 0) {
        console.log('🧹 Clearing local targeting arrows on click');
        setLocalArrows([]);
        clearTargetingArrows();
      }
    };
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, [localArrows.length, clearTargetingArrows]);

  const handleDrag = (type: 'bottom' | 'battlefield' | 'opponent', e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingRef.current = type;
    const handleMouseMove = (ev: MouseEvent) => {
      if (isDraggingRef.current === 'opponent') {
        const container = document.querySelector('.flex-1.flex.flex-col') as HTMLElement;
        if (container) {
          const relativeY = ev.clientY - container.getBoundingClientRect().top;
          setOpponentBattlefieldHeight(Math.max(180, Math.min(500, relativeY)));
        }
      } else if (isDraggingRef.current === 'battlefield') {
        const container = document.querySelector('.flex-1.flex.flex-col') as HTMLElement;
        if (container) {
          const relativeY = ev.clientY - container.getBoundingClientRect().top;
          setOpponentBattlefieldHeight(Math.max(180, Math.min(600, relativeY - 76)));
        }
      } else if (isDraggingRef.current === 'bottom') {
        setHandHeight(Math.max(150, Math.min(400, window.innerHeight - ev.clientY - 8)));
      }
    };
    const handleMouseUp = () => {
      isDraggingRef.current = null;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  // Get the next phase in sequence
  const getNextPhase = (current: string): string | null => {
    const phaseOrder = ['untap', 'upkeep', 'draw', 'main_1', 'begin_combat', 'declare_attackers', 'declare_blockers', 'damage', 'end_combat', 'main_2', 'end_step', 'cleanup'];
    const currentIdx = phaseOrder.indexOf(current);
    if (currentIdx === -1 || currentIdx === phaseOrder.length - 1) return null;
    return phaseOrder[currentIdx + 1];
  };

  const handlePhaseClick = (phase: string, isDoubleClick: boolean = false) => {
    if (playerId !== activePlayerId) return;
    
    // If clicking "next", advance to next phase
    if (phase === 'next') {
      if (currentPhase === 'draw') {
        // Draw a card when moving from draw to main_1
        drawCard();
        setTimeout(() => {
          nextPhase();
        }, 100);
      } else {
        nextPhase();
      }
      return;
    }
    
    // Double-click: move to next phase (regardless of which phase button was clicked)
    if (isDoubleClick) {
      const nextPhaseId = getNextPhase(currentPhase);
      if (nextPhaseId) {
        // If we're currently in draw step, draw a card before moving to next phase
        if (currentPhase === 'draw') {
          drawCard();
          setTimeout(() => {
            setPhase(nextPhaseId);
          }, 100);
        } else {
          setPhase(nextPhaseId);
        }
      }
      return;
    }
    
    // Single click: jump directly to the clicked phase
    setPhase(phase);
  };

  const handleNewGame = () => window.open(window.location.origin, '_blank');

  return (
    <div className="w-screen h-screen flex flex-col" style={{ userSelect: 'none', overflowX: 'hidden', overflowY: 'visible' }}>
      {/* Header - hidden by default, shows on hover */}
      <div className="fixed top-0 left-0 right-0 z-[200] group">
        {/* Invisible hover trigger area - full width, 50px tall */}
        <div className="w-full h-[50px] absolute top-0 left-0" />
        {/* Subtle hint line in center */}
        <div className="w-full h-[8px] flex items-start justify-center relative z-10 pointer-events-none">
          <div className="w-24 h-[2px] mt-1 bg-fantasy-gold/30 rounded group-hover:bg-fantasy-gold/60 transition-colors" />
        </div>
        {/* Actual header content - hidden until hover */}
        <div className="h-[40px] flex items-center justify-between px-6 fantasy-panel opacity-0 group-hover:opacity-100 transition-opacity duration-300 mx-auto -mt-[8px]"
          style={{
            width: '95vw', maxWidth: '1600px',
            background: 'linear-gradient(to bottom, rgba(30, 20, 20, 0.95) 0%, rgba(20, 10, 10, 0.98) 100%)',
            borderBottom: '1px solid rgba(212, 179, 107, 0.6)',
            borderLeft: '1px solid rgba(212, 179, 107, 0.3)', borderRight: '1px solid rgba(212, 179, 107, 0.3)',
            borderRadius: '0 0 12px 12px',
            boxShadow: '0 0 15px rgba(212, 179, 107, 0.3), 0 4px 10px rgba(0, 0, 0, 0.5)',
          }}
        >
        <div className="flex items-center gap-4 z-10">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}
            style={{ boxShadow: isConnected ? '0 0 8px rgba(74, 222, 128, 0.8)' : '0 0 8px rgba(248, 113, 113, 0.8)' }}
            title={isConnected ? 'Connected' : 'Disconnected'}
          />
          <div className="px-4 py-0.5 rounded relative overflow-hidden" style={{ background: '#e3d5b8', border: '1px solid #8b7355', transform: 'skewX(-10deg)' }}>
            <div className="text-xs font-bold tracking-widest relative z-10" style={{ color: '#3e2723', fontFamily: "'Cinzel', serif", transform: 'skewX(10deg)' }}>
              TURN {turnNumber}
            </div>
          </div>
        </div>

        <div className="absolute left-1/2 -translate-x-1/2 top-0 h-[48px] flex items-center justify-center"
          style={{ clipPath: 'polygon(0 0, 100% 0, 95% 100%, 5% 100%)', width: '350px', background: 'linear-gradient(to bottom, rgba(30, 20, 20, 0.95) 0%, rgba(20, 10, 10, 0.98) 100%)' }}
        >
          <div className="absolute inset-0" style={{ borderBottom: '1px solid rgba(212, 179, 107, 0.8)', background: 'linear-gradient(to bottom, rgba(40, 30, 30, 1) 0%, rgba(20, 10, 10, 1) 100%)' }} />
          <div className="relative z-10 flex items-center justify-center gap-4 pb-1">
            <div className="text-xs font-bold tracking-[0.2em] whitespace-nowrap" style={{ color: '#f4d589', fontFamily: "'Cinzel', serif", textShadow: '0 0 10px rgba(212, 179, 107, 0.5), 0 2px 4px rgba(0,0,0,0.8)' }}>
              MAGIC GAMESTATION
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center gap-3">
          <motion.button onClick={copyShareUrl} className="px-2 py-1 text-xs font-bold text-fantasy-gold border border-fantasy-gold/30 rounded hover:bg-fantasy-gold/10 flex items-center gap-1" whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <span>📋</span> Share
          </motion.button>
          <motion.button onClick={handleNewGame} className="px-2 py-1 text-xs font-bold text-red-400 border border-red-400/30 rounded hover:bg-red-500/10 flex items-center gap-1" whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <span>🚪</span> Lobby
          </motion.button>
        </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-2 px-2 pb-0" style={{ overflowX: 'hidden', overflowY: 'visible' }}>
        {/* Left Sidebar */}
        <div className="flex-shrink-0 flex flex-col transition-all duration-300 ease-in-out relative" style={{ width: isLeftPanelOpen ? `${leftPanelWidth}px` : '0px', opacity: isLeftPanelOpen ? 1 : 0, overflow: 'visible' }}>
          <button onClick={() => setIsLeftPanelOpen(!isLeftPanelOpen)} className="absolute bottom-4 -right-8 w-8 h-20 rounded-r-lg bg-fantasy-burgundy/90 border-2 border-l-0 border-fantasy-gold/60 text-fantasy-gold flex items-center justify-center z-[100]">
            <span className="text-xl font-bold">{isLeftPanelOpen ? '‹' : '›'}</span>
          </button>
          <div className="flex flex-col gap-2 h-full pb-2" style={{ width: `${leftPanelWidth}px` }}>
            {opponent && opponent.handCount > 0 && (
              <div className="flex-shrink-0 fantasy-border rounded-lg px-2 py-2 flex flex-wrap justify-center gap-1" style={{ background: 'linear-gradient(135deg, rgba(40, 20, 20, 0.5) 0%, rgba(60, 15, 15, 0.6) 100%)' }}>
                {Array.from({ length: opponent.handCount }).map((_, i) => (
                  <motion.div key={i} className="rounded" style={{ width: '35px', height: '49px', backgroundImage: 'url(/Magic_the_gathering-card_back.jpg)', backgroundSize: 'cover' }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.02 }} />
                ))}
              </div>
            )}
            {opponent && <OpponentPanel ref={opponentPanelRef} name={opponent.name} life={opponent.life} libraryCount={opponent.libraryCount} isTheirTurn={opponent.id === activePlayerId} playerId={opponent.id} onCardDropped={handleCardTargetPlayer} />}
            <div ref={playerPanelRef} className="flex-1"><ControlPanel /></div>
          </div>
        </div>

        {/* Center Area */}
        <div className="flex-1 flex flex-col gap-2" style={{ overflow: 'visible' }}>
          {opponent && (
            <div className="flex-shrink-0 relative z-[100]" style={{ height: `${opponentBattlefieldHeight}px` }}>
              <div ref={opponentBattlefieldContainerRef} className="fantasy-border rounded-lg relative h-full" style={{ background: 'linear-gradient(135deg, rgba(40, 20, 20, 0.4) 0%, rgba(60, 15, 15, 0.5) 100%)', overflow: 'visible' }}>
                {mappedOpponentCards.length > 0 ? (() => {
                  // Calculate z-index range based on y coordinates: lower y = higher z-index
                  const maxY = Math.max(...mappedOpponentCards.map(c => c.y || 0));
                  const minY = Math.min(...mappedOpponentCards.map(c => c.y || 0));
                  const yRange = maxY - minY || 1;
                  
                  return mappedOpponentCards.map((card) => {
                    // Wrap each card in error boundary to prevent one bad card from breaking all cards
                    try {
                      if (!card || !card.id) {
                        console.warn(`[GameView] Skipping invalid opponent card:`, card);
                        return null;
                      }
                      // Cards with higher y get higher z-index (cards displayed lower appear on top)
                      const zIndex = 10 + Math.round((((card.y || 0) - minY) / yRange) * 100);
                      return <OpponentCard key={card.id} card={{...card, zIndex} as any} onCardTargeted={handleCardTargetCard} scale={card.scale || 1} />;
                  } catch (error) {
                    // Only log once per card to prevent flooding
                    const errorKey = `opponent-card-error-${card?.id || 'unknown'}`;
                    const lastLogged = (window as any)[errorKey];
                    const now = Date.now();
                    if (!lastLogged || now - lastLogged > 5000) {
                      console.error(`[GameView] Error rendering opponent card ${card?.id}:`, error);
                      (window as any)[errorKey] = now;
                    }
                    return null;
                  }
                  });
                })() : <div className="absolute inset-0 flex items-center justify-center text-[#8b7355] text-sm italic">No cards in play</div>}
                
                {/* Opponent's Dice Tokens */}
                {diceTokens
                  .filter(die => die.ownerPlayerId === opponent.id)
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
              </div>
            </div>
          )}
          
          {/* Resize handle between opponent and player battlefield */}
          <div className="h-1 cursor-row-resize hover:bg-fantasy-gold/50 transition-colors relative group" onMouseDown={(e) => handleDrag('opponent', e)}><div className="absolute inset-0 h-3 -top-1 group-hover:bg-fantasy-gold/20" /></div>

          <div className="flex-1 overflow-hidden pb-2" style={{ minHeight: '200px' }}>
            <div className="fantasy-border rounded-lg overflow-hidden h-full relative" style={{ paddingBottom: `${handHeight}px` }}>
              <Battlefield cards={battlefieldCards} />
              {/* Hand overlay + drop target (ONLY the visible hand frame, centered) */}
              <div
                id="hand-drop-area"
                className="absolute bottom-0 left-1/2 -translate-x-1/2 z-[5000]"
                style={{ height: `${handHeight}px`, width: 'fit-content' }}
                onDragOver={(e) => {
                  // Allow dropping onto the hand frame/cards
                  e.preventDefault();
                }}
                onDrop={(e) => {
                  // Only handle drops coming from other zones (battlefield, library, etc).
                  // If it's a hand->hand drag, let Hand.tsx handle reordering.
                  e.preventDefault();
                  e.stopPropagation();

                  const cardId = e.dataTransfer.getData('cardId');
                  const sourceZone = e.dataTransfer.getData('sourceZone');
                  const multipleCardIdsData = e.dataTransfer.getData('multipleCardIds');
                  
                  // Check if we're dragging multiple cards
                  let cardIdsToMove: string[] = [];
                  if (multipleCardIdsData) {
                    try {
                      cardIdsToMove = JSON.parse(multipleCardIdsData);
                      console.log('📦 Dropping multiple cards to hand:', cardIdsToMove.length);
                    } catch (e) {
                      console.error('Failed to parse multipleCardIds:', e);
                      cardIdsToMove = [];
                    }
                  }
                  
                  // If no multiple cards, use single card
                  if (cardIdsToMove.length === 0 && cardId) {
                    cardIdsToMove = [cardId];
                  }

                  if (cardIdsToMove.length > 0 && sourceZone && sourceZone !== 'hand') {
                    console.log('✅ Moving', cardIdsToMove.length, 'card(s) to hand');
                    cardIdsToMove.forEach(cardId => moveCard(cardId, 'hand'));
                  }
                }}
              >
                <div className="relative" style={{ width: 'fit-content', height: `${handHeight}px` }}>
                  <div
                    className="absolute top-0 left-0 right-0 h-2 cursor-row-resize hover:bg-fantasy-gold/50 relative z-50"
                    onMouseDown={(e) => handleDrag('bottom', e)}
                  />
                    <Hand cards={handCards} height={handHeight} />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Sidebar - Phase Tracker (always visible) + Graveyard/Exile (collapsible) */}
        <div className="flex-shrink-0 flex relative" style={{ overflow: 'visible' }}>
          {/* Vertical Phase Tracker - Always visible */}
          <div className="flex-shrink-0 h-full pt-14 pb-2">
            <PhaseTracker 
              currentPhase={currentPhase} 
              onPhaseClick={handlePhaseClick} 
              onEndTurn={nextTurn} 
              isMyTurn={playerId === activePlayerId}
              vertical
            />
          </div>
          
          {/* Graveyard/Exile Column - Collapsible */}
          <div className="flex-shrink-0 flex transition-all duration-300 ease-in-out relative" style={{ width: isRightPanelOpen ? `${rightPanelWidth}px` : '0px', opacity: isRightPanelOpen ? 1 : 0, overflow: 'visible' }}>
            <button onClick={() => setIsRightPanelOpen(!isRightPanelOpen)} className="absolute bottom-4 -left-8 w-8 h-20 rounded-l-lg bg-fantasy-burgundy/90 border-2 border-r-0 border-fantasy-gold/60 text-fantasy-gold flex items-center justify-center z-[100]">
              <span className="text-xl font-bold">{isRightPanelOpen ? '›' : '‹'}</span>
            </button>
            
            <div className="flex flex-col h-full" style={{ width: `${rightPanelWidth}px`, paddingBottom: '420px' }}>
              {opponent && opponent.graveyardCards && opponent.graveyardCards.length > 0 && (
                <div className="flex-shrink-0" style={{ height: '120px' }}>
                  <OpponentGraveyard cards={opponent.graveyardCards} opponentName={opponent.name} />
                </div>
              )}
              <div className="flex-1" style={{ minHeight: '100px' }} />
              <div className="flex-shrink-0 mt-20" style={{ height: '320px' }}><Graveyard cards={graveyardCards} /></div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Expand Buttons when collapsed */}
      {!isLeftPanelOpen && <button onClick={() => setIsLeftPanelOpen(true)} className="fixed bottom-4 left-0 w-6 h-16 rounded-r-lg bg-fantasy-burgundy/90 border-fantasy-gold/60 text-fantasy-gold flex items-center justify-center z-[100] shadow-lg">›</button>}
      {!isRightPanelOpen && <button onClick={() => setIsRightPanelOpen(true)} className="fixed bottom-4 right-0 w-6 h-16 rounded-l-lg bg-fantasy-burgundy/90 border-fantasy-gold/60 text-fantasy-gold flex items-center justify-center z-[100] shadow-lg">‹</button>}

      {/* Chat Component */}
      <Chat />

      {/* Targeting Arrows */}
      <svg style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 9999 }}>
        <defs><marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth"><polygon points="0 0, 10 3, 0 6" fill="#ef4444" /></marker></defs>
        {allArrows.map((arrow) => {
          console.log('🎯 Rendering arrow:', arrow);
          const startEl = document.querySelector(`[data-card-id="${arrow.cardId}"]`);
          if (!startEl) {
            console.log('   ⚠️ Start element not found for card:', arrow.cardId);
            return null;
          }
          const startRect = startEl.getBoundingClientRect();
          const startX = startRect.left + startRect.width / 2;
          const startY = startRect.top + startRect.height / 2;
          
          let endX = 0, endY = 0;
          if (arrow.targetPlayerId) {
             // If targeting opponent, use opponentPanelRef; if targeting self, use playerPanelRef
             const isTargetingOpponent = arrow.targetPlayerId === opponent?.id;
             const panel = isTargetingOpponent ? opponentPanelRef.current : playerPanelRef.current;
             console.log('   🎯 Player target:', { targetPlayerId: arrow.targetPlayerId, opponentId: opponent?.id, isTargetingOpponent, panelExists: !!panel });
             if (panel) { const r = panel.getBoundingClientRect(); endX = r.left + r.width/2; endY = r.top + r.height/2; }
          } else if (arrow.targetCardId) {
             const el = document.querySelector(`[data-card-id="${arrow.targetCardId}"]`);
             if (el) { const r = el.getBoundingClientRect(); endX = r.left + r.width/2; endY = r.top + r.height/2; }
          }
          
          return endX ? (
            <g key={arrow.cardId}>
              <line x1={startX + 2} y1={startY + 2} x2={endX + 2} y2={endY + 2} stroke="rgba(0,0,0,0.5)" strokeWidth="4" markerEnd="url(#arrowhead)" />
              <line x1={startX} y1={startY} x2={endX} y2={endY} stroke="#ef4444" strokeWidth="3" markerEnd="url(#arrowhead)" strokeDasharray="5,5">
                <animate attributeName="stroke-dashoffset" from="10" to="0" dur="0.5s" repeatCount="indefinite" />
              </line>
            </g>
          ) : null;
        })}
      </svg>

      {/* Card Settings - Bottom Left (in reserved space) */}
      <div 
        className="fixed bottom-4 z-[100] fantasy-border rounded-lg p-2 opacity-60 hover:opacity-100 transition-all duration-300 ease-in-out"
        style={{ 
          background: 'linear-gradient(135deg, rgba(40, 20, 20, 0.9) 0%, rgba(60, 15, 15, 0.95) 100%)',
          width: '200px',
          left: isLeftPanelOpen ? '10px' : '-210px',
          opacity: isLeftPanelOpen ? 0.6 : 0,
          pointerEvents: isLeftPanelOpen ? 'auto' : 'none'
        }}
      >
        {/* Card Size */}
        <div className="mb-1 w-full">
          <div className="flex items-center justify-between mb-1 w-full">
            <span className="text-[10px] text-fantasy-gold/80 font-bold flex-shrink-0">Card Size</span>
            <div className="flex items-center gap-1 flex-shrink-0">
              <span className="text-[10px] text-fantasy-gold font-bold whitespace-nowrap">{Math.round(cardScale * 100)}%</span>
              {cardScale !== DEFAULT_SCALE && (
                <button
                  onClick={resetScale}
                  className="text-[9px] text-fantasy-gold/60 hover:text-fantasy-gold px-1 rounded hover:bg-fantasy-gold/10 flex-shrink-0"
                  title="Reset to 100%"
                >
                  ↺
                </button>
              )}
            </div>
          </div>
          <input
            type="range"
            min={MIN_SCALE * 100}
            max={MAX_SCALE * 100}
            value={cardScale * 100}
            onChange={(e) => setCardScale(parseInt(e.target.value) / 100)}
            className="w-full h-1 bg-fantasy-burgundy/50 rounded-lg appearance-none cursor-pointer slider-thumb"
            style={{
              background: `linear-gradient(to right, rgba(244, 213, 137, 0.6) 0%, rgba(244, 213, 137, 0.6) ${((cardScale - MIN_SCALE) / (MAX_SCALE - MIN_SCALE)) * 100}%, rgba(60, 30, 30, 0.6) ${((cardScale - MIN_SCALE) / (MAX_SCALE - MIN_SCALE)) * 100}%, rgba(60, 30, 30, 0.6) 100%)`,
            }}
          />
        </div>
        
        {/* Hover Zoom */}
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-fantasy-gold/80 font-bold">Hover Zoom</span>
        </div>
        <div className="flex gap-1">
          {(Object.keys(HOVER_ZOOM_VALUES) as HoverZoomOption[]).map((option) => (
            <button
              key={option}
              onClick={() => setHoverZoom(option)}
              className={`flex-1 px-1 py-0.5 text-[9px] font-bold rounded transition-colors ${
                hoverZoom === option
                  ? 'bg-fantasy-gold/40 text-fantasy-gold'
                  : 'bg-fantasy-burgundy/30 text-fantasy-gold/60 hover:bg-fantasy-burgundy/50 hover:text-fantasy-gold/80'
              }`}
              title={`${HOVER_ZOOM_VALUES[option]}x`}
            >
              {HOVER_ZOOM_LABELS[option]}
            </button>
          ))}
        </div>

        {/* Opponent Card Size */}
        <div className="flex items-center justify-between mb-1 mt-2">
          <span className="text-[10px] text-fantasy-gold/80 font-bold">Opponent Size</span>
        </div>
        <div className="flex gap-1">
          {(Object.keys(OPPONENT_CARD_SIZE_VALUES) as OpponentCardSizeOption[]).map((option) => (
            <button
              key={option}
              onClick={() => setOpponentCardSize(option)}
              className={`flex-1 px-1 py-0.5 text-[9px] font-bold rounded transition-colors ${
                opponentCardSize === option
                  ? 'bg-fantasy-gold/40 text-fantasy-gold'
                  : 'bg-fantasy-burgundy/30 text-fantasy-gold/60 hover:bg-fantasy-burgundy/50 hover:text-fantasy-gold/80'
              }`}
              title={`${Math.round(OPPONENT_CARD_SIZE_VALUES[option] * 100)}%`}
            >
              {OPPONENT_CARD_SIZE_LABELS[option]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

