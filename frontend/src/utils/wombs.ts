/**
 * Utility functions for womb management
 */
import type { GameState, Womb } from '../types/game';

/**
 * Check if player has any functional womb (or legacy assembler_built)
 */
export function hasWomb(state: GameState): boolean {
  if (state.wombs && state.wombs.length > 0) {
    // Check if any womb is functional (durability > 0)
    return state.wombs.some(w => w.durability > 0);
  }
  // Fallback to legacy assembler_built for backward compatibility
  return state.assembler_built || false;
}

/**
 * Get the number of wombs currently built
 */
export function getWombCount(state: GameState): number {
  return state.wombs?.length || 0;
}

/**
 * Get functional wombs only
 */
export function getFunctionalWombs(state: GameState): Womb[] {
  if (!state.wombs) return [];
  return state.wombs.filter(w => w.durability > 0);
}

/**
 * Calculate unlocked womb count based on practice levels
 * (Mirrors backend logic for frontend display)
 */
export function getUnlockedWombCount(state: GameState): number {
  const maxCount = 4; // From CONFIG.WOMB_MAX_COUNT
  const levels = state.practice_levels;
  const maxLevel = Math.max(levels.Kinetic, levels.Cognitive, levels.Constructive);
  const practicesAtL9 = [
    levels.Kinetic >= 9,
    levels.Cognitive >= 9,
    levels.Constructive >= 9
  ].filter(Boolean).length;
  
  // Base: 1 womb always available
  let unlocked = 1;
  
  // +1 at any Practice L4
  if (maxLevel >= 4) unlocked++;
  
  // +1 at any Practice L7
  if (maxLevel >= 7) unlocked++;
  
  // +1 when two Practices reach L9
  if (practicesAtL9 >= 2) unlocked++;
  
  return Math.min(unlocked, maxCount);
}

/**
 * Get next unlock threshold text
 */
export function getNextUnlockHint(state: GameState): string | null {
  const levels = state.practice_levels;
  const maxLevel = Math.max(levels.Kinetic, levels.Cognitive, levels.Constructive);
  const currentWombs = getWombCount(state);
  const unlocked = getUnlockedWombCount(state);
  
  // If already at max, no more unlocks
  if (currentWombs >= unlocked && unlocked >= 4) return null;
  
  // If can build more, show next requirement
  if (maxLevel < 4) {
    return `Next Womb: Reach any Practice Level 4`;
  } else if (maxLevel < 7) {
    return `Next Womb: Reach any Practice Level 7`;
  } else {
    const practicesAtL9 = [
      levels.Kinetic >= 9,
      levels.Cognitive >= 9,
      levels.Constructive >= 9
    ].filter(Boolean).length;
    if (practicesAtL9 < 2) {
      return `Next Womb: Two Practices at Level 9`;
    }
  }
  
  return null;
}

/**
 * Calculate average attention across all wombs
 * Note: Attention is now global, not per-womb
 */
export function getAverageAttention(state: GameState): number {
  return state.global_attention || 0;
}

/**
 * Calculate average attention percentage
 * Note: Attention is now global (0-100), not per-womb
 */
export function getAverageAttentionPercent(state: GameState): number {
  // Global attention is already 0-100 scale
  return Math.min(100, Math.max(0, state.global_attention || 0));
}

/**
 * Calculate practice level from practice XP
 */
function calculatePracticeLevel(practiceXp: number): number {
  const PRACTICE_XP_PER_LEVEL = 100;
  return Math.floor(practiceXp / PRACTICE_XP_PER_LEVEL);
}

/**
 * Get attention gain multiplier based on Cognitive practice level
 * Cognitive L3+ reduces attention gain (and affects decay)
 * Mirrors backend get_attention_gain_multiplier logic
 */
function getAttentionGainMultiplier(state: GameState): number {
  const threshold = 3;
  const mult = 0.95; // From CONFIG.WOMB_SYNERGY_COGNITIVE_ATTENTION_MULT
  
  const cognitiveLevel = calculatePracticeLevel(state.practices_xp?.Cognitive || 0);
  if (cognitiveLevel >= threshold) {
    return mult;
  }
  return 1.0;
}

/**
 * Calculate available grow slots based on functional wombs and parallel limit
 * Mirrors backend get_available_grow_slots logic
 */
export function getAvailableGrowSlots(state: GameState): number {
  const functionalWombs = getFunctionalWombs(state);
  const functionalCount = functionalWombs.length;
  
  if (functionalCount === 0) return 0;
  
  // Parallel grow limit (default 4, should match config)
  const parallelLimit = 4;
  
  // Count active grow tasks
  const activeTasks = state.active_tasks || {};
  const activeGrowTasks = Object.values(activeTasks).filter(
    (task: any) => task.type === 'grow_clone'
  ).length;
  
  // Available slots = min(functional_wombs, parallel_limit) - active_grow_tasks
  const maxSlots = Math.min(functionalCount, parallelLimit);
  const available = Math.max(0, maxSlots - activeGrowTasks);
  
  return available;
}

/**
 * Get parallel womb status info
 */
export function getParallelWombStatus(state: GameState): {
  functionalCount: number;
  activeGrowTasks: number;
  maxSlots: number;
  availableSlots: number;
  isParallelActive: boolean;
} {
  const functionalWombs = getFunctionalWombs(state);
  const functionalCount = functionalWombs.length;
  const parallelLimit = 4;
  
  const activeTasks = state.active_tasks || {};
  const activeGrowTasks = Object.values(activeTasks).filter(
    (task: any) => task.type === 'grow_clone'
  ).length;
  
  const maxSlots = Math.min(functionalCount, parallelLimit);
  const availableSlots = Math.max(0, maxSlots - activeGrowTasks);
  const isParallelActive = functionalCount > 1;
  
  return {
    functionalCount,
    activeGrowTasks,
    maxSlots,
    availableSlots,
    isParallelActive
  };
}

/**
 * Apply attention decay based on idle time
 * Mirrors backend decay_attention logic
 */
export function applyAttentionDecay(state: GameState): GameState {
  const newState = { ...state };
  
  // Initialize global_attention if not present
  if (newState.global_attention === undefined) {
    newState.global_attention = 0.0;
  }
  
  // Calculate hours since last save (matches backend)
  const currentTime = Date.now() / 1000; // Current time in seconds
  const lastSavedTs = newState.last_saved_ts || currentTime;
  const hoursElapsed = Math.max(0.0, (currentTime - lastSavedTs) / 3600.0);
  
  // Decay per hour: 3.0 per hour (matches backend)
  const decayPerHour = 3.0;
  const totalDecay = decayPerHour * hoursElapsed;
  
  // Cognitive synergy affects decay
  // Note: Backend formula is decay_mult = 2.0 - mult
  // If mult = 0.95 (reduces attention gain), decay_mult = 1.05 (increases decay slightly)
  const mult = getAttentionGainMultiplier(newState);
  const decayMult = 2.0 - mult;
  const actualDecay = totalDecay * decayMult;
  
  // Apply decay to global attention (can't go below 0)
  newState.global_attention = Math.max(0.0, (newState.global_attention || 0) - actualDecay);
  
  // Update last_saved_ts to current time for next decay calculation
  newState.last_saved_ts = currentTime;
  
  return newState;
}

