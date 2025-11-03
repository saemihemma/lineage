/**
 * Wombs Panel - displays single womb with attention meter and teaser (before 2nd womb)
 */
import type { GameState } from '../types/game';
import { getWombCount, getUnlockedWombCount, getNextUnlockHint } from '../utils/wombs';
import './WombsPanel.css';

interface WombsPanelProps {
  state: GameState;
}

export function WombsPanel({ state }: WombsPanelProps) {
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
  const attentionPercent = firstWomb.max_attention > 0 
    ? (firstWomb.attention / firstWomb.max_attention) * 100 
    : 0;
  const durabilityPercent = firstWomb.max_durability > 0
    ? (firstWomb.durability / firstWomb.max_durability) * 100
    : 0;
  
  const attentionColor = attentionPercent >= 50 ? 'good' : attentionPercent >= 25 ? 'warning' : 'critical';
  const durabilityColor = durabilityPercent >= 50 ? 'good' : durabilityPercent >= 25 ? 'warning' : 'critical';
  
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
          
          {/* Attention */}
          <div className="womb-stat">
            <div className="womb-stat-label">Attention</div>
            <div className="womb-stat-bar">
              <div 
                className={`womb-stat-fill ${attentionColor}`}
                style={{ width: `${attentionPercent}%` }}
              />
              <div className="womb-stat-text">
                {firstWomb.attention.toFixed(1)} / {firstWomb.max_attention.toFixed(1)}
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
            {firstWomb.durability > 0 && firstWomb.attention < firstWomb.max_attention * 0.5 && (
              <div className="womb-status-warning">
                Attention is low. Womb may not function optimally.
              </div>
            )}
            {firstWomb.durability > 0 && firstWomb.attention >= firstWomb.max_attention * 0.5 && (
              <div className="womb-status-ok">
                Womb is operational
              </div>
            )}
          </div>
          
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

