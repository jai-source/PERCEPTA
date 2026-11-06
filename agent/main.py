from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
import traceback
import urllib.request
import zipfile
from collections import deque
from queue import Empty, Queue
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("percepta.agent")

try:
    from backend.config import config
    from backend.perception.frame_processor import FrameProcessor
    from backend.interaction.engine import InteractionEngine
except ImportError:
    from config import config
    from perception.frame_processor import FrameProcessor
    from interaction.engine import InteractionEngine

try:
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
except ImportError:
    mp_python = vision = None


class ModeManager:
    def __init__(self) -> None:
        self.path = ROOT / "config" / "modes.json"
        self.modes = {"head": False, "hand": False, "voice": False}
        try:
            self.modes.update(json.loads(self.path.read_text()))
        except (OSError, ValueError):
            pass
        self.lock = threading.Lock()

    def update(self, values: dict[str, Any]) -> dict[str, bool]:
        with self.lock:
            for key in self.modes:
                if key in values:
                    self.modes[key] = bool(values[key])
            self.path.parent.mkdir(exist_ok=True)
            self.path.write_text(json.dumps(self.modes, indent=2))
            return dict(self.modes)

    def enabled(self, name: str) -> bool:
        with self.lock:
            return self.modes[name]


class Agent:
    def __init__(self) -> None:
        self.modes = ModeManager()
        self.frame: np.ndarray | None = None
        self.frame_lock = threading.Lock()
        self.running = True
        self.errors: list[str] = []
        self.events: deque[dict[str, Any]] = deque(maxlen=30)
        self.gestures = {"head": "", "hand": "", "voice": ""}
        self.fps = 0.0
        self.last_frame_time = 0.0
        self.processor: FrameProcessor | None = None
        self.engine = InteractionEngine("windows")
        self.screen = self.engine.adapter.get_screen_size()
        self.device = "cpu"
        print(f"[PERCEPTA] adapter={type(self.engine.adapter).__name__} screen={self.screen[0]}x{self.screen[1]}")
        self._threads: list[threading.Thread] = []
        self._voice_command_time = 0.0

    def error(self, message: str) -> None:
        if message not in self.errors:
            self.errors.append(message)
        log.error(message)

    def start(self) -> None:
        self._threads.append(threading.Thread(target=self.camera_loop, daemon=True))
        self._threads.append(threading.Thread(target=self.vision_loop, daemon=True))
        self._threads.append(threading.Thread(target=self.voice_loop, daemon=True))
        for thread in self._threads:
            thread.start()

    def voice_loop(self) -> None:
        while self.running:
            if not self.modes.enabled("voice"):
                time.sleep(0.1)
                continue
            try:
                import sounddevice as sd
                import vosk
                model_dir = ROOT / "models" / "vosk-model-small-en-us-0.15"
                if not model_dir.exists():
                    archive = ROOT / "models" / "vosk-model.zip"
                    urllib.request.urlretrieve(
                        "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip", archive)
                    with zipfile.ZipFile(archive) as zipped:
                        zipped.extractall(ROOT / "models")
                    archive.unlink()
                recognizer = vosk.KaldiRecognizer(vosk.Model(str(model_dir)), 16000,
                    json.dumps(["click", "double click", "right click", "scroll up",
                                "scroll down", "go left", "go right", "go up", "go down",
                                "next slide", "previous slide", "stop", "[unk]"]))
                audio: Queue[bytes] = Queue(maxsize=8)

                def on_audio(data: Any, _frames: int, _time: Any, status: Any) -> None:
                    if status:
                        self.error(f"voice audio: {status}")
                    try:
                        audio.put_nowait(bytes(data))
                    except Exception:
                        pass

                with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype="int16",
                                       channels=1, callback=on_audio):
                    print("[VOICE] Microphone opened", flush=True)
                    while self.running and self.modes.enabled("voice"):
                        try:
                            chunk = audio.get(timeout=0.1)
                        except Empty:
                            continue
                        if recognizer.AcceptWaveform(chunk):
                            phrase = json.loads(recognizer.Result()).get("text", "").strip().lower()
                            if phrase:
                                print(f"[VOICE] Recognized: {phrase}", flush=True)
                                self.handle_voice(phrase)
                    final_phrase = json.loads(recognizer.FinalResult()).get("text", "").strip().lower()
                    if final_phrase:
                        print(f"[VOICE] Recognized: {final_phrase}", flush=True)
                        self.handle_voice(final_phrase)
            except Exception as exc:
                print(f"[VOICE] Error: {exc}", flush=True)
                self.error(f"voice unavailable: {exc}")
                time.sleep(1)

    def handle_voice(self, phrase: str) -> None:
        now = time.time()
        if now - self._voice_command_time < 0.8:
            return
        actions = {
            "click": lambda: self.engine.click(*self._position()),
            "double click": lambda: self.engine.double_click(*self._position()),
            "right click": lambda: self.engine.right_click(*self._position()),
            "scroll up": lambda: self.engine.scroll(120),
            "scroll down": lambda: self.engine.scroll(-120),
            "go left": lambda: self.engine.move_cursor(self._position()[0] - 60, self._position()[1]),
            "go right": lambda: self.engine.move_cursor(self._position()[0] + 60, self._position()[1]),
            "go up": lambda: self.engine.move_cursor(self._position()[0], self._position()[1] - 60),
            "go down": lambda: self.engine.move_cursor(self._position()[0], self._position()[1] + 60),
            "next slide": lambda: self.engine.key("right"),
            "previous slide": lambda: self.engine.key("left"),
        }
        for command, action in sorted(actions.items(), key=lambda item: len(item[0]), reverse=True):
            if command in phrase:
                self._voice_command_time = now
                self.gestures["voice"] = command
                print(f"[VOICE] Executing: {command}", flush=True)
                self._action(command, action, "VOICE")
                return
        if "stop" in phrase:
            self._voice_command_time = now
            self.modes.update({"voice": False})
            self.gestures["voice"] = "stop"
            print("[VOICE] Executing: stop", flush=True)
            self.events.append({"event_type": "VOICE_STOP", "modality": "VOICE", "timestamp": time.time()})

    def camera_loop(self) -> None:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if os.name == "nt" else 0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            self.error("camera could not be opened")
            return
        while self.running:
            ok, frame = cap.read()
            if ok:
                with self.frame_lock:
                    self.frame = frame
            else:
                time.sleep(0.01)
        cap.release()

    def _ensure_processor(self) -> None:
        if self.processor is None:
            self.processor = FrameProcessor()
            self.processor.warmup()
            self.device = getattr(self.processor.provider, "device", "CPU").lower()
            print(f"[PERCEPTA] device={self.device}", flush=True)

    def vision_loop(self) -> None:
        while self.running:
            with self.frame_lock:
                frame = None if self.frame is None else self.frame.copy()
            if frame is not None and (self.modes.enabled("head") or self.modes.enabled("hand")):
                try:
                    self._ensure_processor()
                    self.processor.update_modalities(
                        self.modes.enabled("head"),
                        self.modes.enabled("hand"),
                        self.modes.enabled("voice"),
                    )
                    result = self.processor.process(frame) if self.processor else {}
                    self.fps = float(result.get("fps", self.fps))
                    self.gestures["head"] = (result.get("face") or {}).get("gesture", "")
                    self.gestures["hand"] = (result.get("hand") or {}).get("gesture", "")
                except Exception as exc:
                    self.error(f"vision: {exc}")
                    traceback.print_exc()
            time.sleep(0.005)

    def _position(self) -> tuple[int, int]:
        try:
            import pyautogui
            return pyautogui.position()
        except Exception:
            return self.screen[0] // 2, self.screen[1] // 2

    def _action(self, name: str, action: Any, modality: str = "HAND") -> None:
        try:
            if action():
                self.events.append({"event_type": name.upper(), "modality": modality, "timestamp": time.time()})
        except Exception:
            log.exception("OS action failed: %s", name)

    def status(self) -> dict[str, Any]:
        return {"modes": dict(self.modes.modes), "fps": round(self.fps, 1),
                "device": self.device, "errors": self.errors[-5:],
                "adapter": type(self.engine.adapter).__name__, "screen": self.screen,
                "gestures": dict(self.gestures), "events": list(self.events)}


agent = Agent()
app = FastAPI(title="PERCEPTA Local Agent")

dist = ROOT / "frontend" / "dist"
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")


@app.get("/api/status")
def status() -> dict[str, Any]:
    value = agent.status()
    value["camera_connected"] = agent.frame is not None
    return value


@app.post("/api/modes")
def modes(values: dict[str, Any]) -> dict[str, Any]:
    return {"modes": agent.modes.update(values)}


@app.post("/api/settings")
def settings(values: dict[str, Any]) -> dict[str, Any]:
    applied = {}
    for key, value in values.items():
        if hasattr(config, key) and isinstance(getattr(config, key), (int, float, str, bool)):
            setattr(config, key, type(getattr(config, key))(value))
            applied[key] = getattr(config, key)
    return {"applied": applied}


@app.get("/api/preview.jpg")
def preview() -> Response:
    with agent.frame_lock:
        frame = None if agent.frame is None else agent.frame.copy()
    if frame is None:
        return Response(status_code=404)
    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (320, 240))
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return Response(encoded.tobytes() if ok else b"", media_type="image/jpeg")


@app.websocket("/ws")
async def websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            value = agent.status()
            value["camera_connected"] = agent.frame is not None
            await websocket.send_json({"type": "status", **value})
            await asyncio.sleep(0.1)
    except (WebSocketDisconnect, RuntimeError):
        pass


@app.get("/{path:path}")
def frontend(path: str) -> FileResponse:
    target = dist / path if path else dist / "index.html"
    if target.exists() and target.is_file():
        return FileResponse(target)
    return FileResponse(dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    agent.start()
    uvicorn.run(app, host="127.0.0.1", port=8765)
