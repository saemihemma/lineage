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
        const gameState = await gameAPI.getState();
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
    if (!state || !state.active_tasks || Object.keys(state.active_tasks).length === 0) {
      return;
    }

    // Start polling every 1 second to check for task completion
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const updatedState = await gameAPI.getState();
        
        // Update state to reflect task completion (only if active_tasks changed)
        setState((prevState) => {
          if (!prevState) return prevState;
          
          const prevTasks = prevState.active_tasks || {};
          const newTasks = updatedState.active_tasks || {};
          
          // Check if active_tasks changed (tasks completed)
          const prevTaskKeys = Object.keys(prevTasks);
          const newTaskKeys = Object.keys(newTasks);
          
          if (prevTaskKeys.length !== newTaskKeys.length || 
              prevTaskKeys.some(id => !newTasks[id]) ||
              JSON.stringify(prevTasks) !== JSON.stringify(newTasks)) {
            // Tasks changed - update state to reflect completion
            return updatedState;
          }
          
          return prevState;
        });

        // Check if we should stop polling (no more active tasks)
        const hasActiveTasks = updatedState.active_tasks && Object.keys(updatedState.active_tasks).length > 0;
        if (!hasActiveTasks && pollingIntervalRef.current) {
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
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [state?.active_tasks]); // Re-run when active_tasks changes

  // Save state
  const saveState = useCallback(async (newState: GameState) => {
    try {
      await gameAPI.saveState(newState);
      setState(newState);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save game state');
      throw err;
    }
  }, []);

  // Update state after action
  const updateState = useCallback((newState: GameState) => {
    setState(newState);
    // Auto-save after state update
    gameAPI.saveState(newState).catch((err) => {
      console.error('Failed to auto-save:', err);
    });
  }, []);

  return {
    state,
    loading,
    error,
    saveState,
    updateState,
  };
}

