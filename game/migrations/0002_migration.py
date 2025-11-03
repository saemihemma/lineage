"""
Migration 0002: Convert assembler_built to wombs array
This migration converts the boolean assembler_built field to a wombs array.
If assembler_built was True, creates first womb with max durability/attention.
"""
from core.models import Womb
from core.config import CONFIG


def migrate(state_dict: dict) -> dict:
    """
    Migrate to version 2 (wombs array).
    
    Converts assembler_built boolean to wombs array:
    - If assembler_built was True, creates first womb with max values
    - If assembler_built was False or missing, wombs array is empty
    """
    # Ensure version is at least 2
    state_dict['version'] = 2
    
    # Initialize wombs array if it doesn't exist
    if 'wombs' not in state_dict:
        state_dict['wombs'] = []
    
    # Convert assembler_built to first womb if needed
    # Only migrate if we have assembler_built and no wombs yet
    if state_dict.get('assembler_built', False) and len(state_dict.get('wombs', [])) == 0:
        # Create first womb with max durability (attention is now global, not per-womb)
        max_durability = CONFIG.get("WOMB_MAX_DURABILITY", 100.0)
        
        womb_data = {
            "id": 0,
            "durability": max_durability,
            "max_durability": max_durability
            # Note: attention is now global (stored in global_attention), not per-womb
        }
        state_dict['wombs'] = [womb_data]
    
    # Note: We keep assembler_built field for backward compatibility during transition
    # It will be removed in a future migration if needed
    
    return state_dict

