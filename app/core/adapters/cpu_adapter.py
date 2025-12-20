class CPUAdapter:
    def inference(self, image_path):
        # Placeholder: We will add TensorFlow Lite/ONNX here later
        return {
            "hardware": "CPU",
            "nsfw_score": 0.0,
            "tags": ["cpu_mode_active"]
        }
