import asyncio
import base64
import json
import os
import time
from typing import Any, Optional

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

try:
    from perception.frame_processor import FrameProcessor
    from gestures.voice.voice_processor import VoiceProcessor
    from config import config
except ImportError:
    from ..perception.frame_processor import FrameProcessor
    from ..gestures.voice.voice_processor import VoiceProcessor
    from ..config import config

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()
processor: Optional[FrameProcessor] = None
processor_lock = asyncio.Lock()
TRACE_PIPELINE = os.getenv("PERCEPTA_TRACE_PIPELINE", "true").lower() != "false"


def trace(stage: int, frame_id: str, message: str) -> None:
    if TRACE_PIPELINE:
        print(f"[PERCEPTA_TRACE] stage={stage} frame={frame_id} ts={time.time() * 1000:.0f} {message}", flush=True)


def unpack_binary_frame(data: bytes) -> tuple[str, bytes]:
    frame_id, encoded = data.split(b"\n", 1)
    return frame_id.decode("ascii"), encoded


async def get_processor() -> FrameProcessor:
    """Create the shared model pipeline without blocking the event loop."""
    global processor
    if processor is None:
        async with processor_lock:
            if processor is None:
                processor = await asyncio.to_thread(FrameProcessor)
                await asyncio.to_thread(processor.warmup)
    return processor


def decode_frame(data: Any) -> Any:
    raw = base64.b64decode(data.split(",", 1)[-1]) if isinstance(data, str) else data
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unable to decode camera frame")
    return image

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "status", "state": "initializing", "message": "Loading perception models…"})
        try:
            active_processor = await get_processor()
            startup = active_processor.empty_result()
            startup["hand_model"] = {"name": active_processor.hand_provider.model_name, "loaded": active_processor.hand_provider.loaded, "error": active_processor.hand_provider.error}
            startup["face_model"] = {"name": active_processor.face_provider.model_name, "loaded": active_processor.face_provider.loaded, "error": active_processor.face_provider.error}
            await websocket.send_json(startup)
        except Exception as exc:
            await websocket.send_json({"type": "error", "message": f"Perception startup failed: {exc}"})
            return
        while True:
            packet = await websocket.receive()
            if packet.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect
            if packet.get("bytes") is not None:
                frame_id, encoded_frame = unpack_binary_frame(packet["bytes"])
                trace(3, frame_id, "received")
                trace(4, frame_id, "processing_start")
                result = await asyncio.to_thread(active_processor.process, decode_frame(encoded_frame))
                trace(5, frame_id, f"inference_finished inference_ms={result.get('inference_ms', 0):.1f}")
                result["trace_frame_id"] = frame_id
                trace(6, frame_id, "event_sent")
                await websocket.send_json(result)
                continue
            message = json.loads(packet["text"])
            kind = message.get("type")
            if kind == "frame":
                try:
                    frame_id = str(message.get("frame_id", "legacy"))
                    trace(3, frame_id, "received")
                    trace(4, frame_id, "processing_start")
                    result = await asyncio.to_thread(active_processor.process, decode_frame(message["data"]))
                    trace(5, frame_id, f"inference_finished inference_ms={result.get('inference_ms', 0):.1f}")
                    result["trace_frame_id"] = frame_id
                    trace(6, frame_id, "event_sent")
                    await websocket.send_json(result)
                except WebSocketDisconnect:
                    raise
                except Exception as exc:
                    try:
                        await websocket.send_json({"type": "error", "message": str(exc)})
                    except Exception:
                        break
            elif kind == "voice":
                event = VoiceProcessor().process(message.get("transcript", ""), float(message.get("confidence", 0.0)))
                if event is not None and active_processor.modalities.get("voice", True):
                    await websocket.send_json(await asyncio.to_thread(active_processor.add_voice_event, event))
            elif kind == "modalities":
                active_processor.update_modalities(bool(message.get("face_enabled", True)), bool(message.get("hand_enabled", True)), bool(message.get("voice_enabled", True)))
                await websocket.send_json({"type": "ack", "request": kind})
            elif kind in {"settings", "calibration"}:
                if kind == "settings":
                    applied = {}
                    for key, value in message.items():
                        if key == "type":
                            continue
                        attr = key.lower()
                        if hasattr(config, attr) and isinstance(getattr(config, attr), (int, float)):
                            try:
                                cast = type(getattr(config, attr))
                                setattr(config, attr, cast(value))
                                applied[key] = getattr(config, attr)
                            except (TypeError, ValueError):
                                continue
                    await websocket.send_json({"type": "ack", "request": kind, "applied": applied})
                else:
                    await websocket.send_json({"type": "ack", "request": kind})
    except WebSocketDisconnect:
        manager.disconnect(websocket)