"""
Migration 0001: Initial schema version
This migration represents the baseline schema (version 1).
Old saves without a version field will be migrated to this version.
"""


def migrate(state_dict: dict) -> dict:
    """
    Migrate to version 1 (initial schema).
    
    This migration adds the version field if missing and ensures
    all required fields exist with defaults.
    """
    # If version field doesn't exist, this is a pre-versioned save
    if 'version' not in state_dict:
        state_dict['version'] = 1
    
    # Ensure all required fields exist with defaults
    if 'soul_percent' not in state_dict:
        state_dict['soul_percent'] = 100.0
    
    if 'soul_xp' not in state_dict:
        state_dict['soul_xp'] = 0
    
    if 'assembler_built' not in state_dict:
        state_dict['assembler_built'] = False
    
    if 'resources' not in state_dict:
        state_dict['resources'] = {
            "Tritanium": 60,
            "Metal Ore": 40,
            "Biomass": 8,
            "Synthetic": 8,
            "Organic": 8,
            "Shilajit": 0
        }
    
    if 'clones' not in state_dict:
        state_dict['clones'] = {}
    
    if 'applied_clone_id' not in state_dict:
        state_dict['applied_clone_id'] = ""
    
    if 'practices_xp' not in state_dict:
        state_dict['practices_xp'] = {
            "Kinetic": 0,
            "Cognitive": 0,
            "Constructive": 0
        }
    
    if 'last_saved_ts' not in state_dict:
        import time
        state_dict['last_saved_ts'] = time.time()
    
    if 'self_name' not in state_dict:
        state_dict['self_name'] = ""
    
    # Add rng_seed if missing (None means it will be generated on first use)
    if 'rng_seed' not in state_dict:
        state_dict['rng_seed'] = None
    
    # Add active_tasks if missing (for scheduler persistence)
    if 'active_tasks' not in state_dict:
        state_dict['active_tasks'] = {}
    
    # Add ui_layout if missing (for UI layout persistence)
    if 'ui_layout' not in state_dict:
        state_dict['ui_layout'] = {}
    
    return state_dict

