/**
 * Progress Panel - shows build/craft progress
 */
import './ProgressPanel.css';

interface ProgressPanelProps {
  progress: { value: number; label: string };
}

export function ProgressPanel({ progress }: ProgressPanelProps) {
  return (
    <div className="panel progress-panel">
      <div className="panel-header">Progress</div>
      <div className="panel-content">
        <div className="progress-bar-container">
          <div className="progress-bar">
            <div
              className="progress-bar-fill"
              style={{ width: `${progress.value}%` }}
            />
          </div>
          <div className="progress-label">{progress.label || 'Idle'}</div>
        </div>
      </div>
    </div>
  );
}

