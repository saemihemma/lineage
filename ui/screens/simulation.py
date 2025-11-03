"""Main UI application for LINEAGE"""
import sys
import random
import time
import tkinter as tk
from tkinter import ttk, messagebox

# Import from new modular structure
from core.config import CONFIG
from core.models import CLONE_TYPES, TRAIT_LIST
from core.state_manager import save_state, load_state
from core.game_logic import (
    inflate_costs, can_afford, format_resource_error,
    perk_constructive_cost_mult, perk_constructive_craft_time_mult
)
from game.state import GameState
from game.rules import (
    build_womb, grow_clone, apply_clone, run_expedition,
    upload_clone, gather_resource
)
from ui.leaderboard import LeaderboardWindow
from ui.theme import (
    BG, PANEL, BORDER, TEXT, MUTED, ACCENT, ACCENT_2,
    PADDING_SM, PADDING_MD, PADDING_LG,
    FONT_BODY, FONT_HEADING, FONT_MONO,
    STYLE_H1, STYLE_H2, STYLE_BODY, STYLE_MONO
)


class SimulationScreen(tk.Tk):
    """Simulation screen (main game window)"""

    def __init__(self):
        super().__init__()
        # Load state and convert to GameState
        loaded_state = load_state()
        self.p = GameState(
            version=loaded_state.version,
            rng_seed=loaded_state.rng_seed,
            soul_percent=loaded_state.soul_percent,
            soul_xp=loaded_state.soul_xp,
            assembler_built=loaded_state.assembler_built,
            resources=loaded_state.resources,
            applied_clone_id=loaded_state.applied_clone_id,
            practices_xp=loaded_state.practices_xp,
            last_saved_ts=loaded_state.last_saved_ts,
            self_name=loaded_state.self_name
        )
        # Copy clones
        self.p.clones = loaded_state.clones.copy()
        # Copy active_tasks if present
        if hasattr(loaded_state, "active_tasks"):
            self.p.active_tasks = loaded_state.active_tasks.copy()
        
        # Use RNG from state (seedable/reproducible)
        self.R = self.p.rng
        
        self.agent_mode = False
        self.agent_timer_id = None
        self.is_busy = False  # Track if assembler/clone crafting is in progress
        self.gather_buttons = {}  # Store gather button references
        self.practice_bars = {}  # Store practice progress bars
        self.level_labels = {}  # Store practice level labels
        
        self.title("Frontier — LINEAGE (Prototype v4)")
        
        # Make window fullscreen/maximized
        try:
            if sys.platform == 'win32':
                self.state('zoomed')
            elif sys.platform == 'linux':
                self.attributes('-zoomed', True)
            elif sys.platform == 'darwin':  # macOS
                self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}")
        except Exception:
            # Fallback: use large size
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}")
        
        self.configure(bg=BG)
        self._setup_styles()
        self._build_ui()
        
        self.refresh_all()
        self.update_gather_buttons_state()
        self.tutorial_intro()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_styles(self):
        """Configure UI styles"""
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
        style.configure("Accent.TButton", foreground=TEXT, padding=6)
        style.map("Accent.TButton", background=[
            ("!disabled", ACCENT),
            ("active", ACCENT_2)
        ])
        style.configure("Agent.TButton", foreground=TEXT, padding=6)
        style.map("Agent.TButton", background=[
            ("!disabled", "#00aa00"),
            ("active", "#00cc00")
        ])
        # Configure progress bar to use accent color (orange)
        try:
            style.configure("TProgressbar", background=ACCENT,
                          foreground=ACCENT, troughcolor=PANEL)
        except Exception:
            # If styling fails completely, progress bars will use system default
            pass

    def _build_ui(self):
        """Build the UI layout"""
        # Header
        header = ttk.Frame(self, style="Panel.TFrame")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(header, text="LINEAGE", style="Panel.TLabel").pack(side="left", padx=8, pady=6)
        self.stats = tk.StringVar()
        ttk.Label(header, textvariable=self.stats, style="Panel.TLabel").pack(side="right", padx=8)
        # Agent button in header - less prominent
        self.agent_btn = ttk.Button(header, text="🤖", command=self.toggle_agent, width=3)
        self.agent_btn.pack(side="right", padx=4)

        # Button bar
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=6)
        ttk.Button(bar, text="Build Womb", style="Accent.TButton",
                   command=self.build_assembler).pack(side="left", padx=4)
        ttk.Button(bar, text="Grow Basic Clone", style="Accent.TButton",
                   command=lambda: self.craft("BASIC")).pack(side="left", padx=4)
        ttk.Button(bar, text="Grow Mining Clone", style="Accent.TButton",
                   command=lambda: self.craft("MINER")).pack(side="left", padx=4)
        ttk.Button(bar, text="Grow Volatile Clone", style="Accent.TButton",
                   command=lambda: self.craft("VOLATILE")).pack(side="left", padx=4)
        ttk.Button(bar, text="Apply Clone to Spaceship",
                   command=self.apply_sel).pack(side="left", padx=12)
        ttk.Button(bar, text="Do a Mining Expedition",
                   command=lambda: self.run("MINING")).pack(side="left", padx=4)
        ttk.Button(bar, text="Do a Combat Expedition",
                   command=lambda: self.run("COMBAT")).pack(side="left", padx=4)
        ttk.Button(bar, text="Do an Exploration Expedition",
                   command=lambda: self.run("EXPLORATION")).pack(side="left", padx=4)
        ttk.Button(bar, text="Upload Clone to SELF",
                   command=self.upload_sel).pack(side="left", padx=12)
        
        # Leaderboard button
        self.leaderboard_btn = ttk.Button(bar, text="Leaderboard",
                                          command=self.show_leaderboard)
        self.leaderboard_btn.pack(side="left", padx=12)
        
        # Submit to Leaderboard button
        self.submit_leaderboard_btn = ttk.Button(bar, text="Submit to Leaderboard",
                                                 command=self.submit_to_leaderboard)
        self.submit_leaderboard_btn.pack(side="left", padx=12)

        # Main paned window (vertical split)
        paned = ttk.Panedwindow(self, orient=tk.VERTICAL)
        paned.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        top = ttk.Frame(paned)
        paned.add(top, weight=1)
        bottom = ttk.Frame(paned, style="Panel.TFrame")
        paned.add(bottom, weight=1)

        # Top paned window (horizontal split - 3 columns)
        top_paned = ttk.Panedwindow(top, orient=tk.HORIZONTAL)
        top_paned.pack(fill="both", expand=True)
        col1 = ttk.Frame(top_paned, style="Panel.TFrame")
        top_paned.add(col1, weight=1)
        col2 = ttk.Frame(top_paned, style="Panel.TFrame")
        top_paned.add(col2, weight=1)
        col3 = ttk.Frame(top_paned, style="Panel.TFrame")
        top_paned.add(col3, weight=1)

        # Column 1: Resources and Clones
        col1_paned = ttk.Panedwindow(col1, orient=tk.VERTICAL)
        col1_paned.pack(fill="both", expand=True, padx=0, pady=0)

        # Resources section
        res_section = ttk.Frame(col1_paned, style="Panel.TFrame")
        col1_paned.add(res_section, weight=1)
        ttk.Label(res_section, text="Resources", style="Panel.TLabel").pack(anchor="w", padx=8, pady=(8, 0))
        self.res_text = tk.Text(res_section, bg=PANEL, fg=TEXT, bd=0,
                                highlightbackground=BORDER, insertbackground=TEXT)
        self.res_text.pack(fill="both", expand=True, padx=8, pady=(6, 8))

        # Clones section
        clones_frame = ttk.Frame(col1_paned, style="Panel.TFrame")
        col1_paned.add(clones_frame, weight=1)
        ttk.Label(clones_frame, text="Clones", style="Panel.TLabel").pack(anchor="w", padx=8, pady=(8, 0))
        self.listbox = tk.Listbox(clones_frame, bg=PANEL, fg=TEXT,
                                  highlightbackground=BORDER, selectbackground=ACCENT)
        self.listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.listbox.bind("<<ListboxSelect>>", self.show_selected)

        # Column 2: Costs (75%) and Gather Resources (25% - equal to Clones)
        col2_paned = ttk.Panedwindow(col2, orient=tk.VERTICAL)
        col2_paned.pack(fill="both", expand=True, padx=0, pady=0)

        # Cost List Display
        cost_frame = ttk.Frame(col2_paned, style="Panel.TFrame")
        col2_paned.add(cost_frame, weight=3)
        ttk.Label(cost_frame, text="Costs (Current Level)", style="Panel.TLabel").pack(anchor="w", padx=8, pady=(8, 4))
        self.cost_text = tk.Text(cost_frame, bg=PANEL, fg=TEXT, bd=0,
                                 highlightbackground=BORDER, insertbackground=TEXT,
                                 wrap=tk.WORD, state=tk.DISABLED)
        self.cost_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.cost_text.tag_config("bold", foreground=ACCENT, font=("TkDefaultFont", 9, "bold"))
        self.cost_text.tag_config("muted", foreground=MUTED)

        # Resource gathering buttons (equal to Clones panel size)
        gather_frame = ttk.Frame(col2_paned, style="Panel.TFrame")
        col2_paned.add(gather_frame, weight=1)
        ttk.Label(gather_frame, text="Gather Resources:", style="Panel.TLabel").pack(anchor="w", padx=8, pady=(8, 4))

        gather_btn_container = ttk.Frame(gather_frame, style="Panel.TFrame")
        gather_btn_container.pack(fill="x", padx=8, pady=(0, 8))

        resource_names = ["Tritanium", "Metal Ore", "Biomass", "Synthetic", "Organic", "Shilajit"]
        for i, res in enumerate(resource_names):
            btn = ttk.Button(gather_btn_container, text=f"Gather {res}",
                           command=lambda r=res: self.gather_resource(r))
            if i < 3:
                btn.grid(row=0, column=i, padx=2, pady=2, sticky="ew")
            else:
                btn.grid(row=1, column=i-3, padx=2, pady=2, sticky="ew")
            self.gather_buttons[res] = btn
        for i in range(3):
            gather_btn_container.grid_columnconfigure(i, weight=1, uniform="gather")

        # Column 3: Clone Details and Build/Craft Progress
        col3_paned = ttk.Panedwindow(col3, orient=tk.VERTICAL)
        col3_paned.pack(fill="both", expand=True, padx=0, pady=0)

        # Clone Details
        details_frame = ttk.Frame(col3_paned, style="Panel.TFrame")
        col3_paned.add(details_frame, weight=3)
        ttk.Label(details_frame, text="Clone Details", style="Panel.TLabel").pack(anchor="w", padx=8, pady=(8, 0))
        self.details = tk.Text(details_frame, bg=BG, fg=TEXT, bd=0,
                               highlightbackground=BORDER, insertbackground=TEXT)
        self.details.pack(fill="both", expand=True, padx=8, pady=6)

        # Build/Craft Progress (equal to Clones panel size)
        progfrm = ttk.Frame(col3_paned, style="Panel.TFrame")
        col3_paned.add(progfrm, weight=1)
        ttk.Label(progfrm, text="Progress", style="Panel.TLabel").pack(anchor="w", padx=8, pady=(8, 0))
        self.progress = ttk.Progressbar(progfrm, maximum=100, style="TProgressbar")
        self.progress.pack(fill="x", padx=8, pady=6)
        self.prog_label = ttk.Label(progfrm, text="", style="Panel.TLabel")
        self.prog_label.pack(anchor="w", padx=8)

        # Bottom paned window (terminal and practices)
        bottom_paned = ttk.Panedwindow(bottom, orient=tk.VERTICAL)
        bottom_paned.pack(fill="both", expand=True, padx=0, pady=0)

        # Terminal section
        terminal_frame = ttk.Frame(bottom_paned, style="Panel.TFrame")
        bottom_paned.add(terminal_frame, weight=1)
        ttk.Label(terminal_frame, text="Terminal / Tutorial", style="Panel.TLabel").pack(anchor="w", padx=8, pady=(8, 0))
        self.log = tk.Text(terminal_frame, bg=BG, fg=TEXT,
                           highlightbackground=BORDER, wrap=tk.WORD, insertbackground=TEXT)
        self.log.pack(fill="both", expand=True, padx=8, pady=(8, 8))

        # LINEAGE Practices Panel
        practices_frame = ttk.Frame(bottom_paned, style="Panel.TFrame")
        bottom_paned.add(practices_frame, weight=1)
        ttk.Label(practices_frame, text="LINEAGE Practices", style="Panel.TLabel").pack(anchor="w", padx=8, pady=(8, 2))
        ttk.Label(practices_frame, text="Persistent growth of the SELF through vessels.",
                 style="Panel.TLabel", foreground=MUTED).pack(anchor="w", padx=8, pady=(0, 4))

        for track in CONFIG["PRACTICE_TRACKS"]:
            track_frame = ttk.Frame(practices_frame, style="Panel.TFrame")
            track_frame.pack(fill="x", padx=0, pady=2)

            label_frame = ttk.Frame(track_frame, style="Panel.TFrame")
            label_frame.pack(fill="x")
            ttk.Label(label_frame, text=f"{track}:", style="Panel.TLabel", width=12).pack(side="left")
            self.level_labels[track] = ttk.Label(label_frame, text="Level 0 — 0/100 XP", style="Panel.TLabel")
            self.level_labels[track].pack(side="left", padx=(4, 0))

            self.practice_bars[track] = ttk.Progressbar(track_frame, maximum=CONFIG["PRACTICE_XP_PER_LEVEL"],
                                                       style="TProgressbar")
            self.practice_bars[track].pack(fill="x", padx=0, pady=2)

    def on_close(self):
        """Handle window close event"""
        if self.agent_timer_id:
            self.after_cancel(self.agent_timer_id)
        save_state(self.p)
        self.destroy()

    def toggle_agent(self):
        """Toggle agent mode on/off"""
        if not self.agent_mode:
            # Request confirmation before enabling
            if not messagebox.askyesno("Enable Agent Mode",
                                     "Agent mode will automatically manage your operations.\n\n"
                                     "The agent will:\n"
                                     "- Build assemblers\n"
                                     "- Grow clones\n"
                                     "- Run expeditions\n"
                                     "- Upload clones\n\n"
                                     "Are you sure you want to enable agent mode?\n"
                                     "You can disable it anytime by clicking the 🤖 button."):
                return

        self.agent_mode = not self.agent_mode
        if self.agent_mode:
            self.agent_btn.config(text="🤖")
            self.logline("[AGENT] Agent mode activated. I will manage your operations automatically.")
            self.agent_think()
        else:
            self.agent_btn.config(text="🤖")
            if self.agent_timer_id:
                self.after_cancel(self.agent_timer_id)
                self.agent_timer_id = None
            self.logline("[AGENT] Agent mode deactivated.")

    def agent_think(self):
        """Agent decision-making logic"""
        if not self.agent_mode:
            return

        # Check if we're busy (assembler, clone crafting, or gathering in progress)
        if self.is_busy:
            self.agent_timer_id = self.after(1000, self.agent_think)
            return

        # Priority 1: Build assembler if not built
        if not self.p.assembler_built:
            lvl = self.p.soul_level()
            cost = inflate_costs(CONFIG["ASSEMBLER_COST"], lvl)
            if can_afford(self.p.resources, cost):
                self.logline("[AGENT] Building Womb...")
                self.is_busy = True
                self.build_assembler()
                self.agent_timer_id = self.after(2000, self.agent_think)
                return

        # Priority 2: Upload clones with high XP (>50 total XP threshold)
        best_clone_for_upload = None
        best_xp = 0
        for cid, c in self.p.clones.items():
            if c.alive and not c.uploaded:
                total_xp = c.total_xp()
                if total_xp > best_xp and total_xp >= 50:
                    best_xp = total_xp
                    best_clone_for_upload = cid

        if best_clone_for_upload and len(self.p.clones) > 1:
            cid = best_clone_for_upload
            if cid in self.p.clones:
                self.logline(f"[AGENT] Uploading clone {cid} to soul (XP: {best_xp})...")
                try:
                    new_state, msg = upload_clone(self.p, cid)
                    self.p = new_state
                    self.logline(msg)
                    self.refresh_all()
                    self.agent_timer_id = self.after(500, self.agent_think)
                    return
                except Exception:
                    pass

        # Priority 3: Craft clones if we have assembler and resources
        if self.p.assembler_built:
            lvl = self.p.soul_level()
            alive_clones = [c for c in self.p.clones.values() if c.alive and not c.uploaded]

            clone_to_craft = None
            if len(alive_clones) < 2:  # Keep at least 2 clones
                # Check what we can afford
                for kind in ["MINER", "BASIC", "VOLATILE"]:
                    cost = inflate_costs(CONFIG["CLONE_COSTS"][kind], lvl)
                    if can_afford(self.p.resources, cost):
                        # Check soul integrity
                        min_split = CONFIG["SOUL_SPLIT_BASE"] - CONFIG["SOUL_SPLIT_VARIANCE"]
                        if self.p.soul_percent >= 100.0 * min_split + 5.0:  # Safety margin
                            clone_to_craft = kind
                            break

                if clone_to_craft:
                    self.logline(f"[AGENT] Growing {CLONE_TYPES[clone_to_craft].display}...")
                    self.is_busy = True
                    try:
                        self.craft(clone_to_craft)
                        self.agent_timer_id = self.after(2000, self.agent_think)
                        return
                    except Exception:
                        self.is_busy = False

        # Priority 4: Apply a clone if none is applied
        if not self.p.applied_clone_id or self.p.applied_clone_id not in self.p.clones:
            alive_clones = [(cid, c) for cid, c in self.p.clones.items() if c.alive and not c.uploaded]
            if alive_clones:
                # Pick the clone with highest XP
                best_cid = max(alive_clones, key=lambda x: x[1].total_xp())[0]
                try:
                    new_state, _ = apply_clone(self.p, best_cid)
                    self.p = new_state
                    self.logline(f"[AGENT] Applied clone {best_cid} to spaceship.")
                    self.refresh_all()
                    self.agent_timer_id = self.after(500, self.agent_think)
                    return
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
                    exp_kind = expedition_types[self.R.randint(0, len(expedition_types) - 1)]

                new_state, msg, feral_attack = run_expedition(self.p, exp_kind)
                self.p = new_state
                # Phase 4: Log feral attack if occurred
                if feral_attack:
                    self.logline(f"[AGENT] ⚠️ Feral attack: {feral_attack}")
                self.logline(f"[AGENT] {msg}")
                self.refresh_all()
                self.agent_timer_id = self.after(1500, self.agent_think)
                return

        # If nothing to do, check again in 2 seconds
        self.agent_timer_id = self.after(2000, self.agent_think)

    def logline(self, s: str):
        """Add a line to the log"""
        self.log.insert("end", s + "\n")
        self.log.see("end")

    def update_cost_display(self):
        """Update the cost list based on current soul level"""
        self.cost_text.config(state=tk.NORMAL)
        self.cost_text.delete("1.0", "end")

        level = self.p.soul_level()
        cost_mult = perk_constructive_cost_mult(self.p)

        # Assembler costs (with perks)
        base_assembler_cost = inflate_costs(CONFIG["ASSEMBLER_COST"], level)
        assembler_cost = {k: int(round(v * cost_mult)) for k, v in base_assembler_cost.items()}
        self.cost_text.insert("end", "Womb:\n", "bold")
        for res, amt in assembler_cost.items():
            self.cost_text.insert("end", f"  {res}: {amt}\n")

        # Clone costs (with perks)
        self.cost_text.insert("end", "\nBasic Clone:\n", "bold")
        base_basic_cost = inflate_costs(CONFIG["CLONE_COSTS"]["BASIC"], level)
        basic_cost = {k: int(round(v * cost_mult)) for k, v in base_basic_cost.items()}
        for res, amt in basic_cost.items():
            self.cost_text.insert("end", f"  {res}: {amt}\n")

        self.cost_text.insert("end", "\nMining Clone:\n", "bold")
        base_miner_cost = inflate_costs(CONFIG["CLONE_COSTS"]["MINER"], level)
        miner_cost = {k: int(round(v * cost_mult)) for k, v in base_miner_cost.items()}
        for res, amt in miner_cost.items():
            self.cost_text.insert("end", f"  {res}: {amt}\n")

        self.cost_text.insert("end", "\nVolatile Clone:\n", "bold")
        base_volatile_cost = inflate_costs(CONFIG["CLONE_COSTS"]["VOLATILE"], level)
        volatile_cost = {k: int(round(v * cost_mult)) for k, v in base_volatile_cost.items()}
        for res, amt in volatile_cost.items():
            self.cost_text.insert("end", f"  {res}: {amt}\n")

        # Add soul percentage note for clones
        split_pct = int(round(CONFIG["SOUL_SPLIT_BASE"] * 100))
        self.cost_text.tag_config("muted", foreground=MUTED)
        self.cost_text.insert("end", f"\n(+ ~{split_pct}% SELF per clone)\n", "muted")

        self.cost_text.config(state=tk.DISABLED)

    def refresh_all(self):
        """Refresh all UI displays"""
        agent_status = " | 🤖 AGENT ON" if self.agent_mode else ""
        current_level = self.p.soul_level()
        xp_in_current_level = self.p.soul_xp % CONFIG['SOUL_LEVEL_STEP']
        xp_for_next_level = CONFIG['SOUL_LEVEL_STEP']
        level_xp_display = f" ({xp_in_current_level}/{xp_for_next_level} XP)"
        seed_display = f" | Seed: {self.p.rng_seed if self.p.rng_seed else 'Not set'}"
        self.stats.set(
            f"SELF {self.p.soul_percent:.1f}% | SELF Level {current_level}{level_xp_display} | "
            f"Assembler {'Built' if self.p.assembler_built else 'Missing'}{seed_display}{agent_status}"
        )
        self.res_text.delete("1.0", "end")
        for k in ["Tritanium", "Metal Ore", "Biomass", "Synthetic", "Organic", "Shilajit"]:
            self.res_text.insert("end", f"{k}: {self.p.resources.get(k, 0)}\n")
        self.listbox.delete(0, "end")
        for cid, c in self.p.clones.items():
            if c.uploaded:
                tag = "UPLOADED"
            elif c.alive:
                tag = "ALIVE"
            else:
                tag = "LOST"
            applied = " [APPLIED]" if self.p.applied_clone_id == cid else ""
            self.listbox.insert("end",
                               f"{cid} :: {CLONE_TYPES[c.kind].display} :: Runs {c.survived_runs} :: {tag}{applied}")
        self.update_cost_display()
        # Update LINEAGE Practices
        for track in CONFIG["PRACTICE_TRACKS"]:
            xp = self.p.practices_xp.get(track, 0)
            lvl = xp // CONFIG["PRACTICE_XP_PER_LEVEL"]
            in_lvl = xp % CONFIG["PRACTICE_XP_PER_LEVEL"]
            self.practice_bars[track]["value"] = in_lvl
            self.level_labels[track].config(
                text=f"Level {lvl} — {in_lvl}/{CONFIG['PRACTICE_XP_PER_LEVEL']} XP"
            )

    def tutorial_intro(self):
        """Display tutorial introduction"""
        self.logline("Welcome. Build your base and field clones into expeditions.")
        self.logline("STEP 1 — Build Womb (consumes Tritanium, Metal Ore, Biomass).")
        self.logline("STEP 2 — Grow a clone (costs a slice of your SELF + materials).")
        self.logline("STEP 3 — Apply the clone to your spaceship, then run an expedition.")
        self.logline("STEP 4 — Upload the clone to your SELF to bank progress; future clones begin stronger and costlier.")

    def show_selected(self, event=None):
        """Show details of selected clone"""
        cid = self.get_selected_cid()
        self.details.delete("1.0", "end")
        if not cid:
            return
        c = self.p.clones.get(cid)
        if not c:
            return
        status = "UPLOADED" if c.uploaded else ("ALIVE" if c.alive else "LOST")
        self.details.insert("end", f"Clone {cid}\nType: {CLONE_TYPES[c.kind].display}\nStatus: {status}\n")
        self.details.insert("end", f"Survived Runs: {c.survived_runs}\n")
        self.details.insert("end",
                           f"XP — Mining: {c.xp['MINING']}, Combat: {c.xp['COMBAT']}, "
                           f"Exploration: {c.xp['EXPLORATION']}\n\nTraits:\n")
        for code, val in c.traits.items():
            name = next((t.name for t in TRAIT_LIST if t.code == code), code)
            self.details.insert("end", f"  {name}: {val}\n")

    def get_selected_cid(self):
        """Get the selected clone ID from listbox"""
        sel = self.listbox.curselection()
        if not sel:
            return None
        item = self.listbox.get(sel[0])
        return item.split(" :: ")[0]

    def run_timer(self, seconds: int, label: str, done_cb):
        """Run a progress timer using simple after()"""
        # Update UI immediately
        self.progress["value"] = 0
        self.prog_label.config(text=f"{label}… {seconds}s remaining")
        
        # Update progress bar periodically
        def update_progress(remaining):
            if remaining <= 0:
                self.progress["value"] = 100
                self.prog_label.config(text=f"{label}… complete")
                done_cb()
            else:
                elapsed = seconds - remaining
                pct = int(100 * (elapsed / seconds))
                self.progress["value"] = min(100, max(0, pct))
                self.prog_label.config(text=f"{label}… {remaining}s remaining")
                self.after(1000, lambda: update_progress(remaining - 1))
        
        # Start countdown
        self.after(1000, lambda: update_progress(seconds - 1))

    def build_assembler(self):
        """Build the Womb (assembler)"""
        if self.p.assembler_built:
            self.logline("Womb already built.")
            return
        try:
            # Use pure function - build happens immediately (state is immutable)
            new_state, msg = build_womb(self.p)
            self.p = new_state
            self.is_busy = True
            self.update_gather_buttons_state()
            save_state(self.p)
            
            t_min, t_max = CONFIG["ASSEMBLER_TIME"]
            base_seconds = self.R.randint(t_min, t_max)
            # Apply crafting time perk
            time_mult = perk_constructive_craft_time_mult(self.p)
            seconds = int(round(base_seconds * time_mult))
            self.logline("Building Womb...")
            self.refresh_all()

            def done():
                self.logline("Womb completed. You can now grow clones.")
                self.is_busy = False
                self.update_gather_buttons_state()
                self.refresh_all()
                if self.agent_mode:
                    self.agent_think()

            self.run_timer(seconds, "Building Womb", done)
        except Exception as e:
            self.is_busy = False
            if self.agent_mode:
                self.logline(f"[AGENT] Build failed: {str(e)}")
                self.agent_think()
            else:
                error_msg = format_resource_error(self.p.resources, {}, "Womb") if hasattr(e, 'args') else str(e)
                self.logline(error_msg)

    def craft(self, kind: str):
        """Craft a clone"""
        try:
            # Use pure function - clone is created immediately (state is immutable)
            new_state, clone, split, msg = grow_clone(self.p, kind)
            self.p = new_state
            self.is_busy = True
            self.update_gather_buttons_state()
            save_state(self.p)
            
            split_pct = int(round(split * 100))
            t_min, t_max = CONFIG["CLONE_TIME"][kind]
            base_seconds = self.R.randint(t_min, t_max)
            # Apply crafting time perk
            time_mult = perk_constructive_craft_time_mult(self.p)
            seconds = int(round(base_seconds * time_mult))
            self.logline(f"Growing {CLONE_TYPES[kind].display}… (~{split_pct}% of SELF will be consumed).")
            self.refresh_all()

            def done():
                # Clone is already created by grow_clone() above
                self.logline(msg)
                self.is_busy = False
                self.update_gather_buttons_state()
                self.refresh_all()
                if self.agent_mode:
                    self.agent_think()

            self.run_timer(seconds, f"Growing {CLONE_TYPES[kind].display}", done)
        except Exception as e:
            self.is_busy = False
            if self.agent_mode:
                # In agent mode, just log errors instead of showing popups
                self.logline(f"[AGENT] Craft failed: {str(e)}")
                self.agent_think()
            else:
                messagebox.showerror("Cannot craft", str(e))

    def apply_sel(self):
        """Apply selected clone to spaceship"""
        cid = self.get_selected_cid()
        if not cid:
            messagebox.showinfo("Apply to Spaceship", "Select a clone in the list first.")
            return
        try:
            new_state, msg = apply_clone(self.p, cid)
            self.p = new_state
            save_state(self.p)
            self.logline(msg)
            self.refresh_all()
        except Exception as e:
            messagebox.showerror("Apply failed", str(e))

    def update_gather_buttons_state(self):
        """Enable/disable gather buttons based on busy state"""
        state = "disabled" if self.is_busy else "normal"
        for btn in self.gather_buttons.values():
            btn.config(state=state)

    def gather_resource(self, resource: str):
        """Gather a resource"""
        if self.is_busy:
            self.logline(f"Already busy. Cannot gather {resource} right now.")
            return
        if resource not in CONFIG["GATHER_TIME"]:
            self.logline(f"Unknown resource: {resource}")
            return

        t_min, t_max = CONFIG["GATHER_TIME"][resource]
        seconds = self.R.randint(t_min, t_max)

        self.logline(f"Gathering {resource}...")
        self.is_busy = True
        self.update_gather_buttons_state()

        def done():
            try:
                # Use pure function from game.rules
                from game.rules import gather_resource as gather_resource_rule
                new_state, amount, msg = gather_resource_rule(self.p, resource)
                self.p = new_state
                save_state(self.p)
                self.logline(msg)
            except Exception as e:
                self.logline(f"Error gathering resource: {str(e)}")
            finally:
                self.is_busy = False
                self.update_gather_buttons_state()
                self.refresh_all()
                if self.agent_mode:
                    self.agent_think()

        self.run_timer(seconds, f"Gathering {resource}", done)

    def run(self, kind: str):
        """Run an expedition"""
        new_state, msg, feral_attack = run_expedition(self.p, kind)
        self.p = new_state
        # Phase 4: Log feral attack if occurred
        if feral_attack:
            self.logline(f"⚠️ Feral attack: {feral_attack}")
        save_state(self.p)
        self.logline(msg)
        self.refresh_all()

    def show_leaderboard(self):
        """Show leaderboard window"""
        LeaderboardWindow(self)
    
    def submit_to_leaderboard(self):
        """Submit current SELF stats to leaderboard"""
        from core.api_client import get_api_client
        from tkinter import messagebox
        
        api_client = get_api_client()
        
        # Check if API is available
        if not api_client.is_online():
            messagebox.showwarning(
                "Leaderboard Offline",
                "Cannot submit to leaderboard - API is not reachable.\n\n"
                "Please check your connection or API configuration."
            )
            return
        
        # Check if self_name is set
        if not self.p.self_name or not self.p.self_name.strip():
            messagebox.showwarning(
                "No SELF Name",
                "Please set your SELF name first (in the loading screen)."
            )
            return
        
        # Confirm submission
        if not messagebox.askyesno(
            "Submit to Leaderboard",
            f"Submit your SELF stats to the leaderboard?\n\n"
            f"SELF Name: {self.p.self_name}\n"
            f"Soul Level: {self.p.soul_level()}\n"
            f"Soul XP: {self.p.soul_xp}\n"
            f"Clones Uploaded: {sum(1 for c in self.p.clones.values() if c.uploaded)}\n"
            f"Total Expeditions: {len([c for c in self.p.clones.values() if c.survived_runs > 0 or not c.alive])}"
        ):
            return
        
        # Submit to leaderboard
        success = api_client.submit_to_leaderboard(
            self_name=self.p.self_name,
            soul_level=self.p.soul_level(),
            soul_xp=self.p.soul_xp,
            clones_uploaded=sum(1 for c in self.p.clones.values() if c.uploaded),
            total_expeditions=sum(c.survived_runs for c in self.p.clones.values())
        )
        
        if success:
            messagebox.showinfo(
                "Submission Successful",
                "Your SELF stats have been submitted to the leaderboard!"
            )
        else:
            messagebox.showerror(
                "Submission Failed",
                "Failed to submit to leaderboard.\n\n"
                "Please try again later."
            )

    def upload_sel(self):
        """Upload selected clone to SELF"""
        cid = self.get_selected_cid()
        if not cid:
            messagebox.showinfo("Upload to SELF", "Select a living clone to upload.")
            return
        c = self.p.clones.get(cid)
        if not c or not c.alive:
            messagebox.showinfo("Upload to SELF", "Clone must be alive to upload.")
            return
        if c.uploaded:
            messagebox.showinfo("Upload to SELF", "Clone has already been uploaded.")
            return
        if not messagebox.askyesno("Confirm Upload", "Upload this clone to your SELF and retire it?"):
            return
        new_state, msg = upload_clone(self.p, cid)
        self.p = new_state
        save_state(self.p)
        self.logline(msg)
        self.refresh_all()

