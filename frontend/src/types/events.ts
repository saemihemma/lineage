/**
 * Event types for live state sync
 */

export interface GameEvent {
  id: string;
  type: EventType;
  timestamp: number;
  data: EventData;
}

export type EventType =
  | 'gather.start'
  | 'gather.complete'
  | 'clone.grow.start'
  | 'clone.grow.complete'
  | 'expedition.start'
  | 'expedition.result'
  | 'upload.complete'
  | 'resource.delta'
  | 'error.network'
  | 'error.game';

export interface EventData {
  // Resource delta events
  resource?: string;
  delta?: number;
  new_total?: number;
  
  // Expedition events
  kind?: string;
  loot?: Record<string, number>;
  clone_xp?: Record<string, number>;
  clone_id?: string;
  
  // Clone grow events
  clone?: any;
  
  // Upload events
  soul_percent_delta?: number;
  soul_xp_delta?: number;
  
  // Error events
  message?: string;
  error_type?: string;
}

