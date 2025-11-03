"""
Migration 0003: Add global_attention field and remove per-womb attention
This migration:
- Adds global_attention field (initialized to 0.0)
- Removes attention and max_attention from wombs (they are no longer per-womb)
"""
from core.config import CONFIG


def migrate(state_dict: dict) -> dict:
    """
    Migrate to version 3 (global attention system).
    
    Changes:
    - Add global_attention field (starts at 0.0)
    - Remove attention and max_attention from womb objects (attention is now global)
    """
    # Ensure version is at least 3
    state_dict['version'] = 3
    
    # Initialize global_attention if it doesn't exist
    if 'global_attention' not in state_dict:
        state_dict['global_attention'] = CONFIG.get("WOMB_GLOBAL_ATTENTION_INITIAL", 0.0)
    
    # Remove attention and max_attention from wombs (they are now global)
    if 'wombs' in state_dict:
        for womb in state_dict['wombs']:
            # Remove old attention fields if they exist
            womb.pop('attention', None)
            womb.pop('max_attention', None)
    
    return state_dict

