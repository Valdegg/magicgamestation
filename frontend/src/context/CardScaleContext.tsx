import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// Hover zoom options
export type HoverZoomOption = 'off' | 'subtle' | 'normal' | 'big';

export const HOVER_ZOOM_VALUES: Record<HoverZoomOption, number> = {
  off: 1.0,
  subtle: 1.5,
  normal: 1.8,
  big: 2.16,
};

export const HOVER_ZOOM_LABELS: Record<HoverZoomOption, string> = {
  off: 'Off',
  subtle: 'Subtle',
  normal: 'Normal',
  big: 'Big',
};

// Opponent card size options
export type OpponentCardSizeOption = 'small' | 'medium' | 'large' | 'xlarge';

export const OPPONENT_CARD_SIZE_VALUES: Record<OpponentCardSizeOption, number> = {
  small: 0.96,    // 0.8 * 1.2 = 96%
  medium: 1.2,    // 1.0 * 1.2 = 120%
  large: 1.44,    // 1.2 * 1.2 = 144%
  xlarge: 1.68,   // 1.4 * 1.2 = 168%
};

export const OPPONENT_CARD_SIZE_LABELS: Record<OpponentCardSizeOption, string> = {
  small: 'Small',
  medium: 'Medium',
  large: 'Large',
  xlarge: 'X-Large',
};

interface CardScaleContextType {
  cardScale: number; // 0.8 to 1.4
  setCardScale: (scale: number) => void;
  resetScale: () => void;
  hoverZoom: HoverZoomOption;
  setHoverZoom: (option: HoverZoomOption) => void;
  hoverZoomValue: number; // The actual scale value
  opponentCardSize: OpponentCardSizeOption;
  setOpponentCardSize: (option: OpponentCardSizeOption) => void;
  opponentCardSizeValue: number; // The actual scale value
}

const CardScaleContext = createContext<CardScaleContextType | undefined>(undefined);

const STORAGE_KEY = 'mtg_card_scale';
const HOVER_ZOOM_STORAGE_KEY = 'mtg_hover_zoom';
const OPPONENT_CARD_SIZE_STORAGE_KEY = 'mtg_opponent_card_size';
const DEFAULT_SCALE = 1.0;
const MIN_SCALE = 0.8;
const MAX_SCALE = 1.4;
const DEFAULT_HOVER_ZOOM: HoverZoomOption = 'normal';
const DEFAULT_OPPONENT_CARD_SIZE: OpponentCardSizeOption = 'medium';

export const CardScaleProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [cardScale, setCardScaleState] = useState<number>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = parseFloat(stored);
      if (!isNaN(parsed) && parsed >= MIN_SCALE && parsed <= MAX_SCALE) {
        return parsed;
      }
    }
    return DEFAULT_SCALE;
  });

  const [hoverZoom, setHoverZoomState] = useState<HoverZoomOption>(() => {
    const stored = localStorage.getItem(HOVER_ZOOM_STORAGE_KEY);
    if (stored && stored in HOVER_ZOOM_VALUES) {
      return stored as HoverZoomOption;
    }
    return DEFAULT_HOVER_ZOOM;
  });

  const [opponentCardSize, setOpponentCardSizeState] = useState<OpponentCardSizeOption>(() => {
    const stored = localStorage.getItem(OPPONENT_CARD_SIZE_STORAGE_KEY);
    if (stored && stored in OPPONENT_CARD_SIZE_VALUES) {
      return stored as OpponentCardSizeOption;
    }
    return DEFAULT_OPPONENT_CARD_SIZE;
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, cardScale.toString());
  }, [cardScale]);

  useEffect(() => {
    localStorage.setItem(HOVER_ZOOM_STORAGE_KEY, hoverZoom);
  }, [hoverZoom]);

  useEffect(() => {
    localStorage.setItem(OPPONENT_CARD_SIZE_STORAGE_KEY, opponentCardSize);
  }, [opponentCardSize]);

  const setCardScale = (scale: number) => {
    const clamped = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale));
    setCardScaleState(clamped);
  };

  const resetScale = () => {
    setCardScaleState(DEFAULT_SCALE);
  };

  const setHoverZoom = (option: HoverZoomOption) => {
    setHoverZoomState(option);
  };

  const setOpponentCardSize = (option: OpponentCardSizeOption) => {
    setOpponentCardSizeState(option);
  };

  const hoverZoomValue = HOVER_ZOOM_VALUES[hoverZoom];
  const opponentCardSizeValue = OPPONENT_CARD_SIZE_VALUES[opponentCardSize];

  return (
    <CardScaleContext.Provider value={{ 
      cardScale, 
      setCardScale, 
      resetScale, 
      hoverZoom, 
      setHoverZoom, 
      hoverZoomValue,
      opponentCardSize,
      setOpponentCardSize,
      opponentCardSizeValue
    }}>
      {children}
    </CardScaleContext.Provider>
  );
};

export const useCardScale = (): CardScaleContextType => {
  const context = useContext(CardScaleContext);
  if (!context) {
    throw new Error('useCardScale must be used within a CardScaleProvider');
  }
  return context;
};

export { MIN_SCALE, MAX_SCALE, DEFAULT_SCALE };

