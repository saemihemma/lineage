"""Game configuration constants"""
import json
from pathlib import Path
from data.loader import load_data

# Resource types (order matters for UI display)
RESOURCE_TYPES = ["Tritanium", "Metal Ore", "Biomass", "Synthetic", "Organic", "Shilajit"]

# Load data from JSON files (with fallback to hardcoded CONFIG)
_loaded_data = load_data()

# Build CONFIG dict with data from JSON files (fallback to defaults)
_clones_data = _loaded_data.get("clones", {})
_resources_data = _loaded_data.get("resources", {})
_expeditions_data = _loaded_data.get("expeditions", {})

# Extract clone costs and times from JSON
_clone_costs = {}
_clone_times = {}
for clone_code, clone_info in _clones_data.get("clone_types", {}).items():
    _clone_costs[clone_code] = clone_info.get("costs", {})
    time_range = clone_info.get("time_range", [30, 45])
    _clone_times[clone_code] = tuple(time_range)

# Extract gather times and amounts from JSON
_gather_times = {}
_gather_amounts = {}
for resource, time_range in _resources_data.get("gather_times", {}).items():
    _gather_times[resource] = tuple(time_range)
for resource, amount_range in _resources_data.get("gather_amounts", {}).items():
    _gather_amounts[resource] = tuple(amount_range)

# Extract expedition data from JSON
_expedition_rewards_raw = _expeditions_data.get("rewards", {})
# Convert reward arrays to tuples
_expedition_rewards = {}
for exp_type, rewards_dict in _expedition_rewards_raw.items():
    _expedition_rewards[exp_type] = {}
    for resource, reward_range in rewards_dict.items():
        _expedition_rewards[exp_type][resource] = tuple(reward_range)
_death_prob = _expeditions_data.get("death_probability", 0.12)

CONFIG = {
    "SEED": None,
    "SOUL_START": 100.0,
    "SOUL_SPLIT_BASE": 0.10,
    "SOUL_SPLIT_VARIANCE": 0.03,
    "ASSEMBLER_TIME": (30, 45),
    "CLONE_TIME": _clone_times if _clone_times else {
        "BASIC": (30, 45),
        "MINER": (45, 60),
        "VOLATILE": (60, 90),
    },
    "GATHER_TIME": _gather_times if _gather_times else {
        "Tritanium": (12, 20),
        "Metal Ore": (10, 16),
        "Biomass": (6, 12),
        "Synthetic": (16, 24),
        "Organic": (8, 14),
        "Shilajit": (58, 73),
    },
    "GATHER_AMOUNT": _gather_amounts if _gather_amounts else {
        "Tritanium": (5, 12),
        "Metal Ore": (4, 10),
        "Biomass": (3, 8),
        "Synthetic": (2, 6),
        "Organic": (3, 7),
        "Shilajit": (1, 1),
    },
    "DEATH_PROB": _death_prob if _death_prob else 0.12,
    "MINER_XP_MULT": 1.25,
    "REWARDS": _expedition_rewards if _expedition_rewards else {
        "MINING": {"Tritanium": (8, 16), "Metal Ore": (6, 12)},
        "COMBAT": {"Biomass": (3, 7), "Synthetic": (2, 5)},
        "EXPLORATION": {"Tritanium": (2, 6), "Metal Ore": (2, 6), "Organic": (1, 3)},
    },
    "ASSEMBLER_COST": {"Tritanium": 30, "Metal Ore": 20, "Biomass": 5},
    "CLONE_COSTS": _clone_costs if _clone_costs else {
        "BASIC": {"Synthetic": 6, "Organic": 4, "Shilajit": 1},
        "MINER": {"Synthetic": 8, "Metal Ore": 8, "Organic": 5, "Shilajit": 1},
        "VOLATILE": {"Synthetic": 10, "Biomass": 8, "Organic": 6, "Shilajit": 3},
    },
    "SOUL_XP_RETAIN_RANGE": (0.6, 0.9),
    "SOUL_LEVEL_STEP": 100,
    "TRAIT_BASELINE_PER_LEVEL": 1,
    "COST_INFLATE_PER_LEVEL": 0.05,
    "PRACTICE_TRACKS": ["Kinetic", "Cognitive", "Constructive"],
    "PRACTICE_XP_PER_LEVEL": 100,
    "PASSIVE_XP_PER_HOUR": 5,
    "CROSS_POLL_FRACTION": 0.20,
    "BG": "#0b0f12",
    "PANEL": "#11161a",
    "BORDER": "#151a1f",
    "TEXT": "#e7e7e7",
    "MUTED": "#9aa4ad",
    "ACCENT": "#ff7a00",
    "ACCENT_2": "#ff9933",
    # Agent mode constants
    "MIN_UPLOAD_XP_THRESHOLD": 50,
    "SOUL_SAFETY_MARGIN": 5.0,
    "MIN_CLONES_TO_KEEP": 2,
    # Womb (Assembler) configuration
    "WOMB_MAX_DURABILITY": 100.0,
    "WOMB_MAX_ATTENTION": 100.0,
    "WOMB_ATTENTION_DECAY_PER_HOUR": 1.0,  # Attention lost per hour of idle
    "WOMB_ATTENTION_GAIN_ON_ACTION": 5.0,  # Attention gained per action (grow clone, build womb)
    "WOMB_ATTACK_CHANCE": 0.15,  # Chance of attack on state change (15%)
    "WOMB_ATTACK_DAMAGE_MIN": 5.0,  # Minimum attack damage
    "WOMB_ATTACK_DAMAGE_MAX": 15.0,  # Maximum attack damage
    "WOMB_REPAIR_COST_PER_DURABILITY": {"Tritanium": 0.5, "Metal Ore": 0.3},  # Cost per durability point
    "WOMB_REPAIR_TIME_MIN": 20,  # Minimum repair time in seconds
    "WOMB_REPAIR_TIME_MAX": 40,  # Maximum repair time in seconds
    "WOMB_MAX_COUNT": 4,  # Maximum number of wombs
    # Womb unlock thresholds (Practice levels)
    "WOMB_UNLOCK_ANY_PRACTICE_L4": True,  # +1 womb when any practice reaches L4
    "WOMB_UNLOCK_ANY_PRACTICE_L7": True,  # +1 womb when any practice reaches L7
    "WOMB_UNLOCK_TWO_PRACTICES_L9": True,  # +1 womb when two practices reach L9
    # Practice synergies (multipliers)
    "WOMB_SYNERGY_COGNITIVE_ATTENTION_MULT": 0.95,  # Cognitive L3+ reduces attention decay (increases gain multiplier)
    "WOMB_SYNERGY_KINETIC_ATTACK_MULT": 0.90,  # Kinetic L3+ reduces attack chance/damage
    "WOMB_SYNERGY_CONSTRUCTIVE_REPAIR_MULT": 0.85,  # Constructive L3+ reduces repair cost/time
    "WOMB_SYNERGY_THRESHOLD": 3,  # Practice level required for synergy
}

