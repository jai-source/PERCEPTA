from abc import ABC, abstractmethod

class InteractionAdapter(ABC):
    def move_cursor(self, x: int, y: int) -> bool:
        return False

    @abstractmethod
    def click(self, x: int, y: int) -> bool:
        pass

    @abstractmethod
    def type_text(self, text: str) -> bool:
        pass

    @abstractmethod
    def scroll(self, amount: int) -> bool:
        pass
    
    @abstractmethod
    def get_screen_size(self) -> tuple[int, int]:
        pass
