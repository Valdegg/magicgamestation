import React, { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useGameState } from '../context/GameStateWebSocket';
import DeckSelector from './DeckSelector';
import SearchLibraryModal from './SearchLibraryModal';
import SideboardModal from './SideboardModal';

const ControlPanel: React.FC = () => {
  const { player, cards, changeLife, drawCard, shuffleLibrary, mulligan, libraryCount, playerId, activePlayerId, moveCard, createToken, toggleFaceDown } = useGameState();
  const isMyTurn = playerId === activePlayerId;
  const [editingLife, setEditingLife] = useState(false);
  const [lifeInput, setLifeInput] = useState(player.life.toString());
  const [showDeckSelector, setShowDeckSelector] = useState(false);
  const [clickCount, setClickCount] = useState(0);
  const [clickTimer, setClickTimer] = useState<number | null>(null);
  const [showLibraryMenu, setShowLibraryMenu] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 });
  const [showTokenCreator, setShowTokenCreator] = useState(false);
  const [tokenName, setTokenName] = useState('');
  const [tokenPower, setTokenPower] = useState('1');
  const [tokenToughness, setTokenToughness] = useState('1');
  const [showSearchLibrary, setShowSearchLibrary] = useState(false);
  const [showSideboard, setShowSideboard] = useState(false);
  const [isLibraryDragOver, setIsLibraryDragOver] = useState(false);
  const [draggingLibraryCard, setDraggingLibraryCard] = useState<string | null>(null);

  // Get library cards
  const libraryCards = useMemo(() => cards.filter(card => card.zone === 'library'), [cards]);
  // Get sideboard cards
  const sideboardCards = useMemo(() => cards.filter(card => card.zone === 'sideboard'), [cards]);

  const handleLibraryDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsLibraryDragOver(true);
  };

  const handleLibraryDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only clear if we're actually leaving the library element
    const relatedTarget = e.relatedTarget as HTMLElement;
    const currentTarget = e.currentTarget as HTMLElement;
    
    if (!currentTarget.contains(relatedTarget)) {
      setIsLibraryDragOver(false);
    }
  };

  const handleLibraryDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsLibraryDragOver(false);
    
    const cardId = e.dataTransfer.getData('cardId');
    const sourceZone = e.dataTransfer.getData('sourceZone');
    const multipleCardIdsData = e.dataTransfer.getData('multipleCardIds');
    
    // Check if we're dragging multiple cards
    let cardIdsToMove: string[] = [];
    if (multipleCardIdsData) {
      try {
        cardIdsToMove = JSON.parse(multipleCardIdsData);
        console.log('📚 Library received multiple cards:', cardIdsToMove.length);
      } catch (e) {
        console.error('Failed to parse multipleCardIds:', e);
        cardIdsToMove = [];
      }
    }
    
    // If no multiple cards, use single card
    if (cardIdsToMove.length === 0 && cardId) {
      cardIdsToMove = [cardId];
    }
    
    console.log('📚 Library received drop:', { cardIds: cardIdsToMove, sourceZone });
    
    if (cardIdsToMove.length > 0 && sourceZone !== 'library') {
      console.log('✅ Moving', cardIdsToMove.length, 'card(s) to library');
      cardIdsToMove.forEach(cardId => moveCard(cardId, 'library'));
    }
  };

  // Handle ESC key to close modals
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showTokenCreator) {
          setShowTokenCreator(false);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showTokenCreator]);

  const handleLifeSubmit = () => {
    const newLife = parseInt(lifeInput, 10);
    if (!isNaN(newLife)) {
      changeLife(newLife - player.life);
    }
    setEditingLife(false);
  };

  const handleLibraryClick = () => {
    // If library is empty, open deck selector
    if (libraryCount === 0) {
      setShowDeckSelector(true);
      return;
    }

    // Clear existing timer
    if (clickTimer) {
      clearTimeout(clickTimer);
    }

    const newCount = clickCount + 1;
    setClickCount(newCount);

    // Set a timer to execute the draw after 500ms of no clicks
    const timer = setTimeout(() => {
      console.log(`🎴 Drawing ${newCount} card(s) from library`);
      for (let i = 0; i < newCount; i++) {
        drawCard();
      }
      setClickCount(0);
    }, 500);

    setClickTimer(timer);
  };

  const handleLibraryRightClick = (e: React.MouseEvent) => {
    e.preventDefault();
    setMenuPosition({ x: e.clientX, y: e.clientY });
    setShowLibraryMenu(true);
  };

  const handleMenuAction = (action: 'draw' | 'shuffle' | 'load' | 'search' | 'mulligan' | 'sideboard') => {
    setShowLibraryMenu(false);
    if (action === 'draw' && libraryCount > 0) {
      drawCard();
    } else if (action === 'shuffle' && libraryCount > 0) {
      shuffleLibrary();
    } else if (action === 'mulligan') {
      mulligan();
    } else if (action === 'load') {
      setShowDeckSelector(true);
    } else if (action === 'search' && libraryCount > 0) {
      setShowSearchLibrary(true);
    } else if (action === 'sideboard') {
      setShowSideboard(true);
    }
  };

  return (
    <>
      <div 
        className="fantasy-panel p-2 relative h-full flex flex-col justify-start gap-2 pt-4"
        style={{
          opacity: !isMyTurn ? 0.8 : 1,
          paddingBottom: '180px' // Reserve space at bottom for card size settings
        }}
      >
        {/* Life Total - D20 Dice Style - Compact */}
        <div className="text-center">
          {editingLife ? (
            <input
              type="number"
              value={lifeInput}
              onChange={(e) => setLifeInput(e.target.value)}
              onBlur={handleLifeSubmit}
              onKeyPress={(e) => {
                if (e.key === 'Enter') handleLifeSubmit();
              }}
              className="w-16 bg-fantasy-dark/50 border-2 border-fantasy-gold rounded px-2 text-center text-2xl font-bold text-fantasy-gold"
              autoFocus
            />
          ) : (
            <div 
              className="relative"
              onMouseDown={(e) => {
                // Only allow dragging if not clicking on buttons
                const target = e.target as HTMLElement;
                if (target.closest('.life-button')) {
                  return; // Don't start drag if clicking button
                }
              }}
            >
              <motion.div
                className="relative w-16 h-16 mx-auto cursor-grab active:cursor-grabbing"
                whileHover={{ scale: 1.05, rotate: 3 }}
                whileTap={{ scale: 0.95 }}
                style={{ 
                  perspective: '1000px',
                  filter: 'drop-shadow(0 3px 8px rgba(185, 28, 28, 0.3))',
                }}
              >
                <div
                  draggable
                  onDragStart={(e: React.DragEvent) => {
                    // Prevent drag if clicking on buttons
                    const target = e.target as HTMLElement;
                    if (target.closest('.life-button')) {
                      e.preventDefault();
                      return;
                    }
                    console.log('🎲 Life die drag started');
                    e.dataTransfer.setData('dragType', 'lifeDie');
                    e.dataTransfer.setData('dieType', 'd20');
                    e.dataTransfer.effectAllowed = 'move';
                  }}
                  className="absolute inset-0"
                >
                {/* 3D D20 Dice - Subtle translucent */}
                <div 
                  className="w-full h-full flex items-center justify-center relative"
                  style={{
                    clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
                    background: `
                      radial-gradient(circle at 35% 25%, rgba(248, 180, 180, 0.85) 0%, rgba(220, 90, 90, 0.75) 50%, rgba(165, 42, 42, 0.8) 100%)
                    `,
                    boxShadow: `
                      0 6px 16px rgba(185, 28, 28, 0.35),
                      0 3px 8px rgba(0, 0, 0, 0.3),
                      inset 0 2px 6px rgba(255, 255, 255, 0.3),
                      inset 0 -2px 6px rgba(120, 0, 0, 0.3)
                    `,
                    transform: 'rotateX(8deg) rotateY(-5deg)',
                    transformStyle: 'preserve-3d',
                  }}
                >
                  {/* Inner facet for depth */}
                  <div 
                    className="absolute inset-4"
                    style={{
                      clipPath: 'polygon(50% 15%, 85% 35%, 85% 65%, 50% 85%, 15% 65%, 15% 35%)',
                      background: 'radial-gradient(circle at 40% 30%, rgba(240, 150, 150, 0.4) 0%, rgba(185, 28, 28, 0.5) 100%)',
                    }}
                  />

                  {/* Plus button on top */}
                  <div
                    className="life-button absolute top-0 left-1/2 -translate-x-1/2 w-4 h-4 flex items-center justify-center cursor-pointer hover:scale-110 transition-transform z-20"
                    onClick={(e) => { 
                      e.stopPropagation(); 
                      e.preventDefault();
                      console.log('➕ Increasing life');
                      changeLife(1); 
                    }}
                    onMouseDown={(e) => e.stopPropagation()}
                    style={{
                      color: 'rgba(144, 238, 144, 0.9)',
                      fontSize: '1rem',
                      fontWeight: 'bold',
                      textShadow: '0 0 6px rgba(144, 238, 144, 0.8), 0 2px 4px rgba(0, 0, 0, 0.9)',
                      pointerEvents: 'auto',
                    }}
                  >
                    +
                  </div>

                  {/* Minus button on bottom */}
                  <div
                    className="life-button absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-4 flex items-center justify-center cursor-pointer hover:scale-110 transition-transform z-20"
                    onClick={(e) => { 
                      e.stopPropagation(); 
                      e.preventDefault();
                      console.log('➖ Decreasing life');
                      changeLife(-1); 
                    }}
                    onMouseDown={(e) => e.stopPropagation()}
                    style={{
                      color: 'rgba(255, 127, 127, 0.9)',
                      fontSize: '0.9rem',
                      fontWeight: 'bold',
                      textShadow: '0 0 6px rgba(255, 127, 127, 0.8), 0 2px 4px rgba(0, 0, 0, 0.9)',
                      pointerEvents: 'auto',
                    }}
                  >
                    −
                  </div>
                  
                  {/* Number - White crisp - draggable area */}
                  <div 
                    className="relative z-10 text-2xl font-bold cursor-grab active:cursor-grabbing" 
                    onClick={(e) => {
                      // Only edit if not dragging
                      if (!e.defaultPrevented) {
                        setEditingLife(true);
                        setLifeInput(player.life.toString());
                      }
                    }}
                    style={{
                      color: '#ffffff',
                      textShadow: `
                        0 2px 4px rgba(0, 0, 0, 0.7),
                        0 1px 2px rgba(120, 0, 0, 0.4),
                        0 0 8px rgba(255, 255, 255, 0.2)
                      `,
                      fontFamily: "'Arial Black', sans-serif",
                      letterSpacing: '-0.02em',
                      pointerEvents: 'auto',
                    }}>
                    {player.life}
                  </div>

                  {/* Subtle top highlight */}
                  <div 
                    className="absolute pointer-events-none"
                    style={{
                      top: '15%',
                      left: '30%',
                      width: '40%',
                      height: '25%',
                      background: 'radial-gradient(ellipse at center, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0.15) 50%, transparent 70%)',
                      borderRadius: '50%',
                      filter: 'blur(2px)',
                    }}
                  />
                </div>
                </div>
              </motion.div>
            </div>
          )}
        </div>

        {/* Token Creator Button - Compact */}
        <div className="text-center">
          <motion.button
            onClick={() => setShowTokenCreator(true)}
            className="px-3 py-1 bg-fantasy-gold/20 hover:bg-fantasy-gold/30 text-fantasy-gold rounded transition-colors text-xs font-bold w-full"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            + Token
          </motion.button>
        </div>

        {/* Library - Card Deck - Larger */}
        <div className="text-center mt-8">
          <motion.div
            id="library-zone"
            className="relative w-40 h-56 mx-auto cursor-pointer select-none"
            onClick={handleLibraryClick}
            onContextMenu={handleLibraryRightClick}
            onDragOver={handleLibraryDragOver}
            onDragLeave={handleLibraryDragLeave}
            onDrop={handleLibraryDrop}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            style={{
              opacity: libraryCount === 0 ? 0.3 : 1,
              cursor: libraryCount > 0 ? 'grab' : 'pointer',
            }}
          >
            <div
              draggable={libraryCount > 0}
              onDragStart={(e: React.DragEvent) => {
                if (libraryCards.length > 0) {
                  // Get the top card (last in array, as library is typically LIFO)
                  const topCard = libraryCards[libraryCards.length - 1];
                  console.log('📚 Drag started from library:', topCard.id);
                  setDraggingLibraryCard(topCard.id);
                  e.dataTransfer.setData('cardId', topCard.id);
                  e.dataTransfer.setData('sourceZone', 'library');
                  e.dataTransfer.effectAllowed = 'move';
                } else {
                  e.preventDefault();
                }
              }}
              onDragEnd={(e: React.DragEvent) => {
                if (!draggingLibraryCard) return;
                
                const dropX = e.clientX;
                const dropY = e.clientY;
              
              // Check if dropped on hand
              const handElement = document.getElementById('hand-zone') || document.getElementById('hand-drop-area');
              if (handElement) {
                const handRect = handElement.getBoundingClientRect();
                if (
                  dropX >= handRect.left &&
                  dropX <= handRect.right &&
                  dropY >= handRect.top &&
                  dropY <= handRect.bottom
                ) {
                  console.log('✅ Dropped library card on hand!');
                  moveCard(draggingLibraryCard, 'hand');
                  setDraggingLibraryCard(null);
                  return;
                }
              }
              
              // Check if dropped on battlefield
              const battlefieldElement = document.getElementById('battlefield');
              if (battlefieldElement) {
                const battlefieldRect = battlefieldElement.getBoundingClientRect();
                if (
                  dropX >= battlefieldRect.left &&
                  dropX <= battlefieldRect.right &&
                  dropY >= battlefieldRect.top &&
                  dropY <= battlefieldRect.bottom
                ) {
                  const x = dropX - battlefieldRect.left - 75;
                  const y = dropY - battlefieldRect.top - 105;
                  console.log('✅ Dropped library card on battlefield at', x, y);
                  moveCard(draggingLibraryCard, 'battlefield', Math.round(x), Math.round(y));
                  setDraggingLibraryCard(null);
                  return;
                }
              }
              
              // Check if dropped on graveyard
              const graveyardElement = document.getElementById('graveyard-zone');
              if (graveyardElement) {
                const graveyardRect = graveyardElement.getBoundingClientRect();
                if (
                  dropX >= graveyardRect.left &&
                  dropX <= graveyardRect.right &&
                  dropY >= graveyardRect.top &&
                  dropY <= graveyardRect.bottom
                ) {
                  console.log('✅ Dropped library card on graveyard!');
                  moveCard(draggingLibraryCard, 'graveyard');
                  setDraggingLibraryCard(null);
                  return;
                }
              }
              
              // Check if dropped on exile
              const exileElement = document.getElementById('exile-zone');
              if (exileElement) {
                const exileRect = exileElement.getBoundingClientRect();
                if (
                  dropX >= exileRect.left &&
                  dropX <= exileRect.right &&
                  dropY >= exileRect.top &&
                  dropY <= exileRect.bottom
                ) {
                  console.log('✅ Dropped library card on exile (graveyard + face down)!');
                  moveCard(draggingLibraryCard, 'graveyard');
                  toggleFaceDown(draggingLibraryCard);
                  setDraggingLibraryCard(null);
                  return;
                }
              }
              
              // If dropped nowhere valid, cancel the drag
              console.log('❌ Library card drag cancelled - not dropped on valid zone');
              setDraggingLibraryCard(null);
              }}
              className="absolute inset-0"
            >
            {/* Card back image */}
            <div 
              className="absolute inset-0 fantasy-border rounded-lg overflow-hidden shadow-xl transition-all"
              style={{
                borderColor: isLibraryDragOver ? '#f4d589' : undefined,
                boxShadow: isLibraryDragOver 
                  ? '0 0 30px rgba(244, 213, 137, 0.8), inset 0 0 30px rgba(244, 213, 137, 0.4), 0 4px 12px rgba(0, 0, 0, 0.6)'
                  : undefined,
                transform: isLibraryDragOver ? 'scale(1.08)' : undefined,
              }}
            >
              <img
                src="/Magic_the_gathering-card_back.jpg"
                alt="Library"
                className="w-full h-full object-cover"
                style={{
                  filter: libraryCount === 0 ? 'grayscale(100%)' : 'none',
                }}
              />
              {/* Deck depth effect - multiple card shadows */}
              {libraryCount > 0 && (
                <>
                  <div 
                    className="absolute inset-0 bg-fantasy-dark/20 rounded-lg"
                    style={{ transform: 'translate(2px, 2px)', zIndex: -1 }}
                  />
                  <div 
                    className="absolute inset-0 bg-fantasy-dark/10 rounded-lg"
                    style={{ transform: 'translate(4px, 4px)', zIndex: -2 }}
                  />
                </>
              )}
            </div>
            
            {/* Card count overlay - Center Bottom */}
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2">
              <div 
                className="bg-fantasy-dark/95 px-4 py-1 rounded-full border-2 border-fantasy-gold/60"
                style={{
                  boxShadow: '0 3px 10px rgba(0, 0, 0, 0.8), 0 0 15px rgba(212, 179, 107, 0.3)'
                }}
              >
                <span className="text-fantasy-gold font-bold text-xl">
                  {libraryCount}
                </span>
              </div>
            </div>

            {/* Click counter indicator */}
            {clickCount > 0 && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute top-2 right-2 bg-fantasy-gold text-fantasy-dark px-2 py-1 rounded-full font-bold text-sm"
              >
                +{clickCount}
              </motion.div>
            )}

            {/* Tooltip */}

            {/* Empty state */}
            {libraryCount === 0 && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/60 rounded-lg">
                <span className="text-fantasy-gold/70 text-sm font-bold">
                  Empty
                </span>
              </div>
            )}

            {/* Drag Over Indicator */}
            {isLibraryDragOver && (
              <div className="absolute inset-0 flex items-center justify-center bg-fantasy-gold/20 rounded-lg border-2 border-fantasy-gold animate-pulse">
                <span className="text-fantasy-gold text-lg font-bold drop-shadow-lg">
                  Return to Library
                </span>
              </div>
            )}
            </div>
          </motion.div>
        </div>

      </div>

      {/* Library Context Menu */}
      {showLibraryMenu && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setShowLibraryMenu(false)}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="fixed z-50 fantasy-panel p-2 min-w-[160px]"
            style={{
              left: `${menuPosition.x}px`,
              top: `${menuPosition.y}px`,
            }}
          >
            <button
              className="w-full text-left px-3 py-2 text-fantasy-gold hover:bg-fantasy-gold/20 rounded transition-colors text-sm"
              onClick={() => handleMenuAction('draw')}
              disabled={libraryCount === 0}
            >
              Draw Card
            </button>
            <button
              className="w-full text-left px-3 py-2 text-fantasy-gold hover:bg-fantasy-gold/20 rounded transition-colors text-sm"
              onClick={() => handleMenuAction('mulligan')}
              title="Put hand into library, shuffle, draw 7"
            >
              🔄 Draw New 7
            </button>
            <button
              className="w-full text-left px-3 py-2 text-fantasy-gold hover:bg-fantasy-gold/20 rounded transition-colors text-sm"
              onClick={() => handleMenuAction('shuffle')}
              disabled={libraryCount === 0}
            >
              Shuffle
            </button>
            <button
              className="w-full text-left px-3 py-2 text-fantasy-gold hover:bg-fantasy-gold/20 rounded transition-colors text-sm"
              onClick={() => handleMenuAction('search')}
              disabled={libraryCount === 0}
            >
              🔍 Search Library
            </button>
            <button
              className="w-full text-left px-3 py-2 text-fantasy-gold hover:bg-fantasy-gold/20 rounded transition-colors text-sm"
              onClick={() => handleMenuAction('sideboard')}
            >
              📦 Sideboard
            </button>
            <button
              className="w-full text-left px-3 py-2 text-fantasy-gold hover:bg-fantasy-gold/20 rounded transition-colors text-sm border-t border-fantasy-gold/20 mt-1 pt-2"
              onClick={() => handleMenuAction('load')}
            >
              Load Deck
            </button>
          </motion.div>
        </>
      )}

      {/* Deck Selector Modal */}
      {showDeckSelector && (
        <DeckSelector onClose={() => setShowDeckSelector(false)} />
      )}

      {/* Token Creator Modal */}
      {showTokenCreator && (
        <>
          <div
            className="fixed inset-0 bg-black/60 z-40"
            onClick={() => setShowTokenCreator(false)}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 fantasy-panel p-6 w-96"
          >
            <h3 className="text-fantasy-gold text-xl font-bold text-center mb-4">Create Token</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-fantasy-gold/70 text-sm mb-1">Token Name</label>
                <input
                  type="text"
                  value={tokenName}
                  onChange={(e) => setTokenName(e.target.value)}
                  placeholder="e.g., Goblin, Treasure"
                  className="w-full px-3 py-2 bg-fantasy-dark/50 border border-fantasy-gold/30 rounded text-fantasy-gold"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-fantasy-gold/70 text-sm mb-1">Power</label>
                  <input
                    type="text"
                    value={tokenPower}
                    onChange={(e) => setTokenPower(e.target.value)}
                    className="w-full px-3 py-2 bg-fantasy-dark/50 border border-fantasy-gold/30 rounded text-fantasy-gold text-center"
                  />
                </div>
                <div>
                  <label className="block text-fantasy-gold/70 text-sm mb-1">Toughness</label>
                  <input
                    type="text"
                    value={tokenToughness}
                    onChange={(e) => setTokenToughness(e.target.value)}
                    className="w-full px-3 py-2 bg-fantasy-dark/50 border border-fantasy-gold/30 rounded text-fantasy-gold text-center"
                  />
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowTokenCreator(false)}
                  className="flex-1 py-2 bg-fantasy-dark/50 hover:bg-fantasy-dark/70 text-fantasy-gold/70 rounded transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    // Create token on battlefield
                    createToken(tokenName || 'Token', tokenPower, tokenToughness);
                    
                    setShowTokenCreator(false);
                    setTokenName('');
                    setTokenPower('1');
                    setTokenToughness('1');
                  }}
                  className="flex-1 py-2 bg-fantasy-gold/20 hover:bg-fantasy-gold/30 text-fantasy-gold rounded transition-colors font-bold"
                >
                  Create
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}

      {/* Search Library Modal */}
      {showSearchLibrary && (
        <SearchLibraryModal
          cards={libraryCards}
          onClose={() => setShowSearchLibrary(false)}
        />
      )}

      {/* Sideboard Modal */}
      {showSideboard && (
        <SideboardModal
          libraryCards={libraryCards}
          sideboardCards={sideboardCards}
          onClose={() => setShowSideboard(false)}
        />
      )}
    </>
  );
};

export default ControlPanel;
