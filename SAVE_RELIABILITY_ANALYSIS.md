# Save Reliability Analysis

## Current Save Mechanisms

### Desktop Version (`core/state_manager.py`)

**How it works:**
- Saves to local JSON file: `frontier_save.json`
- Direct file write using `json.dump()`
- No error handling wrapper
- No backup mechanism

**Reliability Issues:**
1. ❌ **No atomic writes** - Direct write can leave corrupted file if interrupted
2. ❌ **No error handling** - Exceptions bubble up, no retry logic
3. ❌ **No backup** - Single file, if corrupted = total data loss
4. ❌ **No transaction safety** - Write happens immediately, no rollback
5. ❌ **Race conditions** - If multiple processes run, file corruption possible

**What CAN go wrong:**
- Process crash mid-write → corrupted JSON file → data loss
- Disk full → write fails → exception → no saved state
- Permission errors → silent failure → no saved state
- Concurrent writes → file corruption

---

### Web Version (Backend + Frontend)

**How it works:**
- Backend: SQLite database with `game_states` table
- Frontend: Auto-saves after every state update
- Session-based via HTTP-only cookies
- Version tracking for optimistic locking (infrastructure exists, not enabled)

**Backend Reliability (`backend/routers/game.py`):**
1. ✅ **Database commits** - SQLite ACID properties
2. ✅ **ON CONFLICT handling** - Uses `ON CONFLICT DO UPDATE`
3. ⚠️ **No optimistic locking** - `check_version=False` by default on save endpoint
4. ⚠️ **No transaction rollback** - If error after state change, partial save possible
5. ⚠️ **SQLite limitations** - Single writer, can timeout under heavy load

**Frontend Reliability (`frontend/src/hooks/useGameState.ts`):**
1. ❌ **Silent auto-save failures** - Line 46-48: errors caught but not surfaced to user
2. ❌ **State updated before save** - Line 44: `setState(newState)` happens before save completes
3. ❌ **No retry logic** - Network failures = lost progress
4. ❌ **No queuing** - Rapid actions can trigger multiple concurrent saves
5. ❌ **No conflict resolution** - Multiple tabs can overwrite each other

**What CAN go wrong:**
- Network interruption during save → frontend shows saved, backend doesn't
- Multiple tabs → last save wins, others lose progress
- Backend error after state change → partial/corrupted state saved
- Rate limiting → save rejected → user doesn't know
- Session cookie lost → can't load save (24hr expiry)

---

## Risk Assessment

### High Risk Scenarios:

1. **Desktop: Process crash mid-write**
   - Probability: Medium
   - Impact: High (total data loss)
   - Current protection: None

2. **Web: Network failure during save**
   - Probability: High (especially mobile/spotty connections)
   - Impact: Medium (user thinks saved, actually lost)
   - Current protection: None (silent failure)

3. **Web: Multiple tabs**
   - Probability: Medium (users open multiple tabs)
   - Impact: High (conflicting saves overwrite progress)
   - Current protection: None (optimistic locking exists but disabled)

4. **Both: Disk/database full**
   - Probability: Low
   - Impact: High (can't save, progress lost)
   - Current protection: Error thrown, but no recovery

---

## Recommendations for "Bulletproof" Saving

### Priority 1: Critical Fixes (Do First)

#### Desktop:
1. **Atomic file writes**
   ```python
   # Write to temp file, then rename (atomic on most OS)
   temp_file = SAVE_FILE + ".tmp"
   with open(temp_file, "w") as f:
       json.dump(data, f)
   os.replace(temp_file, SAVE_FILE)  # Atomic rename
   ```

2. **Error handling with retry**
   ```python
   def save_state(p, retries=3):
       for attempt in range(retries):
           try:
               # ... save logic ...
               return
           except (IOError, OSError) as e:
               if attempt == retries - 1:
                   raise
               time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
   ```

3. **Backup before overwrite**
   ```python
   if os.path.exists(SAVE_FILE):
       backup_file = f"{SAVE_FILE}.backup"
       shutil.copy2(SAVE_FILE, backup_file)
   # ... then save ...
   ```

#### Web Frontend:
1. **Explicit save confirmation**
   - Show save status indicator
   - Retry on failure with user notification
   - Queue saves to prevent concurrent writes

2. **Optimistic updates with rollback**
   - Update UI optimistically
   - If save fails, revert to previous state
   - Show error to user

3. **Enable optimistic locking**
   - Set `check_version=True` on save endpoint
   - Handle version conflicts gracefully
   - Show "please refresh" message on conflict

### Priority 2: Enhancements

1. **Save queue** - Queue saves, process sequentially
2. **Periodic auto-save** - Every 30 seconds, not just on actions
3. **Save on page unload** - `beforeunload` event
4. **LocalStorage backup** - Store state in browser as backup
5. **Save history** - Keep last N saves for recovery

### Priority 3: Advanced

1. **Database transactions** - Wrap saves in transactions with rollback
2. **Write-ahead logging** - For SQLite performance
3. **Backend save queue** - Handle concurrent saves server-side
4. **Database backups** - Automated backups on Railway
5. **Conflict resolution UI** - Show diff and let user choose

---

## Current Status: **NOT Bulletproof** ⚠️

**Desktop:** Medium risk (file corruption possible)
**Web:** Medium-High risk (silent failures, no conflict handling)

---

## Quick Fixes (Can implement now)

1. **Desktop atomic writes** - 15 minutes
2. **Frontend save status indicator** - 30 minutes  
3. **Enable optimistic locking on save** - 10 minutes
4. **Error notification on save failure** - 20 minutes
5. **Save queue to prevent concurrent saves** - 30 minutes

**Total time: ~2 hours for significant improvement**

