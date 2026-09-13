"""
PERCEPTA — Event Types
Defines all perceptual event types, modalities, gesture states, and
the PerceptualEvent dataclass that flows through the entire system.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict


# ─── Enumerations ─────────────────────────────────────────────────────────────

class EventType(str, Enum):
    """Every event type that PERCEPTA can produce."""

    # Head / face movement
    HEAD_MOVE = "HEAD_MOVE"
    HEAD_MOVE_LEFT = "HEAD_MOVE_LEFT"
    HEAD_MOVE_RIGHT = "HEAD_MOVE_RIGHT"
    HEAD_MOVE_UP = "HEAD_MOVE_UP"
    HEAD_MOVE_DOWN = "HEAD_MOVE_DOWN"
    HEAD_TILT = "HEAD_TILT"
    HEAD_NOD = "HEAD_NOD"
    HEAD_SHAKE = "HEAD_SHAKE"
    HAND_TWO_FINGERS = "HAND_TWO_FINGERS"

    # Eye / brow
    EYEBROW_RAISE = "EYEBROW_RAISE"
    BLINK = "BLINK"
    WINK = "WINK"

    # Hand — static
    HAND_OPEN = "HAND_OPEN"
    HAND_FIST = "HAND_FIST"
    HAND_POINT = "HAND_POINT"
    HAND_PINCH = "HAND_PINCH"
    THUMB_UP = "THUMB_UP"
    THUMB_DOWN = "THUMB_DOWN"

    # Hand — dynamic (swipe)
    HAND_SWIPE_LEFT = "HAND_SWIPE_LEFT"
    HAND_SWIPE_RIGHT = "HAND_SWIPE_RIGHT"
    HAND_SWIPE_UP = "HAND_SWIPE_UP"
    HAND_SWIPE_DOWN = "HAND_SWIPE_DOWN"

    # Voice commands
    VOICE_CLICK = "VOICE_CLICK"
    VOICE_DOUBLE_CLICK = "VOICE_DOUBLE_CLICK"
    VOICE_RIGHT_CLICK = "VOICE_RIGHT_CLICK"
    VOICE_SCROLL_UP = "VOICE_SCROLL_UP"
    VOICE_SCROLL_DOWN = "VOICE_SCROLL_DOWN"
    VOICE_GO_LEFT = "VOICE_GO_LEFT"
    VOICE_GO_RIGHT = "VOICE_GO_RIGHT"
    VOICE_GO_UP = "VOICE_GO_UP"
    VOICE_GO_DOWN = "VOICE_GO_DOWN"
    VOICE_GO_BACK = "VOICE_GO_BACK"
    VOICE_GO_FORWARD = "VOICE_GO_FORWARD"
    VOICE_STOP = "VOICE_STOP"
    VOICE_PAUSE = "VOICE_PAUSE"
    VOICE_RESUME = "VOICE_RESUME"

    # Resolved interaction events (produced by interaction engine / fusion)
    CURSOR_MOVE = "CURSOR_MOVE"
    CURSOR_CLICK = "CURSOR_CLICK"
    CURSOR_DOUBLE_CLICK = "CURSOR_DOUBLE_CLICK"
    CURSOR_RIGHT_CLICK = "CURSOR_RIGHT_CLICK"
    CURSOR_SCROLL = "CURSOR_SCROLL"
    CURSOR_DRAG = "CURSOR_DRAG"

    # System
    SYSTEM_CALIBRATION_START = "SYSTEM_CALIBRATION_START"
    SYSTEM_CALIBRATION_COMPLETE = "SYSTEM_CALIBRATION_COMPLETE"
    SYSTEM_USER_LOCKED = "SYSTEM_USER_LOCKED"
    SYSTEM_USER_LOST = "SYSTEM_USER_LOST"


class Modality(str, Enum):
    """Which perceptual channel produced the event."""
    FACE = "FACE"
    HAND = "HAND"
    VOICE = "VOICE"
    SYSTEM = "SYSTEM"
    FUSION = "FUSION"


class GestureState(str, Enum):
    """Temporal state machine for gesture confirmation."""
    NO_GESTURE = "NO_GESTURE"
    DETECTING = "DETECTING"
    CONFIRMED = "CONFIRMED"
    EXECUTED = "EXECUTED"


# ─── Perceptual Event ──────────────────────────────────────────────────────────

@dataclass
class PerceptualEvent:
    """
    Normalized interaction event produced by any perception modality.

    This is the core abstraction of PERCEPTA — all face/hand/voice inputs
    are converted to PerceptualEvents before reaching the interaction engine.
    """

    event_type: EventType
    modality: Modality
    timestamp: float
    confidence: float           # 0.0 – 1.0
    payload: Dict[str, Any]     # Modality-specific context
    source_user_id: int = 0     # Which tracked person produced this event

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-safe dict (for WebSocket transport)."""
        return {
            "event_type": self.event_type.value,
            "modality": self.modality.value,
            "timestamp": self.timestamp,
            "confidence": round(self.confidence, 4),
            "payload": self.payload,
            "source_user_id": self.source_user_id,
        }

    @classmethod
    def make(
        cls,
        event_type: EventType,
        modality: Modality,
        confidence: float = 1.0,
        payload: Dict[str, Any] | None = None,
        source_user_id: int = 0,
    ) -> "PerceptualEvent":
        """Convenience factory."""
        return cls(
            event_type=event_type,
            modality=modality,
            timestamp=time.time(),
            confidence=confidence,
            payload=payload or {},
            source_user_id=source_user_id,
        )
