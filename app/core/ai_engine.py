import os
import logging

class AIEngine:
    """
    The Universal AI Wrapper.
    Automatically detects hardware (Hailo NPU vs Standard CPU)
    and loads the appropriate driver adapter.
    """
    def __init__(self):
        self.mode = "CPU"
        self.adapter = None
        self._detect_hardware()

    def _detect_hardware(self):
        # 1. Check for Raspberry Pi Hailo Hardware
        if os.path.exists("/dev/hailo0"):
            try:
                from app.core.adapters.hailo_adapter import HailoAdapter
                self.adapter = HailoAdapter()
                self.mode = "HAILO-8L (NPU)"
                logging.info("✅ AI Engine: Hailo-8L NPU engaged.")
                return
            except ImportError:
                logging.warning("⚠️ AI Engine: Hailo device found, but libraries missing. Falling back to CPU.")
        
        # 2. Fallback to CPU
        from app.core.adapters.cpu_adapter import CPUAdapter
        self.adapter = CPUAdapter()
        self.mode = "STANDARD (CPU)"
        logging.info("ℹ️ AI Engine: Running in Standard CPU Mode.")

    def analyze_image(self, image_path):
        if not self.adapter:
            return {'error': 'No AI Adapter Loaded'}
        return self.adapter.inference(image_path)
