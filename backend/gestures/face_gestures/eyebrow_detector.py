from typing import Any, Dict
import numpy as np
from ..base import BaseGestureDetector

class EyebrowDetector(BaseGestureDetector):
    def __init__(self):
        self.baseline_distance = None

    def detect(self, landmarks: Any) -> Dict[str, Any]:
        if not landmarks or 'left_eyebrow' not in landmarks or 'left_eye' not in landmarks:
            return {"gesture": "none", "confidence": 0.0}
            
        eyebrow_center = np.mean(landmarks['left_eyebrow'], axis=0)
        eye_center = np.mean(landmarks['left_eye'], axis=0)
        
        distance = np.linalg.norm(eyebrow_center - eye_center)
        
        if self.baseline_distance is None:
            self.baseline_distance = distance
            return {"gesture": "none", "confidence": 0.0}
            
        ratio = distance / self.baseline_distance
        
        if ratio > 1.2:
            return {"gesture": "eyebrow_raise", "confidence": min(1.0, (ratio - 1.2) * 2)}
        elif ratio < 0.9:
            return {"gesture": "eyebrow_furrow", "confidence": min(1.0, (0.9 - ratio) * 5)}
            
        return {"gesture": "none", "confidence": 0.0}
