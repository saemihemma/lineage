/**
 * React hook for polling game events feed and applying incremental state updates
 */
import { useEffect, useRef, useCallback } from 'react';
import { eventsAPI } from '../api/events';
import type { GameEvent } from '../types/events';
import type { GameState } from '../types/game';

export interface UseEventFeedOptions {
  /**
   * Polling interval in milliseconds (default: 1200ms)
   */
  interval?: number;
  
  /**
   * Callback when events are received (for custom handling)
   */
  onEvents?: (events: GameEvent[]) => void;
  
  /**
   * Callback to apply incremental state patch
   * If provided, will be called for each event. If not, uses default patching.
   */
  onStatePatch?: (patchedState: GameState | null) => void;
  
  /**
   * Callback for terminal messages from events
   */
  onTerminalMessage?: (message: string) => void;
  
  /**
   * Current game state (for applying patches)
   */
  currentState?: GameState | null;
  
  /**
   * Whether polling is enabled (default: true)
   */
  enabled?: boolean;
}

/**
 * Hook for polling events feed and applying incremental updates
 * 
 * @param options Configuration options
 * @returns Object with pause/resume functions and last event timestamp
 */
export function useEventFeed(options: UseEventFeedOptions = {}) {
  const {
    interval = 1200, // 1.2 seconds default
    onEvents,
    onStatePatch,
    onTerminalMessage,
    currentState,
    enabled = true,
  } = options;

  const intervalRef = useRef<number | null>(null);
  const pausedRef = useRef(!enabled);
  const lastTimestampRef = useRef(0);
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  
  // Use refs for callbacks to avoid re-creating pollEvents when callbacks change
  const onStatePatchRef = useRef(onStatePatch);
  const onTerminalMessageRef = useRef(onTerminalMessage);
  const onEventsRef = useRef(onEvents);
  const currentStateRef = useRef(currentState);
  
  // Update refs when callbacks or state change
  useEffect(() => {
    onStatePatchRef.current = onStatePatch;
    onTerminalMessageRef.current = onTerminalMessage;
    onEventsRef.current = onEvents;
    currentStateRef.current = currentState;
  }, [onStatePatch, onTerminalMessage, onEvents, currentState]);

  /**
   * Apply incremental patch to state based on event
   */
  const applyEventPatch = useCallback(
    (event: GameEvent, stateToPatch: GameState | null): GameState | null => {
      if (!stateToPatch) return null;

      // Dedupe: skip if we've seen this event (check before marking as seen)
      if (seenEventIdsRef.current.has(event.id)) {
        return null;
      }
      
      // Mark as seen
      seenEventIdsRef.current.add(event.id);

      // Keep only last 1000 event IDs to prevent memory leak
      if (seenEventIdsRef.current.size > 1000) {
        const ids = Array.from(seenEventIdsRef.current);
        seenEventIdsRef.current = new Set(ids.slice(-500));
      }

      const newState = { ...stateToPatch };

      switch (event.type) {
        case 'resource.delta':
          // Update resource amount
          if (event.data.resource && event.data.new_total !== undefined) {
            newState.resources = {
              ...newState.resources,
              [event.data.resource]: event.data.new_total,
            };
          }
          break;

        case 'gather.complete':
          // Resource already updated via resource.delta, just mark task complete
          if (event.data.resource && event.data.new_total !== undefined) {
            newState.resources = {
              ...newState.resources,
              [event.data.resource]: event.data.new_total,
            };
          }
          break;

        case 'clone.grow.complete':
          // Add new clone to state
          if (event.data.clone) {
            newState.clones = {
              ...newState.clones,
              [event.data.clone.id]: event.data.clone,
            };
          }
          break;

        case 'expedition.result':
          // Update clone XP and resources
          if (event.data.clone_id && event.data.clone_xp) {
            const clone = newState.clones[event.data.clone_id];
            if (clone) {
              newState.clones = {
                ...newState.clones,
                [event.data.clone_id]: {
                  ...clone,
                  xp: { ...clone.xp, ...event.data.clone_xp },
                },
              };
            }
          }
          if (event.data.loot) {
            newState.resources = {
              ...newState.resources,
              ...Object.fromEntries(
                Object.entries(event.data.loot).map(([key, value]) => [
                  key,
                  (newState.resources[key] || 0) + value,
                ])
              ),
            };
          }
          break;

        case 'upload.complete':
          // Update soul_percent and soul_xp
          if (event.data.soul_percent_delta !== undefined) {
            newState.soul_percent = Math.min(
              100.0,
              newState.soul_percent + event.data.soul_percent_delta
            );
          }
          if (event.data.soul_xp_delta !== undefined) {
            newState.soul_xp += event.data.soul_xp_delta;
          }
          // Mark clone as uploaded
          if (event.data.clone_id) {
            const clone = newState.clones[event.data.clone_id];
            if (clone) {
              newState.clones = {
                ...newState.clones,
                [event.data.clone_id]: {
                  ...clone,
                  uploaded: true,
                  alive: false,
                },
              };
            }
          }
          break;

        default:
          // Unknown event type - return null (don't patch)
          return null;
      }

      return newState;
    },
    []
  );

  /**
   * Format event into terminal message
   */
  const formatTerminalMessage = useCallback((event: GameEvent): string | null => {
    switch (event.type) {
      case 'gather.start':
        return `Gathering ${event.data.resource}...`;
      
      case 'gather.complete':
        return `Gathered ${event.data.delta} ${event.data.resource}. Total: ${event.data.new_total}`;
      
      case 'clone.grow.start':
        return `Growing ${event.data.clone?.kind || 'clone'}...`;
      
      case 'clone.grow.complete':
        return `${event.data.clone?.kind || 'Clone'} grown successfully. id=${event.data.clone?.id}`;
      
      case 'expedition.start':
        return `Starting ${event.data.kind?.toLowerCase() || 'expedition'} expedition...`;
      
      case 'expedition.result':
        const lootStr = event.data.loot
          ? Object.entries(event.data.loot)
              .map(([k, v]) => `${k}+${v}`)
              .join(', ')
          : '';
        return `${event.data.kind} expedition complete: ${lootStr}`;
      
      case 'upload.complete':
        return `Uploaded clone to SELF. SELF restored by ${event.data.soul_percent_delta?.toFixed(1) || 0}%`;
      
      case 'error.game':
      case 'error.network':
        return event.data.message || 'An error occurred';
      
      default:
        return null;
    }
  }, []);

  /**
   * Poll for new events
   * Uses refs for callbacks to keep dependencies stable (primitives only)
   */
  const pollEvents = useCallback(
    async () => {
      if (pausedRef.current) return;

      const state = currentStateRef.current;
      
      try {
        const after = lastTimestampRef.current || undefined;
        const events = await eventsAPI.getEventsFeed(after);

        if (events.length > 0) {
          // Update last timestamp
          lastTimestampRef.current = Math.max(...events.map(e => e.timestamp));

          // Call onEvents callback (if custom handler) via ref
          if (onEventsRef.current) {
            onEventsRef.current(events);
          }

          // Apply patches for each event (in order, chaining state updates)
          // Dedupe is handled inside applyEventPatch
          let latestState = state;
          events.forEach((event) => {
            // Format and add terminal messages via ref
            const message = formatTerminalMessage(event);
            if (message && onTerminalMessageRef.current) {
              onTerminalMessageRef.current(message);
            }

            // Apply state patch (using latest state, so patches can chain) via ref
            if (latestState && onStatePatchRef.current) {
              const patchedState = applyEventPatch(event, latestState);
              if (patchedState) {
                latestState = patchedState;
                onStatePatchRef.current(patchedState);
              }
            }
          });
        }
      } catch (err) {
        // Don't log 404 errors as errors (endpoint may not exist yet)
        if (err instanceof Error && err.message.includes('404')) {
          // Endpoint doesn't exist - silently degrade (no events, but don't break)
          pausedRef.current = true;
          // Check again in 30 seconds in case backend gets updated
          setTimeout(() => {
            pausedRef.current = false;
          }, 30000);
        } else {
          console.error('Event feed polling error:', err);
          // On error, pause briefly then resume
          pausedRef.current = true;
          setTimeout(() => {
            pausedRef.current = false;
          }, 5000); // Resume after 5 seconds
        }
      }
    },
    [formatTerminalMessage, applyEventPatch] // Only stable functions, no callbacks or state
  );

  /**
   * Start polling
   */
  const startPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (!enabled) {
      pausedRef.current = true;
      return;
    }

    pausedRef.current = false;

    // Poll immediately
    pollEvents();

    // Then poll at interval
    intervalRef.current = setInterval(() => {
      pollEvents();
    }, interval);
  },
  [enabled, interval, pollEvents] // enabled and interval are primitives, pollEvents is stable
  );

  /**
   * Stop polling
   */
  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    pausedRef.current = true;
  }, []);

  /**
   * Resume polling
   */
  const resumePolling = useCallback(() => {
    pausedRef.current = false;
    startPolling();
  }, [startPolling]);

  /**
   * Get last seen event timestamp
   */
  const getLastTimestamp = useCallback(() => {
    return lastTimestampRef.current || eventsAPI.getLastTimestamp();
  }, []);

  /**
   * Reset event tracking (e.g., after reconnection)
   */
  const reset = useCallback(() => {
    seenEventIdsRef.current.clear();
    lastTimestampRef.current = 0;
    eventsAPI.reset();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    startPolling,
    stopPolling,
    resumePolling,
    getLastTimestamp,
    reset,
    applyEventPatch,
  };
}

