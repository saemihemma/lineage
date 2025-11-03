"""Automated agent for managing game operations"""
import random
from typing import Callable, Optional
from game.state import GameState
from game.rules import apply_clone, upload_clone, run_expedition
from core.models import CLONE_TYPES
from core.config import CONFIG
from core.game_logic import inflate_costs, can_afford


class AgentController:
    """Manages automated agent decision-making"""
    
    def __init__(self, state: GameState, rng: random.Random, log_callback: Callable[[str], None]):
        self.p = state
        self.rng = rng
        self.log = log_callback
    
    def think(self, is_busy: bool, build_callback: Optional[Callable], craft_callback: Optional[Callable[[str], None]]) -> tuple[bool, Optional[int]]:
        """
        Agent decision logic
        Returns: (should_wait, delay_ms)
        """
        if is_busy:
            return True, 1000  # Wait 1 second if busy
        
        # Priority 1: Build assembler if not built
        if not self.p.assembler_built:
            lvl = self.p.soul_level()
            cost = inflate_costs(CONFIG["ASSEMBLER_COST"], lvl)
            if can_afford(self.p.resources, cost):
                self.log("[AGENT] Building Womb...")
                if build_callback:
                    build_callback()
                return True, 2000
            # Can't afford assembler, try to get resources
            pass
        
        # Priority 2: Upload clones with high XP
        best_clone_for_upload = None
        best_xp = 0
        for cid, c in self.p.clones.items():
            if c.alive and not c.uploaded:
                total_xp = c.total_xp()
                if total_xp > best_xp and total_xp >= CONFIG["MIN_UPLOAD_XP_THRESHOLD"]:
                    best_xp = total_xp
                    best_clone_for_upload = cid
        
        if best_clone_for_upload and len(self.p.clones) > CONFIG["MIN_CLONES_TO_KEEP"]:
            cid = best_clone_for_upload
            if cid in self.p.clones:
                self.log(f"[AGENT] Uploading clone {cid} to soul (XP: {best_xp})...")
                try:
                    new_state, msg = upload_clone(self.p, cid)
                    self.p = new_state
                    self.log(msg)
                    return True, 500
                except Exception:
                    pass
        
        # Priority 3: Craft clones if we have assembler and resources
        if self.p.assembler_built:
            lvl = self.p.soul_level()
            alive_clones = [c for c in self.p.clones.values() if c.alive and not c.uploaded]
            
            clone_to_craft = None
            if len(alive_clones) < CONFIG["MIN_CLONES_TO_KEEP"]:
                # Check what we can afford
                for kind in ["MINER", "BASIC", "VOLATILE"]:
                    cost = inflate_costs(CONFIG["CLONE_COSTS"][kind], lvl)
                    if can_afford(self.p.resources, cost):
                        # Check soul integrity
                        min_split = CONFIG["SOUL_SPLIT_BASE"] - CONFIG["SOUL_SPLIT_VARIANCE"]
                        if self.p.soul_percent >= 100.0 * min_split + CONFIG["SOUL_SAFETY_MARGIN"]:
                            clone_to_craft = kind
                            break
                
                if clone_to_craft and craft_callback:
                    self.log(f"[AGENT] Growing {CLONE_TYPES[clone_to_craft].display}...")
                    try:
                        craft_callback(clone_to_craft)
                        return True, 2000
                    except Exception:
                        pass
        
        # Priority 4: Apply a clone if none is applied
        if not self.p.applied_clone_id or self.p.applied_clone_id not in self.p.clones:
            alive_clones = [(cid, c) for cid, c in self.p.clones.items() if c.alive and not c.uploaded]
            if alive_clones:
                # Pick the clone with highest XP
                best_cid = max(alive_clones, key=lambda x: x[1].total_xp())[0]
                try:
                    new_state, _ = apply_clone(self.p, best_cid)
                    self.p = new_state
                    self.log(f"[AGENT] Applied clone {best_cid} to spaceship.")
                    return True, 500
                except Exception:
                    pass
        
        # Priority 5: Run expeditions if clone is applied
        if self.p.applied_clone_id and self.p.applied_clone_id in self.p.clones:
            c = self.p.clones[self.p.applied_clone_id]
            if c.alive:
                # Run expeditions - prioritize MINING for resources, but vary
                expedition_types = ["MINING", "COMBAT", "EXPLORATION"]
                # If low on Tritanium/Metal Ore, prioritize MINING
                if (self.p.resources.get("Tritanium", 0) < 30 or
                    self.p.resources.get("Metal Ore", 0) < 30):
                    exp_kind = "MINING"
                else:
                    # Rotate expeditions
                    exp_kind = expedition_types[self.rng.randint(0, len(expedition_types) - 1)]
                
                new_state, msg, feral_attack = run_expedition(self.p, exp_kind)
                self.p = new_state
                # Phase 4: Log feral attack if occurred
                if feral_attack:
                    self.log(f"[AGENT] ⚠️ Feral attack during expedition: {feral_attack}")
                self.log(f"[AGENT] {msg}")
                return True, 1500
        
        # If nothing to do, check again in 2 seconds
        return True, 2000

