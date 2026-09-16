import platform
from .base import InteractionAdapter
from .windows_adapter import WindowsAdapter
from .linux_adapter import LinuxAdapter
from .macos_adapter import MacOSAdapter
from .browser_adapter import BrowserAdapter

_SAFE_MARGIN = 5


class InteractionEngine:
    def __init__(self, mode: str = "os"):
        self.mode = mode
        self.adapter = self._get_adapter()
        screen = self.adapter.get_screen_size()
        print(
            f"[PERCEPTA] InteractionEngine mode={self.mode!r} adapter={type(self.adapter).__name__} screen={screen[0]}x{screen[1]}",
            flush=True,
        )

    def _get_adapter(self) -> InteractionAdapter:
        mode = (self.mode or "windows").lower()
        if mode == "browser":
            return BrowserAdapter()
        if mode == "windows":
            return WindowsAdapter()
        if mode == "linux":
            return LinuxAdapter()
        if mode in {"macos", "darwin"}:
            return MacOSAdapter()

        system = platform.system().lower()
        if system == "windows":
            return WindowsAdapter()
        if system == "linux":
            return LinuxAdapter()
        if system == "darwin":
            return MacOSAdapter()
        return WindowsAdapter()

    def _clamp(self, x: int, y: int) -> tuple[int, int]:
        width, height = self.adapter.get_screen_size()
        return (
            max(_SAFE_MARGIN, min(width - _SAFE_MARGIN, int(x))),
            max(_SAFE_MARGIN, min(height - _SAFE_MARGIN, int(y))),
        )

    def click(self, x: int, y: int) -> bool:
        sx, sy = self._clamp(x, y)
        return self.adapter.click(sx, sy)

    def move_cursor(self, x: int, y: int) -> bool:
        sx, sy = self._clamp(x, y)
        return self.adapter.move_cursor(sx, sy)

    def double_click(self, x: int, y: int) -> bool:
        sx, sy = self._clamp(x, y)
        return self.adapter.click(sx, sy) and self.adapter.click(sx, sy)

    def right_click(self, x: int, y: int) -> bool:
        try:
            import pyautogui
            sx, sy = self._clamp(x, y)
            pyautogui.rightClick(x=sx, y=sy)
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
