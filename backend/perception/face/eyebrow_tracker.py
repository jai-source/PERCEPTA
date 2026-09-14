"""Eyebrow-raise detection via MediaPipe FaceLandmarker.

Only used for the eyebrow-raise -> click gesture; all other perception
stays YOLO-driven.
"""

from __future__ import annotations

import os
import math
import time

import numpy as np

try:
    import mediapipe as mp
    from mediapipe.tasks.python import vision
except ImportError:
    mp = None
    vision = None

_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"


class EyebrowTracker:
    """Lazy-load MediaPipe FaceLandmarker for eyebrow-raise detection."""

    def __init__(self, model_dir: str = "models"):
        self.loaded = False
        self.error: str | None = None
        self._landmarker = None
        self._ts_counter = 0  # monotonic ms counter for detect_for_video
        self._last_ts = 0

        if mp is None or vision is None:
            self.error = "mediapipe not installed"
            return

        model_path = os.path.join(model_dir, "face_landmarker.task")
        try:
            if not os.path.exists(model_path) or os.path.getsize(model_path) < 1024:
                self._download(model_path)
            base = mp.BaseOptions(model_asset_path=model_path)
            opts = vision.FaceLandmarkerOptions(
                base_options=base,
                running_mode=vision.RunningMode.VIDEO,
                num_faces=1,
                output_face_blendshapes=True,
            )
            self._landmarker = vision.FaceLandmarker.create_from_options(opts)
            self.loaded = True
        except Exception as exc:
            self.error = str(exc)

    @staticmethod
    def _download(dest: str) -> None:
        import requests

        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        resp = requests.get(_MODEL_URL, timeout=60)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)

    def process(self, frame_bgr: np.ndarray, timestamp_ms: int | None = None) -> tuple[float, bool]:
        """Return (eyebrow_score, face_found).

        Score is max(browInnerUp, avg(browOuterUpLeft, browOuterUpRight)).
        """
        if not self.loaded or self._landmarker is None:
            return 0.0, False

        # Guarantee strictly increasing timestamps
        if timestamp_ms is not None:
            self._ts_counter = max(self._ts_counter, timestamp_ms) + 1
        else:
            self._ts_counter += 1
        ts = self._ts_counter

        try:
            frame_rgb = cvt_bgr_rgb(frame_bgr)
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            result = self._landmarker.detect_for_video(img, ts)
        except Exception:
            return 0.0, False

        if not result.face_blendshapes or len(result.face_blendshapes) == 0:
            return 0.0, False

        blendshapes = result.face_blendshapes[0]
        score_map = {bs.category_name: bs.score for bs in blendshapes}
        inner = score_map.get("browInnerUp", 0.0)
        outer_left = score_map.get("browOuterUpLeft", 0.0)
        outer_right = score_map.get("browOuterUpRight", 0.0)
        score = max(inner, (outer_left + outer_right) / 2.0)
        return float(score), True


def cvt_bgr_rgb(frame: np.ndarray) -> np.ndarray:
    """OpenCV BGR -> RGB, handling both contiguous and non-contiguous arrays."""
    rgb = frame[:, :, ::-1].copy()
    return rgb