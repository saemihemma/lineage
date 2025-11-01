"""Data loader for JSON configuration files"""
import json
from pathlib import Path
from typing import Dict, Any, Optional


# Get data directory
DATA_DIR = Path(__file__).parent


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


def load_data() -> Dict[str, Any]:
    """
    Load all game data from JSON files.
    
    Returns a dictionary with keys:
    - clones: Clone type definitions
    - resources: Resource gathering data
    - expeditions: Expedition rewards and probabilities
    - phrases: Text content (loading messages, etc.)
    
    Falls back to empty dicts if files are missing.
    """
    data = {
        "clones": load_json_file("clones.json") or {},
        "resources": load_json_file("resources.json") or {},
        "expeditions": load_json_file("expeditions.json") or {},
        "loading_text": load_json_file("loading_text.json") or {},
        "briefing_text": load_json_file("briefing_text.json") or {},
        "phrases": load_json_file("phrases.json") or {}
    }
    
    return data

