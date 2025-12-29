import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameState } from '../context/GameStateWebSocket';

interface DiceTokenProps {
  id: string;
  x: number;
  y: number;
  value: number | null;
  ownerPlayerId: string;
  dieType: string;
  isRolling?: boolean;
}

const DiceToken: React.FC<DiceTokenProps> = ({ id, x, y, value, ownerPlayerId, dieType, isRolling: initialRolling }) => {
  const { playerId, removeDie, moveDie } = useGameState();
  const [isRolling, setIsRolling] = useState(initialRolling || false);
  const [displayValue, setDisplayValue] = useState<number | null>(value);
  const [isDragging, setIsDragging] = useState(false);
  const [showRemoveButton, setShowRemoveButton] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);

  const isOwned = playerId === ownerPlayerId;

  // Handle rolling animation
  useEffect(() => {
    if (value !== null && value !== displayValue) {
      setIsRolling(true);
      const rollDuration = 800 + Math.random() * 300; // 800-1100ms
      const numFlickers = 8 + Math.floor(Math.random() * 7); // 8-14 flickers
      const flickerInterval = rollDuration / numFlickers;
      
      let flickerCount = 0;
      const flickerTimer = setInterval(() => {
        flickerCount++;
        setDisplayValue(Math.floor(Math.random() * 20) + 1);
        
        if (flickerCount >= numFlickers) {
          clearInterval(flickerTimer);
          setDisplayValue(value);
          setTimeout(() => setIsRolling(false), 100);
        }
      }, flickerInterval);
      
      return () => clearInterval(flickerTimer);
    }
  }, [value]);

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY });
  };

  const handleRemove = () => {
    removeDie(id);
    setContextMenu(null);
  };

  const handleDragStart = (e: React.DragEvent) => {
    setIsDragging(true);
    e.dataTransfer.setData('dragType', 'dieToken');
    e.dataTransfer.setData('dieId', id);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnd = (e: React.DragEvent) => {
    setIsDragging(false);
    
    // Check if dropped on battlefield
    const battlefieldElement = document.getElementById('battlefield');
    if (battlefieldElement) {
      const rect = battlefieldElement.getBoundingClientRect();
      const newX = e.clientX - rect.left;
      const newY = e.clientY - rect.top;
      
      if (newX >= 0 && newX <= rect.width && newY >= 0 && newY <= rect.height) {
        moveDie(id, newX, newY);
      }
    }
  };

  return (
    <>
      <motion.div
        draggable={isOwned}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onContextMenu={handleContextMenu}
        onMouseEnter={() => setShowRemoveButton(true)}
        onMouseLeave={() => setShowRemoveButton(false)}
        className="absolute cursor-move"
        style={{
          left: `${x}px`,
          top: `${y}px`,
          transform: 'translate(-50%, -50%)',
          zIndex: 1000,
        }}
        initial={{ scale: 0, opacity: 0 }}
        animate={{ 
          scale: isRolling ? [1, 1.1, 1] : 1,
          opacity: 1,
          rotate: isRolling ? [0, 5, -5, 0] : 0,
        }}
        transition={{ 
          duration: isRolling ? 0.1 : 0.3,
          repeat: isRolling ? Infinity : 0,
        }}
        whileHover={{ scale: 1.1 }}
      >
        <div
          className="relative w-16 h-16"
          style={{
            perspective: '1000px',
            filter: 'drop-shadow(0 3px 8px rgba(185, 28, 28, 0.3))'
          }}
        >
          {/* 3D D20 Dice */}
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

            {/* Number */}
            <div
              className="relative z-10 text-2xl font-bold"
              style={{
                color: '#ffffff',
                textShadow: `
                  0 2px 4px rgba(0, 0, 0, 0.7),
                  0 1px 2px rgba(120, 0, 0, 0.4),
                  0 0 8px rgba(255, 255, 255, 0.2)
                `,
                fontFamily: "'Arial Black', sans-serif",
                letterSpacing: '-0.02em',
              }}
            >
              {displayValue ?? '?'}
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

          {/* Remove button */}
          {isOwned && showRemoveButton && (
            <motion.button
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={handleRemove}
              className="absolute -top-2 -right-2 w-6 h-6 bg-red-600 rounded-full flex items-center justify-center text-white text-xs font-bold hover:bg-red-700 z-20"
              style={{ boxShadow: '0 2px 4px rgba(0, 0, 0, 0.5)' }}
            >
              ×
            </motion.button>
          )}
        </div>
      </motion.div>

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed z-[10001] fantasy-panel"
          style={{
            left: `${contextMenu.x}px`,
            top: `${contextMenu.y}px`,
            minWidth: '150px',
          }}
          onClick={() => setContextMenu(null)}
        >
          <div
            className="px-4 py-2 cursor-pointer hover:bg-fantasy-gold hover:text-fantasy-dark transition-colors"
            onClick={handleRemove}
          >
            Remove Die
          </div>
        </div>
      )}
    </>
  );
};

export default DiceToken;

