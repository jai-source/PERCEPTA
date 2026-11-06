import pyautogui
import logging
from .base import InteractionAdapter

log = logging.getLogger(__name__)

class WindowsAdapter(InteractionAdapter):
    def __init__(self):
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.0

    def click(self, x: int, y: int) -> bool:
        try:
            pyautogui.click(x=x, y=y, _pause=False)
            return True
        except Exception:
            log.exception("click failed")
            return False

    def move_cursor(self, x: int, y: int) -> bool:
        try:
            pyautogui.moveTo(x, y, _pause=False)
            return True
        except Exception:
            log.exception("move failed")
            return False

    def type_text(self, text: str) -> bool:
        try:
            pyautogui.write(text)
            return True
        except Exception:
            log.exception("type failed")
            return False

    def scroll(self, amount: int) -> bool:
        try:
            pyautogui.scroll(120 if amount > 0 else -120, _pause=False)
            return True
        except Exception:
            log.exception("scroll failed")
            return False
            
    def get_screen_size(self) -> tuple[int, int]:
        return pyautogui.size()
