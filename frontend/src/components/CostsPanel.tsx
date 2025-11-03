/**
 * Costs Panel - displays costs for current actions
 */
import type { GameState } from '../types/game';
import { hasWomb, getWombCount, getUnlockedWombCount } from '../utils/wombs';
import './CostsPanel.css';

interface CostsPanelProps {
  state: GameState;
}

export function CostsPanel({ state }: CostsPanelProps) {
  // Use soul_level from backend (single source of truth)
  const soulLevel = state.soul_level;

  const wombCost = calculateWombCost(soulLevel);
  const cloneCosts = calculateCloneCosts(soulLevel);
  const wombCount = getWombCount(state);
  const unlockedCount = getUnlockedWombCount(state);
  const canBuildMore = wombCount < unlockedCount;

  return (
    <div className="panel costs-panel">
      <div className="panel-header">Costs (Level {soulLevel})</div>
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

function calculateWombCost(level: number): Record<string, number> {
  const baseCost = { Tritanium: 30, 'Metal Ore': 20, Biomass: 5 };
  if (level <= 1) return baseCost;
  const mult = Math.pow(1.05, level - 1);
  return Object.fromEntries(
    Object.entries(baseCost).map(([k, v]) => [k, Math.max(1, Math.round(v * mult))])
  );
}

function calculateCloneCosts(level: number): Record<string, Record<string, number>> {
  const baseCosts = {
    BASIC: { Synthetic: 6, Organic: 4, Shilajit: 1 },
    MINER: { Synthetic: 8, 'Metal Ore': 8, Organic: 5, Shilajit: 1 },
    VOLATILE: { Synthetic: 10, Biomass: 8, Organic: 6, Shilajit: 3 },
  };
  
  const mult = level <= 1 ? 1 : Math.pow(1.05, level - 1);
  
  return Object.fromEntries(
    Object.entries(baseCosts).map(([kind, costs]) => [
      kind,
      Object.fromEntries(
        Object.entries(costs).map(([k, v]) => [k, Math.max(1, Math.round(v * mult))])
      ),
    ])
  );
}

