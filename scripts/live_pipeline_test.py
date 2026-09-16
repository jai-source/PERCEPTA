"""Send real frames and voice commands through the live websocket pipeline."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import websockets

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

WS_URL = "ws://127.0.0.1:8000/ws"


def make_test_frame() -> bytes:
    """Synthetic frame with a person-like blob for pose detection."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Body-like rectangle
    cv2.rectangle(img, (220, 80), (420, 460), (180, 160, 140), -1)
    # Head circle
    cv2.circle(img, (320, 120), 45, (200, 180, 160), -1)
    ok, encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    if not ok:
        raise RuntimeError("Failed to encode test frame")
    return encoded.tobytes()


async def run_live_test() -> None:
    frame_bytes = make_test_frame()
    print("=== LIVE PIPELINE TEST START ===", flush=True)
    async with websockets.connect(WS_URL, max_size=8 * 1024 * 1024) as ws:
        startup = json.loads(await ws.recv())
        print("startup:", json.dumps({k: startup[k] for k in startup if k in {"type", "hand_model", "face_model", "tracking_locked"}}, indent=2), flush=True)

        for frame_id in range(1, 9):
            header = f"{frame_id}\n".encode("ascii")
            await ws.send(header + frame_bytes)
            result = json.loads(await ws.recv())
            print(
                f"frame={frame_id} face={result.get('face', {}).get('detected')} "
                f"hand={result.get('hand', {}).get('detected')} gesture={result.get('hand', {}).get('gesture')} "
                f"cursor={result.get('cursor')} inference_ms={result.get('inference_ms', 0):.1f}",
                flush=True,
            )

        voice_cmds = ["scroll up", "scroll down", "go left", "go right", "click"]
        for transcript in voice_cmds:
            await ws.send(json.dumps({"type": "voice", "transcript": transcript, "confidence": 0.95}))
            result = json.loads(await ws.recv())
            events = result.get("events", [])
            et = events[0]["event_type"] if events else "none"
            print(f"voice={transcript!r} -> event={et}", flush=True)

    print("=== LIVE PIPELINE TEST END ===", flush=True)


if __name__ == "__main__":
    asyncio.run(run_live_test())
