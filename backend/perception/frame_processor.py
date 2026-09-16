"""YOLO-backed multimodal frame processing and interaction dispatch."""
from __future__ import annotations

import math
import os
import time
import traceback
from collections import deque
from typing import Any, Dict, Optional, Tuple

import numpy as np

DEBUG_PIPELINE = os.getenv("PERCEPTA_DEBUG_PIPELINE", "true").lower() != "false"

try:
    from config import config
    from tracking.user_tracker import UserTracker
    from events.event_types import EventType, Modality, PerceptualEvent
    from perception.yolo.yolo_provider import YoloProvider
    from interaction.engine import InteractionEngine
    from perception.face.eyebrow_tracker import EyebrowTracker
except ImportError:
    from ..config import config
    from ..tracking.user_tracker import UserTracker
    from ..events.event_types import EventType, Modality, PerceptualEvent
    from .yolo.yolo_provider import YoloProvider
    from ..interaction.engine import InteractionEngine
    from ..perception.face.eyebrow_tracker import EyebrowTracker


class FrameProcessor:
    def __init__(self, provider: Optional[Any] = None, hand_provider: Optional[Any] = None, face_provider: Optional[Any] = None):
        model_dir = config.get_model_path("")
        if provider is None and hand_provider is None and face_provider is None:
            self.provider = YoloProvider(config.pose_model_name, model_dir)
            self.hand_provider = YoloProvider(config.hand_model_name, model_dir)
            self.face_provider = YoloProvider(config.face_model_name, model_dir)
        else:
            self.provider = provider or YoloProvider(config.pose_model_name, model_dir)
            self.hand_provider = hand_provider or (provider if provider is not None and not hasattr(provider, "loaded") else YoloProvider(config.hand_model_name, model_dir))
            self.face_provider = face_provider or (provider if provider is not None else YoloProvider(config.face_model_name, model_dir))
        self.user_tracker = UserTracker()
        self.engine = InteractionEngine(config.interaction_mode)
        self.previous_center: Optional[tuple[float, float]] = None
        self.smoothed_delta = [0.0, 0.0]
        self.delta_history: deque[tuple[float, float]] = deque(maxlen=config.smooth_window)
        self.hand_history: deque[tuple[float, float, float]] = deque(maxlen=config.swipe_min_frames)
        self.last_gesture: Optional[str] = None
        self.gesture_frames = 0
        self.last_gesture_time = 0.0
        self.last_result = self.empty_result()
        self.modalities = {"face": True, "hand": True, "voice": True}
        self.frame_number = 0
        self.hand_interval = 1
        self.pose_interval = 1  # Run pose every frame for head tracking
        self.last_hand_detections = []
        self.last_pose_detections = []
        self.scroll_anchor_y: Optional[float] = None
        # Eyebrow-raise -> click (MediaPipe FaceLandmarker)
        self.eyebrow_tracker = EyebrowTracker(model_dir)
        self._eyebrow_ms_counter = 0
        self._eyebrow_last_gesture: Optional[str] = None
        self._eyebrow_frames = 0
        self._eyebrow_last_time = 0.0
        self.frame_width = 640
        self.frame_height = 480
        self.last_slide_swipe_time = 0.0
        self.slide_swipe_cooldown = 0.9
        self._debug_frame_counter = 0
        self._last_hand_class_log = ""

    def update_modalities(self, face: bool, hand: bool, voice: bool) -> None:
        self.modalities = {"face": face, "hand": hand, "voice": voice}

    def warmup(self) -> None:
        """Run one inference through every loaded provider before accepting clients."""
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        providers = ((self.provider, 320), (self.hand_provider, 256), (self.face_provider, 320))
        # Torch inference is intentionally sequential here: parallel provider
        # construction is safe, but concurrent first calls can stall on Windows.
        for provider, imgsz in providers:
            self._warm_provider(provider, frame, imgsz)

    @staticmethod
    def _warm_provider(provider: Any, frame: np.ndarray, imgsz: int) -> None:
        if not getattr(provider, "loaded", False):
            return
        try:
            provider.process(frame, imgsz=imgsz)
        except TypeError:
            provider.process(frame)

    @staticmethod
    def empty_result() -> Dict[str, Any]:
        return {"type": "perception", "face": {"detected": False, "bbox": None, "keypoints": [], "gesture": None, "confidence": 0.0, "head_pose": None}, "hand": {"detected": False, "bbox": None, "keypoints": [], "gesture": None, "confidence": 0.0, "gesture_state": "NO_GESTURE"}, "events": [], "cursor": {"x": 0.0, "y": 0.0}, "active_user_id": 0, "multi_user_detected": False, "tracking_locked": False, "fps": 0.0, "device": "CPU", "model_name": "unavailable", "hand_model": {"name": "unavailable", "loaded": False, "error": "not initialized"}, "inference_ms": 0.0}

    def process(self, frame: Any) -> Dict[str, Any]:
        try:
            return self._process(frame)
        except Exception as exc:
            traceback.print_exc()
            return self.empty_result()

    def _process(self, frame: Any) -> Dict[str, Any]:
        started = time.perf_counter()
        result = self.empty_result()
        self.frame_number += 1
        self._debug_frame_counter += 1
        if hasattr(frame, "shape") and len(frame.shape) >= 2:
            self.frame_height, self.frame_width = int(frame.shape[0]), int(frame.shape[1])
        pose_due = self.pose_interval <= 1 or self.frame_number % self.pose_interval == 1
        if self.modalities["face"] and pose_due:
            self.last_pose_detections = self.provider.process(frame)
        pose_detections = self.last_pose_detections if self.modalities["face"] else []
        # Pose inference already supplies the person track used for head cursor
        # control. Running the separate face detector on every frame doubles
        # latency without improving cursor movement.
        face_detections = pose_detections
        hand_due = self.hand_interval <= 1 or self.frame_number % self.hand_interval == 1
        if self.modalities["hand"] and hand_due:
            self.last_hand_detections = self._process_hand(frame)
        hand_detections = self.last_hand_detections if self.modalities["hand"] else []
        persons = [item for item in pose_detections if item.get("class_name") == "person"]
        faces = [item for item in face_detections if item.get("class_name", "").lower() in {"face", "person"}]
        tracking_detections = persons or faces
        tracking_result = self.user_tracker.update(tracking_detections)
        tracked = tracking_result["users"]
        active = self._select_active(tracked, self.user_tracker.active_user_id)
        events = []

        # Debug: log active user state every few frames
        if DEBUG_PIPELINE and self._debug_frame_counter % 15 == 0:
            keypoints = active.get("keypoints") or [] if active else []
            nose = keypoints[0] if keypoints else None
            print(
                f"[PERCEPTA_HEAD] active={active is not None} user_id={active['id'] if active else None} "
                f"keypoints={len(keypoints)} nose={nose} pose_due={pose_due} persons={len(persons)}",
                flush=True,
            )

        if active:
            keypoints = active.get("keypoints") or []
            if DEBUG_PIPELINE and self._debug_frame_counter % 15 == 0:
                nose = keypoints[0] if keypoints else None
                print(
                    f"[PERCEPTA_HEAD] active=True user_id={active['id']} keypoints={len(keypoints)} nose={nose}",
                    flush=True,
                )

            eyebrow_raised = False
            score = 0.0
            try:
                # Eyebrow-raise detection via MediaPipe (gated behind face modality
                # and the same interval as pose to bound cost).
                if self.modalities["face"] and pose_due and self.eyebrow_tracker.loaded:
                    self._eyebrow_ms_counter += 100
                    try:
                        score, face_found = self.eyebrow_tracker.process(frame, self._eyebrow_ms_counter)
                    except Exception:
                        traceback.print_exc()
                        score, face_found = 0.0, False
                    if face_found and score >= config.eyebrow_threshold:
                        eyebrow_raised = self._confirm_face()
                    else:
                        self._eyebrow_frames = 0
                if eyebrow_raised:
                    cx, cy = self._current_cursor()
                    events.append(self._event("EYEBROW_RAISE", Modality.FACE, 0.9, {"score": score}, active["id"]))
                    self.engine.click(int(cx), int(cy))
                    if DEBUG_PIPELINE:
                        print(f"[PERCEPTA_EYEBROW] click at ({int(cx)}, {int(cy)}) score={score:.2f}", flush=True)

                bbox = active["bbox"]
                # Prefer nose keypoint; fall back to bbox center when missing/zero.
                if len(keypoints) > 0 and keypoints[0][0] > 0 and keypoints[0][1] > 0:
                    center = (float(keypoints[0][0]), float(keypoints[0][1]))
                else:
                    center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
                
                # Only compute head delta on fresh pose frames.
                # On cached frames the detections are stale and would produce zero deltas,
                # which the EMA would interpret as intentional deceleration.
                if pose_due:
                    if DEBUG_PIPELINE and self._debug_frame_counter % 15 == 0:
                        print(f"[PERCEPTA_DELTA] center={center} prev_center={self.previous_center} pose_due={pose_due}", flush=True)
                    
                    dx, dy = self._smooth_head_delta(center)
                    
                    if DEBUG_PIPELINE and self._debug_frame_counter % 15 == 0:
                        print(f"[PERCEPTA_DELTA] dx={dx:.2f} dy={dy:.2f} smoothed={self.smoothed_delta}", flush=True)
                else:
                    # On cached frames, reuse last smoothed delta without adding zeros to history
                    dx, dy = self.smoothed_delta
                    if DEBUG_PIPELINE and self._debug_frame_counter % 15 == 0:
                        print(f"[PERCEPTA_DELTA] cached frame -> reused dx={dx:.2f} dy={dy:.2f}", flush=True)
                movement = self._head_gesture(dx, dy)
                if movement:
                    events.append(self._event(movement, Modality.FACE, min(1.0, max(abs(dx), abs(dy)) / 40), {"dx": dx, "dy": dy}, active["id"]))
                # Move cursor on any non-zero smoothed delta — not only when a
                # named HEAD_MOVE_* gesture crosses the event threshold.
                if abs(dx) > 0 or abs(dy) > 0:
                    cursor = self._cursor_position(dx, dy)
                    self.engine.move_cursor(*cursor)
                else:
                    cursor = self._current_cursor()
                result["face"] = {"detected": True, "bbox": self._bbox(bbox), "keypoints": active.get("keypoints", []), "gesture": movement, "confidence": active.get("confidence", 0.0), "head_pose": {"dx": dx, "dy": dy, "tilt": 0.0}}
                result["cursor"] = {"x": cursor[0], "y": cursor[1]}
            except Exception:
                traceback.print_exc()
                cursor = self._current_cursor()
                result["face"] = {"detected": True, "bbox": self._bbox(active["bbox"]), "keypoints": active.get("keypoints", []), "gesture": None, "confidence": active.get("confidence", 0.0), "head_pose": {"dx": 0.0, "dy": 0.0, "tilt": 0.0}}
                result["cursor"] = {"x": cursor[0], "y": cursor[1]}
        elif DEBUG_PIPELINE and self._debug_frame_counter % 30 == 0:
            print(f"[PERCEPTA_HEAD] active=False persons={len(persons)} faces={len(faces)}", flush=True)

        hand = self._best_hand([item for item in hand_detections if item.get("class_name", "").lower() not in {"person", "face"}])
        if hand:
            raw_class = hand.get("class_name", "")
            if DEBUG_PIPELINE and raw_class and raw_class != self._last_hand_class_log:
                print(f"[PERCEPTA_HAND] raw class_name={raw_class!r}", flush=True)
                self._last_hand_class_log = raw_class
            center = ((hand["bbox"][0] + hand["bbox"][2]) / 2, (hand["bbox"][1] + hand["bbox"][3]) / 2)
            self.hand_history.append((center[0], center[1], time.time()))
            gesture = self._classify_hand(hand)
            if DEBUG_PIPELINE and gesture == "TWO_FINGERS" and self._debug_frame_counter % 10 == 0:
                print(f"[PERCEPTA_HAND] classified={gesture} raw={raw_class!r} conf={hand.get('confidence', 0.0):.2f}", flush=True)
            state, confirmed = self._confirm(gesture)
            result["hand"] = {"detected": True, "bbox": self._bbox(hand["bbox"]), "keypoints": hand.get("keypoints", []), "gesture": gesture, "confidence": hand.get("confidence", 0.0), "gesture_state": state}
            # FIST drives the cursor. Fingers are curled so fingertip keypoints
            # are unreliable — use the bounding-box centre instead.
            if gesture == "FIST" and hand.get("confidence", 0.0) >= config.gesture_confidence_threshold:
                self.engine.move_cursor(*self._screen_from_bbox(hand["bbox"]))
            # TWO_FINGERS: horizontal swipe advances slides; vertical motion scrolls.
            if gesture == "TWO_FINGERS" and hand.get("confidence", 0.0) >= config.gesture_confidence_threshold:
                slide_swipe = self._horizontal_slide_swipe()
                if slide_swipe and time.time() - self.last_slide_swipe_time >= self.slide_swipe_cooldown:
                    self.last_slide_swipe_time = time.time()
                    key = "right" if slide_swipe == "SWIPE_RIGHT" else "left"
                    self.engine.key(key)
                    if DEBUG_PIPELINE:
                        print(f"[PERCEPTA_SLIDE] {slide_swipe} -> key({key!r})", flush=True)
                    self.scroll_anchor_y = None
                elif not slide_swipe:
                    if self.scroll_anchor_y is None:
                        self.scroll_anchor_y = center[1]
                    else:
                        dy = center[1] - self.scroll_anchor_y
                        if abs(dy) >= config.dead_zone:
                            # Windows only registers a scroll tick at ~±100
                            # (WHEEL_DELTA=120); smaller values are silently dropped.
                            self.engine.scroll(-100 if dy > 0 else 100)
                            self.scroll_anchor_y = center[1]
            else:
                self.scroll_anchor_y = None
            if confirmed:
                event_name = self._hand_event(confirmed)
                if event_name:
                    events.append(self._event(event_name, Modality.HAND, hand.get("confidence", 0.0), {"bbox": hand["bbox"]}, active["id"] if active else 0))
                    # OPEN_PALM performs the click.
                    if confirmed == "OPEN_PALM":
                        self.engine.click(*self._screen_from_bbox(hand["bbox"]))
        else:
            self.scroll_anchor_y = None

        result["events"] = [event.to_dict() for event in events if self.modalities.get(event.modality.value.lower(), True)]
        result["active_user_id"] = active["id"] if active else 0
        result["multi_user_detected"] = len(tracking_detections) > 1
        result["tracking_locked"] = active is not None
        result["device"] = getattr(self.provider, "device", "CPU")
        result["model_name"] = getattr(self.provider, "model_name", config.pose_model_name)
        result["hand_model"] = {"name": getattr(self.hand_provider, "model_name", config.hand_model_name), "loaded": getattr(self.hand_provider, "loaded", False), "error": getattr(self.hand_provider, "error", None)}
        result["face_model"] = {"name": getattr(self.face_provider, "model_name", config.face_model_name), "loaded": getattr(self.face_provider, "loaded", False), "error": getattr(self.face_provider, "error", None)}
        result["inference_ms"] = (time.perf_counter() - started) * 1000
        result["fps"] = 1000 / result["inference_ms"] if result["inference_ms"] else 0.0
        self.last_result = result
        return result

    def add_voice_event(self, event: PerceptualEvent) -> Dict[str, Any]:
        result = dict(self.last_result)
        result["events"] = [event.to_dict()]
        x, y = result["cursor"]["x"], result["cursor"]["y"]
        actions = {EventType.VOICE_CLICK: lambda: self.engine.click(int(x), int(y)), EventType.VOICE_DOUBLE_CLICK: lambda: self.engine.double_click(int(x), int(y)), EventType.VOICE_RIGHT_CLICK: lambda: self.engine.right_click(int(x), int(y)), EventType.VOICE_SCROLL_UP: lambda: self.engine.scroll(100), EventType.VOICE_SCROLL_DOWN: lambda: self.engine.scroll(-100)}
        actions.update({EventType.VOICE_GO_LEFT: lambda: self._nudge_cursor(-60, 0), EventType.VOICE_GO_RIGHT: lambda: self._nudge_cursor(60, 0), EventType.VOICE_GO_UP: lambda: self._nudge_cursor(0, -60), EventType.VOICE_GO_DOWN: lambda: self._nudge_cursor(0, 60), EventType.VOICE_GO_BACK: lambda: self.engine.key("left"), EventType.VOICE_GO_FORWARD: lambda: self.engine.key("right"), EventType.VOICE_STOP: lambda: None, EventType.VOICE_PAUSE: lambda: None, EventType.VOICE_RESUME: lambda: None})
        action = actions.get(event.event_type)
        if action:
            print(f"[PERCEPTA_VOICE] executing {event.event_type.value}", flush=True)
            action()
        return result

    def _current_cursor(self) -> Tuple[float, float]:
        width, height = self.engine.adapter.get_screen_size()
        current = getattr(self, "cursor", None)
        if current is None:
            current = [width / 2, height / 2]
            self.cursor = current
        return float(current[0]), float(current[1])

    def _smooth_head_delta(self, center):
        if self.previous_center is None:
            self.previous_center = center
            return 0.0, 0.0
        dx, dy = center[0] - self.previous_center[0], center[1] - self.previous_center[1]
        self.previous_center = center
        dx = 0.0 if abs(dx) < config.dead_zone else dx
        dy = 0.0 if abs(dy) < config.dead_zone else dy
        self.delta_history.append((dx, dy))
        avg_x = sum(item[0] for item in self.delta_history) / len(self.delta_history)
        avg_y = sum(item[1] for item in self.delta_history) / len(self.delta_history)
        self.smoothed_delta = [config.alpha * avg_x + (1 - config.alpha) * self.smoothed_delta[0], config.alpha * avg_y + (1 - config.alpha) * self.smoothed_delta[1]]
        return float(self.smoothed_delta[0]), float(self.smoothed_delta[1])

    def _cursor_position(self, dx, dy):
        width, height = self.engine.adapter.get_screen_size()
        current = list(self._current_cursor())
        margin = 5
        current[0] = max(margin, min(width - margin, current[0] + config.k_head * dx))
        current[1] = max(margin, min(height - margin, current[1] + config.k_head * dy))
        self.cursor = current
        return int(current[0]), int(current[1])

    def _confirm_face(self) -> bool:
        """Dedicated debounce for the eyebrow-raise gesture.

        Separate state from the hand gesture debounce so they don't reset
        each other. Uses config.click_cooldown as the cooldown.
        """
        self._eyebrow_frames += 1
        if (self._eyebrow_frames >= config.gesture_confirmation_frames
                and time.time() - self._eyebrow_last_time >= config.click_cooldown):
            self._eyebrow_last_time = time.time()
            self._eyebrow_frames = 0
            return True
        return False

    def _nudge_cursor(self, dx, dy):
        """Move the cursor by a fixed step (voice directional commands)."""
        width, height = self.engine.adapter.get_screen_size()
        current = list(self._current_cursor())
        margin = 5
        current[0] = max(margin, min(width - margin, current[0] + dx))
        current[1] = max(margin, min(height - margin, current[1] + dy))
        self.cursor = current
        self.engine.move_cursor(int(current[0]), int(current[1]))
        return int(current[0]), int(current[1])

    def _screen_from_hand(self, hand):
        points = hand.get("keypoints") or []
        point = points[8] if len(points) >= 9 else [(hand["bbox"][0] + hand["bbox"][2]) / 2, (hand["bbox"][1] + hand["bbox"][3]) / 2]
        return self._map_frame_to_screen(point[0], point[1])

    def _screen_from_bbox(self, bbox):
        """Map a hand bounding-box centre to screen coordinates.

        Used for FIST/OPEN_PALM where fingertip keypoints are unreliable
        (fingers curled or model didn't return fine keypoints).
        """
        center_x, center_y = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        return self._map_frame_to_screen(center_x, center_y)

    def _map_frame_to_screen(self, frame_x: float, frame_y: float) -> Tuple[int, int]:
        width, height = self.engine.adapter.get_screen_size()
        fw = max(self.frame_width, 1)
        fh = max(self.frame_height, 1)
        margin = 5
        sx = int(max(margin, min(width - margin, frame_x / fw * width)))
        sy = int(max(margin, min(height - margin, frame_y / fh * height)))
        return sx, sy

    def _classify_hand(self, hand):
        label = hand.get("class_name", "").lower().replace(" ", "_").replace("-", "_")
        aliases = {"open_hand": "OPEN_PALM", "palm": "OPEN_PALM", "stop": "OPEN_PALM", "closed_hand": "FIST", "fist": "FIST", "grip": "FIST", "grabbing": "FIST", "point": "POINT", "one": "POINT", "pinch": "PINCH", "thumb_index": "PINCH", "thumb_index2": "PINCH", "thumb_up": "THUMB_UP", "like": "THUMB_UP", "thumb_down": "THUMB_DOWN", "dislike": "THUMB_DOWN", "peace": "TWO_FINGERS", "peace_inverted": "TWO_FINGERS", "two_up": "TWO_FINGERS", "two_up_inverted": "TWO_FINGERS", "victory": "TWO_FINGERS", "v_sign": "TWO_FINGERS", "two": "TWO_FINGERS"}
        if label in aliases:
            return aliases[label]
        points = hand.get("keypoints") or []
        if len(points) < 21:
            return None
        wrist = points[0]
        palm = max(math.dist(wrist, points[9]), 1.0)
        if math.dist(points[4], points[8]) / palm < 0.28:
            return "PINCH"
        extended = [points[tip][1] < points[pip][1] for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18))]
        if extended[0] and extended[1] and not extended[2] and not extended[3]:
            return "TWO_FINGERS"
        if all(extended):
            return "OPEN_PALM"
        if extended[0] and not any(extended[1:]):
            return "POINT"
        if not any(extended):
            return "FIST"
        return None

    def _swipe(self):
        if len(self.hand_history) < config.swipe_min_frames:
            return None
        start, end = self.hand_history[0], self.hand_history[-1]
        dx, dy = end[0] - start[0], end[1] - start[1]
        if math.hypot(dx, dy) < config.swipe_min_velocity:
            return None
        if abs(dx) > abs(dy) * 1.3:
            return "SWIPE_RIGHT" if dx > 0 else "SWIPE_LEFT"
        if abs(dy) > abs(dx) * 1.3:
            return "SWIPE_DOWN" if dy > 0 else "SWIPE_UP"
        return None

    def _horizontal_slide_swipe(self) -> Optional[str]:
        """Detect a fast horizontal swipe for presentation slide control."""
        if len(self.hand_history) < config.swipe_min_frames:
            return None
        start, end = self.hand_history[0], self.hand_history[-1]
        dx, dy = end[0] - start[0], end[1] - start[1]
        if abs(dx) <= abs(dy) * 1.5:
            return None
        if abs(dx) < config.swipe_min_velocity:
            return None
        return "SWIPE_RIGHT" if dx > 0 else "SWIPE_LEFT"

    def _process_hand(self, frame):
        try:
            return self.hand_provider.process(frame, imgsz=256)
        except TypeError:
            return self.hand_provider.process(frame)

    def _confirm(self, gesture):
        now = time.time()
        if gesture is None:
            self.last_gesture, self.gesture_frames = None, 0
            return "NO_GESTURE", None
        self.gesture_frames = self.gesture_frames + 1 if gesture == self.last_gesture else 1
        self.last_gesture = gesture
        state = "CANDIDATE" if self.gesture_frames < config.gesture_confirmation_frames else "CONFIRMED"
        if self.gesture_frames == config.gesture_confirmation_frames and now - self.last_gesture_time >= config.gesture_cooldown:
            self.last_gesture_time = now
            return state, gesture
        return state, None

    @staticmethod
    def _best_hand(detections):
        return max(detections, key=lambda item: item.get("confidence", 0.0), default=None)

    @staticmethod
    def _select_active(tracked, active_id=None):
        if active_id in tracked:
            return {**tracked[active_id], "id": active_id}
        return max(({**value, "id": key} for key, value in tracked.items()), key=lambda item: item.get("confidence", 0.0), default=None)

    @staticmethod
    def _bbox(box):
        return {"x": box[0], "y": box[1], "w": box[2] - box[0], "h": box[3] - box[1]}

    @staticmethod
    def _head_gesture(dx, dy):
        if max(abs(dx), abs(dy)) < 8:
            return None
        return "HEAD_MOVE_RIGHT" if abs(dx) >= abs(dy) and dx > 0 else "HEAD_MOVE_LEFT" if abs(dx) >= abs(dy) else "HEAD_MOVE_DOWN" if dy > 0 else "HEAD_MOVE_UP"

    @staticmethod
    def _hand_event(gesture):
        return {"OPEN_PALM": "HAND_OPEN", "FIST": "HAND_FIST", "POINT": "HAND_POINT", "PINCH": "HAND_PINCH", "TWO_FINGERS": "HAND_TWO_FINGERS", "THUMB_UP": "THUMB_UP", "THUMB_DOWN": "THUMB_DOWN", "SWIPE_LEFT": "HAND_SWIPE_LEFT", "SWIPE_RIGHT": "HAND_SWIPE_RIGHT", "SWIPE_UP": "HAND_SWIPE_UP", "SWIPE_DOWN": "HAND_SWIPE_DOWN"}.get(gesture)

    @staticmethod
    def _event(name, modality, confidence, payload, user_id):
        return PerceptualEvent.make(EventType[name], modality, confidence, payload, user_id)