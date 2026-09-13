from collections import deque
import time
from enum import Enum


class GestureState(str, Enum):
    NO_GESTURE = "NO_GESTURE"
    DETECTING = "DETECTING"
    CONFIRMED = "CONFIRMED"
    EXECUTED = "EXECUTED"

class TemporalGestureFilter:
    def __init__(self, window_size: int = 10, confidence_threshold: float = 0.7, confirmation_frames: int | None = None, cooldown_seconds: float = 0.0):
        self.window_size = window_size
        self.confidence_threshold = confidence_threshold
        self.history = deque(maxlen=window_size)
        self.confirmation_frames = confirmation_frames or max(1, window_size // 2)
        self.cooldown_seconds = cooldown_seconds
        self.state = GestureState.NO_GESTURE
        self._last_execution = 0.0
        self._cooldown_active = False
    
    @property
    def in_cooldown(self) -> bool:
        return self._cooldown_active

    def update(self, gesture=None, confidence=None, timestamp=None, gesture_detected=None):
        if gesture_detected is not None:
            gesture = gesture_detected
        if isinstance(gesture, bool):
            return self._update_state(gesture, timestamp if timestamp is not None else time.time())

        confidence = float(confidence or 0.0)
        self.history.append((gesture, confidence, time.time()))
        
        if not self.history:
            return "none"
            
        counts = {}
        for g, c, _ in self.history:
            if c >= self.confidence_threshold:
                counts[g] = counts.get(g, 0) + 1
                
        if not counts:
            return "none"
            
        most_common = max(counts.items(), key=lambda x: x[1])
        if most_common[1] >= self.window_size * 0.5:
            return most_common[0]
            
        return "none"

    def _update_state(self, detected: bool, timestamp: float):
        if self._cooldown_active and timestamp - self._last_execution >= self.cooldown_seconds:
            self._cooldown_active = False
        if self.in_cooldown:
            self.state = GestureState.NO_GESTURE
            return self.state
        if not detected:
            self.history.clear()
            self.state = GestureState.NO_GESTURE
            return self.state
        self.history.append((True, 1.0, timestamp))
        if len(self.history) < self.confirmation_frames:
            self.state = GestureState.DETECTING
        elif self.state == GestureState.CONFIRMED:
            self.state = GestureState.EXECUTED
            self._last_execution = timestamp
            self._cooldown_active = True
        else:
            self.state = GestureState.CONFIRMED
        return self.state
