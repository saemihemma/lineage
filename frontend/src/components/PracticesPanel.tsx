/**
 * Practices Panel - shows LINEAGE practice XP progress
 */
import type { GameState } from '../types/game';
import './PracticesPanel.css';

interface PracticesPanelProps {
  practicesXp: Record<string, number>;
  practiceLevels: GameState['practice_levels'];
}

const PRACTICE_TRACKS = ['Kinetic', 'Cognitive', 'Constructive'] as const;
const XP_PER_LEVEL = 100;

export function PracticesPanel({ practicesXp, practiceLevels }: PracticesPanelProps) {
  const calculateProgress = (xp: number): number => {
    return (xp % XP_PER_LEVEL);
  };

  return (
    <div className="panel practices-panel">
      <div className="panel-header">LINEAGE Practices</div>
      <div className="panel-subheader">
        Persistent growth of the SELF through vessels.
      </div>
      <div className="panel-content">
        {PRACTICE_TRACKS.map((track) => {
          const xp = practicesXp[track] || 0;
          const level = practiceLevels[track];  // Use backend-calculated level
          const progress = calculateProgress(xp);
          const progressPercent = (progress / XP_PER_LEVEL) * 100;

          return (
            <div key={track} className="practice-track">
              <div className="practice-header">
                <span className="practice-name">{track}:</span>
                <span className="practice-level">
                  Level {level} — {progress}/100 XP
                </span>
              </div>
              <div className="practice-progress-bar">
                <div
                  className="practice-progress-fill"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

