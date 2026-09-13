from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseDetector(ABC):
    @abstractmethod
    def process(self, frame: Any) -> Dict[str, Any]:
        pass
