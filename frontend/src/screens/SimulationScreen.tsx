/**
 * Simulation Screen - Main game interface
 */
import { useState, useEffect, useRef } from 'react';
import { useGameState } from '../hooks/useGameState';
import { useEventFeed } from '../hooks/useEventFeed';
import { gameAPI } from '../api/game';
import './SimulationScreen.css';
import { ResourcesPanel } from '../components/ResourcesPanel';
import { ClonesPanel } from '../components/ClonesPanel';
import { CostsPanel } from '../components/CostsPanel';
import { GatherPanel } from '../components/GatherPanel';
import { CloneDetailsPanel } from '../components/CloneDetailsPanel';
import { ProgressPanel } from '../components/ProgressPanel';
import { TerminalPanel } from '../components/TerminalPanel';
import { PracticesPanel } from '../components/PracticesPanel';
import { GrowCloneDialog } from '../components/GrowCloneDialog';
import { LeaderboardDialog } from '../components/LeaderboardDialog';
import { FuelBar } from '../components/FuelBar';
import type { GameState } from '../types/game';

export function SimulationScreen() {
  const { state, loading, error, updateState } = useGameState();
  const stateRef = useRef<GameState | null>(state);
  const [selectedCloneId, setSelectedCloneId] = useState<string | null>(null);
  const [terminalMessages, setTerminalMessages] = useState<string[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  // Track multiple concurrent tasks by task_id
  const [activeTaskProgress, setActiveTaskProgress] = useState<Record<string, { value: number; label: string; startTime: number }>>({});
  const [showGrowDialog, setShowGrowDialog] = useState(false);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  // Store pending success messages until tasks complete (progress bar reaches 100%)
  // Using underscore prefix to indicate intentionally unused (we only need the setter)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_pendingMessages, setPendingMessages] = useState<Map<string, string>>(new Map());
  const [hasShownWelcome, setHasShownWelcome] = useState(false);
  
  // Calculate primary progress (for single progress bar display)
  // Show the most recently started task, or first active task if none specified
  const primaryProgress = (() => {
    const tasks = Object.entries(activeTaskProgress);
    if (tasks.length === 0) {
      return { value: 0, label: '' };
    }
    // Sort by start time (most recent first), then pick first
    const sorted = tasks.sort(([, a], [, b]) => b.startTime - a.startTime);
    const [, progress] = sorted[0];
    return { value: progress.value, label: progress.label };
  })();

  // Keep state ref in sync
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const addTerminalMessage = (message: string) => {
    setTerminalMessages((prev) => [...prev, message].slice(-100)); // Keep last 100 messages
  };

  // Event feed hook for live state sync
  const {
    startPolling,
    stopPolling,
    resumePolling,
    reset: resetEventFeed,
  } = useEventFeed({
    interval: 1200, // 1.2 seconds
    currentState: state,
    onTerminalMessage: addTerminalMessage,
    onStatePatch: (patchedState) => {
      if (patchedState) {
        updateState(patchedState);
      }
    },
    enabled: !!state && !loading, // Only poll when state is loaded
  });

  // Start/stop event feed polling based on state availability
  useEffect(() => {
    if (!state || loading) {
      stopPolling();
      return;
    }

    // Start polling when state is available
    startPolling();

    return () => {
      stopPolling();
    };
  }, [state, loading, startPolling, stopPolling]);

  // Reset event feed on reconnection or after long idle
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // Reset and resume when tab becomes visible again
        resetEventFeed();
        if (state && !loading) {
          resumePolling();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [state, loading, resetEventFeed, resumePolling]);

  // Load game state when component mounts (only once)
  useEffect(() => {
    if (state && !hasShownWelcome) {
      setHasShownWelcome(true);
      if (!state.self_name) {
        addTerminalMessage('Welcome to LINEAGE Simulation.');
        addTerminalMessage('Enter your SELF name to begin.');
      } else {
        addTerminalMessage(`Welcome back, ${state.self_name}.`);
      }
    }
  }, [state, hasShownWelcome]);

  // Poll all active tasks - support concurrent tasks (gathering + expeditions)
  useEffect(() => {
    if (!state || !state.active_tasks || Object.keys(state.active_tasks).length === 0) {
      // No active tasks - clear all progress
      setActiveTaskProgress({});
      setIsBusy(false);
      return;
    }

    // Track all active task IDs
    const activeTaskIds = Object.keys(state.active_tasks);
    
    // Initialize progress for new tasks (preserve existing ones to prevent flicker)
    setActiveTaskProgress((prev) => {
      const updated = { ...prev };
      activeTaskIds.forEach((taskId) => {
        if (!updated[taskId]) {
          // New task - initialize progress
          const task = state.active_tasks![taskId];
          updated[taskId] = {
            value: 0,
            label: task.type === 'gather_resource' ? `Gathering ${task.resource}...` : 
                   task.type === 'build_womb' ? 'Building Womb...' :
                   task.type === 'grow_clone' ? `Growing ${task.kind} clone...` : 'Processing...',
            startTime: task.start_time || Date.now(),
          };
        }
      });
      // Remove tasks that are no longer active
      Object.keys(updated).forEach((taskId) => {
        if (!activeTaskIds.includes(taskId)) {
          delete updated[taskId];
        }
      });
      return updated;
    });

    setIsBusy(true);

    // Poll all tasks - get status for each
    const pollInterval = setInterval(async () => {
      try {
        // Poll task status (backend returns status for the primary/active task)
        const status = await gameAPI.getTaskStatus();
        
        if (status.active && status.task) {
          // Update progress for this task (merge, don't replace all)
          setActiveTaskProgress((prev) => {
            const updated = { ...prev };
            if (status.task && updated[status.task.id]) {
              updated[status.task.id] = {
                ...updated[status.task.id],
                value: status.task.progress,
                label: `${status.task.label}… ${status.task.remaining}s remaining`,
              };
            }
            return updated;
          });
        } else if (status.completed && status.task) {
          // Task completed - remove from active progress
          const completedTaskId = status.task.id;
          
          setActiveTaskProgress((prev) => {
            const updated = { ...prev };
            delete updated[completedTaskId];
            return updated;
          });
          
          // Show pending message if any
          setPendingMessages((prev) => {
            if (prev.has(completedTaskId)) {
              const message = prev.get(completedTaskId)!;
              addTerminalMessage(message);
              const newMap = new Map(prev);
              newMap.delete(completedTaskId);
              return newMap;
            }
            return prev;
          });
          
          // Reload state to get updates (events feed will also update, but this ensures sync)
          const updatedState = await gameAPI.getState();
          updateState(updatedState);
          
          // Auto-select newly created clone if this was a grow_clone task
          const completedTask = state.active_tasks?.[completedTaskId];
          if (completedTask?.type === 'grow_clone' && updatedState.clones) {
            const cloneIds = Object.keys(updatedState.clones);
            if (cloneIds.length > 0) {
              const newestCloneId = cloneIds[cloneIds.length - 1];
              setSelectedCloneId(newestCloneId);
              addTerminalMessage(`Tip: Apply this clone (click "Apply Clone" button) to run expeditions.`);
            }
          }
          
          // Check if there are any remaining active tasks
          if (Object.keys(updatedState.active_tasks || {}).length === 0) {
            setIsBusy(false);
          }
        } else {
          // No active task in response - but check state to be sure
          const hasActiveTasks = state.active_tasks && Object.keys(state.active_tasks).length > 0;
          if (!hasActiveTasks) {
            setActiveTaskProgress({});
            setIsBusy(false);
          }
        }
      } catch (err) {
        console.error('Failed to poll task status:', err);
      }
    }, 1000); // Poll every second

    return () => clearInterval(pollInterval);
  }, [state?.active_tasks, updateState]);

  const handleAction = async (action: () => Promise<any>, actionName: string, allowDuringTasks: boolean = false) => {
    // Expeditions and immediate actions can run during gathering tasks
    // But still prevent duplicate requests for the same action type
    if (!state) {
      console.warn(`Action blocked: ${actionName} (no state)`);
      return;
    }
    
    // Check for blocking tasks only if this action requires exclusive access
    if (!allowDuringTasks && isBusy) {
      console.warn(`Action blocked: ${actionName} (exclusive task in progress)`);
      return;
    }

    try {
      // Only set busy for actions that create tasks (build, grow, gather)
      if (!allowDuringTasks) {
        setIsBusy(true);
      }
      const result = await action();
      if (result.state) {
        // Merge active_tasks instead of replacing (prevents flicker)
        const mergedState = {
          ...result.state,
          active_tasks: {
            ...state.active_tasks, // Preserve existing tasks
            ...result.state.active_tasks, // Add/update new tasks
          },
        };
        updateState(mergedState);

        // For timed actions (build womb, gather, grow clone), don't show message immediately
        // Store it to show when progress bar completes
        if (result.message && mergedState.active_tasks && Object.keys(mergedState.active_tasks).length > 0) {
          // Find the new task ID (the one that was just added)
          const newTaskIds = Object.keys(result.state.active_tasks || {});
          const existingTaskIds = Object.keys(state.active_tasks || {});
          const addedTaskId = newTaskIds.find(id => !existingTaskIds.includes(id)) || newTaskIds[0];
          
          if (addedTaskId) {
            setPendingMessages((prev) => {
              const newMap = new Map(prev);
              newMap.set(addedTaskId, result.message);
              return newMap;
            });
          }
        } else if (result.message) {
          // Immediate action (no timer) - show message right away
          addTerminalMessage(result.message);
        }
      }
    } catch (err) {
      // Enhanced error handling
      let errorMsg = `Failed to ${actionName}`;

      if (err instanceof Error) {
        errorMsg = err.message;
      }

      // Check for network errors
      if (err && typeof err === 'object' && 'name' in err) {
        if (err.name === 'TypeError' || err.name === 'NetworkError') {
          errorMsg = 'Network error. Please check your connection.';
        }
      }

      addTerminalMessage(`ERROR: ${errorMsg}`);
      console.error(`Action failed: ${actionName}`, err);

      // Reset busy state on error
      setIsBusy(false);
      // Don't clear progress on error - let it remain to show what was happening
    }
    // Note: Don't set isBusy to false on success - let the polling effect handle it when task completes
  };

  const handleBuildWomb = () => {
    handleAction(() => gameAPI.buildWomb(), 'build womb');
  };

  const handleGrowClone = (kind: string) => {
    handleAction(() => gameAPI.growClone(kind), `grow ${kind} clone`);
  };

  const handleGrowCloneClick = () => {
    if (!state?.assembler_built) {
      addTerminalMessage('ERROR: Build the Womb first before growing clones.');
      return;
    }
    setShowGrowDialog(true);
  };

  const handleGatherResource = (resource: string) => {
    handleAction(() => gameAPI.gatherResource(resource), `gather ${resource}`);
  };

  const handleApplyClone = (cloneId: string) => {
    handleAction(() => gameAPI.applyClone(cloneId), 'apply clone');
  };

  const handleRunExpedition = (kind: string) => {
    // Expeditions can run during gathering (drones continue gathering while on expedition)
    handleAction(() => gameAPI.runExpedition(kind), `run ${kind} expedition`, true);
  };

  const handleUploadClone = (cloneId: string) => {
    handleAction(() => gameAPI.uploadClone(cloneId), 'upload clone');
  };

  if (loading) {
    return (
      <div className="simulation-screen">
        <div className="loading-overlay">Loading simulation...</div>
      </div>
    );
  }

  if (error || !state) {
    return (
      <div className="simulation-screen">
        <div className="error-overlay">
          <div>Failed to load game state</div>
          <div className="error-detail">{error || 'Unknown error'}</div>
          <button 
            className="action-btn"
            onClick={() => window.location.reload()}
            style={{ marginTop: '20px' }}
          >
            Refresh Page
          </button>
          <div style={{ marginTop: '10px', fontSize: '12px', color: '#999' }}>
            If this persists, your session may have been lost during a backend update.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="simulation-screen">
      {/* Top Bar */}
      <div className="simulation-topbar">
        <div className="topbar-left">
          <h1 className="game-title">LINEAGE</h1>
          <div className="self-stats">
            SELF: {state.self_name || 'Unnamed'} | Level: {state.soul_level} | Soul: {state.soul_percent.toFixed(1)}%
          </div>
        </div>
        <div className="topbar-center">
          <FuelBar />
        </div>
        <div className="topbar-actions">
          <button 
            className="action-btn" 
            onClick={handleBuildWomb}
            disabled={isBusy || state.assembler_built}
          >
            Build Womb
          </button>
          <button 
            className="action-btn" 
            onClick={handleGrowCloneClick}
            disabled={isBusy || !state.assembler_built}
          >
            Grow Clone
          </button>
          {state.applied_clone_id && state.applied_clone_id in state.clones && state.clones[state.applied_clone_id].alive && (
            <>
              <button 
                className="action-btn expedition-top-btn"
                onClick={() => handleRunExpedition('MINING')}
                disabled={false}
                title="Mining expeditions earn Tritanium and Metal Ore. Can run while gathering resources."
              >
                Mining Expedition
              </button>
              <button 
                className="action-btn expedition-top-btn"
                onClick={() => handleRunExpedition('COMBAT')}
                disabled={false}
                title="Combat expeditions earn Biomass and Synthetic materials. Can run while gathering resources."
              >
                Combat Expedition
              </button>
              <button 
                className="action-btn expedition-top-btn"
                onClick={() => handleRunExpedition('EXPLORATION')}
                disabled={false}
                title="Exploration expeditions earn mixed resources. Can run while gathering resources."
              >
                Exploration Expedition
              </button>
            </>
          )}
          <button
            className="action-btn"
            onClick={() => setShowLeaderboard(true)}
          >
            Leaderboard
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="simulation-content">
        {/* Top Row - 3 Columns */}
        <div className="top-row">
          {/* Column 1: Resources and Clones */}
          <div className="col-1">
            <ResourcesPanel resources={state.resources} />
            <ClonesPanel 
              clones={state.clones}
              selectedId={selectedCloneId}
              onSelect={setSelectedCloneId}
            />
          </div>

          {/* Column 2: Costs and Gather */}
          <div className="col-2">
            <CostsPanel state={state} />
            <GatherPanel 
              onGather={handleGatherResource}
              disabled={isBusy}
            />
          </div>

          {/* Column 3: Clone Details and Progress */}
          <div className="col-3">
            <CloneDetailsPanel 
              clone={selectedCloneId ? state.clones[selectedCloneId] : null}
              appliedCloneId={state.applied_clone_id || null}
              onApply={() => selectedCloneId && handleApplyClone(selectedCloneId)}
              onUpload={() => selectedCloneId && handleUploadClone(selectedCloneId)}
              disabled={isBusy}
            />
            <ProgressPanel progress={primaryProgress} />
          </div>
        </div>

        {/* Bottom Row - Terminal and Practices */}
        <div className="bottom-row">
          <TerminalPanel messages={terminalMessages} />
          <PracticesPanel
            practicesXp={state.practices_xp}
            practiceLevels={state.practice_levels}
          />
        </div>
      </div>

      {/* Grow Clone Dialog */}
      <GrowCloneDialog
        isOpen={showGrowDialog}
        onClose={() => setShowGrowDialog(false)}
        onGrow={handleGrowClone}
        disabled={isBusy}
      />

      {/* Leaderboard Dialog */}
      <LeaderboardDialog
        isOpen={showLeaderboard}
        onClose={() => setShowLeaderboard(false)}
        currentState={{
          self_name: state.self_name,
          soul_level: state.soul_level,
          soul_xp: state.soul_xp,
          clones: state.clones,
        }}
      />
    </div>
  );
}
