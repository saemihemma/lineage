"""Leaderboard window for displaying online SELF rankings"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from ui.theme import BG, PANEL, TEXT, ACCENT
from core.api_client import get_api_client


class LeaderboardWindow(tk.Toplevel):
    """Leaderboard window showing other SELFs from colleagues"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("LINEAGE — Leaderboard")
        self.geometry("900x700")
        self.configure(bg=BG)
        
        # Make window modal (blocks interaction with parent)
        self.transient(parent)
        self.grab_set()
        
        # Center window on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.winfo_screenheight() // 2) - (700 // 2)
        self.geometry(f"900x700+{x}+{y}")
        
        # Setup styles
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Panel.TFrame",
                       background=PANEL,
                       borderwidth=1,
                       relief="solid")
        style.configure("Title.TLabel",
                       background=PANEL,
                       foreground=TEXT,
                       font=("Helvetica", 24, "bold"))
        style.configure("Leaderboard.TLabel", 
                       background=PANEL,
                       foreground=TEXT,
                       font=("Helvetica", 12))
        style.configure("Header.TLabel",
                       background=PANEL,
                       foreground=TEXT,
                       font=("Helvetica", 12, "bold"))
        style.configure("Error.TLabel",
                       background=PANEL,
                       foreground=ACCENT,
                       font=("Helvetica", 16, "bold"))
        style.configure("Status.TLabel",
                       background=PANEL,
                       foreground=TEXT,
                       font=("Helvetica", 10))
        
        # Get API client
        self.api_client = get_api_client()
        
        # Main container
        main_frame = ttk.Frame(self, style="Panel.TFrame")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Leaderboard", 
                               style="Title.TLabel",
                               font=("Helvetica", 24, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Loading...", 
                                      style="Status.TLabel")
        self.status_label.pack(pady=(0, 10))
        
        # Leaderboard content frame
        self.content_frame = ttk.Frame(main_frame, style="Panel.TFrame")
        self.content_frame.pack(fill="both", expand=True)
        
        # Scrollable text widget for leaderboard entries
        self.leaderboard_text = scrolledtext.ScrolledText(
            self.content_frame,
            wrap=tk.WORD,
            font=("Courier", 10),
            bg=PANEL,
            fg=TEXT,
            state=tk.DISABLED,
            padx=10,
            pady=10
        )
        self.leaderboard_text.pack(fill="both", expand=True)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        # Refresh button
        refresh_btn = ttk.Button(button_frame, text="Refresh",
                                command=self.load_leaderboard)
        refresh_btn.pack(side="left", padx=5)
        
        # Close button
        close_btn = ttk.Button(button_frame, text="Close",
                              command=self.destroy)
        close_btn.pack(side="left", padx=5)
        
        # Load leaderboard data
        self.load_leaderboard()
    
    def load_leaderboard(self):
        """Load and display leaderboard entries"""
        self.status_label.config(text="Loading leaderboard...")
        self.leaderboard_text.config(state=tk.NORMAL)
        self.leaderboard_text.delete(1.0, tk.END)
        
        # Check if API is online
        if not self.api_client.is_online():
            self.status_label.config(text="Offline - API not reachable")
            self.leaderboard_text.insert(tk.END, "Uplink not established.\n\n")
            self.leaderboard_text.insert(tk.END, "The leaderboard API is not available.\n")
            self.leaderboard_text.insert(tk.END, "Please check your connection or API configuration.\n")
            self.leaderboard_text.config(state=tk.DISABLED)
            return
        
        # Fetch leaderboard
        entries = self.api_client.fetch_leaderboard(limit=100)
        
        if not entries:
            self.status_label.config(text="No entries found")
            self.leaderboard_text.insert(tk.END, "No leaderboard entries yet.\n")
            self.leaderboard_text.insert(tk.END, "Be the first to submit your SELF stats!\n")
        else:
            self.status_label.config(text=f"Showing {len(entries)} entries")
            
            # Header
            header = f"{'Rank':<6} {'SELF Name':<30} {'Level':<8} {'Soul XP':<12} {'Clones':<8} {'Expeditions':<12}\n"
            self.leaderboard_text.insert(tk.END, header)
            self.leaderboard_text.insert(tk.END, "-" * 90 + "\n")
            
            # Entries
            for rank, entry in enumerate(entries, 1):
                line = (f"{rank:<6} {entry.self_name[:29]:<30} {entry.soul_level:<8} "
                       f"{entry.soul_xp:<12} {entry.clones_uploaded:<8} {entry.total_expeditions:<12}\n")
                self.leaderboard_text.insert(tk.END, line)
        
        self.leaderboard_text.config(state=tk.DISABLED)

