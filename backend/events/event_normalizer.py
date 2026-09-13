from .event_types import EventType, Modality, PerceptualEvent


class EventNormalizer:
    def normalize_face_gesture(self, gesture: str, confidence: float, payload: dict) -> PerceptualEvent:
        return PerceptualEvent.make(EventType[gesture], Modality.FACE, confidence, payload)

    def normalize_voice_command(self, event_type: str, confidence: float) -> PerceptualEvent:
        return PerceptualEvent.make(EventType[event_type], Modality.VOICE, confidence)
