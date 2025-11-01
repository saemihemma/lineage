/**
 * Simulation Screen - Main game interface
 */
import { useState, useEffect } from 'react';
import { useGameState } from '../hooks/useGameState';
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

export function SimulationScreen() {
  const { state, loading, error, updateState } = useGameState();
  const [selectedCloneId, setSelectedCloneId] = useState<string | null>(null);
  const [terminalMessages, setTerminalMessages] = useState<string[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [progress, setProgress] = useState({ value: 0, label: '' });
  const [showGrowDialog, setShowGrowDialog] = useState(false);

  // Load game state when component mounts
  useEffect(() => {
    if (state && !state.self_name) {
      addTerminalMessage('Welcome to LINEAGE Simulation.');
      addTerminalMessage('Enter your SELF name to begin.');
    } else if (state) {
      addTerminalMessage(`Welcome back, ${state.self_name}.`);
    }
  }, [state]);

  // Poll task status if there's an active task
  useEffect(() => {
    if (!state || !state.active_tasks || Object.keys(state.active_tasks).length === 0) {
      setProgress({ value: 0, label: '' });
      setIsBusy(false);
      return;
    }

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
        } else {
          // Task completed
          setProgress({ value: 0, label: '' });
          setIsBusy(false);
          clearInterval(pollInterval);
          // Reload state to get updates
          gameAPI.getState().then((updatedState) => {
            updateState(updatedState);
          });
        }
      } catch (err) {
        console.error('Failed to poll task status:', err);
      }
    }, 1000); // Poll every second

    return () => clearInterval(pollInterval);
  }, [state?.active_tasks, updateState]);

  const addTerminalMessage = (message: string) => {
    setTerminalMessages((prev) => [...prev, message].slice(-100)); // Keep last 100 messages
  };

  const handleAction = async (action: () => Promise<any>, actionName: string) => {
    if (isBusy || !state) return;
    
    try {
      setIsBusy(true);
      const result = await action();
      if (result.state) {
        updateState(result.state);
        if (result.message) {
          addTerminalMessage(result.message);
        }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : `Failed to ${actionName}`;
      addTerminalMessage(`ERROR: ${errorMsg}`);
      console.error(`Action failed: ${actionName}`, err);
    } finally {
      setIsBusy(false);
      setProgress({ value: 0, label: '' });
    }
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
    handleAction(() => gameAPI.runExpedition(kind), `run ${kind} expedition`);
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
          <div className="error-detail">{error}</div>
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
            SELF: {state.self_name || 'Unnamed'} | Level: {calculateSoulLevel(state.soul_xp)} | Soul: {state.soul_percent.toFixed(1)}%
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
          <button 
            className="action-btn"
            onClick={() => {/* TODO: Show leaderboard */}}
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
              onRunExpedition={handleRunExpedition}
              onUpload={() => selectedCloneId && handleUploadClone(selectedCloneId)}
              disabled={isBusy}
            />
            <ProgressPanel progress={progress} />
          </div>
        </div>

        {/* Bottom Row - Terminal and Practices */}
        <div className="bottom-row">
          <TerminalPanel messages={terminalMessages} />
          <PracticesPanel practicesXp={state.practices_xp} />
        </div>
      </div>

      {/* Grow Clone Dialog */}
      <GrowCloneDialog
        isOpen={showGrowDialog}
        onClose={() => setShowGrowDialog(false)}
        onGrow={handleGrowClone}
        disabled={isBusy}
      />
    </div>
  );
}

function calculateSoulLevel(soulXp: number): number {
  // Simplified - should match backend logic
  let level = 0;
  let xpNeeded = 0;
  while (soulXp >= xpNeeded) {
    level++;
    xpNeeded += 100 * level;
  }
  return level - 1;
}
