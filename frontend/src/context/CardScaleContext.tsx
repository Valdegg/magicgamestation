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

interface CardScaleContextType {
  cardScale: number; // 0.8 to 1.4
  setCardScale: (scale: number) => void;
  resetScale: () => void;
  hoverZoom: HoverZoomOption;
  setHoverZoom: (option: HoverZoomOption) => void;
  hoverZoomValue: number; // The actual scale value
}

const CardScaleContext = createContext<CardScaleContextType | undefined>(undefined);

const STORAGE_KEY = 'mtg_card_scale';
const HOVER_ZOOM_STORAGE_KEY = 'mtg_hover_zoom';
const DEFAULT_SCALE = 1.0;
const MIN_SCALE = 0.8;
const MAX_SCALE = 1.4;
const DEFAULT_HOVER_ZOOM: HoverZoomOption = 'normal';

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

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, cardScale.toString());
  }, [cardScale]);

  useEffect(() => {
    localStorage.setItem(HOVER_ZOOM_STORAGE_KEY, hoverZoom);
  }, [hoverZoom]);

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

  const hoverZoomValue = HOVER_ZOOM_VALUES[hoverZoom];

  return (
    <CardScaleContext.Provider value={{ 
      cardScale, 
      setCardScale, 
      resetScale, 
      hoverZoom, 
      setHoverZoom, 
      hoverZoomValue 
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

