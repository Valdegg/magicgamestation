import React from 'react';
import { motion } from 'framer-motion';

interface PhaseTrackerProps {
  currentPhase: string;
  onPhaseClick: (phase: string, isDoubleClick?: boolean) => void;
  onEndTurn: () => void;
  isMyTurn: boolean;
  vertical?: boolean;
}

const PhaseTracker: React.FC<PhaseTrackerProps> = ({ currentPhase, onPhaseClick, onEndTurn, isMyTurn, vertical = false }) => {
  const startPhases = [
    { id: 'untap', label: 'Untap', fullLabel: 'Untap Step', icon: '⟲' },
    { id: 'upkeep', label: 'Upkeep', fullLabel: 'Upkeep Step', icon: '⏱' },
    { id: 'draw', label: 'Draw', fullLabel: 'Draw Step', icon: '🎴' },
  ];

  const combatPhases = [
    { id: 'begin_combat', label: 'Begin', fullLabel: 'Beginning of Combat', icon: '⚔' },
    { id: 'declare_attackers', label: 'Attack', fullLabel: 'Declare Attackers', icon: '⚔' },
    { id: 'declare_blockers', label: 'Block', fullLabel: 'Declare Blockers', icon: '◈' },
    { id: 'damage', label: 'Damage', fullLabel: 'Combat Damage', icon: '✦' },
    { id: 'end_combat', label: 'End', fullLabel: 'End of Combat', icon: '✓' },
  ];

  const endPhases = [
    { id: 'end_step', label: 'End', fullLabel: 'End Step', icon: '◆' },
    { id: 'cleanup', label: 'Cleanup', fullLabel: 'Cleanup Step', icon: '∅' },
  ];

  const main1Phase = { id: 'main_1', label: 'Main 1', fullLabel: 'Pre-Combat Main Phase', icon: '★' };
  const main2Phase = { id: 'main_2', label: 'Main 2', fullLabel: 'Post-Combat Main Phase', icon: '★' };
  
  const allPhases = [...startPhases, main1Phase, ...combatPhases, main2Phase, ...endPhases];
  
  const renderPhaseButton = (phase: typeof allPhases[0], isInCombat = false) => {
    const isActive = currentPhase === phase.id;
    const isPast = allPhases.findIndex(p => p.id === currentPhase) > allPhases.findIndex(p => p.id === phase.id);
    const isMain = phase.id === 'main_1' || phase.id === 'main_2';
    
    // Vertical mode settings - larger icons
    const vPadding = isMain ? '6px 4px' : (isInCombat ? '4px 3px' : '5px 4px');
    const vIconSize = isMain ? '1.1rem' : (isInCombat ? '0.85rem' : '0.95rem');
    const vMinWidth = '100%';
    
    // Get the full label for tooltip
    const tooltipText = phase.fullLabel || phase.label;
    
    return (
      <motion.button
        key={phase.id}
        disabled={!isMyTurn}
        title={tooltipText}
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
          padding: vertical ? vPadding : (isMain ? '4px 12px' : (isInCombat ? '3px 6px' : '4px 8px')),
          fontSize: vertical ? '0.5rem' : (isMain ? '0.65rem' : (isInCombat ? '0.55rem' : '0.6rem')),
          minWidth: vertical ? vMinWidth : (isMain ? '70px' : (isInCombat ? '45px' : '55px')),
          width: vertical ? '100%' : undefined,
        }}
        whileHover={isMyTurn ? { scale: isActive ? 1.06 : 1.02 } : {}}
        whileTap={isMyTurn ? { scale: 0.98 } : {}}
        onClick={() => isMyTurn && onPhaseClick(phase.id, false)}
        onDoubleClick={() => isMyTurn && onPhaseClick(phase.id, true)}
      >
        <div className={`flex ${vertical ? 'flex-row justify-center' : 'flex-col'} items-center gap-0`}>
          <div style={{ fontSize: vertical ? vIconSize : (isMain ? '0.9rem' : '0.75rem') }}>{phase.icon}</div>
          {!vertical && <div className="whitespace-nowrap">{phase.label}</div>}
        </div>
      </motion.button>
    );
  };

  // Vertical layout for right sidebar
  if (vertical) {
    return (
      <div 
        className="h-full py-1 px-1 overflow-y-auto relative flex flex-col"
        style={{
          background: 'linear-gradient(to bottom, rgba(26, 10, 10, 0.85) 0%, rgba(60, 15, 15, 0.9) 20%, rgba(60, 15, 15, 0.9) 80%, rgba(26, 10, 10, 0.85) 100%)',
          borderLeft: '2px solid rgba(212, 179, 107, 0.3)',
          borderRight: '2px solid rgba(212, 179, 107, 0.3)',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.5), inset 0 1px 2px rgba(212, 179, 107, 0.15)',
          width: '55px',
        }}
      >
        <div className="flex flex-col gap-0.5 items-center flex-1">
          {/* Start Phases */}
          {startPhases.map(phase => renderPhaseButton(phase))}
          
          <div className="text-[0.5rem] font-bold" style={{ color: 'rgba(212, 179, 107, 0.3)' }}>▼</div>
          
          {/* Main Phase 1 */}
          {renderPhaseButton(main1Phase)}
          
          <div className="text-[0.5rem] font-bold" style={{ color: 'rgba(212, 179, 107, 0.3)' }}>▼</div>
          
          {/* Combat Box */}
          <div 
            className="flex flex-col gap-0.5 p-0.5 rounded-lg w-full"
            style={{
              background: 'linear-gradient(135deg, rgba(139, 0, 0, 0.15) 0%, rgba(80, 0, 0, 0.2) 100%)',
              border: '1px solid rgba(220, 38, 38, 0.3)',
            }}
          >
            <div 
              className="font-bold text-center opacity-60"
              style={{ color: 'rgba(220, 38, 38, 0.8)', fontSize: '0.4rem', letterSpacing: '0.05em' }}
            >
              CBT
            </div>
            {combatPhases.map(phase => renderPhaseButton(phase, true))}
          </div>
          
          <div className="text-[0.5rem] font-bold" style={{ color: 'rgba(212, 179, 107, 0.3)' }}>▼</div>
          
          {/* Main Phase 2 */}
          {renderPhaseButton(main2Phase)}
          
          <div className="text-[0.5rem] font-bold" style={{ color: 'rgba(212, 179, 107, 0.3)' }}>▼</div>
          
          {/* End Phases */}
          {endPhases.map(phase => renderPhaseButton(phase))}
          
          {/* Next Phase Button - big obvious button */}
          <motion.button
            disabled={!isMyTurn}
            title="Next Phase"
            className="relative w-full py-2 mt-2 rounded-lg font-bold transition-all"
            style={{
              background: isMyTurn 
                ? 'linear-gradient(135deg, #4ade80 0%, #22c55e 50%, #16a34a 100%)'
                : 'linear-gradient(135deg, rgba(40, 40, 40, 0.6) 0%, rgba(30, 30, 30, 0.7) 100%)',
              border: isMyTurn ? '2px solid #86efac' : '2px solid rgba(100, 100, 100, 0.3)',
              color: isMyTurn ? '#052e16' : 'rgba(150, 150, 150, 0.5)',
              boxShadow: isMyTurn 
                ? '0 0 15px rgba(74, 222, 128, 0.4), 0 3px 8px rgba(0, 0, 0, 0.5)'
                : 'none',
              opacity: !isMyTurn ? 0.4 : 1,
              cursor: !isMyTurn ? 'not-allowed' : 'pointer'
            }}
            whileHover={isMyTurn ? { scale: 1.05, boxShadow: '0 0 20px rgba(74, 222, 128, 0.6), 0 4px 12px rgba(0, 0, 0, 0.5)' } : {}}
            whileTap={isMyTurn ? { scale: 0.95 } : {}}
            onClick={() => isMyTurn && onPhaseClick('next')}
          >
            <div className="flex flex-col items-center gap-0">
              <div className="text-xl">▶</div>
              <div className="text-[0.5rem] font-bold tracking-wider">NEXT</div>
            </div>
          </motion.button>
          
          {/* End Turn Button - right below Next */}
          <motion.button
            disabled={!isMyTurn}
            title="End Turn"
            className="relative w-full py-2 mt-1 rounded-lg font-bold transition-all"
            style={{
              background: isMyTurn 
                ? 'linear-gradient(135deg, #f87171 0%, #ef4444 50%, #dc2626 100%)'
                : 'linear-gradient(135deg, rgba(40, 40, 40, 0.6) 0%, rgba(30, 30, 30, 0.7) 100%)',
              border: isMyTurn ? '2px solid #fca5a5' : '2px solid rgba(100, 100, 100, 0.3)',
              color: isMyTurn ? '#450a0a' : 'rgba(150, 150, 150, 0.5)',
              boxShadow: isMyTurn 
                ? '0 0 15px rgba(248, 113, 113, 0.4), 0 3px 8px rgba(0, 0, 0, 0.5)'
                : 'none',
              opacity: !isMyTurn ? 0.4 : 1,
              cursor: !isMyTurn ? 'not-allowed' : 'pointer'
            }}
            whileHover={isMyTurn ? { scale: 1.05, boxShadow: '0 0 20px rgba(248, 113, 113, 0.6), 0 4px 12px rgba(0, 0, 0, 0.5)' } : {}}
            whileTap={isMyTurn ? { scale: 0.95 } : {}}
            onClick={() => isMyTurn && onEndTurn()}
          >
            <div className="flex flex-col items-center gap-0">
              <div className="text-xl">⏭</div>
              <div className="text-[0.5rem] font-bold tracking-wider">END</div>
            </div>
          </motion.button>
          
          {/* Spacer at bottom */}
          <div className="flex-1" />
        </div>
      </div>
    );
  }

  // Horizontal layout (original)
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
        {renderPhaseButton(main1Phase)}
        
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
        {renderPhaseButton(main2Phase)}
        
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

