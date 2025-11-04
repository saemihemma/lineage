/**
 * localStorage utilities for game state persistence
 */
import type { GameState } from '../types/game';

const STORAGE_KEY = 'lineage_game_state';
const SESSION_ID_KEY = 'lineage_session_id';

/**
 * Calculate soul level from soul_xp
 */
function calculateSoulLevel(soulXp: number): number {
  const SOUL_LEVEL_STEP = 100; // From CONFIG
  return 1 + Math.floor(soulXp / SOUL_LEVEL_STEP);
}

/**
 * Calculate practice level from practice XP
 */
function calculatePracticeLevel(practiceXp: number): number {
  const PRACTICE_XP_PER_LEVEL = 100; // From CONFIG
  return Math.floor(practiceXp / PRACTICE_XP_PER_LEVEL);
}

/**
 * Create a default initial game state
 */
export function createDefaultState(): GameState {
  return {
    version: 1,
    rng_seed: Math.floor(Math.random() * (2**31 - 1)),
    soul_percent: 100.0,
    soul_xp: 0,
    soul_level: 1,
    assembler_built: false,
    wombs: [],
    resources: {
      "Tritanium": 0,
      "Metal Ore": 5,
      "Biomass": 1,
      "Synthetic": 8,
      "Organic": 8,
      "Shilajit": 0
    },
    applied_clone_id: "",
    practices_xp: {
      "Kinetic": 0,
      "Cognitive": 0,
      "Constructive": 0
    },
    practice_levels: {
      "Kinetic": 0,
      "Cognitive": 0,
      "Constructive": 0
    },
    last_saved_ts: Date.now() / 1000,
    self_name: "",
    global_attention: 0.0,  // Start at 0, grows with actions
    clones: {},
    active_tasks: {},
    ui_layout: {}
  };
}

/**
 * Load game state from localStorage
 */
export function loadStateFromLocalStorage(): GameState | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return null;
    }

    const parsed = JSON.parse(stored);
    
    // Ensure calculated fields are present
    if (typeof parsed.soul_level !== 'number') {
      parsed.soul_level = calculateSoulLevel(parsed.soul_xp || 0);
    }
    
    if (!parsed.practice_levels) {
      parsed.practice_levels = {
        Kinetic: calculatePracticeLevel(parsed.practices_xp?.Kinetic || 0),
        Cognitive: calculatePracticeLevel(parsed.practices_xp?.Cognitive || 0),
        Constructive: calculatePracticeLevel(parsed.practices_xp?.Constructive || 0),
      };
    }

    // Ensure required fields with defaults
    if (!parsed.version) parsed.version = 1;
    if (!parsed.wombs) parsed.wombs = [];
    if (!parsed.clones) parsed.clones = {};
    if (!parsed.active_tasks) parsed.active_tasks = {};
    if (!parsed.ui_layout) parsed.ui_layout = {};
    if (typeof parsed.global_attention !== 'number') {
      parsed.global_attention = 0.0;  // Initialize global attention if missing (for old saves)
    }
    // Clear expired prayer cooldown (if it exists and is in the past)
    if (parsed.prayer_cooldown_until && typeof parsed.prayer_cooldown_until === 'number') {
      const now = Date.now() / 1000;
      if (parsed.prayer_cooldown_until < now) {
        parsed.prayer_cooldown_until = undefined; // Clear expired cooldown
      }
    }
    if (!parsed.resources) {
      parsed.resources = {
        "Tritanium": 60,
        "Metal Ore": 40,
        "Biomass": 8,
        "Synthetic": 8,
        "Organic": 8,
        "Shilajit": 0
      };
    }

    return parsed as GameState;
  } catch (error) {
    console.error('Failed to load state from localStorage:', error);
    return null;
  }
}

/**
 * Save game state to localStorage
 */
export function saveStateToLocalStorage(state: GameState): void {
  try {
    // Update calculated fields before saving
    const stateToSave = {
      ...state,
      soul_level: calculateSoulLevel(state.soul_xp),
      practice_levels: {
        Kinetic: calculatePracticeLevel(state.practices_xp.Kinetic || 0),
        Cognitive: calculatePracticeLevel(state.practices_xp.Cognitive || 0),
        Constructive: calculatePracticeLevel(state.practices_xp.Constructive || 0),
      },
      // Preserve last_saved_ts from backend if present, otherwise use current time
      // This ensures backend's timestamp (updated after decay calculation) is preserved
      last_saved_ts: state.last_saved_ts || Date.now() / 1000,
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
  } catch (error) {
    console.error('Failed to save state to localStorage:', error);
    // Check if quota exceeded
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      console.error('localStorage quota exceeded! Game state may be too large.');
    }
  }
}

/**
 * Clear game state from localStorage
 */
export function clearStateFromLocalStorage(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Get or create persistent session ID for rate limiting
 * Uses self_name if available, otherwise creates simple session ID
 */
export function getOrCreateSessionId(): string {
  try {
    // First, check if we have a stored session ID
    let sessionId = localStorage.getItem(SESSION_ID_KEY);

    if (!sessionId) {
      // Try to use self_name from game state
      const state = loadStateFromLocalStorage();
      if (state?.self_name && state.self_name.trim()) {
        sessionId = state.self_name.trim();
        console.log('🆔 Created session ID from self_name:', sessionId);
      } else {
        // Fallback to simple timestamp-based ID
        sessionId = `player_${Date.now()}`;
        console.log('🆔 Created session ID from timestamp:', sessionId);
      }

      localStorage.setItem(SESSION_ID_KEY, sessionId);
    } else {
      console.log('🆔 Using existing session ID:', sessionId);
    }

    return sessionId;
  } catch (error) {
    console.error('Failed to get/create session ID from localStorage:', error);
    // Fallback to simple timestamp
    return `player_${Date.now()}`;
  }
}

