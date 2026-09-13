import pyautogui
from .base import InteractionAdapter

class WindowsAdapter(InteractionAdapter):
    def __init__(self):
        pyautogui.FAILSAFE = False

    def click(self, x: int, y: int) -> bool:
        try:
            pyautogui.click(x=x, y=y)
            return True
        except Exception:
            return False

    def move_cursor(self, x: int, y: int) -> bool:
        try:
            pyautogui.moveTo(x, y, _pause=False)
            return True
        except Exception:
            return False

    def type_text(self, text: str) -> bool:
        try:
            pyautogui.write(text)
            return True
        except Exception:
            return False

    def scroll(self, amount: int) -> bool:
        try:
            pyautogui.scroll(amount)
            return True
        except Exception:
            return False
            
    def get_screen_size(self) -> tuple[int, int]:
        return pyautogui.size()
