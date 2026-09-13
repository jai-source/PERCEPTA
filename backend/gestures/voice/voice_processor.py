from typing import Any, Dict
from ..base import BaseGestureDetector
try:
    from ...events.event_types import EventType, Modality, PerceptualEvent
except ImportError:
    from events.event_types import EventType, Modality, PerceptualEvent

class VoiceCommandProcessor(BaseGestureDetector):
    def __init__(self):
        self.commands = {
            "double click": "VOICE_DOUBLE_CLICK",
            "right click": "VOICE_RIGHT_CLICK",
            "scroll up": "VOICE_SCROLL_UP",
            "scroll down": "VOICE_SCROLL_DOWN",
            "go left": "VOICE_GO_LEFT",
            "go right": "VOICE_GO_RIGHT",
            "go up": "VOICE_GO_UP",
            "go down": "VOICE_GO_DOWN",
            "go back": "VOICE_GO_BACK",
            "go forward": "VOICE_GO_FORWARD",
            "click": "VOICE_CLICK",
            "start": "start_action",
            "stop": "VOICE_STOP",
            "pause": "VOICE_PAUSE",
            "resume": "VOICE_RESUME",
            "select": "select_action",
            "cancel": "cancel_action"
        }

    def detect(self, audio_features: Any) -> Dict[str, Any]:
        if not audio_features or 'transcription' not in audio_features:
            return {"gesture": "none", "confidence": 0.0}

        text = audio_features['transcription'].lower().strip()
        
        for keyword, command in self.commands.items():
            if keyword in text:
                return {"gesture": command, "confidence": 0.9}
                
        return {"gesture": "none", "confidence": 0.0}

class VoiceProcessor(VoiceCommandProcessor):
    """Public voice API that emits normalized perceptual events."""

    def process(self, transcript: str, confidence: float = 1.0) -> PerceptualEvent | None:
        text = transcript.lower().strip()
        for phrase, event_name in self.commands.items():
            if phrase in text and event_name.startswith("VOICE_"):
                return PerceptualEvent.make(
                    event_type=EventType[event_name],
                    modality=Modality.VOICE,
                    confidence=confidence,
                    payload={"command": phrase, "transcript": transcript},
                )
        return None
