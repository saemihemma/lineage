/**
 * Costs Panel - displays costs for current actions
 * Uses backend-equivalent cost calculations
 */
import type { GameState } from '../types/game';
import { hasWomb, getWombCount, getUnlockedWombCount } from '../utils/wombs';
import { calculateCloneCosts, calculateWombCost } from '../utils/costs';
import './CostsPanel.css';

interface CostsPanelProps {
  state: GameState;
}

export function CostsPanel({ state }: CostsPanelProps) {
  // Use backend-equivalent cost calculations
  const wombCost = calculateWombCost(state);
  const cloneCosts = calculateCloneCosts(state);
  const wombCount = getWombCount(state);
  const unlockedCount = getUnlockedWombCount(state);
  const canBuildMore = wombCount < unlockedCount;

  return (
    <div className="panel costs-panel">
      <div className="panel-header">Costs (Level {state.soul_level})</div>
      <div className="panel-content">
        <div className="cost-section">
          <div className={`cost-title ${!canBuildMore ? 'disabled' : ''}`}>
            Womb ({wombCount}/{unlockedCount}):
          </div>
          <div className="cost-items-inline">
            {Object.entries(wombCost).map(([resource, amount]) => (
              <span key={resource} className="cost-item-inline">
                {resource}: <span className="cost-amount">{amount}</span>
              </span>
            ))}
          </div>
        </div>

        {hasWomb(state) && (
          <div className="cost-section">
            <div className="cost-title">Clones:</div>
            {Object.entries(cloneCosts).map(([kind, costs]) => (
              <div key={kind} className="clone-cost-group-compact">
                <span className="clone-cost-kind-compact">{kind}:</span>
                <span className="cost-items-inline">
                  {Object.entries(costs).map(([resource, amount], idx) => (
                    <span key={resource} className="cost-item-inline">
                      {resource}: <span className="cost-amount">{amount}</span>
                      {idx < Object.entries(costs).length - 1 ? ', ' : ''}
                    </span>
                  ))}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

