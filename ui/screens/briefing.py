"""Briefing screen shown before the loading screen"""
import json
from pathlib import Path
from tkinter import Tk, Canvas, NW, CENTER
from tkinter import ttk
from PIL import Image, ImageTk

# Get the directory where this script is located (go up from ui/screens to project root)
SCRIPT_DIR = Path(__file__).parent.parent.parent.absolute()
ASSETS = SCRIPT_DIR / "assets"
TEXT_PATH = SCRIPT_DIR / "briefing_text.json"

WINDOW_W, WINDOW_H = 1920, 1080


class BriefingScreen(Tk):
    """Briefing screen displayed before loading screen"""

    def __init__(self, on_next=None):
        super().__init__()
        self.title("LINEAGE // Briefing")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.configure(bg="#000000")
        
        # Try to force fullscreen, fallback to maximized if fullscreen not supported
        try:
            # Try fullscreen first
            self.attributes('-fullscreen', True)
        except Exception:
            try:
                # Fallback: maximize window
                self.state('zoomed')  # Windows
            except Exception:
                try:
                    self.attributes('-zoomed', True)  # Linux
                except Exception:
                    # macOS - just set geometry to screen size
                    pass

        # Style
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Next.TButton", padding=10, font=("Helvetica", 16),
                       foreground="#111", background="#ff7a00")
        style.map("Next.TButton", background=[("active", "#ff9933")])

        # Canvas with black fallback background
        self.canvas = Canvas(self, width=WINDOW_W, height=WINDOW_H,
                            highlightthickness=0, bg="#000000")
        self.canvas.pack(fill="both", expand=True)

        # Background image - load and draw FIRST, then send to back
        self.bg_photo = None
        try:
            # Try PNG first, then JPG
            IMG_PATH = ASSETS / "briefing_screen.png"
            if not IMG_PATH.exists():
                IMG_PATH = ASSETS / "briefing_screen.jpg"
            if not IMG_PATH.exists():
                IMG_PATH = ASSETS / "briefing_screen.jpeg"
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

        # Load text from JSON
        try:
            if TEXT_PATH.exists():
                data = json.loads(TEXT_PATH.read_text(encoding="utf-8"))
                header_text = data.get("header", "")
                subheader_text = data.get("subheader", "")
                body_lines = data.get("body", [])
                bold_lines = set(data.get("bold_lines", []))
            else:
                # Fallback if JSON file is missing
                header_text = "LINEAGE PROTOCOL — FIELD BRIEFING"
                subheader_text = "Briefing text not found."
                body_lines = []
                bold_lines = set()
                self.canvas.create_text(WINDOW_W // 2, WINDOW_H // 2,
                                       text="Warning: briefing_text.json not found",
                                       fill="#ff7a00", font=("Helvetica", 14))
        except Exception as e:
            header_text = "LINEAGE PROTOCOL — FIELD BRIEFING"
            subheader_text = f"Error loading text: {str(e)}"
            body_lines = []
            bold_lines = set()

        # Text settings
        text_color = "#ffffff"  # White text
        accent_color = "#ff7a00"  # Orange accent color
        header_font = ("Helvetica", 32, "bold")
        subheader_font = ("Helvetica", 18)
        body_font = ("Helvetica", 14)  # White text size
        body_bold_font = ("Helvetica", 16, "bold")  # Orange text size (larger)

        # Starting position
        start_x = 140
        start_y = 120
        y_cursor = start_y

        # Draw header (orange)
        if header_text:
            self.canvas.create_text(start_x, y_cursor, text=header_text,
                                   fill=accent_color, font=header_font, anchor=NW)
            y_cursor += 50

        # Draw subheader
        if subheader_text:
            self.canvas.create_text(start_x, y_cursor, text=subheader_text,
                                   fill=text_color, font=subheader_font, anchor=NW)
            y_cursor += 50

        # Draw body lines
        line_spacing = 24
        body_width = 900  # Max width for text wrapping
        
        # Track step numbers for bold lines
        step_number = 1

        for line in body_lines:
            if line.strip() == "":
                y_cursor += line_spacing // 2  # Smaller gap for blank lines
                continue

            # Check if this line should be bold/orange
            is_bold = line.strip() in bold_lines
            
            # Add step number to bold lines
            if is_bold:
                display_text = f"{step_number}. {line}"
                step_number += 1
            else:
                display_text = line
            
            font_to_use = body_bold_font if is_bold else body_font

            # Simple wrapping if line is too long
            if len(display_text) > 100:
                # Basic word wrap
                words = display_text.split()
                current_line = []
                current_length = 0

                for word in words:
                    test_line = " ".join(current_line + [word])
                    if len(test_line) > 100 and current_line:
                        # Draw current line
                        line_color = accent_color if is_bold else text_color
                        self.canvas.create_text(start_x, y_cursor,
                                               text=" ".join(current_line),
                                               fill=line_color, font=font_to_use,
                                               anchor=NW)
                        y_cursor += line_spacing
                        current_line = [word]
                        current_length = len(word)
                    else:
                        current_line.append(word)
                        current_length = len(test_line)

                # Draw remaining words
                if current_line:
                    line_color = accent_color if is_bold else text_color
                    self.canvas.create_text(start_x, y_cursor,
                                           text=" ".join(current_line),
                                           fill=line_color, font=font_to_use,
                                           anchor=NW)
                    y_cursor += line_spacing
            else:
                # Line fits, draw directly
                line_color = accent_color if is_bold else text_color
                self.canvas.create_text(start_x, y_cursor, text=display_text,
                                       fill=line_color, font=font_to_use,
                                       anchor=NW)
                y_cursor += line_spacing

        # Briefing image on the right side
        self.briefing_img_photo = None
        try:
            # Try PNG first, then JPG
            BRIEFING_IMG_PATH = ASSETS / "briefing_png.png"
            if not BRIEFING_IMG_PATH.exists():
                BRIEFING_IMG_PATH = ASSETS / "briefing_png.jpg"
            if not BRIEFING_IMG_PATH.exists():
                BRIEFING_IMG_PATH = ASSETS / "briefing_png.jpeg"
            if BRIEFING_IMG_PATH.exists():
                briefing_img = Image.open(BRIEFING_IMG_PATH).convert("RGB")
                img_iw, img_ih = briefing_img.size
                # Scale image - reduced width by ~7.5% (from 600 to ~555), maintain aspect ratio
                target_width = 555  # Reduced from 600 (about 7.5% smaller)
                scale = target_width / img_iw
                img_new_w, img_new_h = int(img_iw * scale), int(img_ih * scale)
                briefing_img_resized = briefing_img.resize((img_new_w, img_new_h), Image.LANCZOS)
                self.briefing_img_photo = ImageTk.PhotoImage(briefing_img_resized)
                # Position shifted leftward by ~12% of original gap (was 80px gap, now smaller)
                # Let it overlap into central space - reduce gap between text and image
                img_x = start_x + body_width + 40  # Reduced from 80 to 40 (shifted left ~50%)
                # Calculate the exact middle of the text block (from start_y to y_cursor)
                text_middle_y = (start_y + y_cursor) / 2
                # Since anchor=NW, adjust Y position so image center aligns with text middle
                img_y = text_middle_y - (img_new_h / 2)
                self.briefing_img_id = self.canvas.create_image(img_x, img_y, image=self.briefing_img_photo, anchor=NW)
                
                # Optional: Add faint vertical divider at old image boundary (where gap was ~80px)
                old_boundary_x = start_x + body_width + 80
                divider_y_start = start_y - 10
                divider_y_end = y_cursor + 10
                # Soft orange glow, low opacity (~40%)
                self.canvas.create_line(
                    old_boundary_x, divider_y_start,
                    old_boundary_x, divider_y_end,
                    fill="#ff7a00", width=1, stipple="gray60"
                )
        except Exception:
            # Continue without briefing image if it fails
            pass

        # Next button (moved up to match loading screen button position)
        self.on_next = on_next
        btn_x, btn_y = WINDOW_W // 2, WINDOW_H - 180  # Moved up from -80
        self.next_btn = ttk.Button(self, text="NEXT", style="Next.TButton",
                                   command=self._next)
        self.canvas.create_window(btn_x, btn_y, window=self.next_btn, anchor=CENTER)
        
        # Ensure background image stays at the back after all elements are created
        if hasattr(self, 'bg_image_id'):
            self.canvas.tag_lower(self.bg_image_id)

    def _next(self):
        """Handle NEXT button press"""
        if callable(self.on_next):
            # Pass self (the window) to the callback
            self.on_next(self)


# Convenience: run standalone for testing
if __name__ == "__main__":
    def _demo():
        print("NEXT pressed")

    BriefingScreen(on_next=_demo).mainloop()

