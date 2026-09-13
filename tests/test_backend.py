"""
PERCEPTA Backend Tests
======================
Run with: cd backend && pytest tests/ -v
"""
import sys
import os

# Ensure backend packages are importable from the repository-root test command.
BACKEND_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, BACKEND_ROOT)


# ─── Event Type Tests ────────────────────────────────────────────────────────

def test_perceptual_event_creation():
    """PerceptualEvent should create and serialize cleanly."""
    from events.event_types import PerceptualEvent, EventType, Modality
    import time

    event = PerceptualEvent(
        event_type=EventType.EYEBROW_RAISE,
        modality=Modality.FACE,
        timestamp=time.time(),
        confidence=0.94,
        payload={"ratio": 0.31},
        source_user_id=1,
    )
    d = event.to_dict()
    assert d["event_type"] == "EYEBROW_RAISE"
    assert d["modality"] == "FACE"
    assert d["confidence"] == 0.94


def test_all_event_types_exist():
    """All expected EventType values should be present."""
    from events.event_types import EventType
    required = [
        "HEAD_MOVE", "HEAD_TILT", "HEAD_NOD", "HEAD_SHAKE",
        "EYEBROW_RAISE", "BLINK", "WINK",
        "HAND_OPEN", "HAND_FIST", "HAND_POINT", "HAND_PINCH",
        "HAND_SWIPE_LEFT", "HAND_SWIPE_RIGHT", "HAND_SWIPE_UP", "HAND_SWIPE_DOWN",
        "THUMB_UP", "THUMB_DOWN",
        "VOICE_CLICK", "VOICE_DOUBLE_CLICK", "VOICE_RIGHT_CLICK",
        "VOICE_SCROLL_UP", "VOICE_SCROLL_DOWN", "VOICE_STOP",
    ]
    names = [e.name for e in EventType]
    for name in required:
        assert name in names, f"Missing EventType: {name}"


# ─── Head Tracker Math Tests ──────────────────────────────────────────────────

def test_dead_zone_filtering():
    """Deltas smaller than dead zone should be zeroed."""
    from perception.face.head_tracker import HeadTracker
    from config import PercetpaConfig

    cfg = PercetpaConfig(dead_zone=5.0)
    tracker = HeadTracker(cfg)
    tracker._prev_nose = (100, 100)

    # Movement smaller than dead zone
    dx, dy = tracker._compute_delta((102, 101))
    assert dx == 0.0
    assert dy == 0.0

    # Movement larger than dead zone
    dx, dy = tracker._compute_delta((110, 108))
    assert abs(dx) > 0
    assert abs(dy) > 0


def test_exponential_smoothing():
    """Smoothed value should converge toward input."""
    from perception.face.head_tracker import HeadTracker
    from config import PercetpaConfig

    cfg = PercetpaConfig(alpha=0.5, smooth_window=3, dead_zone=0.0)
    tracker = HeadTracker(cfg)

    # Push large consistent values
    for _ in range(10):
        tracker.dx_buffer.append(10.0)
        tracker.dy_buffer.append(5.0)

    sx, sy = tracker._apply_smoothing(10.0, 5.0)
    assert sx > 0  # Should be positive
    assert sy > 0


def test_cursor_clamped_to_screen():
    """Cursor should not exceed screen bounds."""
    from perception.face.head_tracker import HeadTracker
    from config import PercetpaConfig

    cfg = PercetpaConfig(k_head=100.0, dead_zone=0.0, alpha=1.0, smooth_window=1)
    tracker = HeadTracker(cfg)
    tracker.cursor_x = 0
    tracker.cursor_y = 0

    # Apply huge delta — cursor should clamp
    tracker._update_cursor(1000.0, 1000.0)
    assert tracker.cursor_x <= tracker.screen_width
    assert tracker.cursor_y <= tracker.screen_height
    assert tracker.cursor_x >= 0
    assert tracker.cursor_y >= 0


# ─── Temporal Gesture Filter Tests ────────────────────────────────────────────

def test_gesture_state_machine():
    """Gesture should progress through states correctly."""
    from gestures.temporal import TemporalGestureFilter, GestureState

    gf = TemporalGestureFilter(confirmation_frames=3, cooldown_seconds=0.5)
    import time

    t = time.time()
    # Initially no gesture
    assert gf.state == GestureState.NO_GESTURE

    # Detecting (1st frame)
    state = gf.update(gesture_detected=True, timestamp=t)
    assert state == GestureState.DETECTING

    # Still detecting (2nd frame)
    state = gf.update(gesture_detected=True, timestamp=t + 0.05)
    assert state == GestureState.DETECTING

    # Confirmed (3rd frame)
    state = gf.update(gesture_detected=True, timestamp=t + 0.10)
    assert state == GestureState.CONFIRMED

    # Executed
    state = gf.update(gesture_detected=True, timestamp=t + 0.15)
    assert state == GestureState.EXECUTED

    # After execution, should be in cooldown
    assert gf.in_cooldown


def test_gesture_interrupted():
    """Interrupted gesture should reset to NO_GESTURE."""
    from gestures.temporal import TemporalGestureFilter, GestureState

    gf = TemporalGestureFilter(confirmation_frames=3, cooldown_seconds=0.5)
    import time
    t = time.time()

    gf.update(gesture_detected=True, timestamp=t)
    gf.update(gesture_detected=True, timestamp=t + 0.05)
    # Interrupted
    state = gf.update(gesture_detected=False, timestamp=t + 0.10)
    assert state == GestureState.NO_GESTURE


# ─── Voice Processor Tests ────────────────────────────────────────────────────

def test_voice_command_matching():
    """Standard voice commands should map to correct event types."""
    from gestures.voice.voice_processor import VoiceProcessor
    from events.event_types import EventType

    vp = VoiceProcessor()

    cases = [
        ("click", EventType.VOICE_CLICK),
        ("double click", EventType.VOICE_DOUBLE_CLICK),
        ("right click", EventType.VOICE_RIGHT_CLICK),
        ("scroll up", EventType.VOICE_SCROLL_UP),
        ("scroll down", EventType.VOICE_SCROLL_DOWN),
        ("stop", EventType.VOICE_STOP),
    ]
    for transcript, expected_type in cases:
        event = vp.process(transcript, confidence=0.9)
        assert event is not None, f"No event for '{transcript}'"
        assert event.event_type == expected_type, f"Wrong event for '{transcript}': {event.event_type}"


def test_voice_unknown_command_returns_none():
    """Unknown commands should return None."""
    from gestures.voice.voice_processor import VoiceProcessor
    vp = VoiceProcessor()
    event = vp.process("banana", confidence=0.9)
    assert event is None


def test_voice_command_case_insensitive():
    """Voice commands should be case-insensitive."""
    from gestures.voice.voice_processor import VoiceProcessor
    from events.event_types import EventType

    vp = VoiceProcessor()
    event = vp.process("CLICK", confidence=0.9)
    assert event is not None
    assert event.event_type == EventType.VOICE_CLICK


# ─── User Tracker Tests ───────────────────────────────────────────────────────

def test_single_user_is_active():
    """Single detected person should immediately become active user."""
    from tracking.user_tracker import UserTracker

    tracker = UserTracker()
    persons = [{"id": 0, "bbox": [100, 100, 300, 400], "confidence": 0.92, "keypoints": []}]
    result = tracker.update(persons)
    assert result["active_user"] is not None
    assert result["multi_user_detected"] is False


def test_no_person_detected():
    """Empty detection should return None active user."""
    from tracking.user_tracker import UserTracker

    tracker = UserTracker()
    result = tracker.update([])
    assert result["active_user"] is None


def test_multiple_users_detected():
    """Multiple persons should set multi_user_detected flag."""
    from tracking.user_tracker import UserTracker

    tracker = UserTracker()
    persons = [
        {"id": 0, "bbox": [50, 50, 200, 400], "confidence": 0.91, "keypoints": []},
        {"id": 1, "bbox": [400, 50, 600, 400], "confidence": 0.88, "keypoints": []},
    ]
    result = tracker.update(persons)
    assert result["multi_user_detected"] is True


def test_active_user_sticky():
    """Active user should not switch just because another person is detected."""
    from tracking.user_tracker import UserTracker

    tracker = UserTracker()

    # Establish first person as active user
    person_a = {"id": 0, "bbox": [100, 100, 300, 400], "confidence": 0.90, "keypoints": []}
    tracker.update([person_a])

    # Second frame: first person still present + higher-confidence newcomer
    person_b = {"id": 1, "bbox": [500, 100, 700, 400], "confidence": 0.99, "keypoints": []}
    result = tracker.update([person_a, person_b])

    # Active user should still be person_a (IoU match)
    assert result["active_user"]["id"] == 0


# ─── Event Normalizer Tests ────────────────────────────────────────────────────

def test_normalize_face_gesture():
    from events.event_normalizer import EventNormalizer
    from events.event_types import EventType, Modality

    norm = EventNormalizer()
    event = norm.normalize_face_gesture("EYEBROW_RAISE", confidence=0.88, payload={})
    assert event.event_type == EventType.EYEBROW_RAISE
    assert event.modality == Modality.FACE
    assert event.confidence == 0.88


def test_normalize_voice_command():
    from events.event_normalizer import EventNormalizer
    from events.event_types import EventType, Modality

    norm = EventNormalizer()
    event = norm.normalize_voice_command("VOICE_CLICK", confidence=0.95)
    assert event.event_type == EventType.VOICE_CLICK
    assert event.modality == Modality.VOICE


def test_voice_processor_supports_required_commands():
    from gestures.voice.voice_processor import VoiceProcessor
    from events.event_types import EventType

    processor = VoiceProcessor()
    assert processor.process("right click").event_type == EventType.VOICE_RIGHT_CLICK
    assert processor.process("go left").event_type == EventType.VOICE_GO_LEFT
    assert processor.process("not a command") is None


def test_frame_processor_normalizes_yolo_detections():
    from perception.frame_processor import FrameProcessor

    class FakeProvider:
        model_name = "fake-pose"
        device = "CPU"

        def process(self, frame):
            return [
                {"class_name": "person", "bbox": [10, 10, 110, 210], "confidence": 0.95},
                {"class_name": "open_hand", "bbox": [120, 80, 180, 150], "confidence": 0.88},
            ]

    processor = FrameProcessor(provider=FakeProvider())
    results = [processor.process(object()) for _ in range(3)]
    first = results[0]
    assert first["face"]["detected"] is True
    assert first["hand"]["gesture"] == "OPEN_PALM"
    assert any(event["modality"] == "HAND" for result in results for event in result["events"])
    assert first["tracking_locked"] is True
