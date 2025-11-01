/**
 * Clones Panel - displays list of clones
 */
import type { Clone } from '../types/game';
import './ClonesPanel.css';

interface ClonesPanelProps {
  clones: Record<string, Clone>;
  selectedId: string | null;
  onSelect: (cloneId: string) => void;
}

export function ClonesPanel({ clones, selectedId, onSelect }: ClonesPanelProps) {
  const cloneList = Object.values(clones);

  return (
    <div className="panel clones-panel">
      <div className="panel-header">Clones</div>
      <div className="panel-content clones-list">
        {cloneList.length === 0 ? (
          <div className="empty-state">No clones yet. Build Womb first.</div>
        ) : (
          cloneList.map((clone) => (
            <div
              key={clone.id}
              className={`clone-item ${selectedId === clone.id ? 'selected' : ''} ${!clone.alive ? 'dead' : ''}`}
              onClick={() => onSelect(clone.id)}
            >
              <div className="clone-kind">{clone.kind}</div>
              <div className="clone-stats">
                {clone.alive ? (
                  <>
                    <span>XP: {clone.xp.MINING + clone.xp.COMBAT + clone.xp.EXPLORATION}</span>
                    <span>Runs: {clone.survived_runs}</span>
                  </>
                ) : (
                  <span className="dead-label">DEAD</span>
                )}
              </div>
              {clone.uploaded && <span className="uploaded-badge">UPLOADED</span>}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

