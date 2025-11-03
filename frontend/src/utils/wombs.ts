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

