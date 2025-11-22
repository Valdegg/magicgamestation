import React, { forwardRef, useState } from 'react';

interface OpponentPanelProps {
  name: string;
  life: number;
  libraryCount: number;
  isTheirTurn: boolean;
  playerId?: string;
  onCardDropped?: (cardId: string, playerId: string) => void;
}

const OpponentPanel = forwardRef<HTMLDivElement, OpponentPanelProps>(
  ({ name, life, libraryCount, isTheirTurn, playerId, onCardDropped }, ref) => {
    
    const [isDragOver, setIsDragOver] = useState(false);

    const handleDragOver = (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
    };

    const handleDrop = (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      const cardId = e.dataTransfer.getData('text/plain');
      console.log(`🎯 Dropped card ${cardId} on player ${playerId}`);
      
      if (cardId && playerId && onCardDropped) {
        onCardDropped(cardId, playerId);
      }
    };

    return (
      <div 
        ref={ref}
        className="fantasy-panel p-2 relative"
        style={{
          minHeight: 'auto',
          boxShadow: isDragOver
            ? '0 0 20px rgba(239, 68, 68, 0.6), inset 0 0 20px 2px rgba(239, 68, 68, 0.4)'
            : isTheirTurn 
            ? '0 4px 12px rgba(34, 197, 94, 0.3), inset 0 0 20px 2px rgba(34, 197, 94, 0.3)' 
            : undefined,
          transition: 'box-shadow 0.2s ease'
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
      {/* Player Name */}
      <div className="text-center mb-1">
        <div className="text-fantasy-gold text-base font-bold uppercase tracking-wide">
          {name}
        </div>
        {isTheirTurn && (
          <div className="text-green-400 text-xs mt-1" style={{ textShadow: '0 0 8px rgba(34, 197, 94, 0.6)' }}>
            Their Turn
          </div>
        )}
      </div>

      {/* Library - Card Deck (Upside Down) - Compact */}
      <div className="text-center mb-1">
        <div
          className="relative w-20 h-28 mx-auto select-none"
          style={{
            opacity: libraryCount === 0 ? 0.3 : 1,
          }}
        >
          {/* Card Back Image (Rotated 180°) */}
          <img
            src="/Magic_the_gathering-card_back.jpg"
            alt="Card Back"
            className="absolute inset-0 w-full h-full rounded-lg object-cover"
            style={{
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(212, 179, 107, 0.3)',
              border: '2px solid rgba(212, 179, 107, 0.4)',
              transform: 'rotate(180deg)'
            }}
          />

          {/* Card Count Badge - Center Bottom */}
          {libraryCount > 0 && (
            <div
              className="absolute bottom-1 left-1/2 -translate-x-1/2 bg-fantasy-dark/95 text-fantasy-gold px-2 py-0.5 rounded-full text-sm font-bold border-2 border-fantasy-gold/60"
              style={{
                boxShadow: '0 3px 10px rgba(0, 0, 0, 0.8), 0 0 15px rgba(212, 179, 107, 0.3)'
              }}
            >
              {libraryCount}
            </div>
          )}

          {/* Empty State */}
          {libraryCount === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-fantasy-gold/30 text-xs font-bold">
              Empty
            </div>
          )}
        </div>
      </div>

      {/* Life Total - D20 Dice Style - Compact */}
      <div className="text-center">
        <div
          className="relative w-12 h-12 mx-auto"
          style={{ 
            perspective: '1000px',
          }}
        >
          <div
            className="relative w-full h-full"
            style={{ 
              transformStyle: 'preserve-3d',
              clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
            }}
          >
            {/* Main D20 Body */}
            <div
              className="absolute inset-0"
              style={{
                background: 'linear-gradient(135deg, rgba(220, 38, 38, 0.4) 0%, rgba(153, 27, 27, 0.5) 50%, rgba(127, 29, 29, 0.6) 100%)',
                backdropFilter: 'blur(4px)',
                boxShadow: `
                  0 3px 10px rgba(185, 28, 28, 0.3),
                  inset 0 2px 6px rgba(255, 255, 255, 0.1),
                  inset 0 -2px 6px rgba(0, 0, 0, 0.3)
                `,
                border: '2px solid rgba(220, 38, 38, 0.3)',
              }}
            />

            {/* Top Facet Highlight */}
            <div 
              className="absolute pointer-events-none"
              style={{
                top: '10%',
                left: '25%',
                width: '50%',
                height: '30%',
                background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.05) 50%, transparent 100%)',
                clipPath: 'polygon(50% 0%, 100% 100%, 0% 100%)',
                filter: 'blur(1px)',
              }}
            />

            {/* Number */}
            <div
              className="absolute inset-0 flex items-center justify-center"
              style={{
                fontSize: '1.1rem',
                fontWeight: 'bold',
                color: 'rgba(255, 255, 255, 0.95)',
                textShadow: '0 2px 4px rgba(0, 0, 0, 0.6), 0 0 8px rgba(220, 38, 38, 0.4)',
                letterSpacing: '-0.05em'
              }}
            >
              {life}
            </div>

            {/* Glass Highlight */}
            <div 
              className="absolute pointer-events-none"
              style={{
                top: '15%',
                left: '30%',
                width: '40%',
                height: '25%',
                background: 'radial-gradient(ellipse at center, rgba(255, 255, 255, 0.25) 0%, rgba(255, 255, 255, 0.1) 50%, transparent 70%)',
                borderRadius: '50%',
                filter: 'blur(2px)',
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
});

OpponentPanel.displayName = 'OpponentPanel';

export default OpponentPanel;

