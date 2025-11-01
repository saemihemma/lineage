"""Theme constants for UI styling"""
from ui.scaling import get_scale_factor, scale_font, scale_padding, get_window_dimensions
from typing import Tuple

# Colors
BG = "#0b0f12"
PANEL = "#11161a"
BORDER = "#151a1f"
TEXT = "#e7e7e7"
MUTED = "#9aa4ad"
ACCENT = "#ff7a00"
ACCENT_2 = "#ff9933"

# Base spacing (for 1920x1080)
PADDING_SM_BASE = 4
PADDING_MD_BASE = 8
PADDING_LG_BASE = 12

# Base fonts (for 1920x1080)
FONT_BODY_BASE = ("Helvetica", 9)
FONT_HEADING_BASE = ("Helvetica", 11, "bold")
FONT_MONO_BASE = ("Consolas", 9)

# Styles (can be used with ttk.Style)
STYLE_H1 = "Title.TLabel"
STYLE_H2 = "Panel.TLabel"
STYLE_BODY = "TLabel"
STYLE_MONO = "Mono.TLabel"


def get_scaled_values(window) -> dict:
    """
    Get scaled theme values for a window.
    
    Args:
        window: Tkinter window/widget
    
    Returns:
        Dictionary with scaled padding and font values
    """
    width, height = get_window_dimensions(window)
    scale = get_scale_factor(width, height)
    
    return {
        "PADDING_SM": scale_padding(PADDING_SM_BASE, scale),
        "PADDING_MD": scale_padding(PADDING_MD_BASE, scale),
        "PADDING_LG": scale_padding(PADDING_LG_BASE, scale),
        "FONT_BODY": (FONT_BODY_BASE[0], scale_font(FONT_BODY_BASE[1], scale)),
        "FONT_HEADING": (FONT_HEADING_BASE[0], scale_font(FONT_HEADING_BASE[1], scale), "bold"),
        "FONT_MONO": (FONT_MONO_BASE[0], scale_font(FONT_MONO_BASE[1], scale)),
    }


# Backward compatibility - expose base values as defaults
PADDING_SM = PADDING_SM_BASE
PADDING_MD = PADDING_MD_BASE
PADDING_LG = PADDING_LG_BASE
FONT_BODY = FONT_BODY_BASE
FONT_HEADING = FONT_HEADING_BASE
FONT_MONO = FONT_MONO_BASE
