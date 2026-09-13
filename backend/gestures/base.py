from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseGestureDetector(ABC):
    @abstractmethod
    def detect(self, landmarks: Any) -> Dict[str, Any]:
        """Detect gestures from landmarks/features."""
        pass
