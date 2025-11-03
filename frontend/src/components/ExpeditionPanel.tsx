/**
 * ExpeditionPanel - Detailed view for expeditions
 * Shows expedition launch cards, results, and history
 */
import type { GameState } from '../types/game';
import './ExpeditionPanel.css';

interface ExpeditionPanelProps {
  state: GameState;
  onRunExpedition: (kind: string) => void;
  disabled?: boolean;
}

export function ExpeditionPanel({ state, onRunExpedition, disabled = false }: ExpeditionPanelProps) {
  const hasAppliedClone = state.applied_clone_id && 
    state.clones?.[state.applied_clone_id]?.alive;

  if (!hasAppliedClone) {
    return (
      <div className="panel expedition-panel">
        <div className="panel-header">Expeditions</div>
        <div className="panel-content">
          <div className="expedition-empty">
            <div className="expedition-empty-text">
              Apply a clone to go on expeditions
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel expedition-panel">
      <div className="panel-header">Expeditions</div>
      <div className="panel-content">
        <div className="expedition-launch">
          <div className="expedition-cards">
            <div className="expedition-card">
              <div className="expedition-card-title">Mining</div>
              <div className="expedition-card-desc">
                Earn Tritanium and Metal Ore
              </div>
              <button
                className="expedition-card-btn"
                onClick={() => onRunExpedition('MINING')}
                disabled={disabled}
              >
                Launch
              </button>
            </div>

            <div className="expedition-card">
              <div className="expedition-card-title">Combat</div>
              <div className="expedition-card-desc">
                Earn Biomass and Synthetic materials
              </div>
              <button
                className="expedition-card-btn"
                onClick={() => onRunExpedition('COMBAT')}
                disabled={disabled}
              >
                Launch
              </button>
            </div>

            <div className="expedition-card">
              <div className="expedition-card-title">Exploration</div>
              <div className="expedition-card-desc">
                Earn mixed resources
              </div>
              <button
                className="expedition-card-btn"
                onClick={() => onRunExpedition('EXPLORATION')}
                disabled={disabled}
              >
                Launch
              </button>
            </div>
          </div>
        </div>
        {/* TODO: Add expedition history/results display */}
      </div>
    </div>
  );
}

