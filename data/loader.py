"""Data loader for JSON configuration files"""
import json
from pathlib import Path
from typing import Dict, Any, Optional


# Get data directory
DATA_DIR = Path(__file__).parent
# Get config directory (parent of data directory, then config)
CONFIG_DIR = DATA_DIR.parent / "config"

# Railway-specific: if running from /app/backend/, config is at /app/config/
if not CONFIG_DIR.exists():
    # Try absolute path for Railway deployment
    if Path("/app/config").exists():
        CONFIG_DIR = Path("/app/config")
    else:
        # Fallback: try from project root
        project_root = Path(__file__).parent.parent
        CONFIG_DIR = project_root / "config"


def load_json_file(filename: str) -> Optional[Dict[str, Any]]:
    """Load a JSON file from the data directory"""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return None


def load_config_file(filename: str) -> Optional[Dict[str, Any]]:
    """Load a JSON file from the config directory"""
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        # Try alternative paths for deployment environments
        alt_paths = [
            Path(__file__).parent.parent / "config" / filename,  # From data/ parent
            Path.cwd().parent / "config" / filename,  # From current working directory
            Path("/app/config") / filename,  # Railway deployment path
        ]
        for alt_path in alt_paths:
            if alt_path.exists():
                filepath = alt_path
                break
        else:
            # File not found in any location
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Config file {filename} not found in {CONFIG_DIR} or alternative paths")
            return None
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading config {filename} from {filepath}: {e}")
        return None


def load_data() -> Dict[str, Any]:
    """
    Load all game data from JSON files.
    
    Returns a dictionary with keys:
    - clones: Clone type definitions
    - resources: Resource gathering data
    - expeditions: Expedition rewards and probabilities
    - phrases: Text content (loading messages, etc.)
    - gameplay: Gameplay configuration (traits, etc.) from config directory
    
    Falls back to empty dicts if files are missing.
    """
    data = {
        "clones": load_json_file("clones.json") or {},
        "resources": load_json_file("resources.json") or {},
        "expeditions": load_json_file("expeditions.json") or {},
        "loading_text": load_json_file("loading_text.json") or {},
        "briefing_text": load_json_file("briefing_text.json") or {},
        "phrases": load_json_file("phrases.json") or {},
        "womb_config": load_json_file("womb_config.json") or {},
        "feral_drone_messages": load_json_file("feral_drone_messages.json") or {},
        "clone_crafted_messages": load_json_file("clone_crafted_messages.json") or {},
        "resource_gathering_messages": load_json_file("resource_gathering_messages.json") or {},
        "mining_expedition_success_messages": load_json_file("mining_expedition_success_messages.json") or {},
        "mining_expedition_fail_messages": load_json_file("mining_expedition_fail_messages.json") or {},
        "combat_expedition_success_messages": load_json_file("combat_expedition_success_messages.json") or {},
        "combat_expedition_fail_messages": load_json_file("combat_expedition_fail_messages.json") or {},
        "exploration_expedition_success_messages": load_json_file("exploration_expedition_success_messages.json") or {},
        "exploration_expedition_fail_messages": load_json_file("exploration_expedition_fail_messages.json") or {},
        "upload_to_self_messages": load_json_file("upload_to_self_messages.json") or {},
        "level_up_messages": load_json_file("level_up_messages.json") or {},
        "outcomes_config": load_json_file("outcomes_config.json") or {},
        "gameplay": load_config_file("gameplay.json") or {}
    }
    
    return data

