# Graceful Degradation Notes

## Overview
The frontend implements graceful degradation for new backend endpoints that may not be available immediately. This allows the game to function normally even if Claude hasn't implemented the backend endpoints yet.

## Current Graceful Degradation

### 1. `/api/game/events/feed` (B3 - Live State Sync)
**Location**: `frontend/src/api/events.ts`, `frontend/src/hooks/useEventFeed.ts`

**Behavior**: 
- Returns empty array `[]` on 404
- Silently pauses polling and retries after 30 seconds
- No user-facing errors or broken UI

**Why it's good**: 
- ✅ **Keep this long-term** - Events feed is optional enhancement (live sync vs polling full state)
- If backend is temporarily down, frontend falls back to existing polling mechanism
- No impact on core gameplay

**When to remove**: Never - this is a good fallback pattern

### 2. `/api/game/limits/status` (B1 - Fuel Bar)
**Location**: `frontend/src/api/limits.ts`, `frontend/src/components/FuelBar.tsx`

**Behavior**:
- Returns `null` on 404
- Fuel bar component doesn't render (returns `null`)
- No user-facing errors

**Why it's good**:
- ✅ **Keep this long-term** - Fuel bar is a gamification feature, not core gameplay
- If rate limiting isn't implemented or endpoint is down, game continues normally
- Users can still play without fuel visualization

**When to remove**: Never - fuel bar is optional enhancement

## Recommendation

**Keep graceful degradation permanently** because:
1. Better UX - game never breaks due to missing optional features
2. Resilience - handles temporary backend outages gracefully
3. Progressive enhancement - core features work, enhancements add value when available
4. Development flexibility - can deploy frontend/backend independently

## Removing Graceful Degradation (If Needed)

If you ever want to make endpoints required (remove graceful degradation):

1. **Events Feed**: Change `frontend/src/api/events.ts` to throw error on 404
2. **Fuel Bar**: Change `frontend/src/api/limits.ts` to throw error on 404

**But don't do this** - graceful degradation is a best practice for optional features.

## Status

- ✅ Events feed gracefully degrades
- ✅ Fuel bar gracefully degrades
- ✅ No impact on core gameplay if endpoints missing
- ✅ All error handling tested and working

Last updated: After B1-B5 implementation

