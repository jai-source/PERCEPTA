import platform
from .base import InteractionAdapter
from .windows_adapter import WindowsAdapter
from .linux_adapter import LinuxAdapter
from .macos_adapter import MacOSAdapter
from .browser_adapter import BrowserAdapter

class InteractionEngine:
    def __init__(self, mode: str = "os"):
        self.mode = mode
        self.adapter = self._get_adapter()

    def _get_adapter(self) -> InteractionAdapter:
        if self.mode == "browser":
            return BrowserAdapter()
            
        system = platform.system().lower()
        if system == "windows":
            return WindowsAdapter()
        elif system == "linux":
            return LinuxAdapter()
        elif system == "darwin":
            return MacOSAdapter()
        else:
            return WindowsAdapter()
            
    def click(self, x: int, y: int) -> bool:
        return self.adapter.click(x, y)

    def move_cursor(self, x: int, y: int) -> bool:
        return self.adapter.move_cursor(x, y)

    def double_click(self, x: int, y: int) -> bool:
        return self.adapter.click(x, y) and self.adapter.click(x, y)

    def right_click(self, x: int, y: int) -> bool:
        try:
            import pyautogui
            pyautogui.rightClick(x=x, y=y)
            return True
        except Exception:
            return False

    def key(self, key_name: str) -> bool:
        try:
            import pyautogui
            pyautogui.press(key_name)
            return True
        except Exception:
            return False
        
    def type_text(self, text: str) -> bool:
        return self.adapter.type_text(text)
        
    def scroll(self, amount: int) -> bool:
        return self.adapter.scroll(amount)
