from typing import Any, Dict
import numpy as np
from ..base import BaseGestureDetector

class BlinkDetector(BaseGestureDetector):
    def __init__(self, ear_threshold: float = 0.2, consec_frames: int = 3):
        self.ear_threshold = ear_threshold
        self.consec_frames = consec_frames
        self.frame_counter = 0

    def calculate_ear(self, eye_landmarks):
        if len(eye_landmarks) < 6:
            return 1.0
            
        A = np.linalg.norm(np.array(eye_landmarks[1]) - np.array(eye_landmarks[5]))
        B = np.linalg.norm(np.array(eye_landmarks[2]) - np.array(eye_landmarks[4]))
        C = np.linalg.norm(np.array(eye_landmarks[0]) - np.array(eye_landmarks[3]))
        
        ear = (A + B) / (2.0 * C)
        return ear

    def detect(self, landmarks: Any) -> Dict[str, Any]:
        if not landmarks or 'left_eye' not in landmarks or 'right_eye' not in landmarks:
            return {"gesture": "none", "confidence": 0.0}
            
        left_ear = self.calculate_ear(landmarks['left_eye'])
        right_ear = self.calculate_ear(landmarks['right_eye'])
        
        avg_ear = (left_ear + right_ear) / 2.0
        
        if avg_ear < self.ear_threshold:
            self.frame_counter += 1
            if self.frame_counter >= self.consec_frames:
                return {"gesture": "blink", "confidence": 1.0 - (avg_ear / self.ear_threshold)}
        else:
            self.frame_counter = 0
            
        return {"gesture": "none", "confidence": 0.0}
