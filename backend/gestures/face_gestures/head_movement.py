from typing import Any, Dict
from ..base import BaseGestureDetector

class HeadMovementDetector(BaseGestureDetector):
    def __init__(self):
        self.baseline_pitch = 0.0
        self.baseline_yaw = 0.0
        self.is_calibrated = False

    def calibrate(self, pitch: float, yaw: float):
        self.baseline_pitch = pitch
        self.baseline_yaw = yaw
        self.is_calibrated = True

    def detect(self, landmarks: Any) -> Dict[str, Any]:
        if not landmarks or 'pitch' not in landmarks:
            return {"gesture": "none", "confidence": 0.0}
            
        pitch = landmarks['pitch']
        yaw = landmarks['yaw']
        
        if not self.is_calibrated:
            self.calibrate(pitch, yaw)
            
        pitch_diff = pitch - self.baseline_pitch
        yaw_diff = yaw - self.baseline_yaw
        
        gesture = "none"
        confidence = 0.0
        
        if pitch_diff > 15:
            gesture = "nod_down"
            confidence = min(1.0, pitch_diff / 30.0)
        elif pitch_diff < -15:
            gesture = "nod_up"
            confidence = min(1.0, abs(pitch_diff) / 30.0)
        elif yaw_diff > 20:
            gesture = "turn_right"
            confidence = min(1.0, yaw_diff / 40.0)
        elif yaw_diff < -20:
            gesture = "turn_left"
            confidence = min(1.0, abs(yaw_diff) / 40.0)
            
        return {"gesture": gesture, "confidence": confidence}
