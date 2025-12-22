import os
import sys
import numpy as np
from PIL import Image

# Global flag to track if we are on the Hailo Hardware
HAILO_AVAILABLE = False

try:
    import hailo_platform
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False

class AIProcessor:
    """
    Module F: The Visual Cortex
    Responsibility: Generate semantic 'Visual Vectors' for images.
    """

    def __init__(self):
        self.use_npu = HAILO_AVAILABLE
        
        if self.use_npu:
            print("🧠 AI PROCESSOR: Hailo-8L Chip Detected. Initializing NPU...")
        else:
            print("🧠 AI PROCESSOR: No NPU detected. Falling back to CPU Visual Hashing.")

    def get_visual_hash(self, image_path):
        """
        Main entry point. Returns a Hex String representing the image content.
        Returns None if image is corrupt or unreadable.
        """
        if self.use_npu:
            return self._process_on_hailo(image_path)
        else:
            return self._process_on_cpu(image_path)

    def _process_on_hailo(self, image_path):
        # Placeholder for NPU logic
        return None

    def _process_on_cpu(self, image_path):
        """
        Uses dHash (Difference Hash). 
        Robust to resizing, color changes, and minor edits.
        """
        try:
            # 1. Load, Grayscale, Resize to 9x8
            # We use try/except block to catch corrupt images (like the one that crashed you)
            with Image.open(image_path) as img:
                img = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
                
                # 2. Compare pixels
                pixels = list(img.getdata())
                difference = []
                for row in range(8):
                    for col in range(8):
                        pixel_left = pixels[row * 9 + col]
                        pixel_right = pixels[row * 9 + col + 1]
                        difference.append(pixel_left > pixel_right)
                
                # 3. Convert to Hex String
                decimal_value = 0
                for index, value in enumerate(difference):
                    if value:
                        decimal_value += 2**index
                
                return hex(decimal_value)[2:]
                
        except Exception as e:
            # If image is corrupt, return None (Safely ignored by Organizer)
            # print(f"Warning: Could not process {image_path}: {e}")
            return None
