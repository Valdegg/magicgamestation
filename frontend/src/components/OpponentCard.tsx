import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

import { CardData } from '../types';
import { useCardScale } from '../context/CardScaleContext';
import { useCardDatabase } from '../context/CardDatabaseContext';
import { getCardImagePaths } from '../utils/cardDatabase';

interface OpponentCardProps {
  card: CardData;
  onCardTargeted: (sourceCardId: string, targetCardId: string) => void;
  scale?: number;
}

const OpponentCard: React.FC<OpponentCardProps> = ({ card, onCardTargeted, scale = 1 }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [currentImagePath, setCurrentImagePath] = useState<string | null>(null);
  const [imageLoadFailed, setImageLoadFailed] = useState(false);
  const pathIndexRef = useRef(0);
  const { cardScale: globalCardScale, hoverZoomValue } = useCardScale();
  const { getCard } = useCardDatabase();

  // Get display name - prefer metadata name, fall back to cleaned card name
  const getDisplayName = () => {
    const metadata = getCard(card.name);
    if (metadata?.name) return metadata.name;
    
    // Clean up card ID: strip _UNK suffix and convert to readable name
    let cleanId = card.name;
    const setCodeMatch = cleanId.match(/^(.+)_([A-Z0-9]{2,4})$/i);
    if (setCodeMatch) {
      cleanId = setCodeMatch[1];
    }
    return cleanId
      .replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  const displayName = getDisplayName();

  // Load image with fallback paths
  useEffect(() => {
    if (card.faceDown) return;
    
    const metadata = getCard(card.name);
    const imagePaths = metadata?.image 
      ? [metadata.image, ...getCardImagePaths(displayName)]
      : getCardImagePaths(displayName);
    
    // Remove duplicates and card-back from paths
    const uniquePaths = [...new Set(imagePaths)].filter(p => !p.includes('card-back'));
    
    pathIndexRef.current = 0;
    setImageLoadFailed(false);
    
    const tryNextPath = () => {
      if (pathIndexRef.current < uniquePaths.length) {
        setCurrentImagePath(uniquePaths[pathIndexRef.current]);
      } else {
        setImageLoadFailed(true);
        setCurrentImagePath('/cards/card-back.jpg');
      }
    };
    
    tryNextPath();
  }, [card.name, card.faceDown, displayName]);

  const handleImageError = () => {
    const metadata = getCard(card.name);
    const imagePaths = metadata?.image 
      ? [metadata.image, ...getCardImagePaths(displayName)]
      : getCardImagePaths(displayName);
    const uniquePaths = [...new Set(imagePaths)].filter(p => !p.includes('card-back'));
    
    pathIndexRef.current++;
    if (pathIndexRef.current < uniquePaths.length) {
      setCurrentImagePath(uniquePaths[pathIndexRef.current]);
    } else {
      setImageLoadFailed(true);
      setCurrentImagePath('/cards/card-back.jpg');
    }
  };
  
  // Check if hover zoom is enabled
  const hoverZoomEnabled = hoverZoomValue > 1.0;
  
  // Calculate effective hover scale for opponent cards
  // Since opponent cards are already scaled down, we need a stronger hover
  // to bring them up to readable size (target: ~1.5x of original card size)
  const effectiveScale = scale * globalCardScale;
  const targetHoverSize = hoverZoomValue * 1.2; // Slightly larger than normal hover
  const opponentHoverScale = Math.max(hoverZoomValue, targetHoverSize / effectiveScale);

  const baseWidth = 156;
  const baseHeight = 217;
  // Apply both the layout scale and global card scale
  const scaledWidth = baseWidth * scale * globalCardScale;
  const scaledHeight = baseHeight * scale * globalCardScale;

  return (
    <motion.div
      data-card-id={card.id}
      className="absolute rounded"
      style={{
        width: `${scaledWidth}px`,
        height: `${scaledHeight}px`,
        left: `${card.x || 50}px`,
        top: `${card.y || 50}px`,
        transform: card.tapped ? 'rotate(90deg)' : 'rotate(0deg)',
        transformOrigin: 'center center',
        transition: 'transform 0.3s ease, box-shadow 0.2s ease',
        cursor: 'pointer',
        overflow: 'visible',
        boxShadow: isDragOver 
          ? '0 0 20px rgba(239, 68, 68, 0.8), inset 0 0 10px rgba(239, 68, 68, 0.5)'
          : undefined
      }}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ 
        opacity: 1, 
        scale: 1,
        rotate: card.tapped ? 90 : 0
      }}
      whileHover={hoverZoomEnabled ? { 
        scale: opponentHoverScale,
        y: 80,
        zIndex: 1000,
        transition: { duration: 0.2, delay: 0.8 }
      } : undefined}
      transition={{ duration: 0.2 }}
      onDragOver={(e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(false);
        const sourceCardId = e.dataTransfer.getData('text/plain');
        if (sourceCardId && sourceCardId !== card.id) {
          onCardTargeted(sourceCardId, card.id);
        }
      }}
    >
      {card.faceDown ? (
        <div
          style={{
            width: '100%',
            height: '100%',
            backgroundImage: 'url(/Magic_the_gathering-card_back.jpg)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            boxShadow: '0 2px 6px rgba(0, 0, 0, 0.6), 0 0 10px rgba(212, 179, 107, 0.2)',
            border: '1px solid rgba(212, 179, 107, 0.4)',
            borderRadius: '0.375rem',
            overflow: 'visible'
          }}
        />
      ) : imageLoadFailed ? (
        <div
          className="w-full h-full rounded flex items-center justify-center"
          style={{
            background: 'linear-gradient(135deg, #4a3728 0%, #3a2718 100%)',
            boxShadow: '0 2px 6px rgba(0, 0, 0, 0.6), 0 0 10px rgba(212, 179, 107, 0.2)',
            border: '1px solid rgba(212, 179, 107, 0.4)',
          }}
        >
          <span style={{ color: '#d4b36b', fontSize: '0.7rem', textAlign: 'center', padding: '4px' }}>
            {displayName}
          </span>
        </div>
      ) : (
        <img
          src={currentImagePath || ''}
          alt={displayName}
          className="w-full h-full object-cover rounded"
          style={{
            boxShadow: '0 2px 6px rgba(0, 0, 0, 0.6), 0 0 10px rgba(212, 179, 107, 0.2)',
            border: '1px solid rgba(212, 179, 107, 0.4)',
            overflow: 'visible'
          }}
          onError={handleImageError}
        />
      )}
    </motion.div>
  );
};

export default OpponentCard;

