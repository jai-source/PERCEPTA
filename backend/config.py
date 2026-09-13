"""
PERCEPTA — Configuration
All tunable parameters with pydantic-settings.
Loaded from environment variables (PERCEPTA_ prefix) or .env file.
"""
from __future__ import annotations

import json
import os
from typing import List

try:
    from pydantic import field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    field_validator = None
    BaseSettings = object
    SettingsConfigDict = lambda **kwargs: kwargs


class PercetpaConfig(BaseSettings):
    """Master configuration for the PERCEPTA perception backend."""

    model_config = SettingsConfigDict(
        env_prefix="PERCEPTA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:4173", "http://127.0.0.1:5173"]

    # ── Models ────────────────────────────────────────────────────────────────
    model_dir: str = "../models"
    pose_model_name: str = "yolov8n-pose.pt"
    face_model_name: str = "yolov8n-face.pt"
    hand_model_name: str = "yolov8n-hand.pt"
    fallback_model_name: str = "yolov8n.pt"
    device: str = "auto"          # auto | cpu | cuda
    target_fps: int = 20
    jpeg_quality: int = 75

    # ── Head Tracking (math model) ────────────────────────────────────────────
    k_head: float = 3.0           # Cursor sensitivity multiplier
    dead_zone: float = 4.0        # Min pixel movement to register
    alpha: float = 0.35           # Exponential smoothing factor (0-1)
    smooth_window: int = 5        # Moving average window

    # ── Face Gestures ─────────────────────────────────────────────────────────
    eyebrow_threshold: float = 0.22    # Normalised ratio increase to trigger raise
    click_cooldown: float = 0.8        # Seconds between gesture-clicks
    blink_threshold: float = 0.21      # EAR below this → blink
    blink_consecutive_frames: int = 3  # Frames below threshold before BLINK fires

    # ── Hand Gestures ─────────────────────────────────────────────────────────
    gesture_confidence_threshold: float = 0.65
    gesture_confirmation_frames: int = 3
    gesture_cooldown: float = 0.5
    swipe_min_velocity: float = 30.0   # px/frame
    swipe_min_frames: int = 5

    # ── Voice ─────────────────────────────────────────────────────────────────
    voice_confidence_threshold: float = 0.80

    # ── Interaction ───────────────────────────────────────────────────────────
    interaction_mode: str = "windows"  # windows | linux | macos | browser

    if field_validator:
        @field_validator("cors_origins", mode="before")
        @classmethod
        def parse_cors(cls, v: object) -> List[str]:
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    return [v]
            return v  # type: ignore[return-value]

    def get_model_path(self, model_name: str) -> str:
        """Resolve absolute path to a model file."""
        backend_dir = os.path.dirname(__file__)
        project_dir = os.path.dirname(backend_dir)
        if os.path.isabs(self.model_dir):
            return os.path.join(self.model_dir, model_name)

        configured = os.path.abspath(os.path.join(backend_dir, self.model_dir))
        # Older generated .env files used ./models even though the launcher has
        # always downloaded checkpoints to <project>/models. Prefer that
        # complete directory when the configured directory is absent or partial.
        project_models = os.path.join(project_dir, "models")
        configured_model = os.path.join(configured, model_name) if model_name else configured
        project_model = os.path.join(project_models, model_name) if model_name else project_models
        if os.path.exists(project_model) and not os.path.exists(configured_model):
            return project_model
        if model_name == "" and os.path.isdir(project_models):
            configured_files = os.listdir(configured) if os.path.isdir(configured) else []
            project_files = os.listdir(project_models)
            if len(project_files) > len(configured_files):
                return project_models
        return configured_model


# Module-level singleton — import as: from config import config
if BaseSettings is object:
    def _fallback_init(self, **kwargs):
        for name, value in PercetpaConfig.__dict__.items():
            if not name.startswith("_") and not callable(value):
                setattr(self, name, value)
        for name, value in kwargs.items():
            setattr(self, name, value)
    PercetpaConfig.__init__ = _fallback_init
    config = PercetpaConfig()
    for key, value in list(vars(config).items()):
        env_value = os.getenv(f"PERCEPTA_{key.upper()}")
        if env_value is not None:
            setattr(config, key, env_value)
else:
    config = PercetpaConfig()
