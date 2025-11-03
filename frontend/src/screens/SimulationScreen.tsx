/**
 * Simulation Screen - Main game interface
 */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useGameState } from '../hooks/useGameState';
import { useEventFeed } from '../hooks/useEventFeed';
import { gameAPI } from '../api/game';
import './SimulationScreen.css';
import { ResourcesPanel } from '../components/ResourcesPanel';
import { ClonesPanel } from '../components/ClonesPanel';
import { CostsPanel } from '../components/CostsPanel';
import { GatherPanel } from '../components/GatherPanel';
import { CloneDetailsPanel } from '../components/CloneDetailsPanel';
import { TerminalPanel } from '../components/TerminalPanel';
import { PracticesPanel } from '../components/PracticesPanel';
import { GrowCloneDialog } from '../components/GrowCloneDialog';
import { LeaderboardDialog } from '../components/LeaderboardDialog';
import { FuelBar } from '../components/FuelBar';
import { OnboardingChecklist } from '../components/OnboardingChecklist';
import { WombsPanel } from '../components/WombsPanel';
import { FacilitiesPanel } from '../components/FacilitiesPanel';
import { MissionControlLayout } from '../components/MissionControlLayout';
import { CollapsiblePanel } from '../components/CollapsiblePanel';
import { usePanelState } from '../stores/usePanelState';
import type { GameState } from '../types/game';
import { hasWomb, getWombCount, getUnlockedWombCount, getAverageAttentionPercent } from '../utils/wombs';

export function SimulationScreen() {
  const { state, loading, error, updateState, getCompletedTaskMessages } = useGameState();
  const { setPanelOpen, togglePanel } = usePanelState();
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
  const prevClonesRef = useRef<Record<string, any>>({});

  // Create stable version string for active_tasks to avoid object reference dependencies
  // Only recalculate when active_tasks actually changes, not when any part of state changes
  // This prevents unnecessary re-runs of effects that depend on activeTasksVersion
  const activeTasksVersion = useMemo(() => {
    const tasks = state?.active_tasks;
    if (!tasks || Object.keys(tasks).length === 0) {
      return '';
    }
    return Object.keys(tasks).sort().join('|');
  }, [state?.active_tasks]);

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

  // Memoize addTerminalMessage to ensure stable reference for useEventFeed
  const addTerminalMessage = useCallback((message: string) => {
    setTerminalMessages((prev) => [...prev, message].slice(-100)); // Keep last 100 messages
  }, []); // setTerminalMessages is a stable setState function

  // Event feed hook - DISABLED: Not needed with localStorage-based state management
  // Tasks complete client-side now, so event feed is redundant
  // Keeping the hook setup but not starting polling to avoid unnecessary API calls
  const {
    // startPolling,
    // stopPolling,
    // resumePolling,
    // reset: resetEventFeed,
  } = useEventFeed({
    interval: 1200, // 1.2 seconds
    currentState: state,
    onTerminalMessage: addTerminalMessage,
    onStatePatch: (patchedState) => {
      if (patchedState) {
        updateState(patchedState);
      }
    },
    enabled: false, // DISABLED: Event feed not needed with localStorage
  });

  // Event feed polling disabled - no longer needed with localStorage
  // useEffect(() => {
  //   if (!state || loading) {
  //     stopPolling();
  //     return;
  //   }
  //   startPolling();
  //   return () => {
  //     stopPolling();
  //   };
  // }, [state, loading, startPolling, stopPolling]);

  // Event feed visibility handler - DISABLED: Event feed not needed with localStorage
  // useEffect(() => {
  //   const handleVisibilityChange = () => {
  //     if (document.visibilityState === 'visible') {
  //       // Reset and resume when tab becomes visible again
  //       resetEventFeed();
  //       if (state && !loading) {
  //         resumePolling();
  //       }
  //     }
  //   };
  //
  //   document.addEventListener('visibilitychange', handleVisibilityChange);
  //   return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  // }, [state, loading, resetEventFeed, resumePolling]);

  // Load game state when component mounts (only once)
  useEffect(() => {
    if (state && !hasShownWelcome) {
      setHasShownWelcome(true);
      
      const wombCount = state.wombs?.length || 0;
      console.log('🎮 SimulationScreen: Component mounted with state', {
        hasWombs: Array.isArray(state.wombs),
        wombCount,
        assemblerBuilt: state.assembler_built,
        selfName: state.self_name,
        activeTasks: Object.keys(state.active_tasks || {}).length,
      });
      
      // Fallback to localStorage if state doesn't have self_name
      let displayName = state.self_name;
      if (!displayName) {
        const savedName = localStorage.getItem('lineage_self_name');
        if (savedName) {
          displayName = savedName;
          console.log('📝 SimulationScreen: Syncing name from localStorage to state');
          // Update state with saved name (auto-saves to localStorage)
          if (state) {
            const updatedState = { ...state, self_name: savedName };
            updateState(updatedState);
          }
        }
      }
      
      if (!displayName) {
        addTerminalMessage('Welcome to LINEAGE Simulation.');
        addTerminalMessage('Enter your SELF name to begin.');
      } else {
        addTerminalMessage(`Welcome back, ${displayName}.`);
      }
    }
  }, [state, hasShownWelcome]);

  // Track task progress locally (no backend polling needed)
  useEffect(() => {
    const tasks = state?.active_tasks;
    if (!state || !tasks || Object.keys(tasks).length === 0) {
      // No active tasks - clear all progress
      setActiveTaskProgress({});
      setIsBusy(false);
      return;
    }

    // Track all active task IDs
    const activeTaskIds = Object.keys(tasks);
    
    // Initialize progress for new tasks (preserve existing ones to prevent flicker)
    setActiveTaskProgress((prev) => {
      const updated = { ...prev };
      activeTaskIds.forEach((taskId) => {
        if (!updated[taskId]) {
          // New task - initialize progress
          const task = tasks[taskId];
          updated[taskId] = {
            value: 0,
            label: task.type === 'gather_resource' ? `Gathering ${task.resource}...` : 
                   task.type === 'build_womb' ? 'Building Womb...' :
                   task.type === 'grow_clone' ? `Growing ${task.kind} clone...` :
                   task.type === 'repair_womb' ? `Repairing Womb ${(task.womb_id || 0) + 1}...` :
                   'Processing...',
            startTime: task.start_time || Date.now() / 1000,
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

    // Update progress locally based on task timing
    const progressInterval = setInterval(() => {
      const currentTasks = state?.active_tasks;
      if (!state || !currentTasks || Object.keys(currentTasks).length === 0) {
        return;
      }

      const now = Date.now() / 1000;
      setActiveTaskProgress((prev) => {
        const updated = { ...prev };
        let allComplete = true;

        for (const [taskId, taskData] of Object.entries(currentTasks)) {
          const startTime = taskData.start_time || 0;
          const duration = taskData.duration || 0;
          
          if (duration <= 0) continue;
          
          const elapsed = now - startTime;
          const remaining = Math.max(0, duration - elapsed);
          const progress = Math.min(100, Math.floor((elapsed / duration) * 100));
          
          if (remaining > 0) {
            allComplete = false;
            // Update progress
            if (updated[taskId]) {
              const taskType = taskData.type || 'unknown';
              const labelBase = taskType === 'gather_resource' ? `Gathering ${taskData.resource}...` : 
                               taskType === 'build_womb' ? 'Building Womb...' :
                               taskType === 'grow_clone' ? `Growing ${taskData.kind} clone...` :
                               taskType === 'repair_womb' ? `Repairing Womb ${((taskData.womb_id || 0) + 1)}...` :
                               'Processing...';
              
              updated[taskId] = {
                ...updated[taskId],
                value: progress,
                label: `${labelBase} ${Math.ceil(remaining)}s remaining`,
              };
            }
          } else {
            // Task complete - will be removed by useGameState task checker
            // Just remove from progress tracking
            delete updated[taskId];
          }
        }

        if (allComplete && (!currentTasks || Object.keys(currentTasks).length === 0)) {
          setIsBusy(false);
        }

        return updated;
      });
    }, 500); // Update every 500ms for smoother progress

    return () => clearInterval(progressInterval);
  }, [activeTasksVersion, state]);

  // Listen for task completion and show messages
  useEffect(() => {
    if (!state) return;

    // Get completion messages from completed tasks
    const completedMessages = getCompletedTaskMessages();
    if (completedMessages.length > 0) {
      completedMessages.forEach(message => {
        addTerminalMessage(message);
      });
    }

    // Auto-select newly created clone if one was just grown
    // Check if clones count increased
    if (state.clones && Object.keys(state.clones).length > Object.keys(prevClonesRef.current).length) {
      const cloneIds = Object.keys(state.clones);
      const newCloneIds = cloneIds.filter(id => !prevClonesRef.current[id]);
      if (newCloneIds.length > 0) {
        const newestCloneId = newCloneIds[newCloneIds.length - 1];
        setSelectedCloneId(newestCloneId);
        addTerminalMessage(`Tip: Apply this clone (click "Apply Clone" button) to run expeditions.`);
      }
    }
    prevClonesRef.current = state.clones || {};

    // Check if no more active tasks
    const currentTaskIds = Object.keys(state.active_tasks || {});
    if (currentTaskIds.length === 0) {
      setIsBusy(false);
    }
  }, [state, getCompletedTaskMessages, addTerminalMessage, setSelectedCloneId]);

  // Check if FTUE is complete (for auto-collapse)
  // Guard against null state - calculate only when state exists
  // MUST BE BEFORE EARLY RETURNS to maintain hook order
  // Note: Currently unused - auto-collapse was removed, but keeping for potential future use
  // const ftueComplete = useMemo(() => {
  //   if (!state) return false;
  //   return !!(
  //     state.ftue?.step_build_womb && 
  //     state.ftue?.step_grow_clone && 
  //     (state.applied_clone_id && state.applied_clone_id in (state.clones || {})) &&
  //     state.ftue?.step_first_expedition
  //   );
  // }, [state]);

  // Keep FTUE panel open even when complete - users should see their progress
  // Removed auto-collapse so checklist stays visible

  // Auto-expand Progress when tasks start - MUST BE BEFORE EARLY RETURNS
  useEffect(() => {
    const tasks = state?.active_tasks;
    if (tasks && Object.keys(tasks).length > 0) {
      setPanelOpen('rightOpen', 'progress', true);
    }
  }, [activeTasksVersion, state, setPanelOpen]);

  // Keyboard shortcut: Ctrl+/ toggles Terminal - MUST BE BEFORE EARLY RETURNS
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        togglePanel('terminalOpen', 'terminal');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [togglePanel]);

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

    // Log action start with current state
    const currentWombCount = state.wombs?.length || 0;
    console.log(`🎬 Starting action: ${actionName}`, {
      currentWombs: currentWombCount,
      assemblerBuilt: state.assembler_built,
      hasActiveTasks: Object.keys(state.active_tasks || {}).length > 0,
    });

    try {
      // Only set busy for actions that create tasks (build, grow, gather)
      if (!allowDuringTasks) {
        setIsBusy(true);
      }
      const result = await action();
      console.log(`📥 Action response received: ${actionName}`, {
        hasState: !!result.state,
        hasWombs: Array.isArray(result.state?.wombs),
        wombCount: result.state?.wombs?.length || 0,
        hasActiveTasks: Object.keys(result.state?.active_tasks || {}).length > 0,
        message: result.message,
      });
      
      if (result.state) {
        // Merge active_tasks instead of replacing (prevents flicker)
        // Important: result.state.active_tasks should contain the new task
        const existingTasks = state.active_tasks || {};
        const newTasks = result.state.active_tasks || {};
        
        // Merge tasks (new tasks override existing ones with same ID, add new ones)
        const mergedTasks = {
          ...existingTasks,
          ...newTasks, // This adds the new task from backend
        };
        
        const mergedState = {
          ...result.state,
          active_tasks: mergedTasks,
        };
        
        // Debug: log if task was actually added
        const taskKeys = Object.keys(mergedTasks);
        const hadTasks = Object.keys(existingTasks).length;
        const hasTasks = taskKeys.length;
        const newWombCount = mergedState.wombs?.length || 0;
        
        console.log(`🔄 Merging state after ${actionName}:`, {
          tasksBefore: hadTasks,
          tasksAfter: hasTasks,
          wombsBefore: currentWombCount,
          wombsAfter: newWombCount,
          assemblerBuilt: mergedState.assembler_built,
        });
        
        if (hasTasks > hadTasks) {
          console.log(`✅ Task added: ${taskKeys.length} total tasks`);
        }
        
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
        
        // Show attack message if feral drone attack occurred
        if ((result as any).attack_message) {
          addTerminalMessage((result as any).attack_message);
        }
      }
    } catch (err) {
      // Enhanced error handling
      let errorMsg = `Failed to ${actionName}`;

      if (err instanceof Error) {
        errorMsg = err.message;
      }

      // Check for network errors - provide more helpful messages
      if (err instanceof Error) {
        const errName = (err as any).name || err.constructor.name;
        if (errName === 'NetworkError' || (errName === 'TypeError' && err.message?.includes('fetch'))) {
          // More detailed network error message
          const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
          errorMsg = `Network error: Unable to connect to API at ${apiUrl}. Check your connection and ensure the backend is running.`;
          console.error(`🌐 Network Error Details:`, {
            action: actionName,
            apiUrl,
            error: err,
            suggestion: 'Verify VITE_API_URL is set correctly in production',
          });
        }
      }

      addTerminalMessage(`ERROR: ${errorMsg}`);
      console.error(`Action failed: ${actionName}`, {
        error: err,
        errorType: err instanceof Error ? err.constructor.name : typeof err,
        errorMessage: err instanceof Error ? err.message : String(err),
      });

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
    if (!state || !hasWomb(state)) {
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

  const handleRepairWomb = (wombId: number) => {
    handleAction(() => gameAPI.repairWomb(wombId), `repair womb ${wombId + 1}`);
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

  // Top HUD component (defined after early returns to ensure state is available)
  const topHud = (
    <div className="simulation-topbar">
        <div className="topbar-left">
          <h1 className="game-title">LINEAGE</h1>
          <div className="self-stats">
            SELF: {state.self_name || localStorage.getItem('lineage_self_name') || 'Unnamed'} | Level: {state.soul_level} | Soul: {(state.soul_percent || 0).toFixed(1)}%
          </div>
        </div>
        <div className="topbar-center">
          <FuelBar />
          <div className="attention-bar-global">
            <span className="attention-bar-label">Attention:</span>
            <div className="attention-bar-visual">
              <div
                className={`attention-bar-fill ${getAverageAttentionPercent(state) >= 50 ? 'good' : getAverageAttentionPercent(state) >= 25 ? 'warning' : 'critical'}`}
                style={{ width: `${getAverageAttentionPercent(state)}%` }}
              />
              <span className="attention-bar-text">{getAverageAttentionPercent(state).toFixed(0)}%</span>
            </div>
          </div>
          {/* Progress bar in HUD */}
          <div className="progress-bar-hud">
            <span className="progress-bar-label">{primaryProgress.label || 'Idle'}</span>
            <div className="progress-bar-visual">
              <div
                className="progress-bar-fill"
                style={{ width: `${primaryProgress.value}%` }}
              />
            </div>
          </div>
        </div>
        <div className="topbar-actions">
          <button 
            className="action-btn" 
            onClick={handleBuildWomb}
            disabled={isBusy || getWombCount(state) >= getUnlockedWombCount(state)}
            title={getWombCount(state) >= getUnlockedWombCount(state) 
              ? `All ${getUnlockedWombCount(state)} womb${getUnlockedWombCount(state) > 1 ? 's' : ''} built. Unlock more through practice progression.`
              : `Build Womb ${getWombCount(state) + 1}/${getUnlockedWombCount(state)}`}
          >
            Build Womb {getWombCount(state) > 0 ? `(${getWombCount(state)}/${getUnlockedWombCount(state)})` : ''}
          </button>
          <button 
            className="action-btn" 
            onClick={handleGrowCloneClick}
            disabled={isBusy || !hasWomb(state)}
          >
            Grow Clone
          </button>
          {state.applied_clone_id && state.clones?.[state.applied_clone_id]?.alive && (
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
  );

  return (
    <div className="simulation-screen">
      <MissionControlLayout topHud={topHud}>
        {/* Left Column */}
        <div className="mission-control-left">
          <CollapsiblePanel
            id="ftue"
            category="leftOpen"
            title="Getting Started"
            defaultOpen={true}
          >
            <OnboardingChecklist state={state} />
          </CollapsiblePanel>
          
          <CollapsiblePanel
            id="resources"
            category="leftOpen"
            title="Resources"
            defaultOpen={false}
          >
            <ResourcesPanel resources={state.resources} />
          </CollapsiblePanel>
        </div>

        {/* Center Column */}
        <div className="mission-control-center">
          <CollapsiblePanel
            id="womb"
            category="centerOpen"
            title="Womb"
            defaultOpen={true}
          >
            {getWombCount(state) < 2 && <WombsPanel state={state} />}
            {getWombCount(state) >= 2 && (
              <FacilitiesPanel 
                state={state}
                onRepair={handleRepairWomb}
                disabled={isBusy}
              />
            )}
          </CollapsiblePanel>
          
          <CollapsiblePanel
            id="clones"
            category="centerOpen"
            title="Clones"
            defaultOpen={true}
          >
            <ClonesPanel
              clones={state.clones}
              selectedId={selectedCloneId}
              onSelect={setSelectedCloneId}
            />
          </CollapsiblePanel>
        </div>

        {/* Right Column */}
        <div className="mission-control-right">
          <CollapsiblePanel
            id="cloneDetails"
            category="rightOpen"
            title="Clone Details"
            defaultOpen={true}
          >
            <CloneDetailsPanel 
              clone={selectedCloneId ? state.clones?.[selectedCloneId] : null}
              appliedCloneId={state.applied_clone_id || null}
              onApply={() => selectedCloneId && handleApplyClone(selectedCloneId)}
              onUpload={() => selectedCloneId && handleUploadClone(selectedCloneId)}
              disabled={isBusy}
            />
          </CollapsiblePanel>

          <CollapsiblePanel
            id="self"
            category="rightOpen"
            title="SELF & Practices"
            defaultOpen={true}
          >
            <PracticesPanel
              practicesXp={state.practices_xp}
              practiceLevels={state.practice_levels}
              state={state}
            />
          </CollapsiblePanel>
        </div>

        {/* Bottom Row (3 columns) */}
        <div className="mission-control-bottom-left">
          <CollapsiblePanel
            id="costs"
            category="bottomLeftOpen"
            title="Costs"
            defaultOpen={true}
          >
            <CostsPanel state={state} />
          </CollapsiblePanel>
        </div>

        <div className="mission-control-terminal">
          <CollapsiblePanel
            id="terminal"
            category="terminalOpen"
            title="Terminal"
            defaultOpen={true}
            className="terminal-panel"
          >
            <TerminalPanel messages={terminalMessages} />
          </CollapsiblePanel>
        </div>

        <div className="mission-control-bottom-right">
          <CollapsiblePanel
            id="gather"
            category="bottomRightOpen"
            title="Gather Resources"
            defaultOpen={true}
          >
            <GatherPanel
              onGather={handleGatherResource}
              disabled={isBusy}
            />
          </CollapsiblePanel>
        </div>
      </MissionControlLayout>

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
