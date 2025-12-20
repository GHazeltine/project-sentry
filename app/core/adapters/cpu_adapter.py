import logging
from nudenet import NudeDetector

class CPUAdapter:
    """
    Standard AI Adapter.
    Uses NudeNet (ONNX) on the CPU.
    Works on Raspberry Pi, Laptops, and Servers.
    """
    def __init__(self):
        logging.info("🧠 CPU Adapter: Loading NudeNet Model...")
        # This downloads the model automatically on first run
        self.detector = NudeDetector()
        logging.info("✅ CPU Adapter: Model Loaded.")

    def inference(self, image_path):
        """
        Scans an image for sensitive content.
        Returns: {'nsfw_score': 0.0-1.0, 'tags': [...]}
        """
        try:
            # Detect returns a list of detections: 
            # [{'class': 'EXPOSED_BREAST_F', 'score': 0.8}, ...]
            detections = self.detector.detect(image_path)
            
            nsfw_score = 0.0
            tags = []
            
            for d in detections:
                label = d.get('class', '')
                score = d.get('score', 0.0)
                
                # Check for sensitive classes
                if score > 0.40:  # 40% Confidence Threshold
                    tags.append(label)
                    # If it's a critical body part, boost the score
                    if 'GENITALIA' in label or 'BREAST' in label or 'BUTTOCKS' in label:
                        nsfw_score = max(nsfw_score, score)

            return {
                "hardware": "CPU (NudeNet)",
                "nsfw_score": nsfw_score,
                "tags": tags
            }
            
        except Exception as e:
            logging.error(f"❌ AI Inference Failed: {e}")
            return {"error": str(e), "nsfw_score": 0.0}
