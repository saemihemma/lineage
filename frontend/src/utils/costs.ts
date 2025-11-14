/**
 * Cost calculation utilities - replicate backend logic exactly
 * 
 * Matches backend/engine/outcomes.py resolve_grow() cost calculation
 */

import type { GameState } from '../types/game';

// Base costs from gameplay.json (grow.base_costs)
const BASE_COSTS = {
  BASIC: { Synthetic: 6, Organic: 4, Shilajit: 1 },
  MINER: { Synthetic: 8, 'Metal Ore': 8, Organic: 5, Shilajit: 1 },
  VOLATILE: { Synthetic: 10, Biomass: 8, Organic: 6, Shilajit: 3 },
};

// Clone cost curve from gameplay.json (self.clone_cost_curve)
const COST_CURVE = {
  base_mult: 1.0,
  per_level_add: 0.025,
  breakpoints: [
    { level: 4, slope_mult: 0.5 },
    { level: 7, slope_mult: 0.25 },
    { level: 10, slope_mult: 0.0 },
  ],
  max_mult: 1.85,
};

// Practice XP per level (from CONFIG)
const PRACTICE_XP_PER_LEVEL = 100;

/**
 * Compute clone cost multiplier using piecewise breakpoints.
 * Matches backend compute_clone_cost_multiplier() exactly.
 */
function computeCloneCostMultiplier(selfLevel: number): number {
  const { base_mult, per_level_add, breakpoints, max_mult } = COST_CURVE;
  
  let current = base_mult;
  let slope = per_level_add;
  
  for (let level = 1; level <= selfLevel; level++) {
    current += slope;
    // Check if we hit a breakpoint
    for (const bp of breakpoints) {
      if (level === bp.level) {
        slope *= bp.slope_mult;
        break;
      }
    }
  }
  
  return Math.min(current, max_mult);
}

/**
 * Calculate Constructive practice cost reduction multiplier.
 * Matches backend resolve_grow() practice mods.
 * 
 * cost_mult_per_level = 0.995 (from gameplay.json practices.Constructive)
 * cost_mult_cumulative = cost_mult_per_level ^ constructive_level
 */
function getConstructiveCostMultiplier(state: GameState): number {
  const constructiveXp = state.practices_xp?.Constructive || 0;
  const constructiveLevel = Math.floor(constructiveXp / PRACTICE_XP_PER_LEVEL);
  
  if (constructiveLevel <= 0) {
    return 1.0;
  }
  
  // cost_mult_per_level = 0.995 (from gameplay.json)
  const costMultPerLevel = 0.995;
  const costMultCumulative = Math.pow(costMultPerLevel, constructiveLevel);
  
  // Only apply if significant difference
  if (Math.abs(costMultCumulative - 1.0) > 0.0001) {
    return costMultCumulative;
  }
  
  return 1.0;
}

/**
 * Calculate clone costs for all clone types.
 * Matches backend resolve_grow() cost calculation exactly.
 */
export function calculateCloneCosts(state: GameState): Record<string, Record<string, number>> {
  const selfLevel = state.soul_level || 1;
  
  // 1. Compute base cost multiplier (piecewise breakpoints)
  const costMultBase = computeCloneCostMultiplier(selfLevel);
  
  // 2. Apply Constructive practice cost reduction
  const constructiveMult = getConstructiveCostMultiplier(state);
  
  // 3. Final cost multiplier (base * practice mods)
  // Note: Backend also applies feral attack cost_mult penalty, but we don't show that in preview
  const finalCostMult = costMultBase * constructiveMult;
  
  // 4. Calculate costs for each clone type
  const costs: Record<string, Record<string, number>> = {};
  
  for (const [kind, baseCosts] of Object.entries(BASE_COSTS)) {
    costs[kind] = {};
    for (const [resource, baseAmount] of Object.entries(baseCosts)) {
      const cost = Math.max(1, Math.round(baseAmount * finalCostMult));
      costs[kind][resource] = cost;
    }
  }
  
  return costs;
}

/**
 * Calculate womb cost (simpler - just SELF level inflation).
 * Matches backend build_womb() cost calculation.
 */
export function calculateWombCost(state: GameState): Record<string, number> {
  const baseCost = { Tritanium: 30, 'Metal Ore': 20, Biomass: 5 };
  const selfLevel = state.soul_level || 1;
  
  if (selfLevel <= 1) {
    return baseCost;
  }
  
  // Simple inflation: 1.05 per level (matches old CONFIG behavior)
  const mult = Math.pow(1.05, selfLevel - 1);
  
  return Object.fromEntries(
    Object.entries(baseCost).map(([k, v]) => [k, Math.max(1, Math.round(v * mult))])
  );
}



