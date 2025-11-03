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
    _rng_instance: Optional[random.Random] = None  # Cached RNG instance (not serialized)
    
    def __post_init__(self):
        """Initialize RNG if seed is set"""
        # Ensure seed is initialized
        if self.rng_seed is None:
            self.rng_seed = random.randint(0, 2**31 - 1)
        # Initialize cached RNG instance
        self._rng_instance = random.Random(self.rng_seed)
    
    @property
    def rng(self) -> random.Random:
        """Get RNG instance for this state (cached for state preservation)"""
        # Use cached instance if available and seed matches
        if self._rng_instance is None or self.rng_seed is None:
            self._rng_instance = random.Random(self.rng_seed)
        elif hasattr(self._rng_instance, '_seed') and self._rng_instance._seed != self.rng_seed:
            # Seed changed, recreate RNG
            self._rng_instance = random.Random(self.rng_seed)
        return self._rng_instance
    
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
            global_attention=getattr(self, 'global_attention', 0.0),
            active_tasks=copy.deepcopy(self.active_tasks),
            ui_layout=copy.deepcopy(self.ui_layout)
        )
        # Copy clones
        new_state.clones = {cid: copy.deepcopy(c) for cid, c in self.clones.items()}
        # Copy wombs if they exist (for backward compatibility, check if attribute exists)
        if hasattr(self, 'wombs'):
            new_state.wombs = [copy.deepcopy(w) for w in self.wombs]
        # Copy ftue if it exists (use getattr/setattr for dynamic attribute)
        ftue = getattr(self, 'ftue', None)
        if ftue is not None:
            setattr(new_state, 'ftue', copy.deepcopy(ftue))
        else:
            setattr(new_state, 'ftue', {})
        # Copy RNG state by copying the internal state of the Random object
        # This preserves RNG sequence across state copies
        if hasattr(self, '_rng_instance') and self._rng_instance is not None:
            new_state._rng_instance = random.Random()
            # Copy the internal state of the RNG
            new_state._rng_instance.setstate(self._rng_instance.getstate())
        return new_state

