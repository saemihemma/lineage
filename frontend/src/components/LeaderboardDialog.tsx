/**
 * Leaderboard Dialog - view global rankings and submit stats
 */
import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { LeaderboardEntry } from '../api/client';
import './LeaderboardDialog.css';

interface LeaderboardDialogProps {
  isOpen: boolean;
  onClose: () => void;
  currentState: {
    self_name: string;
    soul_level: number;
    soul_xp: number;
    clones: Record<string, any>;
  };
}

export function LeaderboardDialog({ isOpen, onClose, currentState }: LeaderboardDialogProps) {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const loadLeaderboard = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const data = await apiClient.fetchLeaderboard(50);
      setEntries(data);
    } catch (error) {
      console.error('Failed to load leaderboard:', error);
      setMessage({ type: 'error', text: 'Failed to load leaderboard' });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!currentState.self_name) {
      setMessage({ type: 'error', text: 'SELF name is required' });
      return;
    }

    setSubmitting(true);
    setMessage(null);

    // Calculate total expeditions and clones uploaded
    let totalExpeditions = 0;
    let clonesUploaded = 0;

    Object.values(currentState.clones || {}).forEach((clone: any) => {
      // Count actual expeditions (survived_runs), not XP
      totalExpeditions += (clone.survived_runs || 0);
      if (clone.uploaded) {
        clonesUploaded++;
      }
    });

    try {
      const success = await apiClient.submitToLeaderboard({
        self_name: currentState.self_name,
        soul_level: currentState.soul_level,
        soul_xp: currentState.soul_xp,
        clones_uploaded: clonesUploaded,
        total_expeditions: totalExpeditions,
      });

      if (success) {
        setMessage({ type: 'success', text: 'Stats submitted successfully!' });
        // Reload leaderboard to show updated rankings
        await loadLeaderboard();
      } else {
        setMessage({ type: 'error', text: 'Failed to submit stats' });
      }
    } catch (error) {
      console.error('Failed to submit stats:', error);
      setMessage({ type: 'error', text: 'Failed to submit stats' });
    } finally {
      setSubmitting(false);
    }
  };

  // Load leaderboard when dialog opens
  useEffect(() => {
    if (isOpen) {
      loadLeaderboard();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="leaderboard-dialog-content" onClick={(e) => e.stopPropagation()}>
        <h3 className="dialog-title">Global Leaderboard</h3>
        <p className="dialog-subtitle">Top 50 SELFs ranked by level and XP</p>

        {message && (
          <div className={`leaderboard-message ${message.type}`}>
            {message.text}
          </div>
        )}

        <div className="leaderboard-actions-top">
          <button
            className="leaderboard-btn refresh"
            onClick={loadLeaderboard}
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
          <button
            className="leaderboard-btn submit"
            onClick={handleSubmit}
            disabled={submitting || loading}
          >
            {submitting ? 'Submitting...' : 'Submit My Stats'}
          </button>
        </div>

        <div className="leaderboard-table-container">
          {loading && entries.length === 0 ? (
            <div className="leaderboard-loading">Loading leaderboard...</div>
          ) : entries.length === 0 ? (
            <div className="leaderboard-empty">
              No entries yet. Be the first to submit your stats!
            </div>
          ) : (
            <table className="leaderboard-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>SELF Name</th>
                  <th>Level</th>
                  <th>XP</th>
                  <th>Clones</th>
                  <th>Expeditions</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry, index) => (
                  <tr
                    key={entry.id}
                    className={entry.self_name === currentState.self_name ? 'current-user' : ''}
                  >
                    <td className="rank">#{index + 1}</td>
                    <td className="self-name">{entry.self_name}</td>
                    <td className="level">{entry.soul_level}</td>
                    <td className="xp">{entry.soul_xp}</td>
                    <td className="clones">{entry.clones_uploaded}</td>
                    <td className="expeditions">{entry.total_expeditions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="dialog-actions">
          <button className="dialog-btn cancel" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
