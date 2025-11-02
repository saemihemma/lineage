/**
 * Clone Details Panel - shows selected clone information and actions
 */
import type { Clone } from '../types/game';
import './CloneDetailsPanel.css';

interface CloneDetailsPanelProps {
  clone: Clone | null;
  appliedCloneId: string | null;
  onApply: () => void;
  onUpload: () => void;
  disabled: boolean;
}

export function CloneDetailsPanel({
  clone,
  appliedCloneId,
  onApply,
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

  const totalXp = (clone.xp.MINING || 0) + (clone.xp.COMBAT || 0) + (clone.xp.EXPLORATION || 0);

  return (
    <div className="panel clone-details-panel">
      <div className="panel-header">Clone Details</div>
      <div className="panel-content">
        {/* Action buttons at the top for visibility */}
        {clone.alive && !clone.uploaded && (
          <div className="clone-actions-top">
            <button
              className="action-button"
              onClick={onApply}
              disabled={disabled}
            >
              Apply Clone (Required for Expeditions)
            </button>
            <button
              className="action-button upload-btn"
              onClick={onUpload}
              disabled={disabled}
            >
              Upload to SELF (Save Progress)
            </button>
            {!appliedCloneId || appliedCloneId !== clone.id ? (
              <div className="action-note warning-note">
                ⚠ Apply this clone first to enable expeditions (shown in top bar)
              </div>
            ) : (
              <div className="action-note success-note">
                ✓ Clone applied - Expeditions available in top bar
              </div>
            )}
          </div>
        )}

        {/* Clone info details below */}
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
          {clone.biological_days !== undefined && (
            <div className="clone-info-row">
              <span className="label">Biological Days:</span>
              <span className="value">{clone.biological_days.toFixed(2)}</span>
            </div>
          )}
          <div className="xp-breakdown">
            <div className="xp-item">Mining: {clone.xp.MINING || 0}</div>
            <div className="xp-item">Combat: {clone.xp.COMBAT || 0}</div>
            <div className="xp-item">Exploration: {clone.xp.EXPLORATION || 0}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

