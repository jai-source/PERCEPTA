from typing import Dict, Any

class EyeAnalyzer:
    def __init__(self):
        pass

    def analyze(self, frame: Any, face_bbox: list) -> Dict[str, Any]:
        return {
            "gaze_direction": "center",
            "is_blinking": False
        }
