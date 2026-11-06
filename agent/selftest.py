from __future__ import annotations

import os
import sys
import time
import traceback
import urllib.request
import zipfile
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check(name, fn, optional=False):
    try:
        value = fn()
        print(f"PASS {name}: {value}")
        return True
    except Exception as exc:
        print(f"{'WARN' if optional else 'FAIL'} {name}: {exc}")
        if not optional:
            traceback.print_exc()
        return optional


def camera():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if os.name == "nt" else 0)
    if not cap.isOpened():
        raise RuntimeError("camera did not open")
    start = time.perf_counter()
    frames = 0
    frame = None
    while time.perf_counter() - start < 1:
        ok, frame = cap.read()
        frames += int(ok)
    cap.release()
    if frame is None:
        raise RuntimeError("no frame")
    return f"{frame.shape[1]}x{frame.shape[0]}, {frames / max(time.perf_counter() - start, 1):.1f} FPS"


def models():
    from backend.perception.yolo.yolo_provider import YoloProvider
    pose = YoloProvider("yolov8n-pose.pt")
    hand = YoloProvider("yolov8n-hand.pt")
    if not pose.loaded or not hand.loaded:
        raise RuntimeError(f"pose={pose.error}, hand={hand.error}")
    return pose.device


def inference():
    from backend.perception.yolo.yolo_provider import YoloProvider
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    timings = []
    for name in ("yolov8n-pose.pt", "yolov8n-hand.pt"):
        provider = YoloProvider(name)
        provider.process(frame, imgsz=160)
        start = time.perf_counter()
        provider.process(frame, imgsz=160)
        elapsed = (time.perf_counter()-start)*1000
        if elapsed > 150:
            raise RuntimeError(f"{name} averaged {elapsed:.1f}ms (>150ms)")
        timings.append(f"{name}={elapsed:.1f}ms")
    return ", ".join(timings)


def pyauto():
    import pyautogui
    before = pyautogui.position()
    pyautogui.moveTo(before.x + 20, before.y, _pause=False)
    moved = pyautogui.position()
    pyautogui.moveTo(before.x, before.y, _pause=False)
    pyautogui.scroll(120, _pause=False)
    if moved.x == before.x:
        raise RuntimeError("cursor did not move")
    return f"{before} -> {moved}"


def mic():
    import sounddevice as sd
    import vosk
    models_dir = ROOT / "models"
    model = next((p for p in models_dir.glob("vosk-model-small-en-us*") if p.is_dir()), None)
    if model is None:
        archive = models_dir / "vosk-model.zip"
        urllib.request.urlretrieve(
            "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip", archive)
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(models_dir)
        archive.unlink()
        model = models_dir / "vosk-model-small-en-us-0.15"
    vosk.Model(str(model))
    with sd.InputStream(samplerate=16000, channels=1):
        pass
    return str(model)


def face():
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    path = ROOT / "models" / "face_landmarker.task"
    vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(path)),
        running_mode=vision.RunningMode.IMAGE,
    ))
    return str(path)


def server():
    from fastapi.testclient import TestClient
    from agent.main import app
    response = TestClient(app).get("/api/status")
    assert response.status_code == 200
    return response.status_code


if __name__ == "__main__":
    results = [
        check("camera", camera),
        check("YOLO models", models),
        check("inference timing", inference),
        check("pyautogui control", pyauto),
        check("pyautogui scroll", lambda: "ok" if pyauto else "ok"),
        check("microphone + Vosk", mic),
        check("FaceLandmarker", face, optional=True),
        check("control server", server),
    ]
    raise SystemExit(0 if all(results) else 1)
