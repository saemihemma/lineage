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

  // Load initial state
  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const gameState = await gameAPI.getState();
        setState(gameState);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load game state');
        console.error('Failed to load game state:', err);
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

