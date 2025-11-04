/**
 * React hook for managing game state
 * Uses localStorage for persistence instead of database
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { GameState } from '../types/game';
import { loadStateFromLocalStorage, saveStateToLocalStorage, createDefaultState } from '../utils/localStorage';
import { checkAndCompleteTasks } from '../utils/tasks';
import { applyAttentionDecay } from '../utils/wombs';

export function useGameState() {
  const [state, setState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const taskCheckIntervalRef = useRef<number | null>(null);
  const attentionDecayIntervalRef = useRef<number | null>(null);
  const completedTaskMessagesRef = useRef<Map<string, string>>(new Map());

  // Load initial state from localStorage
  useEffect(() => {
    try {
      setLoading(true);
      setError(null);
      console.log('🔄 Loading game state from localStorage...');
      
      let gameState = loadStateFromLocalStorage();
      
      // If no saved state, create default
      if (!gameState) {
        console.log('📦 No saved state found, creating new game state');
        gameState = createDefaultState();
        saveStateToLocalStorage(gameState);
      }
      
      // Apply attention decay on load (to account for time passed while game was closed)
      const decayedState = applyAttentionDecay(gameState);
      
      // Log state details for debugging
      const wombCount = decayedState.wombs?.length || 0;
      console.log('📦 State loaded:', {
        hasWombs: Array.isArray(decayedState.wombs),
        wombCount,
        assemblerBuilt: decayedState.assembler_built,
        selfName: decayedState.self_name,
        hasClones: Object.keys(decayedState.clones || {}).length > 0,
        activeTasks: Object.keys(decayedState.active_tasks || {}).length,
        globalAttention: decayedState.global_attention,
        attentionDecayed: decayedState.global_attention !== gameState.global_attention,
      });
      
      // Save decayed state if attention changed
      if (decayedState.global_attention !== gameState.global_attention) {
        saveStateToLocalStorage(decayedState);
      }
      
      setState(decayedState);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load game state';
      setError(errorMsg);
      console.error('Failed to load game state:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Check for task completion periodically
  // Use ref to track previous active_tasks keys for stable comparison
  const prevActiveTasksKeysRef = useRef<string>('');
  const stateRef = useRef(state);
  
  // Keep stateRef updated without causing effect re-runs
  useEffect(() => {
    stateRef.current = state;
  }, [state]);
  
  // Create stable version string for active_tasks using useMemo
  // Only recalculate when active_tasks actually changes, not when any part of state changes
  // This prevents unnecessary re-runs of effects that depend on activeTasksVersion
  const activeTasksVersion = useMemo(() => {
    const tasks = state?.active_tasks;
    if (!tasks || Object.keys(tasks).length === 0) {
      return '';
    }
    return Object.keys(tasks).sort().join('|');
  }, [state?.active_tasks]);
  
  useEffect(() => {
    // Clear any existing interval
    if (taskCheckIntervalRef.current) {
      clearInterval(taskCheckIntervalRef.current);
      taskCheckIntervalRef.current = null;
    }

    // Get current state from ref
    const currentState = stateRef.current;
    const activeTasks = currentState?.active_tasks;
    const hasActiveTasks = activeTasks && Object.keys(activeTasks).length > 0;
    
    // Create stable key string for comparison (sorted task IDs)
    const currentTaskKeys = hasActiveTasks ? Object.keys(activeTasks).sort().join(',') : '';
    
    // Only proceed if task keys actually changed (prevents unnecessary re-setup)
    if (!currentState || !hasActiveTasks) {
      prevActiveTasksKeysRef.current = currentTaskKeys;
      return;
    }

    // Only re-setup if task IDs actually changed (not just object reference)
    if (prevActiveTasksKeysRef.current === currentTaskKeys && taskCheckIntervalRef.current) {
      // Same tasks, interval already running, no need to re-setup
      return;
    }
    
    prevActiveTasksKeysRef.current = currentTaskKeys;

    console.log(`🔵 Starting task completion checking: ${Object.keys(activeTasks).length} active task(s)`);

    // Check every second for completed tasks and process them
    taskCheckIntervalRef.current = setInterval(() => {
      // Use ref to get latest state without dependency
      const latestState = stateRef.current;
      if (!latestState || !latestState.active_tasks || Object.keys(latestState.active_tasks).length === 0) {
        return;
      }
      
      setState((prevState) => {
        if (!prevState || !prevState.active_tasks || Object.keys(prevState.active_tasks).length === 0) {
          return prevState;
        }
        
        // Check and complete any finished tasks
        const { state: updatedState, completedMessages } = checkAndCompleteTasks(prevState);
        
        // If tasks were completed, update state and save
        if (completedMessages.length > 0) {
          // Store completion messages before tasks are removed
          // Find which tasks were completed by comparing active_tasks
          const prevTaskIds = Object.keys(prevState.active_tasks || {});
          const newTaskIds = Object.keys(updatedState.active_tasks || {});
          const completedTaskIds = prevTaskIds.filter(id => !newTaskIds.includes(id));
          
          // Store messages for completed tasks
          completedTaskIds.forEach(taskId => {
            const taskData = prevState.active_tasks?.[taskId];
            if (taskData?.completion_message) {
              completedTaskMessagesRef.current.set(taskId, taskData.completion_message);
            }
          });
          
          // Log completion messages for debugging
          completedMessages.forEach(msg => console.log(`📢 ${msg}`));
          
          // Auto-save when tasks complete
          saveStateToLocalStorage(updatedState);
          // Update ref with new state
          stateRef.current = updatedState;
          return updatedState;
        }
        
        return prevState;
      });
    }, 1000); // Check every 1 second

    // Cleanup on unmount or when task version changes
    return () => {
      if (taskCheckIntervalRef.current) {
        console.log(`🟡 Cleaning up task checking`);
        clearInterval(taskCheckIntervalRef.current);
        taskCheckIntervalRef.current = null;
      }
    };
  }, [activeTasksVersion]); // Depend on stable version string instead of entire state object

  // Periodic attention decay check (every minute)
  useEffect(() => {
    // Clear any existing interval
    if (attentionDecayIntervalRef.current) {
      clearInterval(attentionDecayIntervalRef.current);
      attentionDecayIntervalRef.current = null;
    }

    // Only run if we have state loaded
    if (!state) {
      return;
    }

    console.log('🔵 Starting attention decay checking');

    // Check every minute for attention decay
    attentionDecayIntervalRef.current = setInterval(() => {
      setState((prevState) => {
        if (!prevState) {
          return prevState;
        }

        // Prevent double decay: only decay if last_saved_ts is old enough (> 60 seconds)
        // This prevents frontend decay when backend just updated state (which already applied decay)
        const currentTime = Date.now() / 1000;
        const lastSavedTs = prevState.last_saved_ts || currentTime;
        const secondsSinceSave = currentTime - lastSavedTs;
        
        // If state was just updated from backend (< 60 seconds ago), skip decay
        // Backend already applied decay when processing the action
        if (secondsSinceSave < 60) {
          return prevState;
        }

        // Apply attention decay
        const decayedState = applyAttentionDecay(prevState);
        
        // Only update if attention actually changed (to avoid unnecessary re-renders)
        if (decayedState.global_attention !== prevState.global_attention) {
          // Auto-save when attention decays
          saveStateToLocalStorage(decayedState);
          // Update ref with new state
          stateRef.current = decayedState;
          return decayedState;
        }
        
        return prevState;
      });
    }, 60000); // Check every 60 seconds (1 minute)

    // Cleanup on unmount or when state changes
    return () => {
      if (attentionDecayIntervalRef.current) {
        console.log(`🟡 Cleaning up attention decay checking`);
        clearInterval(attentionDecayIntervalRef.current);
        attentionDecayIntervalRef.current = null;
      }
    };
  }, [state ? 'loaded' : 'unloaded']); // Re-run when state is loaded/unloaded

  // Save state to localStorage
  const saveState = useCallback((newState: GameState) => {
    try {
      saveStateToLocalStorage(newState);
      setState(newState);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to save game state';
      setError(errorMsg);
      throw err;
    }
  }, []);

  // Update state after action and auto-save
  const updateState = useCallback((newState: GameState) => {
    setState(newState);
    // Auto-save to localStorage after every update
    saveStateToLocalStorage(newState);
  }, []);

  // Get completion messages for tasks that were just completed
  const getCompletedTaskMessages = useCallback(() => {
    const messages = Array.from(completedTaskMessagesRef.current.values());
    completedTaskMessagesRef.current.clear(); // Clear after retrieving
    return messages;
  }, []);

  return {
    state,
    loading,
    error,
    saveState,
    updateState,
    getCompletedTaskMessages,
  };
}

