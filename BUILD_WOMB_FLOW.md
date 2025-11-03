# Build Womb Flow - localStorage Implementation

## Current Implementation Status

### ✅ How It Works Now:

1. **User clicks "Build Womb"**
   - `SimulationScreen.handleBuildWomb()` → `handleAction(() => gameAPI.buildWomb(), 'build womb')`

2. **Frontend sends request to backend**
   - Sends current state from localStorage in request body
   - Backend validates resources, creates task, returns updated state with task in `active_tasks`

3. **Frontend receives response**
   - Merges new task into existing `active_tasks`
   - Calls `updateState(mergedState)` which:
     - Updates React state
     - **Saves to localStorage immediately** ✅

4. **Progress bar shows**
   - Calculated from `active_tasks[taskId].start_time` + `duration` vs current time
   - Updates every second showing remaining time

5. **Task completion (every 1 second check)**
   - `useGameState` hook runs `checkAndCompleteTasks(state)` every 1 second
   - When `current_time >= start_time + duration`:
     - Creates womb object in state
     - Adds to `state.wombs` array
     - Removes task from `active_tasks`
     - Sets `assembler_built = true` (if first womb)
     - **Saves to localStorage** ✅
     - Stores completion message

6. **Completion message displayed**
   - Message appears in terminal
   - Progress bar disappears
   - Womb is now available

### ✅ localStorage Saves Happen:
- ✅ Immediately after backend response (`updateState`)
- ✅ When task completes (`checkAndCompleteTasks` → `saveStateToLocalStorage`)
- ✅ Every time state changes (`updateState` callback)

### Potential Issues to Check:

1. **Timing issue**: Make sure `start_time` and `duration` are correctly set by backend
2. **State persistence**: Verify womb is in localStorage after completion
3. **Progress calculation**: Ensure progress bar uses correct timestamps

## Testing Checklist:

- [ ] Press "Build Womb" - does it create a task?
- [ ] Does progress bar show and update?
- [ ] After timer completes, is womb created?
- [ ] Is womb saved in localStorage? (Check browser DevTools → Application → Local Storage)
- [ ] Does womb persist after page refresh?

## Debugging Commands:

```javascript
// In browser console:
localStorage.getItem('lineage_game_state')
// Parse and check:
JSON.parse(localStorage.getItem('lineage_game_state')).wombs
// Check active tasks:
JSON.parse(localStorage.getItem('lineage_game_state')).active_tasks
```

