from typing import Dict, Any, List
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

try:
    import torch
except ImportError:
    torch = None

try:
    from backend.perception.yolo.model_manager import YoloModelManager
    from backend.config import config as _config
except ImportError:
    from .model_manager import YoloModelManager
    from ...config import config as _config


# Cache the CUDA availability check — calling torch.cuda.is_available()
# repeatedly is a known source of multi-second stalls on machines with a
# mismatched/broken NVIDIA driver.
_CUDA_AVAILABLE: bool | None = None


def _cuda_available() -> bool:
    """Check CUDA availability exactly once per process, with driver-level
    exception fallback to CPU."""
    global _CUDA_AVAILABLE
    if _CUDA_AVAILABLE is None:
        try:
            _CUDA_AVAILABLE = bool(torch is not None and torch.cuda.is_available())
        except Exception:
            _CUDA_AVAILABLE = False
    return _CUDA_AVAILABLE


def _resolve_device(requested: str) -> str:
    """Resolve 'auto'/'cpu'/'cuda' against actual hardware availability."""
    requested = (requested or "auto").lower()
    has_cuda = _cuda_available()
    if requested == "cuda":
        return "cuda" if has_cuda else "cpu"
    if requested == "cpu":
        return "cpu"
    return "cuda" if has_cuda else "cpu"  # auto


class YoloProvider:
    def __init__(self, model_name: str = "yolov8n.pt", models_dir: str = "models"):
        self.manager = YoloModelManager(model_name, models_dir)
        self.model_path = self.manager.ensure_model()
        self.model_name = model_name
        self.device = _resolve_device(getattr(_config, "device", "auto")).upper()
        self.loaded = False
        self.error = None
        if YOLO is not None and self.model_path:
            try:
                self.model = YOLO(self.model_path)
                if self.device == "CUDA":
                    self.model.to("cuda")
                self.loaded = True
            except Exception as exc:
                self.model = None
                self.error = str(exc)
        elif YOLO is not None:
            self.model = None
            self.error = f"{model_name} is not cached in the local models directory"
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