import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ContextMenuProps {
  x: number;
  y: number;
  onClose: () => void;
  options: {
    label: string;
    onClick: () => void;
  }[];
}

const ContextMenu: React.FC<ContextMenuProps> = ({ x, y, onClose, options }) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = React.useState({ x, y });

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  // Adjust position to prevent menu from going off-screen
  useEffect(() => {
    if (menuRef.current) {
      const menuRect = menuRef.current.getBoundingClientRect();
      const windowWidth = window.innerWidth;
      const windowHeight = window.innerHeight;
      
      let adjustedX = x;
      let adjustedY = y;
      
      // Adjust horizontal position if menu would go off right edge
      if (x + menuRect.width > windowWidth) {
        adjustedX = windowWidth - menuRect.width - 10; // 10px margin
      }
      
      // Adjust vertical position if menu would go off bottom edge
      if (y + menuRect.height > windowHeight) {
        adjustedY = windowHeight - menuRect.height - 10; // 10px margin
      }
      
      // Keep menu at least 10px from edges
      adjustedX = Math.max(10, adjustedX);
      adjustedY = Math.max(10, adjustedY);
      
      setPosition({ x: adjustedX, y: adjustedY });
    }
  }, [x, y]);

  return (
    <AnimatePresence>
      <motion.div
        ref={menuRef}
        className="context-menu"
        style={{
          left: position.x,
          top: position.y,
          zIndex: 10000, // Ensure it's above all hover effects
        }}
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ duration: 0.15 }}
      >
        {options.map((option, index) => (
          <div
            key={index}
            className="context-menu-item"
            onClick={() => {
              option.onClick();
              onClose();
            }}
          >
            {option.label}
          </div>
        ))}
      </motion.div>
    </AnimatePresence>
  );
};

export default ContextMenu;

