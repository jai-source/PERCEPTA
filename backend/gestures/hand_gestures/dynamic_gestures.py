from typing import Any, Dict
from collections import deque
import numpy as np
from ..base import BaseGestureDetector

class DynamicHandGestureDetector(BaseGestureDetector):
    def __init__(self, history_len: int = 15):
        self.history = deque(maxlen=history_len)

    def detect(self, landmarks: Any) -> Dict[str, Any]:
        if not landmarks or 'hand_center' not in landmarks:
            return {"gesture": "none", "confidence": 0.0}
            
        center = landmarks['hand_center']
        self.history.append(np.array(center))
        
        if len(self.history) < 10:
            return {"gesture": "none", "confidence": 0.0}
            
        start = self.history[0]
        end = self.history[-1]
        
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        magnitude = np.sqrt(dx**2 + dy**2)
        
        if magnitude > 50:
            if abs(dx) > abs(dy):
                if dx > 0:
                    return {"gesture": "swipe_right", "confidence": min(1.0, magnitude / 100.0)}
                else:
                    return {"gesture": "swipe_left", "confidence": min(1.0, magnitude / 100.0)}
            else:
                if dy > 0:
                    return {"gesture": "swipe_down", "confidence": min(1.0, magnitude / 100.0)}
                else:
                    return {"gesture": "swipe_up", "confidence": min(1.0, magnitude / 100.0)}
                    
        return {"gesture": "none", "confidence": 0.0}
