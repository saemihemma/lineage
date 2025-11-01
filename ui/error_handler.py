"""Error handling utilities for UI"""
import traceback
import tkinter.messagebox as messagebox
from typing import Callable, Any
import functools


def handle_ui_error(func: Callable) -> Callable:
    """
    Decorator to wrap UI functions with error handling.
    Catches exceptions and shows user-friendly messages instead of crashing.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log the full traceback for debugging
            error_msg = str(e)
            traceback.print_exc()
            
            # Show user-friendly error message
            try:
                messagebox.showerror(
                    "Error",
                    f"An error occurred: {error_msg}\n\nPlease check the console for details."
                )
            except:
                # If even messagebox fails, print to console
                print(f"ERROR in {func.__name__}: {error_msg}")
            
            return None
    
    return wrapper


class ErrorBoundary:
    """Context manager for error boundaries in UI code"""
    
    def __init__(self, on_error: Callable[[Exception], None] = None):
        self.on_error = on_error
        self.error_occurred = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error_occurred = True
            traceback.print_exception(exc_type, exc_val, exc_tb)
            
            if self.on_error:
                try:
                    self.on_error(exc_val)
                except:
                    pass
            else:
                # Default: show messagebox
                try:
                    messagebox.showerror(
                        "Error",
                        f"An error occurred: {str(exc_val)}\n\nPlease check the console for details."
                    )
                except:
                    pass
            
            return True  # Suppress exception propagation
        return False

