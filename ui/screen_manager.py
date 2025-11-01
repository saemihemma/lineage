"""Screen state machine for managing transitions between screens"""
import tkinter as tk
from enum import Enum
from typing import Optional


class ScreenState(Enum):
    """Enumeration of possible screen states"""
    BRIEFING = "briefing"
    LOADING = "loading"
    SIMULATION = "simulation"


class ScreenManager:
    """Manages screen transitions and state"""
    
    def __init__(self, root: Optional[tk.Tk] = None):
        self.root = root
        self.current_screen = None
        self.current_state: Optional[ScreenState] = None
        self.screen_instances = {}
    
    def transition_to(self, state: ScreenState, **kwargs):
        """
        Transition to a new screen.
        
        Args:
            state: Target screen state
            **kwargs: Arguments to pass to screen constructor
        """
        # Preserve fullscreen state if transitioning
        is_fullscreen = False
        if self.current_screen:
            try:
                is_fullscreen = self.current_screen.attributes('-fullscreen')
            except:
                pass
            # Destroy old screen
            try:
                self.current_screen.destroy()
            except:
                pass
        
        # Import and create new screen
        if state == ScreenState.BRIEFING:
            from ui.screens.briefing import BriefingScreen
            self.current_screen = BriefingScreen(
                on_next=lambda old_win=None: self._handle_briefing_next(old_win)
            )
        elif state == ScreenState.LOADING:
            from ui.screens.loading import LoadingScreen
            self.current_screen = LoadingScreen(
                on_enter=lambda: self._handle_loading_enter()
            )
            # Preserve fullscreen
            if is_fullscreen:
                self._apply_fullscreen(self.current_screen)
        elif state == ScreenState.SIMULATION:
            from ui.screens.simulation import SimulationScreen
            self.current_screen = SimulationScreen(**kwargs)
            # Preserve fullscreen
            if is_fullscreen:
                self._apply_fullscreen(self.current_screen)
        
        self.current_state = state
        self.screen_instances[state] = self.current_screen
    
    def _handle_briefing_next(self, old_window=None):
        """Handle NEXT button from briefing screen"""
        # Close current briefing screen
        if self.current_screen:
            try:
                self.current_screen.destroy()
            except:
                pass
        
        # Transition to loading
        self.transition_to(ScreenState.LOADING)
        if self.current_screen:
            self.current_screen.mainloop()
    
    def _handle_loading_enter(self):
        """Handle ENTER SIMULATION button from loading screen"""
        # Close current loading screen
        if self.current_screen:
            try:
                self.current_screen.destroy()
            except:
                pass
        
        # Transition to simulation
        self.transition_to(ScreenState.SIMULATION)
        if self.current_screen:
            self.current_screen.mainloop()
    
    def _apply_fullscreen(self, window):
        """Apply fullscreen to window with fallbacks"""
        try:
            window.attributes('-fullscreen', True)
        except:
            try:
                window.state('zoomed')  # Windows
            except:
                try:
                    window.attributes('-zoomed', True)  # Linux
                except:
                    window.geometry(f"{window.winfo_screenwidth()}x{window.winfo_screenheight()}")
    
    def get_current_screen(self):
        """Get the current screen instance"""
        return self.current_screen
