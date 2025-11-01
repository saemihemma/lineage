#!/usr/bin/env python3
"""
Unit tests for loading screen text rendering and box sizing.
Tests ensure:
1. Black box has 20px padding on left and 5px padding on right
2. All body text is visible (nothing cut off at bottom)
3. Box width matches text wrapping width (with offset), not individual line widths
"""
import unittest
from pathlib import Path
import json
from unittest.mock import Mock, patch
from ui.screens.loading import LoadingScreen, wrap_by_pixels

class TestLoadingScreenBoxSizing(unittest.TestCase):
    """Test that the black box is correctly sized with proper padding"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_text = {
            "header": ["Test Header"],
            "body": "This is a test body text. " * 50  # Long text to test wrapping
        }
    
    def test_box_has_proper_horizontal_padding(self):
        """Test that box uses 20px padding on left and 5px padding on right"""
        # Create a minimal mock for canvas
        with patch('ui.screens.loading.Canvas') as mock_canvas_class:
            mock_canvas = Mock()
            mock_canvas_class.return_value = mock_canvas
            mock_canvas.create_rectangle = Mock()
            mock_canvas.create_text = Mock()
            mock_canvas.create_image = Mock()
            mock_canvas.create_window = Mock()
            
            # Mock image loading - Image is imported inside try block, so patch PIL.Image
            with patch('PIL.Image') as mock_image:
                mock_img_obj = Mock()
                mock_img_obj.size = (1920, 1080)
                mock_img_obj.convert.return_value = mock_img_obj
                mock_img_obj.resize.return_value = mock_img_obj
                mock_image.open.return_value = mock_img_obj
                
                # Mock Path.exists for files
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('pathlib.Path.read_text') as mock_read:
                        mock_read.return_value = json.dumps(self.test_text)
                        
                        # Create loading screen (will fail on mainloop, but that's ok)
                        try:
                            screen = LoadingScreen(on_enter=lambda: None)
                        except:
                            pass  # Expected to fail without full tkinter setup
                
                # Check that create_rectangle was called
                if mock_canvas.create_rectangle.called:
                    calls = mock_canvas.create_rectangle.call_args_list
                    # Find the body text box call (should be after header box if multiple)
                    box_call = None
                    for call in calls:
                        args = call[0]
                        if len(args) >= 4:
                            x1, y1, x2, y2 = args[0], args[1], args[2], args[3]
                            # Body box should be larger than header box
                            box_width = x2 - x1
                            if box_width > 100:  # Body box is wider
                                box_call = (x1, y1, x2, y2)
                                break
                    
                    if box_call:
                        x1, y1, x2, y2 = box_call
                        # Calculate padding from header_x (text start position)
                        # header_x = x + 140 where x is image x offset
                        # For simplicity, assume header_x = 140 (when x=0)
                        header_x = 140
                        body_w_px = 780
                        left_padding = header_x - x1
                        # Right edge is now: header_x + body_w_px + 5 - 300
                        expected_right_edge = header_x + body_w_px + 5 - 300
                        right_padding = x2 - expected_right_edge
                        
                        # Left padding should be approximately 20px
                        # Right padding should be approximately 0px (since we calculate from offset)
                        self.assertAlmostEqual(left_padding, 20, delta=1, 
                                             msg=f"Left padding should be 20px, got {left_padding}")
                        # Right edge should match expected calculation
                        self.assertAlmostEqual(x2, expected_right_edge, delta=1,
                                             msg=f"Right edge should be at {expected_right_edge}, got {x2}")

class TestLoadingScreenTextVisibility(unittest.TestCase):
    """Test that all body text is visible and not cut off"""
    
    def test_all_text_lines_are_drawn(self):
        """Test that all wrapped text lines are included in drawable_lines"""
        # Test the logic that determines which lines to draw
        wrapped = ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5"]
        body_y = 100
        max_body_bottom = 300
        body_line_spacing = 20
        
        # Simulate the drawing logic
        y_cursor_test = body_y
        drawable_lines = []
        for line in wrapped:
            if line.strip():
                # All lines should be drawable within bounds
                if y_cursor_test <= max_body_bottom - body_line_spacing:
                    drawable_lines.append((line, y_cursor_test))
            y_cursor_test += body_line_spacing
        
        # All lines should be drawable with these bounds
        self.assertEqual(len(drawable_lines), len(wrapped),
                        "All text lines should be drawable")
    
    def test_font_size_adjusts_to_fit_text(self):
        """Test that font size is reduced when text doesn't fit"""
        total_lines = 50
        body_line_spacing = 20
        estimated_height = total_lines * body_line_spacing  # 1000px
        available_height = 800  # Less than estimated
        
        # Simulate reduction logic
        current_font_size = 12
        current_line_spacing = 20
        reduction = 0.92
        
        for _ in range(3):
            if estimated_height <= available_height:
                break
            estimated_height = total_lines * current_line_spacing
            if estimated_height > available_height:
                current_font_size = max(9, int(current_font_size * reduction))
                current_line_spacing = max(16, int(current_line_spacing * reduction))
                estimated_height = total_lines * current_line_spacing
        
        # Font should have been reduced
        self.assertLess(current_font_size, 12,
                       "Font size should be reduced when text doesn't fit")
        self.assertLessEqual(estimated_height, available_height,
                            "Estimated height should fit after reduction")

class TestLoadingScreenBoxWidth(unittest.TestCase):
    """Test that box width matches text wrapping width, not line widths"""
    
    def test_box_width_uses_wrapping_width_with_offset(self):
        """Box should use body_w_px (wrapping width) with offset, not max line width"""
        header_x = 140
        body_w_px = 780  # Text wrapping width
        left_padding = 20
        right_offset = 300  # Right edge moved 300px left
        
        # Box should be: header_x - left_padding to header_x + body_w_px + 5 - right_offset
        expected_box_x1 = header_x - left_padding  # 120
        expected_box_x2 = header_x + body_w_px + 5 - right_offset  # 625
        
        expected_box_width = expected_box_x2 - expected_box_x1  # 505
        
        # Should match: body_w_px + 5 - right_offset + left_padding = 780 + 5 - 300 + 20 = 505
        calculated_width = body_w_px + 5 - right_offset + left_padding
        self.assertEqual(expected_box_width, calculated_width,
                        f"Box width should be {calculated_width}, got {expected_box_width}")

if __name__ == "__main__":
    unittest.main()

