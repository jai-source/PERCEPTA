import time
from typing import List
from .event_types import PerceptualEvent, EventType, Modality
from .event_bus import EventBus

class MultimodalFusion:
    def __init__(self, event_bus: EventBus, time_window: float = 2.0):
        self.event_bus = event_bus
        self.time_window = time_window  # seconds
        self.recent_events: List[PerceptualEvent] = []
        
        # Subscribe to relevant modalities for fusion
        self.event_bus.subscribe(Modality.VISION, self._handle_event)
        self.event_bus.subscribe(Modality.AUDIO, self._handle_event)

    async def _handle_event(self, event: PerceptualEvent):
        # Prevent looping with FUSION events
        if event.modality == Modality.FUSION:
            return 
            
        current_time = time.time()
        
        # Add to buffer and clean up old events
        self.recent_events.append(event)
        self.recent_events = [
            e for e in self.recent_events 
            if current_time - e.timestamp <= self.time_window
        ]
        
        await self._evaluate_fusion_rules()

    async def _evaluate_fusion_rules(self):
        """
        Evaluates rules over recent events and publishes fused intents if criteria are met.
        """
        # Example Rule: Voice pointing command + pointing gesture -> Target Selection Intent
        voice_events = [e for e in self.recent_events if e.event_type == EventType.VOICE_COMMAND]
        gesture_events = [e for e in self.recent_events if e.event_type == EventType.GESTURE]
        
        if not voice_events or not gesture_events:
            return
            
        latest_voice = voice_events[-1]
        latest_gesture = gesture_events[-1]
        
        # Check time proximity between the two events
        if abs(latest_voice.timestamp - latest_gesture.timestamp) < 1.0:
            text = latest_voice.data.get("text", "").lower()
            gesture_name = latest_gesture.data.get("gesture_name", "").lower()
            
            # Simple keyword matching and gesture verification
            if any(word in text for word in ["this", "that", "there", "select"]):
                if gesture_name in ["point", "index_finger"]:
                    
                    # Create Fused Intent Event
                    fused_event = PerceptualEvent(
                        modality=Modality.FUSION,
                        event_type=EventType.FUSED_INTENT,
                        source="fusion_engine",
                        confidence=(latest_voice.confidence + latest_gesture.confidence) / 2,
                        data={
                            "intent": "select_target",
                            "voice_trigger": latest_voice.id,
                            "gesture_trigger": latest_gesture.id,
                            "target_location": latest_gesture.data.get("landmarks", [])
                        }
                    )
                    
                    # Clear events that were consumed to prevent re-triggering
                    self.recent_events = [
                        e for e in self.recent_events 
                        if e.id != latest_voice.id and e.id != latest_gesture.id
                    ]
                    
                    await self.event_bus.publish(fused_event)
