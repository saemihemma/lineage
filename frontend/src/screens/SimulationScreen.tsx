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
import type { GameState } from '../types/game';

export function SimulationScreen() {
  const { state, loading, error, updateState } = useGameState();
  const stateRef = useRef<GameState | null>(state);
  const [selectedCloneId, setSelectedCloneId] = useState<string | null>(null);
  const [terminalMessages, setTerminalMessages] = useState<string[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [progress, setProgress] = useState({ value: 0, label: '' });
  const [showGrowDialog, setShowGrowDialog] = useState(false);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  // Store pending success messages until tasks complete (progress bar reaches 100%)
  // Using underscore prefix to indicate intentionally unused (we only need the setter)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_pendingMessages, setPendingMessages] = useState<Map<string, string>>(new Map());
  const [hasShownWelcome, setHasShownWelcome] = useState(false);

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

  // Poll task status if there's an active task
  useEffect(() => {
    if (!state || !state.active_tasks || Object.keys(state.active_tasks).length === 0) {
      setProgress({ value: 0, label: '' });
      setIsBusy(false);
      return;
    }

    // Get taskId before polling starts (for message retrieval later)
    const taskId = Object.keys(state.active_tasks)[0];

    // Start polling
    setIsBusy(true);
    const pollInterval = setInterval(async () => {
      try {
        const status = await gameAPI.getTaskStatus();
        if (status.active && status.task) {
          setProgress({
            value: status.task.progress,
            label: `${status.task.label}… ${status.task.remaining}s remaining`
          });
        } else if (status.completed) {
          // Task completed - progress bar reached 100%
          setProgress({ value: 0, label: '' });
          setIsBusy(false);
          clearInterval(pollInterval);
          
          // Show pending message if any (e.g., "Womb built successfully", "Clone grown")
          // This ensures message only appears after progress bar completes
          setPendingMessages((prev) => {
            if (taskId && prev.has(taskId)) {
              const message = prev.get(taskId)!;
              addTerminalMessage(message);
              const newMap = new Map(prev);
              newMap.delete(taskId);
              return newMap;
            }
            return prev;
          });
          
          // Reload state to get updates
          const updatedState = await gameAPI.getState();
          updateState(updatedState);
          
          // Auto-select newly created clone if this was a grow_clone task
          // Check the task type before state was updated (from closure)
          const completedTaskType = state.active_tasks?.[taskId]?.type;
          if (completedTaskType === 'grow_clone' && updatedState.clones) {
            // Find the newest clone (last one in the list, which should be the most recent)
            const cloneIds = Object.keys(updatedState.clones);
            if (cloneIds.length > 0) {
              const newestCloneId = cloneIds[cloneIds.length - 1];
              setSelectedCloneId(newestCloneId);
              addTerminalMessage(`Tip: Apply this clone (click "Apply Clone" button) to run expeditions.`);
            }
          }
        } else {
          // No active task
          setProgress({ value: 0, label: '' });
          setIsBusy(false);
          clearInterval(pollInterval);
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
        updateState(result.state);

        // For timed actions (build womb, gather, grow clone), don't show message immediately
        // Store it to show when progress bar completes
        if (result.message && result.state.active_tasks && Object.keys(result.state.active_tasks).length > 0) {
          // This is a timed action - store message for later
          const taskId = Object.keys(result.state.active_tasks)[0];
          setPendingMessages((prev) => {
            const newMap = new Map(prev);
            newMap.set(taskId, result.message);
            return newMap;
          });
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
      setProgress({ value: 0, label: '' });
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
            <ProgressPanel progress={progress} />
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
