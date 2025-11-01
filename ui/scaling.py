"""UI scaling utilities for responsive layouts"""
from typing import Tuple


def get_scale_factor(window_width: int = 1920, window_height: int = 1080) -> float:
    """
    Calculate UI scale factor based on window dimensions.
    
    Args:
        window_width: Current window width
        window_height: Current window height
    
    Returns:
        Scale factor (1.0 = 1920x1080 baseline)
    """
    baseline_width = 1920
    baseline_height = 1080
    
    scale_w = window_width / baseline_width
    scale_h = window_height / baseline_height
    
    # Use minimum to ensure UI fits on screen
    return min(scale_w, scale_h)


def scale_font(base_size: int, scale: float) -> int:
    """
    Scale a font size by the scale factor.
    
    Args:
        base_size: Base font size (for 1920x1080)
        scale: Scale factor
    
    Returns:
        Scaled font size
    """
    return max(8, int(base_size * scale))


def scale_padding(base_padding: int, scale: float) -> int:
    """
    Scale padding/margin by the scale factor.
    
    Args:
        base_padding: Base padding (for 1920x1080)
        scale: Scale factor
    
    Returns:
        Scaled padding
    """
    return max(1, int(base_padding * scale))


def get_window_dimensions(window) -> Tuple[int, int]:
    """
    Get window dimensions.
    
    Args:
        window: Tkinter window/widget
    
    Returns:
        Tuple of (width, height)
    """
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    
    # Fallback to geometry if winfo_width/height return 1
    if width <= 1 or height <= 1:
        try:
            geom = window.geometry()
            if 'x' in geom:
                parts = geom.split('+')[0].split('x')
                width = int(parts[0])
                height = int(parts[1])
        except:
            pass
    
    return max(800, width), max(600, height)

