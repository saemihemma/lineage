/**
 * Wombs Panel - Unified view showing all unlocked wombs (built + unbuilt)
 */
import type { GameState } from '../types/game';
import { getWombCount, getUnlockedWombCount, getNextUnlockHint } from '../utils/wombs';
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
  
  // Create array of all unlocked womb slots (0 to unlockedCount-1)
  const wombSlots = Array.from({ length: unlockedCount }, (_, i) => i);
  
  return (
    <div className="panel wombs-panel">
      <div className="panel-header">Wombs ({wombCount}/{unlockedCount})</div>
      <div className="panel-content">
        <div className="wombs-grid">
          {wombSlots.map((wombId) => {
            const womb = wombs.find(w => w.id === wombId);
            const isBuilt = !!womb;
            // Only show build button on the next unbuilt womb (sequential building)
            const isNextUnbuilt = !isBuilt && wombId === wombCount;
            
            if (!isBuilt) {
              // Unbuilt womb - show greyed out placeholder
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
                  className="womb-card womb-card-unbuilt"
                  title={unlockHint}
                >
                  <div className="womb-card-header">
                    <div className="womb-card-title">Womb {wombId + 1}</div>
                    <div className="womb-card-status-badge locked">LOCKED</div>
                  </div>
                  <div className="womb-card-content-unbuilt">
                    <div className="womb-card-hint">Not built yet</div>
                    {isNextUnbuilt && onBuild && (
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
            const needsRepair = womb.durability < womb.max_durability;
            
            return (
              <div 
                key={wombId} 
                className={`womb-card ${!isFunctional ? 'womb-card-damaged' : ''}`}
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
                      {Math.round(womb.durability)} / {Math.round(womb.max_durability)}
                    </div>
                    <div className="womb-card-durability-bar">
                      <div 
                        className={`womb-card-durability-fill ${durabilityColor}`}
                        style={{ width: `${durabilityPercent}%` }}
                      />
                    </div>
                  </div>
                  
                  {/* Always show repair button if onRepair handler exists */}
                  {onRepair && (
                    <button
                      className="womb-card-action-btn"
                      onClick={() => onRepair(womb.id)}
                      disabled={disabled || womb.durability >= womb.max_durability}
                      title={womb.durability >= womb.max_durability ? "Womb is at full durability" : "Repair womb"}
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
