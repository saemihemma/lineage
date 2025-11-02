/**
 * React hook for managing game state
 */
import { useState, useEffect, useCallback } from 'react';
import { gameAPI } from '../api/game';
import type { GameState } from '../types/game';

export function useGameState() {
  const [state, setState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

