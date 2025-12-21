import os
import logging

class AIEngine:
    def __init__(self):
        self.mode = "CPU"
        self.adapter = None
        self._detect_hardware()

    def _detect_hardware(self):
        # FORCE CPU MODE for current testing phase
        from app.core.adapters.cpu_adapter import CPUAdapter
        self.adapter = CPUAdapter()
        self.mode = "STANDARD (CPU)"
        logging.info("ℹ️ AI Engine: Running in Standard CPU Mode.")

    def analyze_image(self, image_path):
        if not self.adapter:
            return {'error': 'No AI Adapter Loaded'}
        return self.adapter.inference(image_path)
