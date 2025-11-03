/**
 * React hook for managing game state
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { gameAPI } from '../api/game';
import type { GameState } from '../types/game';

export function useGameState() {
  const [state, setState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollingIntervalRef = useRef<number | null>(null);

  // Load initial state with retry logic
  useEffect(() => {
    async function load(retries = 3) {
      try {
        setLoading(true);
        setError(null);
        console.log('🔄 Loading initial game state...');
        const gameState = await gameAPI.getState();
        
        // Log state details for debugging
        const wombCount = gameState.wombs?.length || 0;
        console.log('📦 State loaded:', {
          hasWombs: Array.isArray(gameState.wombs),
          wombCount,
          assemblerBuilt: gameState.assembler_built,
          selfName: gameState.self_name,
          hasClones: Object.keys(gameState.clones || {}).length > 0,
          activeTasks: Object.keys(gameState.active_tasks || {}).length,
        });
        
        setState(gameState);
      } catch (err) {
        if (retries > 0) {
          // Retry on transient errors (network, server restart, etc.)
          console.warn(`Failed to load game state, retrying... (${retries} retries left)`);
          await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
          return load(retries - 1);
        }
        const errorMsg = err instanceof Error ? err.message : 'Failed to load game state';
        setError(errorMsg);
        console.error('Failed to load game state after retries:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Poll state when active tasks exist (to detect task completion)
  useEffect(() => {
    // Clear any existing polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    // Only poll if state exists and has active tasks
    const activeTasks = state?.active_tasks;
    const hasActiveTasks = activeTasks && Object.keys(activeTasks).length > 0;
    
    if (!state || !hasActiveTasks) {
      return;
    }

    console.log(`🔵 Starting task polling: ${Object.keys(activeTasks).length} active task(s)`);

    // Start polling every 1 second to check for task completion
    // CRITICAL: Always use backend state - backend is source of truth for resources, XP, etc.
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const updatedState = await gameAPI.getState();
        
        // Always update state from backend (backend is source of truth)
        // This ensures resources, practices XP, and other changes are reflected immediately
        setState((prevState) => {
          if (!prevState) return updatedState;
          
          const prevTasks = prevState.active_tasks || {};
          const newTasks = updatedState.active_tasks || {};
          
          // Check if active_tasks changed (tasks completed or new tasks added)
          const prevTaskKeys = Object.keys(prevTasks);
          const newTaskKeys = Object.keys(newTasks);
          const tasksChanged = prevTaskKeys.length !== newTaskKeys.length || 
                              prevTaskKeys.some(id => !newTasks[id]) ||
                              newTaskKeys.some(id => !prevTasks[id]) ||
                              JSON.stringify(prevTasks) !== JSON.stringify(newTasks);
          
          // Check if wombs changed
          const prevWombCount = prevState.wombs?.length || 0;
          const newWombCount = updatedState.wombs?.length || 0;
          const wombsChanged = prevWombCount !== newWombCount;
          
          // Always use backend state when polling - it has the latest resources, XP, etc.
          // The backend saves state after every action, so polling should always sync
          if (tasksChanged) {
            console.log(`🟢 Tasks changed: ${prevTaskKeys.length} → ${newTaskKeys.length}, syncing state from backend`);
          }
          
          if (wombsChanged) {
            console.log(`🏗️ Wombs changed: ${prevWombCount} → ${newWombCount}, syncing state from backend`);
          }
          
          // Always return backend state - it's the source of truth
          // Even if tasks didn't change, backend might have updated resources, XP, etc.
          return updatedState;
        });

        // Check if we should stop polling (no more active tasks)
        const stillHasActiveTasks = updatedState.active_tasks && Object.keys(updatedState.active_tasks).length > 0;
        if (!stillHasActiveTasks && pollingIntervalRef.current) {
          console.log(`🔴 No more active tasks - stopping polling`);
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      } catch (err) {
        // Don't spam errors if polling fails (might be transient network issue)
        console.warn('Failed to poll game state for task completion:', err);
      }
    }, 1000); // Poll every 1 second

    // Cleanup on unmount or when state changes
    return () => {
      if (pollingIntervalRef.current) {
        console.log(`🟡 Cleaning up task polling`);
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [state?.active_tasks]); // Re-run when active_tasks changes

  // Save state
  const saveState = useCallback(async (newState: GameState) => {
    try {
      const result = await gameAPI.saveState(newState);
      // If saveState returns a state (version conflict), use that instead
      if (result) {
        setState(result);
      } else {
        setState(newState);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save game state');
      throw err;
    }
  }, []);

  // Update state after action
  // NOTE: Do NOT auto-save here - backend already saves state on every action.
  // Auto-save causes race conditions where frontend overwrites newer backend state.
  const updateState = useCallback((newState: GameState) => {
    setState(newState);
    // No auto-save - backend handles persistence on actions
    // If you need to save state explicitly, use saveState() instead
  }, []);

  return {
    state,
    loading,
    error,
    saveState,
    updateState,
  };
}

