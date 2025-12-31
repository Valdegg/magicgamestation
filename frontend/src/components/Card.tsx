import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { CardData } from '../types';
import { useCardDatabase } from '../context/CardDatabaseContext';
import { getCardImagePaths, normalizeCardName } from '../utils/cardDatabase';
import { useCardScale } from '../context/CardScaleContext';
import { gameApi } from '../api/gameApi';

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
  const [hoverZoomActive, setHoverZoomActive] = useState(false);
  const hoverZoomTimerRef = useRef<number | null>(null);
  const downloadAttemptedRef = useRef<boolean>(false);
  const lastLoadedCardRef = useRef<string>('');
  const cachedImagePathRef = useRef<string>('');
  const { getCard, reload: reloadDatabase } = useCardDatabase();
  const { cardScale, hoverZoomValue } = useCardScale();
  
  // Check if hover zoom is enabled (value > 1.0)
  const hoverZoomEnabled = hoverZoomValue > 1.0;

  // Get card metadata from database
  // Normalize cardId to handle cases where it has double underscores or other inconsistencies
  // This ensures cards with IDs like "phlage__titan_of_fires_fury" can find metadata stored as "phlage_titan_of_fires_fury"
  const normalizedCardId = card.cardId ? normalizeCardName(card.cardId) : null;
  let metadata = normalizedCardId ? getCard(normalizedCardId) : null;
  
  // If still not found and we have a cardId, try the original (in case it's already normalized)
  if (!metadata && card.cardId && card.cardId !== normalizedCardId) {
    metadata = getCard(card.cardId);
  }

  // Debug logging for metadata lookup
  useEffect(() => {
    if (card.cardId) {
      getCard(card.cardId);
      // console.log('🔍 Metadata lookup:', {
      //   cardId: card.cardId,
      //   found: !!found,
      //   metadataName: found?.name,
      //   metadataSet: found?.set,
      //   metadataImage: found?.image
      // });
    } else {
      console.log('⚠️ No cardId for card:', card.name);
    }
  }, [card.cardId, card.name, getCard]);

  // Reset download attempt flag when card changes
  useEffect(() => {
    downloadAttemptedRef.current = false;
  }, [card.id, card.name]);

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
    // Create a unique key for this card's identity
    const cardIdentity = `${card.cardId || card.name}`;
    
    // If we already loaded an image for this card identity, use the cached path and skip reloading
    if (lastLoadedCardRef.current === cardIdentity && cachedImagePathRef.current) {
      if (currentImagePath !== cachedImagePathRef.current) {
        setCurrentImagePath(cachedImagePathRef.current);
      }
      return;
    }
    
    // Reset download attempt flag at the start of each image loading attempt
    downloadAttemptedRef.current = false;
    
    const tryLoadImage = async () => {
      // console.log('🎴 ===== CARD IMAGE LOADING START =====');
      // console.log('🎴 Card details:', {
      //   cardId: card.cardId,
      //   cardName: card.name,
      //   metadataName: metadata?.name,
      //   metadataSet: metadata?.set,
      //   metadataImage: metadata?.image,
      //   hasMetadata: !!metadata
      // });
      
      // If metadata has an image path, use it first (most reliable)
      const possiblePaths: string[] = [];
      
      if (metadata?.image) {
        possiblePaths.push(metadata.image);
      }
      
      // Use metadata name if available, otherwise try to extract name from card ID
      // IMPORTANT: Always prefer metadata.name over card.name, as card.name might be a card ID
      let displayName = metadata?.name;
      
      // If no metadata, try to extract a readable name from the card ID
      // Card IDs like "wild_mongrel_UNK" or "phlage__titan_of_fires_fury" need cleanup
      if (!displayName) {
        // Normalize the card ID to match database format (collapse double underscores)
        const normalizedId = normalizeCardName(card.name);
        // Try lookup again with normalized ID
        const normalizedMetadata = getCard(normalizedId);
        
        if (normalizedMetadata?.name) {
          displayName = normalizedMetadata.name;
        } else {
          // Convert card ID to readable name by stripping set codes and formatting
          // e.g., "wild_mongrel_UNK" -> "Wild Mongrel"
          let cleanId = card.name;
          // Strip _UNK or other set code suffixes
          const setCodeMatch = cleanId.match(/^(.+)_([A-Z0-9]{2,4})$/i);
          if (setCodeMatch) {
            const suffix = setCodeMatch[2].toUpperCase();
            if (suffix === 'UNK' || /^[A-Z0-9]{2,4}$/.test(suffix)) {
              cleanId = setCodeMatch[1];
            }
          }
          // Convert underscores to spaces and title case
          displayName = cleanId
            .replace(/_/g, ' ')
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
        }
      }
      
      console.log('📝 Display name decision:', {
        hasMetadata: !!metadata,
        metadataName: metadata?.name,
        cardName: card.name,
        normalizedCardId: normalizeCardName(card.name),
        usingDisplayName: displayName
      });
      
      // Get all possible image paths using normalization (set codes ignored)
      // The normalization function will strip any _XXX set code suffixes
      const normalizedPaths = getCardImagePaths(displayName);
      possiblePaths.push(...normalizedPaths);
      
      // Remove duplicates while preserving order
      const uniquePaths = Array.from(new Set(possiblePaths));

      // Filter out card-back from paths we'll try (we'll use it as final fallback)
      const cardImagePaths = uniquePaths.filter(p => !p.includes('card-back'));
      const cardBackPath = uniquePaths.find(p => p.includes('card-back')) || '/cards/card-back.jpg';
      
      // Try each card image path until one works
      for (let i = 0; i < cardImagePaths.length; i++) {
        const path = cardImagePaths[i];
        try {
          console.log(`  🔍 [${i + 1}/${cardImagePaths.length}] Trying path: "${path}"`);
          
          const img = new Image();
          const loaded = await new Promise<boolean>((resolve) => {
            const timeout = setTimeout(() => {
              console.log(`  ⏱️ Timeout after 5s for: ${path}`);
              resolve(false);
            }, 5000);
            
            img.onload = () => {
              clearTimeout(timeout);
              // console.log(`  ✅ SUCCESS! Loaded: ${path}`);
              // console.log(`  ✅ Image dimensions: ${img.width}x${img.height}`);
              resolve(true);
            };
            img.onerror = () => {
              clearTimeout(timeout);
              console.log(`  ❌ Failed to load: ${path}`);
              resolve(false);
            };
            img.src = path;
          });

          if (loaded) {
            // console.log(`  ✅ Setting currentImagePath to: ${path}`);
            setCurrentImagePath(path);
            cachedImagePathRef.current = path; // Cache the image path
            lastLoadedCardRef.current = cardIdentity; // Remember we loaded this card
            // console.log('🎴 ===== CARD IMAGE LOADING SUCCESS =====');
            return;
          }
        } catch (e) {
          console.log(`  ⚠️ Exception trying ${path}:`, e);
          // Try next path
          continue;
        }
      }

      // If all card image paths failed, check if card exists in database before downloading
      console.log(`🔍 Download check: downloadAttempted=${downloadAttemptedRef.current}, cardImagePaths.length=${cardImagePaths.length}, displayName=${displayName}`);
      if (!downloadAttemptedRef.current && cardImagePaths.length > 0) {
        // Check if card already exists in database (might have image but path was wrong)
        const existingCard = getCard(displayName);
        if (existingCard?.image) {
          // Card exists in database with image path - try loading it one more time
          console.log(`🔄 Card exists in database with image path: ${existingCard.image}, retrying load...`);
          const retryImg = new Image();
          const retryLoaded = await new Promise<boolean>((resolve) => {
            const timeout = setTimeout(() => resolve(false), 5000);
            retryImg.onload = () => {
              clearTimeout(timeout);
              resolve(true);
            };
            retryImg.onerror = () => {
              clearTimeout(timeout);
              resolve(false);
            };
            retryImg.src = existingCard.image + '?t=' + Date.now(); // Cache bust
          });
          
          if (retryLoaded) {
            console.log(`✅ Successfully loaded existing card image: ${existingCard.image}`);
            setCurrentImagePath(existingCard.image);
            cachedImagePathRef.current = existingCard.image;
            lastLoadedCardRef.current = cardIdentity;
            return;
          }
        }
        
        // Only download if card doesn't exist in database or has no image
        console.log(`📥 Card not in database or missing image, attempting to download: ${displayName}`);
        downloadAttemptedRef.current = true;
        
        try {
          const result = await gameApi.fetchCardImage(displayName);
          if (result.success && result.card?.image) {
            console.log(`✅ Successfully downloaded image for ${displayName}, reloading database...`);
            // Reload the database to get the new card metadata
            await reloadDatabase();
            // Wait a moment for the file to be written, then try loading again
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Try loading the newly downloaded image
            const newImg = new Image();
            const loaded = await new Promise<boolean>((resolve) => {
              const timeout = setTimeout(() => resolve(false), 5000);
              newImg.onload = () => {
                clearTimeout(timeout);
                resolve(true);
              };
              newImg.onerror = () => {
                clearTimeout(timeout);
                resolve(false);
              };
              newImg.src = result.card.image + '?t=' + Date.now(); // Cache bust
            });
            
            if (loaded) {
              console.log(`✅ Successfully loaded downloaded image for ${displayName}`);
              setCurrentImagePath(result.card.image);
              cachedImagePathRef.current = result.card.image; // Cache the image path
              lastLoadedCardRef.current = cardIdentity; // Remember we loaded this card
              return;
            }
          } else {
            console.warn(`⚠️ Failed to download image for ${displayName}:`, result.error);
          }
        } catch (error) {
          console.error(`❌ Error downloading image for ${displayName}:`, error);
        }
      }

      // If download failed or wasn't attempted, use card-back fallback
      console.log('⚠️ All paths failed, using fallback:', cardBackPath);
      setCurrentImagePath(cardBackPath);
      cachedImagePathRef.current = cardBackPath; // Cache even the fallback
      lastLoadedCardRef.current = cardIdentity; // Remember we tried this card
    };

    tryLoadImage();
  }, [card.cardId, card.name]); // Only re-run if card identity changes, not on zone moves

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

  // Calculate card dimensions with global scale
  const baseWidth = cardWidth || (inHand ? 246 : 119);
  const baseHeight = cardHeight || (inHand ? 345 : 166);
  // Round to whole pixels
  const width = Math.round(baseWidth * cardScale);
  const height = Math.round(baseHeight * cardScale);

  const handleHoverStart = () => {
    console.log('🔍 HOVER START:', {
      cardName: card.name,
      inHand,
      scale: inHand ? 1.6 : 1.8, // Adjusted scale for larger base size
      yOffset: inHand ? -80 : 0,
      width,
      height
    });
  };

  const handleHoverEnd = () => {
    console.log('🔍 HOVER END:', card.name);
  };

  return (
    <div
      className={`card-frame cursor-pointer select-none ${isDragging ? 'opacity-50' : ''}`}
      style={{
        width: `${width}px`,
        height: `${height}px`,
        transformOrigin: 'center center',
        overflow: 'visible',
        // Don't force GPU compositing in hand - let browser handle it naturally
        // This prevents subpixel blur on high-DPI displays
        ...(inHand ? {} : { transform: 'translateZ(0)' }),
        ...style,
      }}
        draggable
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onClick={handleClick}
        onContextMenu={(e) => {
          e.preventDefault();
          if (onContextMenu) onContextMenu(e);
        }}
      onMouseEnter={() => {
        if (inHand || disableHover || !hoverZoomEnabled) return;
        handleHoverStart();
        if (hoverZoomTimerRef.current) window.clearTimeout(hoverZoomTimerRef.current);
        hoverZoomTimerRef.current = window.setTimeout(() => setHoverZoomActive(true), 800);
      }}
      onMouseLeave={() => {
        if (inHand || disableHover) return;
        handleHoverEnd();
        if (hoverZoomTimerRef.current) window.clearTimeout(hoverZoomTimerRef.current);
        hoverZoomTimerRef.current = null;
        setHoverZoomActive(false);
      }}
    >
      <motion.div
        className="relative"
        style={{ 
          width: `${width}px`,
          height: `${height}px`,
          overflow: 'visible', 
          pointerEvents: 'none',
          // Only force GPU compositing when needed (not in hand default state)
          ...(inHand && !hoverZoomActive ? {} : { transform: 'translateZ(0)' }),
        }}
        animate={{
          rotate: card.tapped && !inHand ? 90 : 0,
          scale: !inHand && !disableHover && hoverZoomActive && hoverZoomEnabled ? hoverZoomValue : 1,
        }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
      >
        {/* Check if it's a token - always show as face-down with Token label */}
        {card.data?.is_token ? (
          <div className="w-full h-full relative">
            <img
              src="/Magic_the_gathering-card_back.jpg"
              alt="Token"
              className="w-full h-full object-cover"
              style={{
                // Removed crisp-edges to improve quality
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
              // Removed crisp-edges
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
                  objectFit: 'cover',
                  borderRadius: '0.5rem',
                  // Don't apply any transforms to image - let it render at natural size
                  // This prevents browser from scaling/rendering at wrong resolution
                  display: 'block',
                  // Ensure image renders crisply without browser smoothing artifacts
                  imageRendering: 'auto',
                }}
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  console.error('❌ Image failed to load:', {
                    attemptedPath: currentImagePath,
                    fullUrl: target.src,
                    cardName: card.name,
                    cardId: card.cardId
                  });
                  
                  // If card-back fails, there's nothing more we can do
                  if (currentImagePath.includes('card-back')) {
                    return;
                  }
                  
                  // The download attempt should have already happened in the useEffect
                  // This is just a fallback in case the image element's onError fires
                  // before the useEffect's download attempt completes
                }}
                onLoad={(e) => {
                  const target = e.target as HTMLImageElement;
                  console.log('✅ Image loaded:', {
                    path: currentImagePath,
                    fullUrl: target.src,
                    cardName: card.name,
                    dimensions: `${target.naturalWidth}x${target.naturalHeight}`
                  });
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
        
        {/* Tapped indicator - removed */}
        
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
    </motion.div>
    </div>
  );
};

export default Card;
