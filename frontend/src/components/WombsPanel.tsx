/**
 * Wombs Panel - displays single womb with durability status and teaser (before 2nd womb)
 */
import type { GameState } from '../types/game';
import { getWombCount, getUnlockedWombCount, getNextUnlockHint } from '../utils/wombs';
import './WombsPanel.css';

interface WombsPanelProps {
  state: GameState;
  onRepair?: (wombId: number) => void;
  disabled?: boolean;
}

export function WombsPanel({ state, onRepair, disabled = false }: WombsPanelProps) {
  const wombs = state.wombs || [];
  const wombCount = getWombCount(state);
  const unlockedCount = getUnlockedWombCount(state);
  const nextHint = getNextUnlockHint(state);
  
  if (wombCount === 0) {
    return (
      <div className="panel wombs-panel">
        <div className="panel-header">Womb</div>
        <div className="panel-content">
          <div className="womb-empty">
            <div className="womb-status">No wombs built yet</div>
            <div className="womb-hint">Build your first womb to start growing clones</div>
          </div>
        </div>
      </div>
    );
  }
  
  // Show single womb view (before 2nd womb)
  const firstWomb = wombs[0];
  const durabilityPercent = firstWomb.max_durability > 0
    ? (firstWomb.durability / firstWomb.max_durability) * 100
    : 0;

  const durabilityColor = durabilityPercent >= 50 ? 'good' : durabilityPercent >= 25 ? 'warning' : 'critical';
  const needsRepair = firstWomb.durability < firstWomb.max_durability;
  
  return (
    <div className="panel wombs-panel">
      <div className="panel-header">Womb {firstWomb.id + 1}</div>
      <div className="panel-content">
        <div className="womb-single">
          {/* Durability */}
          <div className="womb-stat">
            <div className="womb-stat-label">Durability</div>
            <div className="womb-stat-bar">
              <div 
                className={`womb-stat-fill ${durabilityColor}`}
                style={{ width: `${durabilityPercent}%` }}
              />
              <div className="womb-stat-text">
                {firstWomb.durability.toFixed(1)} / {firstWomb.max_durability.toFixed(1)}
              </div>
            </div>
          </div>

          {/* Status */}
          <div className="womb-status-info">
            {firstWomb.durability <= 0 && (
              <div className="womb-status-critical">
                Womb is damaged and non-functional. Repair required.
              </div>
            )}
            {firstWomb.durability > 0 && !needsRepair && (
              <div className="womb-status-ok">
                Womb is operational
              </div>
            )}
            {firstWomb.durability > 0 && needsRepair && (
              <div className="womb-status-warning">
                Womb needs repair
              </div>
            )}
          </div>

          {/* Repair Button */}
          {needsRepair && onRepair && (
            <button
              className="womb-repair-btn"
              onClick={() => onRepair(firstWomb.id)}
              disabled={disabled}
            >
              Repair Womb
            </button>
          )}
          
          {/* Next Unlock Hint */}
          {wombCount < unlockedCount && nextHint && (
            <div className="womb-unlock-hint">
              <div className="womb-unlock-label">Next Womb Unlock:</div>
              <div className="womb-unlock-text">{nextHint}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

