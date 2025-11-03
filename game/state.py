"""Game state management with RNG integration"""
import random
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from core.models import PlayerState, Womb


@dataclass
class GameState(PlayerState):
    """
    Extended game state with RNG integration.
    
    GameState extends PlayerState and provides an integrated RNG instance
    that is automatically seeded from the state's rng_seed field.
    """
    active_tasks: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # For task persistence
    ui_layout: Dict[str, Any] = field(default_factory=dict)  # For UI layout persistence (paned window positions)
    
    def __post_init__(self):
        """Initialize RNG if seed is set"""
        # Ensure seed is initialized
        if self.rng_seed is None:
            self.rng_seed = random.randint(0, 2**31 - 1)
    
    @property
    def rng(self) -> random.Random:
        """Get RNG instance for this state"""
        return self.get_rng()
    
    def copy(self) -> 'GameState':
        """Create a copy of this state (for immutable updates)"""
        import copy
        new_state = GameState(
            version=self.version,
            rng_seed=self.rng_seed,
            soul_percent=self.soul_percent,
            soul_xp=self.soul_xp,
            assembler_built=self.assembler_built,
            resources=copy.deepcopy(self.resources),
            applied_clone_id=self.applied_clone_id,
            practices_xp=copy.deepcopy(self.practices_xp),
            last_saved_ts=self.last_saved_ts,
            self_name=self.self_name,
            active_tasks=copy.deepcopy(self.active_tasks),
            ui_layout=copy.deepcopy(self.ui_layout)
        )
        # Copy clones
        new_state.clones = {cid: copy.deepcopy(c) for cid, c in self.clones.items()}
        # Copy wombs if they exist (for backward compatibility, check if attribute exists)
        if hasattr(self, 'wombs'):
            new_state.wombs = [copy.deepcopy(w) for w in self.wombs]
        return new_state

