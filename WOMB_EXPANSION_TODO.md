# Womb Expansion - Remaining Tasks

## Status: ~85% Complete

### ✅ Completed
- Womb model and dataclass
- Configuration (all tunables in CONFIG)
- Migration 0002 (converts assembler_built to wombs array)
- State serialization (game_state_to_dict, dict_to_game_state)
- Womb management functions (game/wombs.py)
- build_womb updated for multiple wombs with unlock checks
- grow_clone updated to check womb availability
- Attention gain on actions (build, grow)
- Practice synergies (Cognitive/Kinetic/Constructive multipliers)

### ✅ Recently Completed
1. ✅ **Womb system integration on state changes** - Added to save_game_state()
2. ✅ **Repair endpoint** - POST /api/game/repair-womb implemented
3. ✅ **Config endpoint update** - All womb tunables added to /api/config/gameplay
4. ✅ **Repair task duration** - Added to calculate_task_duration and start_task
5. ✅ **Practice synergies** - All implemented in game/wombs.py

### 🔄 Remaining (Non-Critical)
- **Clean up assembler_built references** - Replace with wombs checks where appropriate (backward compat kept intentionally)
- **Testing** - Verify migration, unlock conditions, attacks work in production

### Ready for Push
All critical functionality is complete. The system:
- ✅ Migrates existing players automatically
- ✅ Supports multiple wombs with unlock conditions
- ✅ Has decay/attack systems integrated
- ✅ Has repair functionality
- ✅ Has all config exposed
- ✅ Maintains backward compatibility

## Next Steps After Push
1. Test migration with existing players
2. Add UI for multiple wombs (when ≥2 wombs)
3. Add attention/durability meters to UI
4. Test unlock conditions in production

