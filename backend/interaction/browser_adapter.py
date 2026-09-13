from .base import InteractionAdapter

class BrowserAdapter(InteractionAdapter):
    def __init__(self):
        pass

    def click(self, x: int, y: int) -> bool:
        return True

    def move_cursor(self, x: int, y: int) -> bool:
        return True

    def type_text(self, text: str) -> bool:
        return True

    def scroll(self, amount: int) -> bool:
        return True
        
    def get_screen_size(self) -> tuple[int, int]:
        return (1920, 1080)
