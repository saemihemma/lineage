/**
 * Type definitions for LINEAGE game state and models
 */

export interface Clone {
  id: string;
  kind: string;
  traits: string[];
  xp: Record<string, number>;
  survived_runs: number;
  alive: boolean;
  uploaded: boolean;
  created_at?: number;  // Unix timestamp
  biological_days?: number;  // Calculated biological days (8 sim days per real day)
}

export interface Womb {
  id: number;  // Index-based ID (0, 1, 2, ...)
  durability: number;  // Current durability (0 to max_durability)
  attention: number;  // Current attention (0 to max_attention)
  max_durability: number;  // Maximum durability
  max_attention: number;  // Maximum attention
}

export interface GameState {
  version: number;
  rng_seed: number | null;
  soul_percent: number;
  soul_xp: number;
  soul_level: number;  // Calculated on backend
  assembler_built: boolean;  // DEPRECATED: Use wombs array instead (kept for backward compatibility)
  wombs?: Womb[];  // Array of wombs (replaces assembler_built)
  resources: Record<string, number>;
  applied_clone_id: string;
  practices_xp: Record<string, number>;
  practice_levels: {  // Calculated on backend
    Kinetic: number;
    Cognitive: number;
    Constructive: number;
  };
  last_saved_ts: number;
  self_name: string;
  clones: Record<string, Clone>;
  active_tasks?: Record<string, any>;
  ui_layout?: Record<string, any>;
  ftue?: {
    step_gather_10_tritanium?: boolean;
    step_build_womb?: boolean;
    step_grow_clone?: boolean;
    step_first_expedition?: boolean;
    step_upload_clone?: boolean;
  };
}

export interface ResourceCost {
  resource: string;
  amount: number;
}

export interface GameActionResponse {
  success: boolean;
  message?: string;
  new_state?: GameState;
}

