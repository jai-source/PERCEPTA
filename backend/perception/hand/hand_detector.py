from typing import List, Dict, Any

class HandDetector:
    def __init__(self):
        pass

    def detect_hands(self, yolo_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        hands = []
        for res in yolo_results:
            if res["class_name"] in ["hand", "person"]: 
                hands.append({
                    "bbox": res["bbox"],
                    "confidence": res["confidence"]
                })
        return hands
