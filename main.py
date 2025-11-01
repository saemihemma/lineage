#!/usr/bin/env python3
"""Main entry point for LINEAGE game"""
import sys
import tkinter as tk

# Check for tkinter availability
try:
    import tkinter  # noqa
except Exception:
    print("Tkinter/Tk not available; install a standard Python 3 build with Tk support.")
    sys.exit(1)

from ui.screen_manager import ScreenManager, ScreenState


def main():
    """Main entry point - uses screen manager for transitions"""
    # Create manager (no root window needed, screens are independent)
    manager = ScreenManager()
    
    # Start with briefing screen
    manager.transition_to(ScreenState.BRIEFING)
    
    # Start event loop on current screen
    if manager.current_screen:
        manager.current_screen.mainloop()


if __name__ == "__main__":
    main()
