/**
 * Wombs Panel - Unified view showing all unlocked wombs (built + unbuilt)
 */
import type { GameState } from '../types/game';
import { getWombCount, getUnlockedWombCount } from '../utils/wombs';
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
              return (
                <div key={wombId} className="womb-card womb-card-unbuilt">
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
                  
                  {needsRepair && onRepair && (
                    <button
                      className="womb-card-action-btn"
                      onClick={() => onRepair(womb.id)}
                      disabled={disabled}
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
