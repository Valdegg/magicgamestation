import React, { useState } from 'react';
import { motion } from 'framer-motion';

import { CardData } from '../types';

interface OpponentCardProps {
  card: CardData;
  onCardTargeted: (sourceCardId: string, targetCardId: string) => void;
  scale?: number;
}

const OpponentCard: React.FC<OpponentCardProps> = ({ card, onCardTargeted, scale = 1 }) => {
  const [isDragOver, setIsDragOver] = useState(false);

  const baseWidth = 90;
  const baseHeight = 126;
  const scaledWidth = baseWidth * scale;
  const scaledHeight = baseHeight * scale;

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
      whileHover={{ 
        scale: 1.7,
        y: 80,
        zIndex: 1000,
        transition: { duration: 0.2, delay: 0.8 }
      }}
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
      ) : (
        <img
          src={`/card_images/${card.name?.replace(/\s+/g, '_')}.jpg`}
          alt={card.name || 'Card'}
          className="w-full h-full object-cover rounded"
          style={{
            boxShadow: '0 2px 6px rgba(0, 0, 0, 0.6), 0 0 10px rgba(212, 179, 107, 0.2)',
            border: '1px solid rgba(212, 179, 107, 0.4)',
            overflow: 'visible'
          }}
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            const parent = target.parentElement;
            if (parent) {
              parent.style.background = 'linear-gradient(135deg, #4a3728 0%, #3a2718 100%)';
              parent.style.display = 'flex';
              parent.style.alignItems = 'center';
              parent.style.justifyContent = 'center';
              parent.innerHTML = `<span style="color: #d4b36b; font-size: 0.7rem; text-align: center; padding: 4px;">${card.name || 'Unknown'}</span>`;
            }
          }}
        />
      )}
    </motion.div>
  );
};

export default OpponentCard;

