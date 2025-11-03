/**
 * Client-side task completion logic
 * Ported from backend check_and_complete_tasks function
 */
import type { GameState, Womb, Clone } from '../types/game';

// Flavor text messages (matching backend)
const CLONE_CRAFTED_MESSAGES = [
  "Clone scaffold imprinted. Bioglass sings; the cradle empties. You are accounted for.",
  "Spindle spins down. A new vessel stands ready to receive a Rider."
];

const RESOURCE_GATHERING_MESSAGES = [
  "Harvest buffer fills; augers chant. Your hold grows heavier with spoils.",
  "Sluice lines clear. Tailings fall quiet. The Keep tallies your take."
];

// Helper functions to format messages with flavor text
function formatCloneCraftedMessage(cloneKind: string, cloneId: string, traits: Record<string, number>): string {
  const flavorMsg = CLONE_CRAFTED_MESSAGES[Math.floor(Math.random() * CLONE_CRAFTED_MESSAGES.length)];
  const traitOrder = ['PWC', 'SSC', 'MGC', 'DLT', 'ENF', 'ELK', 'FRK'];
  const traitStr = traitOrder
    .map(traitId => {
      const value = traits[traitId];
      return value !== undefined ? `${traitId} ${value}` : null;
    })
    .filter(Boolean)
    .join(', ');
  return `${flavorMsg}. ${cloneKind} Clone #${cloneId} crafted — Traits: ${traitStr}.`;
}

function formatResourceGatheringMessage(resource: string, amount: number, total: number): string {
  const flavorMsg = RESOURCE_GATHERING_MESSAGES[Math.floor(Math.random() * RESOURCE_GATHERING_MESSAGES.length)];
  let functionalDetails: string;
  if (resource === 'Shilajit') {
    functionalDetails = `Shilajit sample extracted. Resource +1. Total: ${total}`;
  } else {
    functionalDetails = `Gathered ${amount} ${resource}. Total: ${total}`;
  }
  return `${flavorMsg}. ${functionalDetails}`;
}

// Constants from CONFIG
const WOMB_MAX_DURABILITY = 100.0;

/**
 * Create a new womb with max durability (attention is now global, not per-womb)
 */
function createWomb(wombId: number): Womb {
  return {
    id: wombId,
    durability: WOMB_MAX_DURABILITY,
    max_durability: WOMB_MAX_DURABILITY,
    // Note: attention is now global (stored in GameState.global_attention), not per-womb
  };
}

/**
 * Award practice XP (simple implementation)
 */
function awardPracticeXp(state: GameState, practice: string, amount: number): void {
  if (!state.practices_xp[practice]) {
    state.practices_xp[practice] = 0;
  }
  state.practices_xp[practice] += amount;
}

/**
 * Check for completed tasks and auto-complete them.
 * Returns updated state with completed tasks processed.
 * 
 * Based on backend check_and_complete_tasks function from simpler working version.
 */
export function checkAndCompleteTasks(state: GameState): { state: GameState; completedMessages: string[] } {
  if (!state.active_tasks || Object.keys(state.active_tasks).length === 0) {
    return { state, completedMessages: [] };
  }

  const currentTime = Date.now() / 1000; // Current time in seconds
  const newState = { ...state };
  const completedMessages: string[] = [];

  // Deep copy resources and clones to avoid mutations
  newState.resources = { ...state.resources };
  newState.clones = { ...state.clones };
  newState.wombs = state.wombs ? [...state.wombs] : [];
  newState.active_tasks = { ...state.active_tasks };
  newState.practices_xp = { ...state.practices_xp };

  // Check each active task
  for (const [taskId, taskData] of Object.entries(newState.active_tasks)) {
    const startTime = taskData.start_time || 0;
    const duration = taskData.duration || 0;
    const taskType = taskData.type || 'unknown';

    // Check if task is complete
    if (currentTime >= startTime + duration && duration > 0) {
      console.log(`✅ Task ${taskId} (${taskType}) completed`);

      // Process gather_resource task
      if (taskType === 'gather_resource') {
        const resource = taskData.resource;
        const pendingAmount = taskData.pending_amount || 0;
        
        if (resource && pendingAmount > 0) {
          const oldTotal = newState.resources[resource] || 0;
          newState.resources[resource] = oldTotal + pendingAmount;
          const newTotal = newState.resources[resource];

          // Award practice XP
          awardPracticeXp(newState, 'Kinetic', 2);

          // Store completion message with flavor text
          const message = formatResourceGatheringMessage(resource, pendingAmount, newTotal);
          completedMessages.push(message);
          taskData.completion_message = message;
        }
      }

      // Process build_womb task
      if (taskType === 'build_womb') {
        const oldWombCount = newState.wombs ? newState.wombs.length : 0;
        const newWombId = oldWombCount;
        
        // Create new womb
        const newWomb = createWomb(newWombId);
        
        // Initialize wombs array if needed
        if (!newState.wombs) {
          newState.wombs = [];
        }
        newState.wombs.push(newWomb);

        // Set assembler_built for backward compatibility (if first womb)
        if (newState.wombs.length === 1) {
          newState.assembler_built = true;
        }

        const message = `Womb ${newWombId + 1} built successfully. You can now grow clones.`;
        completedMessages.push(message);
        taskData.completion_message = message;
        
        console.log(`🏗️ Womb created: ID=${newWombId}, total wombs=${newState.wombs.length}`);
      }

      // Process repair_womb task
      if (taskType === 'repair_womb') {
        const wombId = taskData.womb_id;
        if (wombId !== undefined && newState.wombs) {
          const targetWomb = newState.wombs.find(w => w.id === wombId);
          if (targetWomb) {
            // Restore durability to full
            targetWomb.durability = targetWomb.max_durability;
            const message = `Womb ${wombId + 1} repaired to full durability.`;
            completedMessages.push(message);
            taskData.completion_message = message;
          }
        }
      }

      // Process grow_clone task
      if (taskType === 'grow_clone') {
        const cloneData = taskData.pending_clone_data;
        if (cloneData) {
          // Set creation timestamp
          cloneData.created_at = currentTime;

          // Create clone and add to state
          const clone: Clone = {
            id: cloneData.id,
            kind: cloneData.kind,
            traits: cloneData.traits || [],
            xp: cloneData.xp || {},
            survived_runs: cloneData.survived_runs || 0,
            alive: cloneData.alive !== undefined ? cloneData.alive : true,
            uploaded: cloneData.uploaded || false,
            created_at: cloneData.created_at,
          };

          // Ensure clones object exists
          if (!newState.clones) {
            newState.clones = {};
          }
          newState.clones[clone.id] = clone;
          // Format message with flavor text
          const message = formatCloneCraftedMessage(cloneData.kind || 'BASIC', clone.id, cloneData.traits || {});
          completedMessages.push(message);
          taskData.completion_message = message;
        }
      }

      // Remove completed task
      delete newState.active_tasks[taskId];
      console.log(`🗑️ Removed completed task ${taskId} (${taskType})`);
    }
  }

  if (completedMessages.length > 0) {
    console.log(`✅ Completed ${completedMessages.length} task(s)`);
  }

  return { state: newState, completedMessages };
}

