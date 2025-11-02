# Backend Integration Guide for Claude

## Overview
This document outlines the backend endpoints and data structures needed to complete the frontend features (B1-B8). The frontend is already implemented with graceful degradation, so the game works even if these endpoints aren't ready yet.

---

## Required Backend Endpoints

### 1. `/api/game/events/feed` (B3 - Live State Sync)

**Purpose**: Incremental event stream for live state updates without full state reloads.

**Endpoint**: `GET /api/game/events/feed?after=<timestamp>`

**Request Headers**:
- `If-None-Match: <etag>` (optional, for efficient polling)

**Response**:
- **200 OK**: `GameEvent[]` - Array of events since timestamp
- **304 Not Modified**: No new events (if ETag matches)
- **404 Not Found**: Endpoint not implemented (frontend gracefully degrades)

**Event Format**:
```typescript
interface GameEvent {
  id: string;              // Unique event ID (for deduplication)
  type: EventType;          // Event type (see below)
  timestamp: number;        // Unix timestamp
  data: EventData;          // Event-specific data
}

type EventType =
  | 'gather.start'
  | 'gather.complete'
  | 'clone.grow.start'
  | 'clone.grow.complete'
  | 'expedition.start'
  | 'expedition.result'
  | 'upload.complete'
  | 'resource.delta'
  | 'error.network'
  | 'error.game';

interface EventData {
  // Resource delta events
  resource?: string;
  delta?: number;
  new_total?: number;
  
  // Expedition events
  kind?: string;              // "MINING" | "COMBAT" | "EXPLORATION"
  loot?: Record<string, number>;
  clone_xp?: Record<string, number>;
  clone_id?: string;
  
  // Clone grow events
  clone?: CloneObject;
  
  // Upload events
  soul_percent_delta?: number;
  soul_xp_delta?: number;
  
  // Error events
  message?: string;
  error_type?: string;
}
```

**Implementation Notes**:
- Track events per session_id in a time-ordered buffer
- Support `after` parameter to return events since timestamp
- Implement ETag support for efficient polling (304 responses)
- Clear old events periodically (keep last N events per session)
- Emit events when:
  - `gather_resource` starts/completes → `gather.start`, `gather.complete`, `resource.delta`
  - `grow_clone` starts/completes → `clone.grow.start`, `clone.grow.complete`
  - `run_expedition` starts/completes → `expedition.start`, `expedition.result`
  - `upload_clone` completes → `upload.complete`

**Frontend Integration**:
- Frontend polls every 1.2 seconds
- Uses ETag/If-None-Match headers
- Applies incremental state patches on events
- Falls back to full state polling if endpoint returns 404

---

### 2. `/api/game/limits/status` (B1 - Fuel Bar)

**Purpose**: Rate limit status for fuel bar gamification.

**Endpoint**: `GET /api/game/limits/status`

**Response**:
- **200 OK**: `LimitsStatus` object
- **404 Not Found**: Endpoint not implemented (frontend gracefully degrades, hides fuel bar)

**Response Format**:
```typescript
interface LimitsStatus {
  window_seconds: number;     // Rate limit window duration (e.g., 60)
  now: number;                // Current Unix timestamp
  endpoints: {
    [key: string]: EndpointLimit;
    combined: EndpointLimit;   // Combined limit across all action endpoints
  };
}

interface EndpointLimit {
  remaining: number;          // Remaining actions in current window
  reset_at: number;           // Unix timestamp when limit resets
}
```

**Expected Endpoints in Response**:
- `/gather/start` - Gather resource actions
- `/clone/grow` - Grow clone actions
- `/expedition/start` - Expedition actions
- `/upload` - Upload clone actions
- `combined` - Sum of all action endpoints

**Implementation Notes**:
- Use existing rate limiting system (slowapi) to track remaining counts
- Calculate `combined` as sum of all action endpoint remaining counts
- Track reset times per endpoint based on window start time
- Return current timestamp (`now`) for frontend countdown calculations

**Frontend Integration**:
- Frontend polls every 2.5 seconds
- Displays fuel bar with color coding (green/yellow/red)
- Shows time until refuel when depleted
- Silently hides if endpoint returns 404

---

## Optional Backend Enhancements

### 3. `ftue` Object in GameState (B8 - Onboarding)

**Purpose**: Server-side tracking of onboarding completion for persistence across sessions.

**Field to Add to `GameState`**:
```python
ftue: Dict[str, bool] = {
    "step_gather_10_tritanium": False,
    "step_build_womb": False,
    "step_grow_clone": False,
    "step_first_expedition": False,
    "step_upload_clone": False,
}
```

**Detection Logic** (to implement in game action handlers):
- `step_gather_10_tritanium`: Check `resources.get("Tritanium", 0) >= 10` after gather completes
- `step_build_womb`: Set when `build_womb` task completes
- `step_grow_clone`: Set when `grow_clone` task completes
- `step_first_expedition`: Set after first expedition result (any clone has expedition XP)
- `step_upload_clone`: Set when `upload_clone` completes

**Frontend Integration**:
- Frontend already works client-side (checks state directly)
- Server-side `ftue` flags provide persistence across sessions
- If `ftue` object missing, frontend gracefully falls back to client-side checks

**Note**: This is optional - onboarding checklist works without it, but server-side flags provide better persistence.

---

## Data Structure Changes

### GameState Schema Updates

**Frontend expects these fields** (all optional, with graceful degradation):
```typescript
interface GameState {
  // ... existing fields ...
  ftue?: {
    step_gather_10_tritanium?: boolean;
    step_build_womb?: boolean;
    step_grow_clone?: boolean;
    step_first_expedition?: boolean;
    step_upload_clone?: boolean;
  };
}
```

**Backend should support**:
- Adding `ftue` to `GameState` dataclass (optional field)
- Serialization/deserialization in `game_state_to_dict` / `dict_to_game_state`
- Migration logic to initialize empty `ftue` for existing saves

---

## Integration Testing Checklist

Once backend endpoints are implemented:

1. **Events Feed** (`/api/game/events/feed`):
   - [ ] Test `gather.start` event on gather action start
   - [ ] Test `gather.complete` + `resource.delta` on gather completion
   - [ ] Test `clone.grow.start` on grow action start
   - [ ] Test `clone.grow.complete` on grow completion
   - [ ] Test `expedition.start` on expedition start
   - [ ] Test `expedition.result` with loot/clone_xp on completion
   - [ ] Test `upload.complete` with soul_percent_delta on upload
   - [ ] Test ETag support (304 responses)
   - [ ] Test `after` parameter filtering
   - [ ] Verify frontend applies incremental patches correctly

2. **Limits Status** (`/api/game/limits/status`):
   - [ ] Test rate limit tracking per endpoint
   - [ ] Test `combined` calculation (sum of all endpoints)
   - [ ] Test `reset_at` timestamp accuracy
   - [ ] Test window reset behavior
   - [ ] Verify frontend fuel bar displays correctly
   - [ ] Verify fuel bar hides gracefully on 404

3. **FTUE Flags** (optional):
   - [ ] Test `ftue` object creation on new game state
   - [ ] Test detection logic for each step
   - [ ] Test persistence across sessions
   - [ ] Verify frontend reads flags correctly

---

## Frontend Graceful Degradation

**Important**: The frontend is designed to work even if backend endpoints are missing:

1. **Events Feed**: Returns empty array `[]` on 404, silently degrades
2. **Limits Status**: Returns `null` on 404, fuel bar doesn't render
3. **FTUE Flags**: Checks client-side state if `ftue` object missing

**No breaking changes** - game continues to work normally without these features.

---

## Quick Reference: Endpoint Contracts

### Events Feed
```
GET /api/game/events/feed?after=1730544000
Headers: If-None-Match: "etag-value"
Response: GameEvent[]
```

### Limits Status
```
GET /api/game/limits/status
Response: LimitsStatus
```

### FTUE (implicit in GameState)
```
POST /api/game/state
Request body includes: { ..., "ftue": {...} }
```

---

## Questions for Implementation

1. **Event Storage**: How should events be stored? In-memory per session? Database? Time-to-live?
2. **Rate Limiting**: Is the existing slowapi rate limiting system sufficient, or need custom tracking?
3. **ETag Generation**: How should ETags be generated for events feed? Hash of event list? Version number?

---

Last updated: After B1-B8 frontend implementation

