from typing import List, Dict, Any

class FaceDetector:
    def __init__(self):
        pass

    def detect_faces(self, yolo_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        faces = []
        for res in yolo_results:
            if res["class_name"] == "person":
                faces.append({
                    "bbox": res["bbox"],
                    "confidence": res["confidence"]
                })
        return faces
