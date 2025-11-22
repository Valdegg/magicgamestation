import React from 'react';
import { motion } from 'framer-motion';

interface PhaseTrackerProps {
  currentPhase: string;
  onPhaseClick: (phase: string) => void;
  onEndTurn: () => void;
  isMyTurn: boolean;
}

const PhaseTracker: React.FC<PhaseTrackerProps> = ({ currentPhase, onPhaseClick, onEndTurn, isMyTurn }) => {
  const startPhases = [
    { id: 'untap', label: 'Untap', icon: '⟲' },
    { id: 'upkeep', label: 'Upkeep', icon: '⏱' },
    { id: 'draw', label: 'Draw', icon: '🎴' },
  ];

  const combatPhases = [
    { id: 'begin_combat', label: 'Begin', icon: '⚔' },
    { id: 'declare_attackers', label: 'Attack', icon: '⚔' },
    { id: 'declare_blockers', label: 'Block', icon: '◈' },
    { id: 'damage', label: 'Damage', icon: '✦' },
    { id: 'end_combat', label: 'End', icon: '✓' },
  ];

  const endPhases = [
    { id: 'end_step', label: 'End', icon: '◆' },
    { id: 'cleanup', label: 'Cleanup', icon: '∅' },
  ];

  const allPhases = [...startPhases, { id: 'main_1', label: 'Main 1', icon: '★' }, ...combatPhases, { id: 'main_2', label: 'Main 2', icon: '★' }, ...endPhases];
  
  const renderPhaseButton = (phase: typeof allPhases[0], isInCombat = false) => {
    const isActive = currentPhase === phase.id;
    const isPast = allPhases.findIndex(p => p.id === currentPhase) > allPhases.findIndex(p => p.id === phase.id);
    const isMain = phase.id === 'main_1' || phase.id === 'main_2';
    
    return (
      <motion.button
        key={phase.id}
        disabled={!isMyTurn}
        className="relative rounded-lg font-bold transition-all uppercase tracking-wide"
        style={{
          background: isActive
            ? 'linear-gradient(135deg, #f4d589 0%, #d4b36b 50%, #8b7355 100%)'
            : isPast
            ? 'linear-gradient(135deg, rgba(60, 15, 15, 0.5) 0%, rgba(26, 10, 10, 0.7) 100%)'
            : 'linear-gradient(135deg, rgba(40, 20, 20, 0.8) 0%, rgba(60, 15, 15, 0.6) 100%)',
          border: isActive 
            ? '2px solid #d4b36b' 
            : '2px solid rgba(212, 179, 107, 0.25)',
          color: isActive ? '#1a0a0a' : isPast ? 'rgba(231, 216, 177, 0.4)' : 'rgba(231, 216, 177, 0.85)',
          boxShadow: isActive
            ? '0 0 15px rgba(212, 179, 107, 0.4), inset 0 1px 2px rgba(255, 255, 255, 0.3), 0 3px 8px rgba(0, 0, 0, 0.5)'
            : isPast
            ? 'inset 0 2px 4px rgba(0, 0, 0, 0.6)'
            : '0 2px 6px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(212, 179, 107, 0.1)',
          transform: isActive ? 'scale(1.04)' : 'scale(1)',
          opacity: !isMyTurn ? 0.4 : 1,
          cursor: !isMyTurn ? 'not-allowed' : 'pointer',
          padding: isMain ? '4px 12px' : (isInCombat ? '3px 6px' : '4px 8px'),
          fontSize: isMain ? '0.65rem' : (isInCombat ? '0.55rem' : '0.6rem'),
          minWidth: isMain ? '70px' : (isInCombat ? '45px' : '55px')
        }}
        whileHover={isMyTurn ? { scale: isActive ? 1.06 : 1.02 } : {}}
        whileTap={isMyTurn ? { scale: 0.98 } : {}}
        onClick={() => isMyTurn && onPhaseClick(phase.id)}
      >
        <div className="flex flex-col items-center gap-0">
          <div className="opacity-70" style={{ fontSize: isMain ? '0.9rem' : '0.75rem' }}>{phase.icon}</div>
          <div className="whitespace-nowrap">{phase.label}</div>
        </div>
      </motion.button>
    );
  };

  return (
    <div 
      className="w-full py-0.5 px-2 overflow-x-auto relative"
      style={{
        background: 
          'linear-gradient(to right, rgba(26, 10, 10, 0.85) 0%, rgba(60, 15, 15, 0.9) 20%, rgba(60, 15, 15, 0.9) 80%, rgba(26, 10, 10, 0.85) 100%)',
        borderTop: '2px solid transparent',
        borderBottom: '2px solid transparent',
        borderImage: 'linear-gradient(90deg, transparent 0%, rgba(212, 179, 107, 0.3) 10%, rgba(212, 179, 107, 0.4) 50%, rgba(212, 179, 107, 0.3) 90%, transparent 100%) 1',
        boxShadow: 
          '0 2px 8px rgba(0, 0, 0, 0.5), ' +
          'inset 0 1px 2px rgba(212, 179, 107, 0.15), ' +
          'inset 0 -1px 2px rgba(0, 0, 0, 0.3)'
      }}
    >
      <div className="flex gap-1 justify-center items-center min-w-max mx-auto">
        {/* Start Phases */}
        {startPhases.map(phase => renderPhaseButton(phase))}
        
        <div className="text-xs font-bold" style={{ color: 'rgba(212, 179, 107, 0.3)' }}>▶</div>
        
        {/* Main Phase 1 - Larger */}
        {renderPhaseButton({ id: 'main_1', label: 'Main 1', icon: '★' })}
        
        <div className="text-xs font-bold" style={{ color: 'rgba(212, 179, 107, 0.3)' }}>▶</div>
        
        {/* Combat Box */}
        <div 
          className="flex gap-0.5 p-1 rounded-lg"
          style={{
            background: 'linear-gradient(135deg, rgba(139, 0, 0, 0.15) 0%, rgba(80, 0, 0, 0.2) 100%)',
            border: '1px solid rgba(220, 38, 38, 0.3)',
            boxShadow: 'inset 0 1px 2px rgba(220, 38, 38, 0.2)'
          }}
        >
          <div 
            className="font-bold self-center mr-0.5 opacity-60"
            style={{ 
              color: 'rgba(220, 38, 38, 0.8)',
              writingMode: 'vertical-rl',
              transform: 'rotate(180deg)',
              letterSpacing: '0.05em',
              fontSize: '0.6rem'
            }}
          >
            COMBAT
          </div>
          {combatPhases.map((phase, idx) => (
            <React.Fragment key={phase.id}>
              {renderPhaseButton(phase, true)}
              {idx < combatPhases.length - 1 && (
                <div className="font-bold self-center" style={{ color: 'rgba(212, 179, 107, 0.3)', fontSize: '0.6rem' }}>›</div>
              )}
            </React.Fragment>
          ))}
        </div>
        
        <div className="text-xs font-bold" style={{ color: 'rgba(212, 179, 107, 0.3)' }}>▶</div>
        
        {/* Main Phase 2 - Larger */}
        {renderPhaseButton({ id: 'main_2', label: 'Main 2', icon: '★' })}
        
        <div className="text-xs font-bold" style={{ color: 'rgba(212, 179, 107, 0.3)' }}>▶</div>
        
        {/* End Phases */}
        {endPhases.map(phase => renderPhaseButton(phase))}
        
        {/* Separator before End Turn */}
        <div className="text-xs font-bold mx-1" style={{ color: 'rgba(212, 179, 107, 0.3)' }}>|</div>
        
        {/* End Turn Button */}
        <motion.button
          disabled={!isMyTurn}
          className="relative px-2 py-0.5 rounded-lg font-bold transition-all uppercase tracking-wide"
          style={{
            background: 'linear-gradient(135deg, rgba(139, 0, 0, 0.8) 0%, rgba(80, 0, 0, 0.9) 100%)',
            border: '2px solid rgba(220, 38, 38, 0.5)',
            color: 'rgba(254, 202, 202, 0.9)',
            boxShadow: '0 2px 6px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(220, 38, 38, 0.2)',
            minWidth: '65px',
            fontSize: '0.6rem',
            opacity: !isMyTurn ? 0.4 : 1,
            cursor: !isMyTurn ? 'not-allowed' : 'pointer'
          }}
          whileHover={isMyTurn ? { 
            scale: 1.03,
            boxShadow: '0 3px 10px rgba(220, 38, 38, 0.4), inset 0 1px 0 rgba(220, 38, 38, 0.3)'
          } : {}}
          whileTap={isMyTurn ? { scale: 0.98 } : {}}
          onClick={() => isMyTurn && onEndTurn()}
        >
          <div className="flex flex-col items-center gap-0.5">
            <div className="text-sm opacity-70">⏭</div>
            <div className="whitespace-nowrap">End Turn</div>
          </div>
        </motion.button>
      </div>
    </div>
  );
};

export default PhaseTracker;

