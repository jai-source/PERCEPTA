import math
from typing import Tuple, Optional

class HeadTracker:
    def __init__(self, config=None, ema_alpha: float = 0.5, dead_zone_radius: float = 5.0):
        self.ema_alpha = getattr(config, "alpha", ema_alpha) if config is not None else ema_alpha
        self.dead_zone_radius = getattr(config, "dead_zone", dead_zone_radius) if config is not None else dead_zone_radius
        self.dead_zone = self.dead_zone_radius
        self._prev_nose = None
        self.dx_buffer = []
        self.dy_buffer = []
        self.smooth_window = getattr(config, "smooth_window", 5) if config is not None else 5
        self.cursor_x = 0.0
        self.cursor_y = 0.0
        self.screen_width, self.screen_height = 1920, 1080
        self.alpha = self.ema_alpha
        self.current_pos: Optional[Tuple[float, float]] = None

    def _compute_delta(self, nose):
        if self._prev_nose is None:
            self._prev_nose = nose
            return 0.0, 0.0
        dx, dy = nose[0] - self._prev_nose[0], nose[1] - self._prev_nose[1]
        self._prev_nose = nose
        return (0.0 if abs(dx) < self.dead_zone else float(dx), 0.0 if abs(dy) < self.dead_zone else float(dy))

    def _apply_smoothing(self, dx, dy):
        self.dx_buffer.append(dx)
        self.dy_buffer.append(dy)
        self.dx_buffer = self.dx_buffer[-self.smooth_window:]
        self.dy_buffer = self.dy_buffer[-self.smooth_window:]
        avg_x = sum(self.dx_buffer) / len(self.dx_buffer)
        avg_y = sum(self.dy_buffer) / len(self.dy_buffer)
        return self.alpha * avg_x + (1 - self.alpha) * getattr(self, "_smooth_x", 0.0), self.alpha * avg_y + (1 - self.alpha) * getattr(self, "_smooth_y", 0.0)

    def _update_cursor(self, dx, dy):
        self.cursor_x = max(0.0, min(self.screen_width, self.cursor_x + dx))
        self.cursor_y = max(0.0, min(self.screen_height, self.cursor_y + dy))
        return self.cursor_x, self.cursor_y

    def update(self, center_x: float, center_y: float) -> Tuple[float, float]:
        if self.current_pos is None:
            self.current_pos = (center_x, center_y)
            return self.current_pos

        dx = center_x - self.current_pos[0]
        dy = center_y - self.current_pos[1]
        distance = math.sqrt(dx**2 + dy**2)

        if distance > self.dead_zone_radius:
            new_x = self.current_pos[0] * (1 - self.ema_alpha) + center_x * self.ema_alpha
            new_y = self.current_pos[1] * (1 - self.ema_alpha) + center_y * self.ema_alpha
            self.current_pos = (new_x, new_y)
            
        return self.current_pos
