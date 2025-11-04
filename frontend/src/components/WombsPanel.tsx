/**
 * Wombs Panel - Unified view showing all unlocked wombs (built + unbuilt)
 */
import type { GameState } from '../types/game';
import { getWombCount, getUnlockedWombCount, getParallelWombStatus } from '../utils/wombs';
import './WombsPanel.css';

interface WombsPanelProps {
  state: GameState;
  onRepair?: (wombId: number) => void;
  onBuild?: () => void;
  disabled?: boolean;
}

export function WombsPanel({ state, onRepair, onBuild, disabled = false }: WombsPanelProps) {
  const wombs = state.wombs || [];
  const wombCount = getWombCount(state);
  const unlockedCount = getUnlockedWombCount(state);
  const maxWombs = 4; // Always show all 4 womb slots
  
  // Get parallel womb status
  const parallelStatus = getParallelWombStatus(state);
  
  // Create array of all 4 womb slots (0 to 3)
  const wombSlots = Array.from({ length: maxWombs }, (_, i) => i);
  
  // Build parallel status tooltip
  const parallelTooltip = parallelStatus.isParallelActive
    ? `Parallel Active: ${parallelStatus.functionalCount} functional womb(s)\n` +
      `Grow Slots: ${parallelStatus.activeGrowTasks}/${parallelStatus.maxSlots} in use\n` +
      `Overload: +${4 * (parallelStatus.functionalCount - 1)} attention, ${(1.03 ** (parallelStatus.functionalCount - 1)).toFixed(2)}x time\n` +
      `Risk: Feral attacks cause splash damage to all wombs`
    : '';
  
  return (
    <div className="panel wombs-panel">
      <div className="panel-header">
        <span>Wombs ({wombCount}/{unlockedCount})</span>
        {parallelStatus.isParallelActive && (
          <span 
            className="parallel-status-badge" 
            title={parallelTooltip}
          >
            Parallel Active ({parallelStatus.activeGrowTasks}/{parallelStatus.maxSlots})
          </span>
        )}
      </div>
      <div className="panel-content">
        <div className="wombs-grid">
          {wombSlots.map((wombId) => {
            const womb = wombs.find(w => w.id === wombId);
            const isBuilt = !!womb;
            // Only show build button on the next unbuilt womb (sequential building)
            const isNextUnbuilt = !isBuilt && wombId === wombCount;
            
            if (!isBuilt) {
              // Unbuilt womb - show greyed out placeholder
              const isLocked = wombId >= unlockedCount; // Beyond unlocked count = locked
              
              // Get unlock hint for this specific womb
              const getUnlockHintForWomb = (wombIndex: number): string => {
                if (wombIndex === 0) return "Available to build now";
                if (wombIndex === 1) {
                  const levels = state.practice_levels;
                  const maxLevel = Math.max(levels.Kinetic, levels.Cognitive, levels.Constructive);
                  if (maxLevel < 4) return "Unlock: Reach any Practice Level 4";
                  return "Available to build";
                }
                if (wombIndex === 2) {
                  const levels = state.practice_levels;
                  const maxLevel = Math.max(levels.Kinetic, levels.Cognitive, levels.Constructive);
                  if (maxLevel < 7) return "Unlock: Reach any Practice Level 7";
                  return "Available to build";
                }
                if (wombIndex === 3) {
                  const levels = state.practice_levels;
                  const practicesAtL9 = [
                    levels.Kinetic >= 9,
                    levels.Cognitive >= 9,
                    levels.Constructive >= 9
                  ].filter(Boolean).length;
                  if (practicesAtL9 < 2) return "Unlock: Two Practices at Level 9";
                  return "Available to build";
                }
                return "Locked";
              };
              
              const unlockHint = getUnlockHintForWomb(wombId);
              
              return (
                <div 
                  key={wombId} 
                  className={`womb-card womb-card-unbuilt ${isLocked ? 'womb-card-locked' : ''}`}
                  title={unlockHint}
                >
                  <div className="womb-card-header">
                    <div className="womb-card-title">Womb {wombId + 1}</div>
                    <div className={`womb-card-status-badge ${isLocked ? 'locked' : 'unlocked'}`}>
                      {isLocked ? 'LOCKED' : 'NOT BUILT'}
                    </div>
                  </div>
                  <div className="womb-card-content-unbuilt">
                    <div className="womb-card-hint">{isLocked ? unlockHint : 'Not built yet'}</div>
                    {isNextUnbuilt && onBuild && !isLocked && (
                      <button
                        className="womb-card-build-btn"
                        onClick={onBuild}
                        disabled={disabled}
                        title={unlockHint}
                      >
                        Build Womb
                      </button>
                    )}
                  </div>
                </div>
              );
            }
            
            // Built womb - show full details
            const durabilityPercent = womb.max_durability > 0
              ? (womb.durability / womb.max_durability) * 100
              : 0;

            const durabilityColor = durabilityPercent >= 50 ? 'good' : durabilityPercent >= 25 ? 'warning' : 'critical';
            const isFunctional = womb.durability > 0;
            const needsRepair = durabilityPercent < 50;  // Only show "needs repair" below 50%
            
            // Flavorful tooltip with subtle functional hints
            const wombTooltip = isFunctional 
              ? "The vessel of becoming. Where clones are shaped from essence. Integrity must be maintained, or the vessel fails."
              : "The vessel is broken. Repair restores its function and allows the cycle to continue.";
            
            return (
              <div 
                key={wombId} 
                className={`womb-card ${!isFunctional ? 'womb-card-damaged' : ''}`}
                title={wombTooltip}
              >
                <div className="womb-card-header">
                  <div className="womb-card-title">Womb {womb.id + 1}</div>
                  {!isFunctional && (
                    <div className="womb-card-status-badge critical">DAMAGED</div>
                  )}
                  {isFunctional && needsRepair && (
                    <div className="womb-card-status-badge warning">NEEDS REPAIR</div>
                  )}
                  {isFunctional && !needsRepair && (
                    <div className="womb-card-status-badge good">OPERATIONAL</div>
                  )}
                </div>
                
                <div className="womb-card-content">
                  <div className="womb-card-durability">
                    <div className="womb-card-durability-label">Health</div>
                    <div className="womb-card-durability-value">
                      {womb.durability.toFixed(1)} / {womb.max_durability.toFixed(1)}
                    </div>
                    <div className="womb-card-durability-bar">
                      <div 
                        className={`womb-card-durability-fill ${durabilityColor}`}
                        style={{ width: `${durabilityPercent}%` }}
                      />
                    </div>
                  </div>
                  
                  {/* Show repair button only when durability < 50% */}
                  {onRepair && needsRepair && (
                    <button
                      className="womb-card-action-btn"
                      onClick={() => onRepair(womb.id)}
                      disabled={disabled}
                      title="Repair womb (restores 5 durability points)"
                    >
                      Repair
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
