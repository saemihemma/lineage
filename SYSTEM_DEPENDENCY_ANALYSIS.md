# System Dependency Analysis

## Overview
Analysis of dependencies between gathering, wombs, feral attacks, attention, durability, and task completion systems.

---

## ✅ VERIFIED DEPENDENCIES (Properly Handled)

### 1. Womb Availability Checks
- ✅ **grow_clone**: Checks `check_womb_available()` AND `is_functional()` before allowing clone growth
- ✅ **build_womb**: Checks unlock conditions before allowing new womb construction
- ✅ **repair_womb**: Checks womb exists and can be repaired

### 2. Resource Validation
- ✅ All actions check `can_afford()` before deducting resources
- ✅ Soul percent checked before clone growth
- ✅ Resources validated before build/repair actions

### 3. Womb System Integration
- ✅ `check_and_apply_womb_systems()` called after ALL state-changing actions:
  - gather_resource_endpoint
  - build_womb_endpoint
  - grow_clone_endpoint
  - run_expedition_endpoint
  - upload_clone_endpoint
  - repair_womb_endpoint
- ✅ Attention decay and attacks applied consistently

### 4. Attention Gain
- ✅ Attention gained on: build_womb, grow_clone, run_expedition
- ✅ Attention decays over time based on `last_saved_ts`

### 5. Attack System
- ✅ Attacks only happen if functional wombs exist
- ✅ Attacks reduce attention after occurrence
- ✅ Attack probability scales with global attention (0% = 0% chance, 100% = 25% chance)

---

## ⚠️ MISSING DEPENDENCIES (We Assume But Don't Verify)

### 1. **Gathering Resources - No Womb Requirement**
**Issue**: `gather_resource()` and `gather_resource_endpoint()` do NOT check if wombs exist or are functional.

**Current Behavior**: Players can gather resources even with:
- No wombs built
- All wombs destroyed (durability = 0)

**Questions**:
- Is this intentional (drones can gather without wombs)?
- Should gathering require at least one functional womb?
- Should gathering be disabled if all wombs destroyed?

**Location**: `game/rules.py:332`, `backend/routers/game.py:1079`

### 2. **Gathering Resources - No Attention Gain**
**Issue**: Gathering resources does NOT trigger `gain_attention()`, unlike build/grow/expeditions.

**Impact**: Gathering is a state-changing action but doesn't increase global attention, meaning:
- Players can gather forever without increasing attention
- This might be intentional (passive gathering vs active actions)

**Location**: `game/rules.py:332` (no attention gain), compare to `game/rules.py:53-56` (build_womb has attention gain)

### 3. **Task Completion - No Womb Re-Check**
**Issue**: When tasks complete (`check_and_complete_tasks`), we don't verify womb state after attacks that may have occurred during task duration.

**Scenario**:
1. Player starts gathering (womb exists, functional)
2. During gathering, feral attack destroys all wombs
3. Gathering completes successfully (resources added)
4. BUT: If gathering required womb, we should have cancelled it

**Impact**: Tasks complete even if preconditions (like womb availability) are no longer met.

**Location**: `backend/routers/game.py:337` (`check_and_complete_tasks`)

### 4. **Clone Growth Task Completion - No Womb Validation**
**Issue**: When `grow_clone` task completes, we don't re-check if womb is still functional.

**Scenario**:
1. Player starts growing clone (womb functional)
2. During growth, attack destroys womb
3. Clone still grows successfully despite womb being destroyed

**Current**: Clone growth completes regardless of womb state at completion time.

**Location**: `backend/routers/game.py:437` (grow_clone completion handler)

### 5. **Repair Task - Womb May Not Exist At Completion**
**Issue**: When repair task completes, we don't verify the womb still exists.

**Scenario**:
1. Player starts repairing womb 0
2. Player builds/gets new womb 0 (duplicate ID? unlikely but possible)
3. Repair completes on wrong womb

**Location**: `backend/routers/game.py:426` (repair_womb completion handler)

### 6. **All Wombs Destroyed - What Can Player Do?**
**Issue**: If all wombs have durability = 0:
- ✅ Cannot grow clones (blocked by `check_womb_available()`)
- ❓ Can still gather resources? (NO CHECK)
- ❓ Can still run expeditions? (NO CHECK - expeditions don't require womb)
- ✅ Can still repair wombs (if they have resources)

**Question**: Should gathering/expeditions be disabled if no functional wombs?

---

## 🔄 ORDER OF OPERATIONS ISSUES

### 1. **Womb Systems Applied AFTER Task Start, Not After Task Completion**
**Current Flow**:
```
gather_resource_endpoint():
  1. Start task (creates task with pending_amount)
  2. Apply womb systems (decay, attacks) ← Happens IMMEDIATELY
  3. Return state (resources NOT added yet)
  
  [Time passes...]
  
check_and_complete_tasks():
  4. Add resources when task completes
  5. NO womb system check here ← MISSING
```

**Issue**: 
- Attacks happen when task STARTS, not when it completes
- If attack destroys womb during gathering, gathering still completes
- No validation that womb requirements are still met at completion

**Better Flow**:
- Apply womb systems both when task starts AND when it completes
- Validate prerequisites at completion time

### 2. **Attention Gain Timing**
**Current**: Attention gained immediately when action is taken:
- `build_womb`: Gains attention on existing wombs (if any)
- `grow_clone`: Gains attention after clone is grown
- `run_expedition`: Gains attention after expedition completes

**Question**: Should attention gain happen:
- When action STARTS (current for build/grow)?
- When action COMPLETES (would make more sense for timed actions)?
- Both?

### 3. **Repair Task - Womb Systems Not Applied After Repair**
**Issue**: When repair task completes, we restore durability but don't apply womb systems.

**Current Flow**:
```
repair_womb_endpoint():
  1. Start repair task
  2. Apply womb systems (decay, attacks) ← Happens when repair STARTS
  
  [Time passes...]
  
check_and_complete_tasks():
  3. Restore durability to full
  4. NO womb system check ← MISSING
```

**Impact**: 
- If attack happens during repair, durability restored anyway
- No attention decay/attack check after repair completes

---

## 🔴 EDGE CASES & RACE CONDITIONS

### 1. **Multiple Attacks During Long Tasks**
**Scenario**: Long gather/grow task (60+ seconds), high attention (25% attack chance)
- Attack 1: Destroys womb 0 (durability → 0)
- Attack 2: Can't attack (no functional wombs)
- Task completes: Resources/clone added despite no functional womb

**Current**: No validation that preconditions are still met.

### 2. **All Wombs Destroyed Mid-Task**
**Scenario**: Player has 2 wombs, starts gathering:
- Attack during gathering destroys both wombs
- Gathering completes successfully
- Player can't grow clones (no functional wombs) ✅ Correct
- Player can still gather more ❓ Intended?

### 3. **Womb Destroyed While Clone Growing**
**Scenario**: Clone growth task in progress, womb destroyed by attack
- Current: Clone still grows (no validation at completion)
- Should: Cancel clone growth? Or allow it?

### 4. **Attention Maxes Out During Action**
**Scenario**: Attention at 95%, player starts gathering:
- Gathering starts: Attention at 95%
- Gathering completes: Attention could be 100% (from other actions)
- Attack probability changes mid-task

**Current**: This is fine (attention is global, not locked per-task)

### 5. **Repair Cost Changes During Repair**
**Scenario**: Player starts repairing womb, but resources consumed by other actions
- Current: Repair still completes (cost already deducted at start)
- Impact: Could repair without having resources at completion time

**Location**: `backend/routers/game.py:1690` - resources already deducted when repair starts

---

## 🎯 RECOMMENDATIONS

### High Priority

1. **Add Womb Validation at Task Completion**
   - In `check_and_complete_tasks()`, re-validate womb availability for:
     - `grow_clone` task completion (should cancel if no functional womb)
     - `gather_resource` task completion (if gathering requires womb)

2. **Apply Womb Systems After Task Completion**
   - Call `check_and_apply_womb_systems()` after tasks complete in `check_and_complete_tasks()`
   - Ensures attacks can happen when tasks finish (not just when they start)

3. **Decide: Does Gathering Require Womb?**
   - If YES: Add `check_womb_available()` check in `gather_resource_endpoint`
   - If NO: Document this intentional design decision

### Medium Priority

4. **Add Attention Gain on Gathering**
   - If gathering is considered an "action", add attention gain
   - If gathering is "passive", document why it doesn't gain attention

5. **Validate Womb Exists at Repair Completion**
   - Check womb still exists when repair task completes
   - Handle case where womb might have been deleted (shouldn't happen, but defensive)

6. **Handle All-Wombs-Destroyed State**
   - Document/implement recovery path:
     - Can player still gather? (to get resources for repair)
     - Can player repair with zero-durability wombs?
     - Add UI warning when all wombs destroyed

### Low Priority

7. **Consider Attention Gain Timing**
   - Review if attention should gain when action starts vs completes
   - Current mix might be intentional (immediate actions vs timed actions)

8. **Add Logging for Edge Cases**
   - Log when tasks complete despite missing prerequisites
   - Log when attacks destroy wombs during active tasks

---

## 📊 DEPENDENCY MATRIX

| Action | Requires Womb? | Gains Attention? | Triggers Attack? | Validates at Completion? |
|--------|---------------|------------------|-----------------|--------------------------|
| gather_resource | ❌ NO CHECK | ❌ NO | ✅ YES (at start) | ❌ NO |
| build_womb | ❌ NO (creates it) | ✅ YES | ✅ YES (at start) | N/A (creates womb) |
| grow_clone | ✅ YES | ✅ YES | ✅ YES (at start) | ❌ NO |
| run_expedition | ❌ NO CHECK | ✅ YES | ✅ YES (after) | N/A (immediate) |
| upload_clone | ❌ NO CHECK | ❌ NO | ✅ YES (after) | N/A (immediate) |
| repair_womb | ✅ YES (target) | ❌ NO | ✅ YES (at start) | ⚠️ PARTIAL (checks exists) |

---

## 🧪 TESTING GAPS

### Missing Test Cases:
1. Gather resource when all wombs destroyed → Should it work?
2. Grow clone task completes after womb destroyed → Should clone still grow?
3. Attack during long gather task destroys womb → Does gathering complete?
4. Multiple attacks in sequence → Do attacks stop when no functional wombs?
5. Repair task: womb deleted (edge case) → Handle gracefully?
6. All wombs destroyed → What actions are still available?

---

## 💡 DESIGN DECISIONS NEEDED

1. **Should gathering require functional womb?**
   - Current: NO
   - Recommendation: YES (for consistency, drones need wombs to operate)

2. **Should gathering gain attention?**
   - Current: NO
   - Recommendation: YES (it's a player action that could attract attention)

3. **Should tasks cancel if prerequisites fail?**
   - Current: NO (tasks complete regardless)
   - Recommendation: YES for critical tasks (grow_clone), NO for non-critical (gather)

4. **Should womb systems apply at task completion?**
   - Current: NO (only at task start)
   - Recommendation: YES (allows attacks during task duration)

5. **What happens when all wombs destroyed?**
   - Current: Can't grow clones (correct), can gather (questionable)
   - Recommendation: Document recovery path clearly

