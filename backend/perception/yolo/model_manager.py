import os
import urllib.request
from pathlib import Path

MODEL_URLS = {
    "yolov8n-hand.pt": "https://rndml-team-cv.obs.ru-moscow-1.hc.sbercloud.ru/datasets/hagrid_v2/models/YOLOv10n_gestures.pt",
    "yolov8n-face.pt": "https://github.com/akanametov/yolo-face/releases/download/1.0.0/yolov8n-face.pt",
}

class YoloModelManager:
    def __init__(self, model_name: str = "yolov8n.pt", models_dir: str = "models"):
        self.model_name = model_name
        self.models_dir = models_dir
        self.model_path = os.path.join(models_dir, model_name)
        
    def ensure_model(self) -> str:
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)
        if os.path.exists(self.model_path) and os.path.getsize(self.model_path) > 1_000_000:
            return self.model_path
        url = MODEL_URLS.get(self.model_name)
        if not url:
            return ""
        temporary_path = f"{self.model_path}.part"
        try:
            urllib.request.urlretrieve(url, temporary_path)
            if os.path.getsize(temporary_path) <= 1_000_000:
                raise ValueError("downloaded checkpoint is unexpectedly small")
            os.replace(temporary_path, self.model_path)
            return self.model_path
        except Exception:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
            return ""
