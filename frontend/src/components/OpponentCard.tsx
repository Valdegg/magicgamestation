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

// Throttled error logger to prevent log flooding
const errorLogCache = new Map<string, number>();
const ERROR_LOG_THROTTLE_MS = 5000; // Only log same error once per 5 seconds

const logErrorOnce = (key: string, message: string, error?: any) => {
  const now = Date.now();
  const lastLogged = errorLogCache.get(key);
  if (!lastLogged || now - lastLogged > ERROR_LOG_THROTTLE_MS) {
    errorLogCache.set(key, now);
    console.error(`[OpponentCard] ${message}`, error || '');
  }
};

const OpponentCard: React.FC<OpponentCardProps> = ({ card, onCardTargeted, scale = 1 }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [currentImagePath, setCurrentImagePath] = useState<string | null>(null);
  const [imageLoadFailed, setImageLoadFailed] = useState(false);
  const [renderError, setRenderError] = useState<string | null>(null);
  const pathIndexRef = useRef(0);
  const { cardScale: globalCardScale, hoverZoomValue, opponentCardSizeValue } = useCardScale();
  const { getCard } = useCardDatabase();

  // Get display name - prefer metadata name, fall back to cleaned card name
  const getDisplayName = () => {
    try {
      if (!card?.name) {
        logErrorOnce(`missing-name-${card?.id}`, `Card missing name: ${card?.id}`);
        return 'Unknown Card';
      }
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
    } catch (error) {
      logErrorOnce(`display-name-error-${card?.id}`, `Error getting display name for card ${card?.id}`, error);
      return card?.name || 'Unknown Card';
    }
  };

  const displayName = getDisplayName();

  // Load image with fallback paths
  useEffect(() => {
    try {
      if (card.faceDown) return;
      
      if (!card?.name) {
        logErrorOnce(`missing-card-name-${card?.id}`, `Card missing name: ${card?.id}`);
        setImageLoadFailed(true);
        return;
      }
      
      const metadata = getCard(card.name);
      
      // Try multiple name variations: metadata name, display name, and raw card name
      const nameVariations = new Set<string>();
      if (metadata?.name) nameVariations.add(metadata.name);
      if (displayName && displayName !== metadata?.name) nameVariations.add(displayName);
      if (card.name && card.name !== displayName && card.name !== metadata?.name) nameVariations.add(card.name);
      
      // Generate paths for all name variations
      const imagePaths: string[] = [];
      if (metadata?.image) {
        imagePaths.push(metadata.image);
      }
      
      // Add paths for each name variation
      nameVariations.forEach(name => {
        const paths = getCardImagePaths(name);
        imagePaths.push(...paths);
      });
      
      // Remove duplicates and card-back from paths
      const uniquePaths = [...new Set(imagePaths)].filter(p => !p.includes('card-back'));
      
      // Debug logging for image path generation
      if (card.name?.toLowerCase().includes('mishra') || displayName?.toLowerCase().includes('mishra')) {
        console.log(`[OpponentCard] Image paths for ${displayName}:`, {
          cardId: card.id,
          cardName: card.name,
          displayName: displayName,
          metadataName: metadata?.name,
          metadataImage: metadata?.image,
          nameVariations: Array.from(nameVariations),
          allPaths: imagePaths,
          uniquePaths: uniquePaths,
          uniquePathsCount: uniquePaths.length
        });
      }
      
      pathIndexRef.current = 0;
      setImageLoadFailed(false);
      setRenderError(null);
      
      const tryNextPath = () => {
        if (pathIndexRef.current < uniquePaths.length) {
          const pathToTry = uniquePaths[pathIndexRef.current];
          if (card.name?.toLowerCase().includes('mishra') || displayName?.toLowerCase().includes('mishra')) {
            console.log(`[OpponentCard] Trying image path ${pathIndexRef.current + 1}/${uniquePaths.length}: ${pathToTry}`);
          }
          setCurrentImagePath(pathToTry);
        } else {
          setImageLoadFailed(true);
          setCurrentImagePath('/cards/card-back.jpg');
        }
      };
      
      tryNextPath();
    } catch (error) {
      logErrorOnce(`image-load-error-${card?.id}`, `Error loading image for card ${card?.id}`, error);
      setImageLoadFailed(true);
      setRenderError('Failed to load card');
    }
  }, [card.name, card.faceDown, displayName, card?.id]);

  const handleImageError = () => {
    try {
      const metadata = getCard(card.name);
      
      // Try multiple name variations: metadata name, display name, and raw card name
      const nameVariations = new Set<string>();
      if (metadata?.name) nameVariations.add(metadata.name);
      if (displayName && displayName !== metadata?.name) nameVariations.add(displayName);
      if (card.name && card.name !== displayName && card.name !== metadata?.name) nameVariations.add(card.name);
      
      // Generate paths for all name variations
      const imagePaths: string[] = [];
      if (metadata?.image) {
        imagePaths.push(metadata.image);
      }
      
      // Add paths for each name variation
      nameVariations.forEach(name => {
        imagePaths.push(...getCardImagePaths(name));
      });
      
      const uniquePaths = [...new Set(imagePaths)].filter(p => !p.includes('card-back'));
      
      pathIndexRef.current++;
      if (pathIndexRef.current < uniquePaths.length) {
        setCurrentImagePath(uniquePaths[pathIndexRef.current]);
      } else {
        setImageLoadFailed(true);
        setCurrentImagePath('/cards/card-back.jpg');
        // Log all attempted paths for debugging
        console.error(`[OpponentCard] All image paths failed for card: ${displayName} (${card?.id})`, {
          cardId: card.id,
          cardName: card.name,
          displayName: displayName,
          metadataName: metadata?.name,
          metadataImage: metadata?.image,
          attemptedPaths: uniquePaths,
          attemptedPathsCount: uniquePaths.length,
          nameVariations: Array.from(nameVariations),
          pathIndex: pathIndexRef.current,
          allImagePaths: imagePaths
        });
        logErrorOnce(`image-all-failed-${card?.id}`, `All image paths failed for card: ${displayName} (${card?.id})`);
      }
    } catch (error) {
      logErrorOnce(`image-error-handler-${card?.id}`, `Error in image error handler for card ${card?.id}`, error);
      setImageLoadFailed(true);
    }
  };
  
  // Check if hover zoom is enabled
  const hoverZoomEnabled = hoverZoomValue > 1.0;
  
  // Calculate hover scale for opponent cards
  // Since opponent cards are smaller, we add a modest boost to make them more readable when hovered
  // The effective base scale is: scale * globalCardScale * opponentCardSizeValue
  const effectiveBaseScale = scale * globalCardScale * opponentCardSizeValue;
  // Add a small boost (20-40%) for smaller cards, but cap the total hover scale
  const boost = effectiveBaseScale < 0.7 ? 1.3 : effectiveBaseScale < 0.9 ? 1.2 : 1.1;
  const opponentHoverScale = Math.min(hoverZoomValue * boost, 2.0); // Cap at 2.0x max

  const baseWidth = 156;
  const baseHeight = 217;
  // Apply layout scale, global card scale, and opponent card size multiplier
  const scaledWidth = baseWidth * scale * globalCardScale * opponentCardSizeValue;
  const scaledHeight = baseHeight * scale * globalCardScale * opponentCardSizeValue;

  // Validate card data before rendering
  if (!card || !card.id) {
    logErrorOnce(`invalid-card-${card?.id || 'unknown'}`, `Invalid card data:`, card);
    return null;
  }

  // Render with error boundary
  if (renderError) {
    return (
      <div
        data-card-id={card.id}
        className="absolute rounded"
        style={{
          width: `${scaledWidth}px`,
          height: `${scaledHeight}px`,
          left: `${card.x || 50}px`,
          top: `${card.y || 50}px`,
          background: 'linear-gradient(135deg, #4a3728 0%, #3a2718 100%)',
          border: '1px solid rgba(212, 179, 107, 0.4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span style={{ color: '#d4b36b', fontSize: '0.7rem', textAlign: 'center', padding: '4px' }}>
          {displayName}
        </span>
      </div>
    );
  }

  // Calculate z-index: cards with lower y coordinate should appear on top
  // Use card.zIndex if provided, otherwise calculate from y position
  const cardZIndex = (card as any).zIndex || Math.round(1000 - (card.y || 0));

  return (
    <motion.div
        data-card-id={card.id}
        className="absolute rounded"
        style={{
          width: `${scaledWidth}px`,
          height: `${scaledHeight}px`,
          left: `${card.x || 50}px`,
          top: `${card.y || 50}px`,
          zIndex: cardZIndex,
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

