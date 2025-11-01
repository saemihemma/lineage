# loading_screen.py
import json
import textwrap
import os
import random
import time
from pathlib import Path
from tkinter import Tk, Canvas, NW, CENTER
from tkinter import ttk, Entry, Label
import tkinter as tk
from PIL import ImageFont
from core.state_manager import load_state, save_state

# Get the directory where this script is located (go up from ui/screens to project root)
SCRIPT_DIR = Path(__file__).parent.parent.parent.absolute()
ASSETS = SCRIPT_DIR / "assets"
FONT_PATH = ASSETS / "Orbitron-Regular.ttf"  # optional; falls back if missing
TEXT_PATH = SCRIPT_DIR / "loading_text.json"
MESSAGES_PATH = SCRIPT_DIR / "loading_messages.json"

WINDOW_W, WINDOW_H = 1920, 1080

# --- font helpers ------------------------------------------------------------
def load_font(size: int):
    try:
        return ImageFont.truetype(str(FONT_PATH), size)
    except Exception:
        # Tk default if TTF missing
        return None

# --- text measurement for wrapping (Pillow for accurate width) ---------------
def wrap_by_pixels(text: str, font: ImageFont.FreeTypeFont, max_px: int):
    """Wrap text respecting paragraphs, with better word breaking"""
    if not text:
        return []
    lines = []
    paragraphs = text.split("\n\n")  # Split by paragraph breaks
    
    for para_idx, paragraph in enumerate(paragraphs):
        if para_idx > 0:
            lines.append("")  # Add blank line between paragraphs
        
        # Handle single newlines within paragraphs
        for line_segment in paragraph.split("\n"):
            if not line_segment.strip():
                if lines and lines[-1]:  # Only add blank if previous line wasn't blank
                    lines.append("")
                continue
            
            words = line_segment.split()
            cur = []
            for w in words:
                test = (" ".join(cur + [w])).strip()
                # Better width estimation: use font if available, otherwise estimate
                if font:
                    w_px = font.getlength(test)
                else:
                    # Rough estimate: ~8-9 pixels per character for Helvetica 20pt
                    w_px = len(test) * 8.5
                
                if w_px <= max_px or not cur:
                    cur.append(w)
                else:
                    if cur:  # Only add if we have words
                        lines.append(" ".join(cur))
                    cur = [w]
            
            if cur:
                lines.append(" ".join(cur))
    
    return lines

# --- main UI -----------------------------------------------------------------
class LoadingScreen(Tk):
    def __init__(self, on_enter=None):
        super().__init__()
        self.title("LINEAGE // Loading")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.configure(bg="#000000")
        
        # Try to set fullscreen (will be overridden by main.py if previous window was fullscreen)
        try:
            self.attributes('-fullscreen', True)
        except Exception:
            try:
                self.state('zoomed')  # Windows
            except Exception:
                try:
                    self.attributes('-zoomed', True)  # Linux
                except Exception:
                    pass

        # style
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Enter.TButton", padding=10, font=("Helvetica", 16), foreground="#111",
                        background="#ff7a00")
        style.map("Enter.TButton", background=[("active", "#ff9933")])

        # canvas with black fallback background
        self.canvas = Canvas(self, width=WINDOW_W, height=WINDOW_H, highlightthickness=0, bg="#000000")
        self.canvas.pack(fill="both", expand=True)

        # Background image - load and draw FIRST, then send to back
        self.bg_photo = None
        x, y = 0, 0  # Initialize for use in text positioning
        try:
            from PIL import Image, ImageTk
            IMG_PATH = ASSETS / "loading_base.png"
            if IMG_PATH.exists():
                img = Image.open(IMG_PATH).convert("RGB")
                iw, ih = img.size
                # Scale to fit window (fit mode, maintains aspect ratio)
                scale = min(WINDOW_W / iw, WINDOW_H / ih)
                new_w, new_h = int(iw * scale), int(ih * scale)
                img_resized = img.resize((new_w, new_h), Image.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(img_resized)  # Store reference to prevent GC
                # Center the image
                x = (WINDOW_W - new_w) // 2
                y = (WINDOW_H - new_h) // 2
                self.bg_image_id = self.canvas.create_image(x, y, image=self.bg_photo, anchor=NW)
                # Force image to stay at the back (behind all other elements)
                self.canvas.tag_lower(self.bg_image_id)
            else:
                # Fallback: keep black background
                pass
        except Exception:
            # Fallback: keep black background
            pass

        # load text
        try:
            if TEXT_PATH.exists():
                data = json.loads(TEXT_PATH.read_text(encoding="utf-8"))
                header_lines = data.get("header", [])
                body_text = data.get("body", "")
            else:
                # Fallback if JSON file is missing
                header_lines = ["Loading..."]
                body_text = "loading_text.json not found. Please ensure the file exists."
                self.canvas.create_text(WINDOW_W // 2, WINDOW_H // 2 + 100,
                                       text="Warning: loading_text.json not found",
                                       fill="#ff7a00", font=("Helvetica", 14))
        except Exception as e:
            # Fallback if JSON parsing fails
            header_lines = ["Loading..."]
            body_text = f"Error loading text: {str(e)}"
            self.canvas.create_text(WINDOW_W // 2, WINDOW_H // 2 + 100,
                                   text=f"Error: {str(e)}",
                                   fill="#ff7a00", font=("Helvetica", 14))

        # fonts
        header_font_pillow = load_font(26)
        body_font_pillow = load_font(22)

        # --- Zone A: header block (top-left) ---------------------------------
        header_x, header_y = x + 140, y + 80  # Moved higher vertically (was 140, now 80)
        header_color = "#e8dcc0"
        
        # Store initial positions for background calculation
        text_start_y = header_y
        
        # Use better font if available
        header_font_size = 18  # Slightly smaller for rest of header (was 22)
        header_font_tuple = ("Helvetica", header_font_size, "bold") if header_font_pillow is None else None
        header_line_spacing = 28  # Slightly tighter spacing

        # Calculate text dimensions first (to determine background size)
        body_w_px = 780
        body_x = header_x
        
        # Text wrapping for body (to estimate final height)
        if body_font_pillow is None:
            wrapped = wrap_by_pixels(body_text, None, body_w_px)
        else:
            wrapped = wrap_by_pixels(body_text, body_font_pillow, body_w_px)

        # Estimate final text height
        estimated_height = 0
        estimated_height += 40  # First header line
        estimated_height += len(header_lines) * header_line_spacing  # Rest of header
        estimated_height += 30  # Gap
        body_line_spacing = 18
        for line in wrapped:
            if line.strip():
                estimated_height += body_line_spacing
            else:
                estimated_height += body_line_spacing // 2
        
        # Draw transparent black background BEFORE text (so it appears behind)
        # Fixed coordinates - not tied to text width
        text_start_x = header_x - 20  # 20px padding left
        text_end_x = header_x + body_w_px + 5 - 300  # Right edge position (EDIT THIS VALUE to adjust box width: smaller number = wider, larger number = narrower)
        text_bg_y = text_start_y - 20  # 20px padding top
        text_end_y = text_start_y + estimated_height + 5  # Reduced bottom padding from 10px to 5px
        
        # Create semi-transparent black background using PIL with alpha channel
        from PIL import Image, ImageTk
        bg_width = int(text_end_x - text_start_x)
        bg_height = int(text_end_y - text_bg_y)
        # Create RGBA image with black and transparency (128 = 50% opacity)
        bg_image = Image.new("RGBA", (bg_width, bg_height), (0, 0, 0, 128))
        bg_photo = ImageTk.PhotoImage(bg_image)
        bg_rect_id = self.canvas.create_image(
            text_start_x, text_bg_y,
            image=bg_photo, anchor=NW
        )
        # Store reference to prevent garbage collection
        self.bg_text_photo = bg_photo
        # Ensure background is behind all text elements
        self.canvas.tag_lower(bg_rect_id)

        # draw header lines with better spacing
        y_cursor = header_y
        for i, line in enumerate(header_lines):
            if line.strip():  # Skip empty lines
                # Make first line (Incarnation Information) larger
                if i == 0 and ("Incarnation" in line.strip() or "Incarnation Information" in line.strip()):
                    font_to_use = ("Helvetica", 32, "bold") if header_font_pillow is None else None  # Larger font
                    self.canvas.create_text(header_x, y_cursor, text=line, fill=header_color,
                                            font=font_to_use, anchor=NW)
                    y_cursor += 40  # Extra breathing space after title
                else:
                    font_to_use = header_font_tuple
                    self.canvas.create_text(header_x, y_cursor, text=line, fill=header_color,
                                            font=font_to_use, anchor=NW)
                    y_cursor += header_line_spacing

        # --- Zone B: body block (left side, under header) -------------------------------
        body_y = y_cursor + 30  # Moved up from 40

        # Text settings
        body_line_spacing = 18  # Reduced from 20
        body_font_size = 12  # Reduced from 13
        text_color = "#e8dcc0"
        body_font_tuple = ("Helvetica", body_font_size) if body_font_pillow is None else None
        
        # Draw body text with paragraph spacing
        y_cursor = body_y
        prev_was_blank = False
        for line in wrapped:
            if line.strip():
                self.canvas.create_text(body_x, y_cursor, text=line, fill=text_color,
                                       font=body_font_tuple, anchor=NW)
                y_cursor += body_line_spacing
                prev_was_blank = False
            else:
                # Add extra space for paragraph breaks (only if not consecutive blanks)
                if not prev_was_blank:
                    y_cursor += body_line_spacing // 2
                prev_was_blank = True

        # --- Enter button, IDENTITY field, and Loading bar ---------------------
        self.on_enter = on_enter
        
        # Load existing SELF name from state
        existing_name = ""
        try:
            p = load_state()
            existing_name = p.self_name if p.self_name else ""
        except Exception:
            pass
        
        # Load loading messages
        try:
            if MESSAGES_PATH.exists():
                messages_data = json.loads(MESSAGES_PATH.read_text(encoding="utf-8"))
                all_messages = messages_data.get("messages", [])
                self.loading_messages = all_messages if all_messages else ["Loading...", "Preparing simulation..."]
            else:
                self.loading_messages = ["Loading...", "Preparing simulation..."]
        except Exception:
            self.loading_messages = ["Loading...", "Preparing simulation..."]
        
        # Button position
        btn_x, btn_y = WINDOW_W // 2, WINDOW_H - 180
        
        # IDENTITY field above button
        identity_label_y = btn_y - 75
        identity_entry_y = btn_y - 50
        
        # Label for IDENTITY
        identity_label = Label(self, text="IDENTITY", 
                              bg="#000000", fg="#e8dcc0", 
                              font=("Helvetica", 11))
        self.canvas.create_window(btn_x, identity_label_y, window=identity_label, anchor=CENTER)
        
        # Text entry field for IDENTITY
        self.name_var = tk.StringVar(value=existing_name)
        identity_entry = Entry(self, textvariable=self.name_var,
                              bg="#0b0f12", fg="#e8dcc0",
                              font=("Helvetica", 12),
                              borderwidth=1, relief="solid",
                              width=30)
        identity_entry.configure(insertbackground="#ff7a00")
        self.canvas.create_window(btn_x, identity_entry_y, window=identity_entry, anchor=CENTER)
        
        # Enter button (disabled initially - needs name AND loading complete)
        self.enter_btn = ttk.Button(self, text="ENTER SIMULATION", style="Enter.TButton",
                                    command=self._enter, state="disabled")
        self.canvas.create_window(btn_x, btn_y, window=self.enter_btn, anchor=CENTER)
        
        # Loading bar (below button)
        progress_y = btn_y + 70
        progress_width = 400
        progress_height = 20
        
        # Background rectangle
        self.progress_bar_bg = self.canvas.create_rectangle(
            btn_x - progress_width // 2, progress_y - progress_height // 2,
            btn_x + progress_width // 2, progress_y + progress_height // 2,
            fill="#11161a", outline="#151a1f", width=1
        )
        # Fill rectangle - start with 1px width so it's visible
        self.progress_bar_fill = self.canvas.create_rectangle(
            btn_x - progress_width // 2, progress_y - progress_height // 2,
            btn_x - progress_width // 2 + 1, progress_y + progress_height // 2,
            fill="#ff7a00", outline=""
        )
        # Percentage text
        self.progress_bar_text = self.canvas.create_text(
            btn_x, progress_y,
            text="0%",
            fill="#e8dcc0", font=("Helvetica", 11, "bold"),
            anchor=CENTER
        )
        
        # Message text (below loading bar)
        self.message_label = self.canvas.create_text(btn_x, progress_y + 45,
                                                    text="",
                                                    fill="#e8dcc0", font=("Helvetica", 12),
                                                    anchor=CENTER)
        
        # Loading state
        self.loading_progress = 0
        self.loading_duration = random.randint(25, 30)
        self.loading_start_time = time.time()
        self.message_update_interval = random.randint(4, 5)
        self.last_message_update = time.time()
        
        # Show first message
        if self.loading_messages:
            self.canvas.itemconfig(self.message_label, text=random.choice(self.loading_messages))
        
        # Track name entry and loading status for button enable/disable
        def on_name_change(*args):
            """Enable/disable button based on name entry and loading status"""
            name_value = self.name_var.get().strip()
            if name_value and self.loading_progress >= 100:
                self.enter_btn.config(state="normal")
            else:
                self.enter_btn.config(state="disabled")
        
        self.on_name_change = on_name_change
        self.name_var.trace("w", on_name_change)
        on_name_change()  # Initial check
        
        # Ensure image stays at the back
        if hasattr(self, 'bg_image_id'):
            self.canvas.tag_lower(self.bg_image_id)
        
        # Force canvas to update so progress bar is visible
        self.canvas.update_idletasks()
        
        # Start loading animation
        self._update_loading()
    
    def _enter(self):
        """Handle enter button press"""
        # Validate name is entered (button should be disabled if not, but double-check)
        name_value = self.name_var.get().strip()
        if not name_value:
            return  # Don't proceed without name
        
        # Save SELF name to state before entering
        try:
            p = load_state()
            p.self_name = name_value
            save_state(p)
        except Exception:
            pass  # Continue even if save fails
        
        if callable(self.on_enter):
            self.on_enter()
    
    def _update_loading(self):
        """Update loading bar and messages"""
        if not hasattr(self, 'progress_bar_fill'):
            self.after(50, self._update_loading)
            return
        
        elapsed = time.time() - self.loading_start_time
        progress = min(100, int((elapsed / self.loading_duration) * 100))
        self.loading_progress = progress
        
        # Update progress bar fill
        bar_width = 400
        fill_width = max(1, int((progress / 100) * bar_width))  # At least 1px visible
        btn_x = WINDOW_W // 2
        progress_y = WINDOW_H - 180 + 70
        
        fill_left = btn_x - bar_width // 2
        fill_right = btn_x - bar_width // 2 + fill_width
        fill_top = progress_y - 10
        fill_bottom = progress_y + 10
        
        # Update canvas items
        self.canvas.coords(self.progress_bar_fill, fill_left, fill_top, fill_right, fill_bottom)
        self.canvas.itemconfig(self.progress_bar_text, text=f"{progress}%")
        
        # Update message periodically
        if time.time() - self.last_message_update >= self.message_update_interval:
            if self.loading_messages:
                self.canvas.itemconfig(self.message_label, text=random.choice(self.loading_messages))
                self.message_update_interval = random.randint(4, 5)
            self.last_message_update = time.time()
        
        # Complete or continue
        if progress >= 100:
            self.loading_progress = 100
            self.canvas.itemconfig(self.message_label, text="Ready")
            self.on_name_change()
        else:
            self.after(50, self._update_loading)

# convenience: run standalone for testing
if __name__ == "__main__":
    def _demo():
        print("ENTER SIMULATION pressed")
    LoadingScreen(on_enter=_demo).mainloop()

