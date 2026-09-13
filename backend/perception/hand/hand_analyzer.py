from typing import Dict, Any

class HandAnalyzer:
    def __init__(self):
        pass

    def analyze(self, frame: Any, hand_bbox: list) -> Dict[str, Any]:
        x1, y1, x2, y2 = hand_bbox
        wrist_pos = ((x1 + x2) / 2, y2)
        return {
            "wrist_position": wrist_pos,
            "gesture": "unknown"
        }
