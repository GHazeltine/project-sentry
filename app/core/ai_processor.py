import os
import sys
import numpy as np
from PIL import Image

# Global flag to track if we are on the Hailo Hardware
HAILO_AVAILABLE = False

try:
    # We attempt to import the Hailo Runtime. 
    # On your laptop, this will fail (triggering the except block).
    # On the Pi (once drivers are installed), this will succeed.
    import hailo_platform
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False

class AIProcessor:
    """
    Module F: The Visual Cortex
    Responsibility: Generate semantic 'Visual Vectors' for images.
    Hardware: Uses Hailo-8L NPU if available; falls back to CPU Perceptual Hashing if not.
    """

    def __init__(self):
        self.use_npu = HAILO_AVAILABLE
        self.model = None
        
        if self.use_npu:
            print("🧠 AI PROCESSOR: Hailo-8L Chip Detected. Initializing NPU...")
            self._init_hailo()
        else:
            print("🧠 AI PROCESSOR: No NPU detected. Falling back to CPU Visual Hashing.")

    def _init_hailo(self):
        """
        Placeholder for loading the compiled HEF (Hailo Executable Format) model.
        In production, we would load 'resnet_v1_50.hef' here.
        """
        # TODO: Load the actual HEF file path from config
        self.hef_path = "models/resnet_v1_50.hef"
        pass

    def get_visual_hash(self, image_path):
        """
        Returns a string representing the visual content of the image.
        """
        try:
            if self.use_npu:
                return self._process_on_hailo(image_path)
            else:
                return self._process_on_cpu(image_path)
        except Exception as e:
            # If an image is corrupt, don't crash the scanner, just skip visual tag.
            return "ERROR"

    def _process_on_hailo(self, image_path):
        """
        The Fast Path (Raspberry Pi 5 + Hailo).
        """
        # 1. Preprocess (Resize image to 224x224 for ResNet)
        # 2. Pass to NPU
        # 3. Get Vector
        # For now (since we don't have the physical chip to handshake), 
        # we return a placeholder signal that shows logic flow.
        return "HAILO_VECTOR_DATA"

    def _process_on_cpu(self, image_path):
        """
        The Fallback Path (Laptop / Standard CPU).
        Uses a simple 'Difference Hash' (dHash) to identify similar images.
        """
        try:
            # 1. Grayscale & Resize to 9x8
            img = Image.open(image_path).convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            
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
            
        except OSError:
            return "CORRUPT_IMG"
