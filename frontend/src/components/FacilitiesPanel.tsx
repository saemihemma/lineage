/**
 * Facilities Panel - displays grid of wombs when >= 2 wombs built
 */
import type { GameState, Womb } from '../types/game';
import { getAverageAttentionPercent } from '../utils/wombs';
import './FacilitiesPanel.css';

interface FacilitiesPanelProps {
  state: GameState;
  onRepair?: (wombId: number) => void;
  disabled?: boolean;
}

export function FacilitiesPanel({ state, onRepair, disabled = false }: FacilitiesPanelProps) {
  const wombs = state.wombs || [];
  
  if (wombs.length < 2) {
    return null; // Don't show if less than 2 wombs
  }
  
  const avgAttention = getAverageAttentionPercent(state);
  const attentionColor = avgAttention >= 50 ? 'good' : avgAttention >= 25 ? 'warning' : 'critical';
  
  return (
    <div className="panel facilities-panel">
      <div className="panel-header">
        Facilities ({wombs.length} Wombs)
        <div className="facilities-attention-bar">
          <div className="facilities-attention-label">Avg Attention:</div>
          <div className="facilities-attention-visual">
            <div 
              className={`facilities-attention-fill ${attentionColor}`}
              style={{ width: `${avgAttention}%` }}
            />
            <span className="facilities-attention-text">{avgAttention.toFixed(1)}%</span>
          </div>
        </div>
      </div>
      <div className="panel-content facilities-grid">
        {wombs.map((womb) => (
          <WombCard 
            key={womb.id} 
            womb={womb}
            state={state}
            onRepair={onRepair}
            disabled={disabled}
          />
        ))}
      </div>
    </div>
  );
}

interface WombCardProps {
  womb: Womb;
  state: GameState;
  onRepair?: (wombId: number) => void;
  disabled?: boolean;
}

function WombCard({ womb, state, onRepair, disabled }: WombCardProps) {
  // Attention is now global, not per-womb (0-100 scale)
  const attentionPercent = Math.min(100, Math.max(0, state.global_attention || 0));
  const durabilityPercent = womb.max_durability > 0
    ? (womb.durability / womb.max_durability) * 100
    : 0;
  
  const attentionColor = attentionPercent >= 50 ? 'good' : attentionPercent >= 25 ? 'warning' : 'critical';
  const durabilityColor = durabilityPercent >= 50 ? 'good' : durabilityPercent >= 25 ? 'warning' : 'critical';
  const isFunctional = womb.durability > 0;
  const needsRepair = womb.durability < womb.max_durability;
  
  return (
    <div className={`facilities-womb-card ${!isFunctional ? 'non-functional' : ''}`}>
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
      
      <div className="womb-card-stats">
        <div className="womb-card-stat">
          <div className="womb-card-stat-label">Durability</div>
          <div className="womb-card-stat-bar">
            <div 
              className={`womb-card-stat-fill ${durabilityColor}`}
              style={{ width: `${durabilityPercent}%` }}
            />
          </div>
          <div className="womb-card-stat-value">
            {womb.durability.toFixed(1)} / {womb.max_durability.toFixed(1)}
          </div>
        </div>
        
        <div className="womb-card-stat">
          <div className="womb-card-stat-label">Attention (Global)</div>
          <div className="womb-card-stat-bar">
            <div 
              className={`womb-card-stat-fill ${attentionColor}`}
              style={{ width: `${attentionPercent}%` }}
            />
          </div>
          <div className="womb-card-stat-value">
            {attentionPercent.toFixed(1)} / 100.0
          </div>
        </div>
      </div>
      
      {needsRepair && onRepair && (
        <button
          className="womb-card-repair-btn"
          onClick={() => onRepair(womb.id)}
          disabled={disabled}
        >
          Repair Womb
        </button>
      )}
    </div>
  );
}

