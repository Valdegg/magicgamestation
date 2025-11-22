import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { CardData } from '../types';
import { useCardDatabase } from '../context/CardDatabaseContext';
import { getCardImagePaths } from '../utils/cardDatabase';

interface CardProps {
  card: CardData;
  onTap?: () => void;
  onContextMenu?: (e: React.MouseEvent) => void;
  onDragStart?: (e: React.DragEvent) => void;
  onDragEnd?: (e: React.DragEvent) => void;
  style?: React.CSSProperties;
  inHand?: boolean;
  cardWidth?: number;
  cardHeight?: number;
  disableHover?: boolean;
}

const Card: React.FC<CardProps> = ({
  card,
  onTap,
  onContextMenu,
  onDragStart,
  onDragEnd,
  style,
  inHand = false,
  cardWidth,
  cardHeight,
  disableHover = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [currentImagePath, setCurrentImagePath] = useState<string>('');
  const { getCard } = useCardDatabase();

  // Get card metadata from database
  const metadata = card.cardId ? getCard(card.cardId) : null;

  // Debug logging for metadata lookup
  useEffect(() => {
    if (card.cardId) {
      const found = getCard(card.cardId);
      console.log('🔍 Metadata lookup:', {
        cardId: card.cardId,
        found: !!found,
        metadataName: found?.name,
        metadataSet: found?.set,
        metadataImage: found?.image
      });
    } else {
      console.log('⚠️ No cardId for card:', card.name);
    }
  }, [card.cardId, card.name, getCard]);

  // Log tapped state changes
  useEffect(() => {
    if (!inHand) {
      console.log('🎴 Card tapped state changed:', {
        id: card.id,
        name: card.name,
        tapped: card.tapped
      });
    }
  }, [card.tapped, card.id, card.name, inHand]);

  // Smart image loading with fallbacks
  useEffect(() => {
    const tryLoadImage = async () => {
      console.log('🎴 ===== CARD IMAGE LOADING START =====');
      console.log('🎴 Card details:', {
        cardId: card.cardId,
        cardName: card.name,
        metadataName: metadata?.name,
        metadataSet: metadata?.set,
        metadataImage: metadata?.image,
        hasMetadata: !!metadata
      });
      
      // If metadata has an image path, use it first (most reliable)
      const possiblePaths: string[] = [];
      
      if (metadata?.image) {
        console.log('📁 Using metadata image path:', metadata.image);
        possiblePaths.push(metadata.image);
      }
      
      // Use metadata name if available, otherwise use card.name
      // IMPORTANT: Always prefer metadata.name over card.name, as card.name might be a card ID
      const displayName = metadata?.name || card.name;
      
      console.log('📝 Display name decision:', {
        hasMetadata: !!metadata,
        metadataName: metadata?.name,
        cardName: card.name,
        usingDisplayName: displayName
      });
      
      // Get all possible image paths using normalization (set codes ignored)
      // The normalization function will strip any _XXX set code suffixes
      const normalizedPaths = getCardImagePaths(displayName);
      possiblePaths.push(...normalizedPaths);
      
      // Remove duplicates while preserving order
      const uniquePaths = Array.from(new Set(possiblePaths));

      console.log('📁 All possible paths to try:', uniquePaths);
      console.log('📁 Current window location:', window.location.href);
      console.log('📁 Base URL would be:', window.location.origin);

      // Try each path until one works
      for (let i = 0; i < uniquePaths.length; i++) {
        const path = uniquePaths[i];
        try {
          const fullUrl = `${window.location.origin}${path}`;
          console.log(`  🔍 [${i + 1}/${possiblePaths.length}] Trying path: "${path}"`);
          console.log(`  🔍 Full URL would be: "${fullUrl}"`);
          
          const img = new Image();
          const loaded = await new Promise<boolean>((resolve) => {
            const timeout = setTimeout(() => {
              console.log(`  ⏱️ Timeout after 5s for: ${path}`);
              resolve(false);
            }, 5000);
            
            img.onload = () => {
              clearTimeout(timeout);
              console.log(`  ✅ SUCCESS! Loaded: ${path}`);
              console.log(`  ✅ Image dimensions: ${img.width}x${img.height}`);
              resolve(true);
            };
            img.onerror = (e) => {
              clearTimeout(timeout);
              console.log(`  ❌ FAILED: ${path}`);
              console.log(`  ❌ Error event:`, e);
              console.log(`  ❌ Image src was: "${img.src}"`);
              resolve(false);
            };
            img.src = path;
          });

          if (loaded) {
            console.log(`  ✅ Setting currentImagePath to: ${path}`);
            setCurrentImagePath(path);
            console.log('🎴 ===== CARD IMAGE LOADING SUCCESS =====');
            return;
          }
        } catch (e) {
          console.log(`  ⚠️ Exception trying ${path}:`, e);
          // Try next path
          continue;
        }
      }

      // If all paths fail, use last one (card-back)
      console.log('⚠️ ===== ALL PATHS FAILED =====');
      console.log('⚠️ Using fallback:', uniquePaths[uniquePaths.length - 1]);
      setCurrentImagePath(uniquePaths[uniquePaths.length - 1]);
      console.log('🎴 ===== CARD IMAGE LOADING END (FALLBACK) =====');
    };

    tryLoadImage();
  }, [card.name, metadata?.set]);

  const handleDragStart = (e: React.DragEvent) => {
    setIsDragging(true);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('cardId', card.id);
    if (onDragStart) onDragStart(e);
  };

  const handleDragEnd = (e: React.DragEvent) => {
    setIsDragging(false);
    if (onDragEnd) onDragEnd(e);
  };

  const handleClick = () => {
    console.log('🎴 Card clicked:', card.id, 'current tapped state:', card.tapped);
    if (onTap) {
      onTap();
    }
  };

  // Calculate card dimensions
  const width = cardWidth || (inHand ? 120 : 110);
  const height = cardHeight || (inHand ? 168 : 154);

  const handleHoverStart = () => {
    console.log('🔍 HOVER START:', {
      cardName: card.name,
      inHand,
      scale: inHand ? 1.6 : 2.0,
      yOffset: inHand ? -80 : 0,
      width,
      height
    });
  };

  const handleHoverEnd = () => {
    console.log('🔍 HOVER END:', card.name);
  };

  return (
    <motion.div
      className={`card-frame cursor-pointer select-none ${isDragging ? 'opacity-50' : ''}`}
      style={{
        width: `${width}px`,
        height: `${height}px`,
        transformOrigin: 'center center',
        overflow: 'visible',
        ...style,
      }}
      animate={{
        rotate: card.tapped && !inHand ? 90 : 0,
      }}
      transition={{ 
        duration: 0.3,
        ease: "easeInOut"
      }}
      whileHover={!inHand && !disableHover ? { 
        scale: 1.7, 
        y: 0,
        zIndex: 1000,
        transition: { duration: 0.2, delay: 0.8 }
      } : undefined}
      onHoverStart={!inHand && !disableHover ? handleHoverStart : undefined}
      onHoverEnd={!inHand && !disableHover ? handleHoverEnd : undefined}
    >
      <div
        draggable
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onClick={handleClick}
        onContextMenu={(e) => {
          e.preventDefault();
          if (onContextMenu) onContextMenu(e);
        }}
        className="w-full h-full"
        style={{ overflow: 'visible' }}
      >
      <div className="w-full h-full relative" style={{ overflow: 'visible' }}>
        {/* Check if it's a token - always show as face-down with Token label */}
        {card.data?.is_token ? (
          <div className="w-full h-full relative">
            <img
              src="/Magic_the_gathering-card_back.jpg"
              alt="Token"
              className="w-full h-full object-cover"
              style={{
                imageRendering: 'crisp-edges',
              }}
            />
            <div className="absolute top-0 left-0 right-0 bg-fantasy-gold/90 text-fantasy-dark text-center py-1 px-2 font-bold text-sm shadow-lg">
              TOKEN
            </div>
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 bg-fantasy-dark/90 text-fantasy-gold text-center py-1 px-3 rounded font-bold text-xs shadow-lg whitespace-nowrap">
              {card.data.power}/{card.data.toughness}
            </div>
          </div>
        ) : card.faceDown ? (
          <img
            src="/Magic_the_gathering-card_back.jpg"
            alt="Card Back"
            className="w-full h-full object-cover"
            style={{
              imageRendering: 'crisp-edges',
            }}
          />
        ) : (
          <>
            {currentImagePath ? (
              <img
                src={currentImagePath}
                alt={card.name}
                className="w-full h-full"
                style={{
                  imageRendering: 'crisp-edges',
                  objectFit: 'cover',
                  borderRadius: '0.5rem'
                }}
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  console.error('❌ ===== IMG ELEMENT ERROR =====');
                  console.error('❌ Image failed to load in <img> tag:', {
                    attemptedPath: currentImagePath,
                    fullUrl: target.src,
                    cardName: card.name,
                    cardId: card.cardId,
                    cardIdFromCard: card.cardId,
                    metadata: metadata,
                    metadataName: metadata?.name,
                    metadataSet: metadata?.set,
                    displayName: metadata?.name || card.name
                  });
                  console.error('❌ Error event:', e);
                  console.error('❌ Image element src:', target.src);
                  console.error('❌ Image element complete:', target.complete);
                  console.error('❌ Image element naturalWidth:', target.naturalWidth);
                  console.error('❌ Image element naturalHeight:', target.naturalHeight);
                  // Try fallback
                  if (!currentImagePath.includes('card-back')) {
                    console.log('🔄 Trying fallback: /cards/card-back.jpg');
                    target.src = '/cards/card-back.jpg';
                  }
                  console.error('❌ ===== END IMG ELEMENT ERROR =====');
                }}
                onLoad={(e) => {
                  const target = e.target as HTMLImageElement;
                  console.log('✅ ===== IMG ELEMENT LOADED =====');
                  console.log('✅ Image loaded successfully in <img> tag:', {
                    path: currentImagePath,
                    fullUrl: target.src,
                    cardName: card.name,
                    dimensions: `${target.naturalWidth}x${target.naturalHeight}`
                  });
                  console.log('✅ ===== END IMG ELEMENT LOADED =====');
                }}
              />
            ) : (
              <div className="w-full h-full bg-gradient-to-br from-fantasy-burgundy to-fantasy-dark flex items-center justify-center">
                <div className="text-fantasy-gold/50 text-xs text-center p-2">
                  Loading...
                </div>
              </div>
            )}
          </>
        )}
        
        {/* Tapped indicator */}
        {card.tapped && !card.faceDown && (
          <div className="absolute top-1 right-1 bg-fantasy-gold text-fantasy-dark text-xs px-2 py-0.5 rounded font-bold shadow-lg">
            ⟲
          </div>
        )}
        
        {/* Counter badges */}
        {!card.faceDown && card.data && (
          <div className="absolute top-1 left-1 flex flex-col gap-1">
            {card.data['counters_+1/+1'] && card.data['counters_+1/+1'] > 0 && (
              <div className="bg-green-600 text-white text-xs px-2 py-0.5 rounded-full font-bold shadow-lg flex items-center gap-1">
                <span>+1/+1</span>
                <span className="bg-green-800 rounded-full px-1.5">
                  {card.data['counters_+1/+1']}
                </span>
              </div>
            )}
            {card.data['counters_-1/-1'] && card.data['counters_-1/-1'] > 0 && (
              <div className="bg-purple-600 text-white text-xs px-2 py-0.5 rounded-full font-bold shadow-lg flex items-center gap-1">
                <span>-1/-1</span>
                <span className="bg-purple-800 rounded-full px-1.5">
                  {card.data['counters_-1/-1']}
                </span>
              </div>
            )}
            {card.data['counters_loyalty'] && card.data['counters_loyalty'] > 0 && (
              <div className="bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full font-bold shadow-lg flex items-center gap-1">
                <span>⚡</span>
                <span className="bg-blue-800 rounded-full px-1.5">
                  {card.data['counters_loyalty']}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
      </div>
    </motion.div>
  );
};

export default Card;
