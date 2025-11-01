/**
 * Clone Details Panel - shows selected clone information and actions
 */
import type { Clone } from '../types/game';
import './CloneDetailsPanel.css';

interface CloneDetailsPanelProps {
  clone: Clone | null;
  onApply: () => void;
  onRunExpedition: (kind: string) => void;
  onUpload: () => void;
  disabled: boolean;
}

export function CloneDetailsPanel({
  clone,
  onApply,
  onRunExpedition,
  onUpload,
  disabled,
}: CloneDetailsPanelProps) {
  if (!clone) {
    return (
      <div className="panel clone-details-panel">
        <div className="panel-header">Clone Details</div>
        <div className="panel-content">
          <div className="empty-state">Select a clone to view details</div>
        </div>
      </div>
    );
  }

  const totalXp = clone.xp.MINING + clone.xp.COMBAT + clone.xp.EXPLORATION;

  return (
    <div className="panel clone-details-panel">
      <div className="panel-header">Clone Details</div>
      <div className="panel-content">
        <div className="clone-info">
          <div className="clone-info-row">
            <span className="label">Kind:</span>
            <span className="value">{clone.kind}</span>
          </div>
          <div className="clone-info-row">
            <span className="label">ID:</span>
            <span className="value">{clone.id}</span>
          </div>
          <div className="clone-info-row">
            <span className="label">Status:</span>
            <span className={`value ${clone.alive ? 'alive' : 'dead'}`}>
              {clone.alive ? 'ALIVE' : 'DEAD'}
            </span>
          </div>
          {clone.uploaded && (
            <div className="clone-info-row">
              <span className="label">Status:</span>
              <span className="value uploaded">UPLOADED</span>
            </div>
          )}
          <div className="clone-info-row">
            <span className="label">Survived Runs:</span>
            <span className="value">{clone.survived_runs}</span>
          </div>
          <div className="clone-info-row">
            <span className="label">Total XP:</span>
            <span className="value">{totalXp}</span>
          </div>
          <div className="xp-breakdown">
            <div className="xp-item">Mining: {clone.xp.MINING || 0}</div>
            <div className="xp-item">Combat: {clone.xp.COMBAT || 0}</div>
            <div className="xp-item">Exploration: {clone.xp.EXPLORATION || 0}</div>
          </div>
        </div>

        {clone.alive && !clone.uploaded && (
          <div className="clone-actions">
            <button
              className="action-button"
              onClick={onApply}
              disabled={disabled}
            >
              Apply Clone
            </button>
            <div className="expedition-buttons">
              <button
                className="action-button expedition-btn"
                onClick={() => onRunExpedition('MINING')}
                disabled={disabled}
              >
                Mining Expedition
              </button>
              <button
                className="action-button expedition-btn"
                onClick={() => onRunExpedition('COMBAT')}
                disabled={disabled}
              >
                Combat Expedition
              </button>
              <button
                className="action-button expedition-btn"
                onClick={() => onRunExpedition('EXPLORATION')}
                disabled={disabled}
              >
                Exploration Expedition
              </button>
            </div>
            <button
              className="action-button upload-btn"
              onClick={onUpload}
              disabled={disabled}
            >
              Upload to SELF
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

