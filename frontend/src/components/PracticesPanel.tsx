/**
 * Practices Panel - shows LINEAGE practice XP progress
 */
import type { GameState } from '../types/game';
import { getNextUnlockHint, getWombCount, getUnlockedWombCount } from '../utils/wombs';
import './PracticesPanel.css';

interface PracticesPanelProps {
  practicesXp: Record<string, number>;
  practiceLevels: GameState['practice_levels'];
  state: GameState;
}

const PRACTICE_TRACKS = ['Kinetic', 'Cognitive', 'Constructive'] as const;
const XP_PER_LEVEL = 100;

// Tooltips for practices (flavor + functional)
const PRACTICE_TOOLTIPS: Record<string, string> = {
  Kinetic: 'The body remembers. Physical mastery sharpens reflexes and strengthens vessels. Increases expedition success & rewards (MINING/COMBAT). At Level 3+, reduces feral drone attack chance.',
  Cognitive: 'The mind accelerates. Mental refinement streamlines processes and reduces entropy. Reduces time for all actions globally. At Level 3+, slows attention decay.',
  Constructive: 'The synthesis perfects. Creative mastery finds efficiency in form and function. Reduces costs for all actions globally. At Level 3+, improves womb repair efficiency.'
};

export function PracticesPanel({ practicesXp, practiceLevels, state }: PracticesPanelProps) {
  const calculateProgress = (xp: number): number => {
    return (xp % XP_PER_LEVEL);
  };
  
  const nextHint = getNextUnlockHint(state);
  const wombCount = getWombCount(state);
  const unlockedCount = getUnlockedWombCount(state);
  const canUnlockMore = wombCount < unlockedCount && unlockedCount < 4;

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
            <div 
              key={track} 
              className="practice-track"
              title={PRACTICE_TOOLTIPS[track]}
            >
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
        
        {/* Womb Unlock Hints */}
        {canUnlockMore && nextHint && (
          <div className="practice-unlocks-box">
            <div className="practice-unlocks-title">Throughput Unlocks</div>
            <div className="practice-unlocks-hint">{nextHint}</div>
            <div className="practice-unlocks-current">
              Current: {wombCount} / {unlockedCount} Wombs
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

