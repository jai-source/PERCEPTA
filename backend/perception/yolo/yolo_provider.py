from typing import Dict, Any, List
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

try:
    from backend.perception.yolo.model_manager import YoloModelManager
except ImportError:
    from .model_manager import YoloModelManager

class YoloProvider:
    def __init__(self, model_name: str = "yolov8n.pt", models_dir: str = "models"):
        self.manager = YoloModelManager(model_name, models_dir)
        self.model_path = self.manager.ensure_model()
        self.model_name = model_name
        self.device = "CPU"
        self.loaded = False
        self.error = None
        if YOLO is not None and self.model_path:
            try:
                self.model = YOLO(self.model_path)
                self.loaded = True
            except Exception as exc:
                self.model = None
                self.error = str(exc)
        elif YOLO is not None:
            self.model = None
            self.error = f"{model_name} is not cached in the local models directory"
            try:
                self.device = str(next(self.model.model.parameters()).device).upper()
            except Exception:
                pass
        else:
            self.model = None
            self.error = "ultralytics is not installed"

    def process(self, frame, imgsz: int = 320) -> List[Dict[str, Any]]:
        results = []
        if self.model is None:
            return results
            
        prediction = self.model(frame, verbose=False, imgsz=imgsz, conf=0.35, device=self.device.lower())[0]
        for box in prediction.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            name = self.model.names[cls_id]
            results.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": conf,
                "class_id": cls_id,
                "class_name": name
            })
            if getattr(prediction, "keypoints", None) is not None:
                points = prediction.keypoints.xy
                if len(points) > len(results) - 1:
                    results[-1]["keypoints"] = points[len(results) - 1].tolist()
        return results
