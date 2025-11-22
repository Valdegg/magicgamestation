import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useGameState } from '../context/GameStateWebSocket';
import Battlefield from './Battlefield';
import Hand from './Hand';
import ControlPanel from './ControlPanel';
import OpponentPanel from './OpponentPanel';
import OpponentGraveyard from './OpponentGraveyard';
import Graveyard from './Graveyard';
import ZonePiles from './ZonePiles';
import PhaseTracker from './PhaseTracker';
import OpponentCard from './OpponentCard';

interface GameViewProps {
  onBackToLobby?: () => void;
}

export default function GameView({ onBackToLobby }: GameViewProps) {
  const { 
    cards, 
    currentPhase, 
    nextPhase, 
    drawCard,
    turnNumber, 
    nextTurn,
    isConnected,
    playerId,
    activePlayerId,
    opponent,
    copyShareUrl
  } = useGameState();

  const handCards = cards.filter(card => card.zone === 'hand');
  const battlefieldCards = cards.filter(card => card.zone === 'battlefield');
  const graveyardCards = cards.filter(card => card.zone === 'graveyard');
  const exileCards = cards.filter(card => card.zone === 'exile');

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
  }, []);

  const mappedOpponentCards = React.useMemo(() => {
    if (!opponent || !opponent.battlefieldCards || opponent.battlefieldCards.length === 0) return [];
    if (measuredOpponentWidth === 0 || measuredOpponentHeight === 0) return opponent.battlefieldCards;

    const cards = opponent.battlefieldCards;
    const cardWidth = 90;
    const cardHeight = 126;
    const padding = 10;

    const xs = cards.map(c => c.x || 0);
    const ys = cards.map(c => c.y || 0);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const groupWidth = rangeX + cardWidth;
    const groupHeight = rangeY + cardHeight;
    const availableWidth = Math.max(0, measuredOpponentWidth - (padding * 2));
    const availableHeight = Math.max(0, measuredOpponentHeight - (padding * 2));

    const scale = Math.min(availableWidth / groupWidth, availableHeight / groupHeight);
    const scaledGroupWidth = groupWidth * scale;
    const scaledGroupHeight = groupHeight * scale;
    const scaledCardWidth = cardWidth * scale;
    const scaledCardHeight = cardHeight * scale;

    const offsetX = padding + (availableWidth - scaledGroupWidth) / 2;
    const offsetY = padding + (availableHeight - scaledGroupHeight) / 2;

    return cards.map(card => {
      const cardX = card.x || minX;
      const cardY = card.y || minY;
      const scaledX = (cardX - minX) * scale;
      const scaledY = (cardY - minY) * scale;
      
      return { 
        ...card, 
        x: offsetX + (scaledGroupWidth - scaledX - scaledCardWidth), 
        y: offsetY + (scaledGroupHeight - scaledY - scaledCardHeight), 
        scale 
      };
    });
  }, [opponent, measuredOpponentWidth, measuredOpponentHeight]);

  const [targetingArrows, setTargetingArrows] = useState<Array<{ cardId: string; targetPlayerId?: string; targetCardId?: string; }>>([]);
  const opponentPanelRef = useRef<HTMLDivElement>(null);
  const playerPanelRef = useRef<HTMLDivElement>(null);

  const handleCardTargetPlayer = (cardId: string, targetPlayerId: string) => {
    setTargetingArrows(prev => [...prev.filter(arrow => arrow.cardId !== cardId), { cardId, targetPlayerId }]);
  };

  const handleCardTargetCard = (cardId: string, targetCardId: string) => {
    setTargetingArrows(prev => [...prev.filter(arrow => arrow.cardId !== cardId), { cardId, targetCardId }]);
  };

  useEffect(() => {
    const handleClick = () => targetingArrows.length > 0 && setTargetingArrows([]);
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, [targetingArrows.length]);

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

  const handlePhaseClick = () => {
    if (playerId !== activePlayerId) return;
    if (currentPhase === 'upkeep') {
      drawCard();
      setTimeout(nextPhase, 100);
    }
    nextPhase();
  };

  const handleNewGame = () => window.open(window.location.origin, '_blank');

  return (
    <div className="w-screen h-screen flex flex-col" style={{ userSelect: 'none', overflowX: 'hidden', overflowY: 'visible' }}>
      {/* Header */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 z-[50] h-[40px] flex items-center justify-between px-6 fantasy-panel"
        style={{
          width: '95%', maxWidth: '1600px',
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
          style={{ clipPath: 'polygon(0 0, 100% 0, 95% 100%, 5% 100%)', width: '500px', background: 'linear-gradient(to bottom, rgba(30, 20, 20, 0.95) 0%, rgba(20, 10, 10, 0.98) 100%)' }}
        >
          <div className="absolute inset-0" style={{ borderBottom: '1px solid rgba(212, 179, 107, 0.8)', background: 'linear-gradient(to bottom, rgba(40, 30, 30, 1) 0%, rgba(20, 10, 10, 1) 100%)' }} />
          <div className="relative z-10 flex items-center justify-center gap-4 pb-1">
            <div className="text-xs font-bold tracking-[0.2em] whitespace-nowrap" style={{ color: '#f4d589', fontFamily: "'Cinzel', serif", textShadow: '0 0 10px rgba(212, 179, 107, 0.5), 0 2px 4px rgba(0,0,0,0.8)' }}>
              MAGIC WORKSTATION
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

      {/* Main Content */}
      <div className="flex-1 flex gap-2 px-2 pb-0" style={{ overflowX: 'hidden', overflowY: 'visible' }}>
        {/* Left Sidebar */}
        <div className="flex-shrink-0 flex flex-col transition-all duration-300 ease-in-out relative" style={{ width: isLeftPanelOpen ? `${leftPanelWidth}px` : '0px', opacity: isLeftPanelOpen ? 1 : 0, overflow: 'visible' }}>
          <button onClick={() => setIsLeftPanelOpen(!isLeftPanelOpen)} className="absolute top-1/2 -right-8 w-8 h-20 rounded-r-lg bg-fantasy-burgundy/90 border-2 border-l-0 border-fantasy-gold/60 text-fantasy-gold flex items-center justify-center z-[100]" style={{ transform: 'translateY(-50%)' }}>
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
            <div className="flex-1"><ControlPanel /></div>
          </div>
        </div>

        {/* Center Area */}
        <div className="flex-1 flex flex-col gap-2" style={{ overflow: 'visible' }}>
          {opponent && (
            <div className="flex-shrink-0" style={{ height: `${opponentBattlefieldHeight}px` }}>
              <div ref={opponentBattlefieldContainerRef} className="fantasy-border rounded-lg relative h-full overflow-hidden" style={{ background: 'linear-gradient(135deg, rgba(40, 20, 20, 0.4) 0%, rgba(60, 15, 15, 0.5) 100%)' }}>
                {mappedOpponentCards.length > 0 ? mappedOpponentCards.map(card => (
                  <OpponentCard key={card.id} card={card} onCardTargeted={handleCardTargetCard} scale={card.scale || 1} />
                )) : <div className="absolute inset-0 flex items-center justify-center text-[#8b7355] text-sm italic">No cards in play</div>}
              </div>
            </div>
          )}
          
          <div className="h-1 cursor-row-resize hover:bg-fantasy-gold/50 transition-colors relative group" onMouseDown={(e) => handleDrag('opponent', e)}><div className="absolute inset-0 h-3 -top-1 group-hover:bg-fantasy-gold/20" /></div>
          <div className="flex-shrink-0"><PhaseTracker currentPhase={currentPhase} onPhaseClick={handlePhaseClick} onEndTurn={nextTurn} isMyTurn={playerId === activePlayerId} /></div>
          <div className="h-1 cursor-row-resize hover:bg-fantasy-gold/50 transition-colors relative group" onMouseDown={(e) => handleDrag('battlefield', e)}><div className="absolute inset-0 h-3 -top-1 group-hover:bg-fantasy-gold/20" /></div>

          <div className="flex-1 overflow-hidden pb-2" style={{ minHeight: '200px' }}>
            <div className="fantasy-border rounded-lg overflow-hidden h-full relative" style={{ paddingBottom: `${handHeight}px` }}>
              <Battlefield cards={battlefieldCards} />
              <div className="absolute bottom-0 left-0 right-0 flex gap-2 px-2 z-50" style={{ height: `${handHeight}px`, pointerEvents: 'none' }}>
                <div className="flex-1 flex justify-center items-end" style={{ pointerEvents: 'none' }}>
                  <div className="relative" style={{ width: 'fit-content', pointerEvents: 'auto' }}>
                    <div className="absolute top-0 left-0 right-0 h-2 cursor-row-resize hover:bg-fantasy-gold/50 relative z-50" onMouseDown={(e) => handleDrag('bottom', e)} />
                    <Hand cards={handCards} height={handHeight} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="flex-shrink-0 flex flex-col transition-all duration-300 ease-in-out relative" style={{ width: isRightPanelOpen ? `${rightPanelWidth}px` : '0px', opacity: isRightPanelOpen ? 1 : 0, overflow: 'visible' }}>
          <button onClick={() => setIsRightPanelOpen(!isRightPanelOpen)} className="absolute top-1/2 -left-8 w-8 h-20 rounded-l-lg bg-fantasy-burgundy/90 border-2 border-r-0 border-fantasy-gold/60 text-fantasy-gold flex items-center justify-center z-[100]" style={{ transform: 'translateY(-50%)' }}>
            <span className="text-xl font-bold">{isRightPanelOpen ? '›' : '‹'}</span>
          </button>
          <div className="flex flex-col h-full pb-2" style={{ width: `${rightPanelWidth}px` }}>
            {opponent && opponent.graveyardCards && opponent.graveyardCards.length > 0 && (
              <div className="flex-shrink-0" style={{ height: '120px' }}>
                <OpponentGraveyard cards={opponent.graveyardCards} opponentName={opponent.name} />
              </div>
            )}
            <div className="flex-1" style={{ minHeight: '20px' }} />
            <div className="flex-shrink-0 mb-2 flex justify-center"><ZonePiles exile={exileCards} /></div>
            <div className="flex-shrink-0" style={{ height: '180px' }}><Graveyard cards={graveyardCards} /></div>
          </div>
        </div>
      </div>
      
      {/* Expand Buttons when collapsed */}
      {!isLeftPanelOpen && <button onClick={() => setIsLeftPanelOpen(true)} className="fixed top-1/2 left-0 w-6 h-16 rounded-r-lg bg-fantasy-burgundy/90 border-fantasy-gold/60 text-fantasy-gold flex items-center justify-center z-[100] shadow-lg" style={{ transform: 'translateY(-50%)' }}>›</button>}
      {!isRightPanelOpen && <button onClick={() => setIsRightPanelOpen(true)} className="fixed top-1/2 right-0 w-6 h-16 rounded-l-lg bg-fantasy-burgundy/90 border-fantasy-gold/60 text-fantasy-gold flex items-center justify-center z-[100] shadow-lg" style={{ transform: 'translateY(-50%)' }}>‹</button>}

      {/* Targeting Arrows */}
      <svg style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 9999 }}>
        <defs><marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth"><polygon points="0 0, 10 3, 0 6" fill="#ef4444" /></marker></defs>
        {targetingArrows.map((arrow) => {
          const startEl = document.querySelector(`[data-card-id="${arrow.cardId}"]`);
          if (!startEl) return null;
          const startRect = startEl.getBoundingClientRect();
          const startX = startRect.left + startRect.width / 2;
          const startY = startRect.top + startRect.height / 2;
          
          let endX = 0, endY = 0;
          if (arrow.targetPlayerId) {
             const panel = arrow.targetPlayerId === opponent?.id ? opponentPanelRef.current : playerPanelRef.current;
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
    </div>
  );
}

