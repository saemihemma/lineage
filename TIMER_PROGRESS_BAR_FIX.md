# Timer/Progress Bar Fix - URGENT

## Problem

When user clicks "Build Womb":
- ❌ Shows "Building Womb..." but no progress bar
- ❌ Never completes (stuck forever)
- ❌ Breaks core gameplay

## Root Cause

**Frontend never polls for task completion!**

1. ✅ Backend creates task with timer (works)
2. ✅ Backend auto-completes task when timer expires (works)
3. ❌ Frontend never checks `/api/game/state` to get completed task

**Current frontend behavior:**
```typescript
// useGameState.ts loads state ONCE on mount
useEffect(() => {
  load(); // Only runs once!
}, []);

// No polling = never sees task completion
```

## Solution

**Add polling to refresh state when there are active tasks.**

### Option 1: Add polling to useGameState (RECOMMENDED)

```typescript
// frontend/src/hooks/useGameState.ts

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
        const errorMsg = err instanceof Error ? err.message : 'Failed to load game state';
        setError(errorMsg);
        console.error('Failed to load game state:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // NEW: Poll for task completion when there are active tasks
  useEffect(() => {
    if (!state || !state.active_tasks || Object.keys(state.active_tasks).length === 0) {
      return; // No active tasks, no need to poll
    }

    // Poll every 1 second while tasks are active
    const pollInterval = setInterval(async () => {
      try {
        const updatedState = await gameAPI.getState();
        setState(updatedState);

        // If no more active tasks, interval will be cleared on next render
      } catch (err) {
        console.error('Failed to poll game state:', err);
        // Don't clear interval - will retry next tick
      }
    }, 1000); // Poll every 1 second

    return () => clearInterval(pollInterval);
  }, [state?.active_tasks]); // Re-run when active_tasks change

  // ... rest of hook unchanged
}
```

### Option 2: Create separate useTaskPolling hook

```typescript
// frontend/src/hooks/useTaskPolling.ts

import { useEffect, useState } from 'react';
import { gameAPI } from '../api/game';

interface TaskStatus {
  active: boolean;
  completed: boolean;
  task: any;
  tasks: any[];
}

export function useTaskPolling(enabled: boolean) {
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Poll task status every 1 second
    const pollInterval = setInterval(async () => {
      try {
        // Assuming gameAPI has a getTaskStatus method
        const status = await gameAPI.getTaskStatus();
        setTaskStatus(status);
      } catch (err) {
        console.error('Failed to poll task status:', err);
      }
    }, 1000);

    return () => clearInterval(pollInterval);
  }, [enabled]);

  return taskStatus;
}
```

## Backend is Ready!

The backend already:
- ✅ Auto-completes tasks in `/api/game/state` endpoint (game.py:724)
- ✅ Provides `/api/game/tasks/status` endpoint
- ✅ Returns task progress with elapsed time

**Backend code (already working):**
```python
# backend/routers/game.py:724
def load_game_state(db, session_id):
    # ...
    state = dict_to_game_state(data)

    # Auto-complete finished tasks
    state = check_and_complete_tasks(state)  # ← This works!

    if state.active_tasks != data.get("active_tasks", {}):
        # Tasks were completed, save updated state
        save_game_state(db, session_id, state)

    return state
```

**Task completion logic (backend/routers/game.py:388):**
```python
if current_time >= start_time + duration:
    # Task is complete
    if task_type == "build_womb":
        # Create womb and set assembler_built = True
        new_womb = create_womb(new_womb_id)
        new_state.wombs.append(new_womb)
        new_state.assembler_built = True  # ← Gets set!
```

## Testing the Fix

**Before fix:**
```bash
# User clicks "Build Womb"
# Womb build starts
# Shows "Building Womb..." forever
# Never completes ❌
```

**After fix:**
```bash
# User clicks "Build Womb"
# Womb build starts
# Progress bar shows 0% → 10% → 20% → ... → 100%
# After 33-45 seconds, womb completes
# UI updates, shows "Womb built!" ✅
```

## Implementation Checklist

- [ ] Add polling to `useGameState.ts` (Option 1 recommended)
- [ ] Test: Build womb, verify progress bar shows
- [ ] Test: Wait for timer to expire, verify completion
- [ ] Test: Polling stops when no active tasks
- [ ] Test: Gather resources (also uses timers)
- [ ] Test: Grow clone (also uses timers)

## Technical Details

**Polling Frequency:** 1 second
- Fast enough for responsive UI
- Not too frequent to overload server
- Backend auto-completes tasks, so polling just fetches updated state

**Why polling instead of WebSocket?**
- Simpler to implement
- Works with existing backend
- Good enough for 1-3 concurrent users
- Can upgrade to WebSocket later if needed

**When polling stops:**
- When `state.active_tasks` is empty
- useEffect cleanup clears interval
- Resumes when new task starts

## Alternative: Manual Refresh

**Temporary workaround** (until Cursor adds polling):

User can manually refresh the page after timer expires:
1. Click "Build Womb"
2. Wait 33-45 seconds
3. Refresh page (F5)
4. Womb will be built ✅

But this is a terrible UX - **polling is required!**

---

## For Claude (Backend Developer)

Backend is working correctly! ✅

The issue is **purely frontend** - they need to poll for task completion.

All backend tests pass:
```bash
./pre-commit-check.sh
→ ✅ Timer mechanics validated
→ ✅ Golden path complete (game is playable)
```

---

## For Cursor (Frontend Developer)

**Priority: URGENT** - Game is unplayable without this fix!

**Quick fix:** Add polling to `useGameState.ts` (see Option 1 above)

**Files to modify:**
- `frontend/src/hooks/useGameState.ts` (add polling useEffect)

**API already available:**
- `gameAPI.getState()` - Returns state with updated active_tasks
- `gameAPI.getTaskStatus()` - Returns task progress (optional)

**Test endpoints:**
```bash
# Backend running on http://localhost:8000
GET /api/game/state  # Returns full state (use this)
GET /api/game/tasks/status  # Returns just task info (alternative)
```

---

## Priority

🔴 **CRITICAL BUG** - Blocks core gameplay

Without this fix:
- Can't build womb (stuck forever)
- Can't gather resources (stuck forever)
- Can't grow clones (stuck forever)
- **Game is completely unplayable!**

**Fix needed ASAP!**
