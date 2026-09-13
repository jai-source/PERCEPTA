from typing import Any, Dict
from ..base import BaseGestureDetector

class StaticHandGestureDetector(BaseGestureDetector):
    def __init__(self):
        self.gestures = {
            "open_palm": self._is_open_palm,
            "closed_fist": self._is_closed_fist,
            "peace_sign": self._is_peace_sign,
            "thumbs_up": self._is_thumbs_up
        }

    def detect(self, landmarks: Any) -> Dict[str, Any]:
        if not landmarks or 'hand' not in landmarks:
            return {"gesture": "none", "confidence": 0.0}
            
        hand_lms = landmarks['hand']
        
        best_gesture = "none"
        best_confidence = 0.0
        
        for name, func in self.gestures.items():
            conf = func(hand_lms)
            if conf > best_confidence:
                best_confidence = conf
                best_gesture = name
                
        return {"gesture": best_gesture, "confidence": best_confidence}
        
    def _is_open_palm(self, lms):
        return 0.8  # Stub logic for demo
        
    def _is_closed_fist(self, lms):
        return 0.0
        
    def _is_peace_sign(self, lms):
        return 0.0
        
    def _is_thumbs_up(self, lms):
        return 0.0
