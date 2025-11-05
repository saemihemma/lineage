"""Game data models"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
import random
from .config import CONFIG


@dataclass
class Trait:
    """Trait definition for clones"""
    code: str
    name: str
    min_val: int = 1
    max_val: int = 10
    value: int = 0


@dataclass
class CloneType:
    """Clone type definition"""
    code: str
    display: str


CLONE_TYPES = {
    "BASIC": CloneType("BASIC", "Basic Clone"),
    "MINER": CloneType("MINER", "Mining Clone"),
    "VOLATILE": CloneType("VOLATILE", "Volatile Clone"),
}

TRAIT_LIST = [
    Trait("PWC", "Pilot‑Wave Coupling"),
    Trait("SSC", "Static Shear Cohesion"),
    Trait("MGC", "Morphogenetic Cohesion"),
    Trait("DLT", "Differential‑Drift Tolerance"),
    Trait("ENF", "Exotronic Noise Floor"),
    Trait("ELK", "Entropic Luck"),
    Trait("FRK", "Feralization Risk"),
]


@dataclass
class Clone:
    """Clone data model"""
    id: str
    kind: str
    traits: Dict[str, int]
    xp: Dict[str, int]
    survived_runs: int = 0
    alive: bool = True
    uploaded: bool = False
    created_at: float = 0.0  # Unix timestamp when clone was created

    def total_xp(self) -> int:
        """Calculate total XP across all types"""
        return sum(self.xp.values())
    
    def biological_days(self, current_time: float = None) -> float:
        """
        Calculate biological days (configurable rate per real day).
        
        Systems v1: Reads bio_days_per_real_day from gameplay config (default 20.0).
        """
        import time
        from core.config import GAMEPLAY_CONFIG
        
        if current_time is None:
            current_time = time.time()
        if self.created_at == 0.0:
            return 0.0
        
        # Get rate from config (default 20.0 per real day)
        aging_config = GAMEPLAY_CONFIG.get("aging", {})
        bio_days_per_real_day = aging_config.get("bio_days_per_real_day", 20.0)
        
        # Calculate: bio_days_per_real_day / 86400 per second
        elapsed_seconds = current_time - self.created_at
        return elapsed_seconds * (bio_days_per_real_day / 86400.0)


@dataclass
class Womb:
    """Womb (assembler) data model"""
    id: int  # Index-based ID (0, 1, 2, ...)
    durability: float  # Current durability (0 to max_durability)
    max_durability: float = 100.0  # Maximum durability
    # Note: attention is now global (stored in PlayerState.global_attention), not per-womb
    
    def is_functional(self) -> bool:
        """Check if womb is functional (durability > 0)"""
        return self.durability > 0
    
    def durability_percent(self) -> float:
        """Get durability as percentage"""
        if self.max_durability == 0:
            return 0.0
        return (self.durability / self.max_durability) * 100.0


@dataclass
class PlayerState:
    """Player game state"""
    version: int = 1  # Schema version for migrations
    rng_seed: int = None  # RNG seed for reproducible behavior
    soul_percent: float = CONFIG["SOUL_START"]
    soul_xp: int = 0
    assembler_built: bool = False  # DEPRECATED: Use wombs array instead (kept for migration)
    wombs: List[Womb] = field(default_factory=list)  # Array of wombs (replaces assembler_built)
    resources: Dict[str, int] = field(default_factory=lambda: {
        "Tritanium": 0,
        "Metal Ore": 20,
        "Biomass": 5,
        "Synthetic": 8,
        "Organic": 8,
        "Shilajit": 0
    })
    clones: Dict[str, Clone] = field(default_factory=dict)
    applied_clone_id: str = ""
    practices_xp: Dict[str, int] = field(default_factory=lambda: {
        k: 0 for k in CONFIG["PRACTICE_TRACKS"]
    })
    last_saved_ts: float = 0.0
    self_name: str = ""
    global_attention: float = 0.0  # Global attention (0-100), shared across all wombs
    prayer_cooldown_until: Optional[float] = None  # Timestamp when prayer can be used again
    last_pray_effect: Optional[Dict[str, Any]] = None  # Last prayer effect (for expedition bonus)

    def soul_level(self) -> int:
        """Calculate current SELF level"""
        return 1 + (self.soul_xp // CONFIG["SOUL_LEVEL_STEP"])

    def practice_level(self, track: str) -> int:
        """Calculate practice level for a track"""
        return self.practices_xp.get(track, 0) // CONFIG["PRACTICE_XP_PER_LEVEL"]
    
    def get_rng(self) -> random.Random:
        """Get RNG instance for this state. Creates seed if missing."""
        if self.rng_seed is None:
            # Generate random seed if not set
            self.rng_seed = random.randint(0, 2**31 - 1)
        return random.Random(self.rng_seed)

