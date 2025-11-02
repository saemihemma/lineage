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

export interface GameState {
  version: number;
  rng_seed: number | null;
  soul_percent: number;
  soul_xp: number;
  soul_level: number;  // Calculated on backend
  assembler_built: boolean;
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

