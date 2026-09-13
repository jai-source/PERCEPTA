from typing import List, Dict, Any

def calculate_iou(box1: list, box2: list) -> float:
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    if box1_area + box2_area - inter_area <= 0:
        return 0.0

    iou = inter_area / float(box1_area + box2_area - inter_area)
    return iou

class UserTracker:
    def __init__(self, iou_threshold: float = 0.3):
        self.iou_threshold = iou_threshold
        self.active_users: Dict[int, Dict[str, Any]] = {}
        self.next_id = 0
        self.active_user_id = None

    def update(self, detected_users: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        new_active_users = {}
        
        for det in detected_users:
            best_iou = 0.0
            best_id = None
            
            for uid, user_data in self.active_users.items():
                iou = calculate_iou(det["bbox"], user_data["bbox"])
                if iou > best_iou and iou > self.iou_threshold:
                    best_iou = iou
                    best_id = uid
                    
            if best_id is not None:
                new_active_users[best_id] = det
                del self.active_users[best_id]
            else:
                new_active_users[self.next_id] = det
                self.next_id += 1
                
        self.active_users = new_active_users
        if self.active_user_id in new_active_users:
            pass
        if self.active_user_id is None and new_active_users:
            self.active_user_id = max(new_active_users, key=lambda uid: new_active_users[uid].get("confidence", 0.0))
        elif self.active_user_id not in new_active_users and new_active_users:
            # A newcomer cannot take control while the previous identity is still tracked.
            self.active_user_id = min(new_active_users)
        active = self.active_users.get(self.active_user_id)
        active_record = {**active, "id": self.active_user_id} if active is not None else None
        return {"users": self.active_users, "active_user": active_record, "multi_user_detected": len(self.active_users) > 1}
