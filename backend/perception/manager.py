from typing import Dict, Any, List
from ..gestures.face_gestures.head_movement import HeadMovementDetector
from ..gestures.face_gestures.blink_detector import BlinkDetector
from ..gestures.face_gestures.eyebrow_detector import EyebrowDetector
from ..gestures.hand_gestures.static_gestures import StaticHandGestureDetector
from ..gestures.hand_gestures.dynamic_gestures import DynamicHandGestureDetector
from ..gestures.voice.voice_processor import VoiceCommandProcessor
from ..gestures.temporal import TemporalGestureFilter

class PerceptionManager:
    def __init__(self):
        self.face_detectors = [
            HeadMovementDetector(),
            BlinkDetector(),
            EyebrowDetector()
        ]
        self.hand_detectors = [
            StaticHandGestureDetector(),
            DynamicHandGestureDetector()
        ]
        self.voice_processor = VoiceCommandProcessor()
        
        self.gesture_filters = {
            "face": TemporalGestureFilter(window_size=5),
            "hand": TemporalGestureFilter(window_size=10),
            "voice": TemporalGestureFilter(window_size=1, confidence_threshold=0.8) 
        }

    def process_frame(self, frame_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single multimodal frame containing video and audio features.
        """
        results = {
            "face_gestures": [],
            "hand_gestures": [],
            "voice_commands": []
        }
        
        if 'face_landmarks' in frame_data:
            best_face_gesture = {"gesture": "none", "confidence": 0.0}
            for detector in self.face_detectors:
                res = detector.detect(frame_data['face_landmarks'])
                if res['confidence'] > best_face_gesture['confidence']:
                    best_face_gesture = res
            
            filtered = self.gesture_filters['face'].update(
                best_face_gesture['gesture'], best_face_gesture['confidence']
            )
            if filtered != "none":
                results['face_gestures'].append(filtered)
                
        if 'hand_landmarks' in frame_data:
            best_hand_gesture = {"gesture": "none", "confidence": 0.0}
            for detector in self.hand_detectors:
                res = detector.detect(frame_data['hand_landmarks'])
                if res['confidence'] > best_hand_gesture['confidence']:
                    best_hand_gesture = res
                    
            filtered = self.gesture_filters['hand'].update(
                best_hand_gesture['gesture'], best_hand_gesture['confidence']
            )
            if filtered != "none":
                results['hand_gestures'].append(filtered)
                
        if 'audio_features' in frame_data:
            res = self.voice_processor.detect(frame_data['audio_features'])
            filtered = self.gesture_filters['voice'].update(
                res['gesture'], res['confidence']
            )
            if filtered != "none":
                results['voice_commands'].append(filtered)
                
        return self._fuse_modalities(results)
        
    def _fuse_modalities(self, raw_results: Dict[str, List[str]]) -> Dict[str, Any]:
        intents = []
        
        if "nod_down" in raw_results['face_gestures'] or "thumbs_up" in raw_results['hand_gestures']:
            intents.append("CONFIRM")
            
        if "swipe_right" in raw_results['hand_gestures']:
            intents.append("NEXT")
            
        if "blink" in raw_results['face_gestures'] and "open_palm" in raw_results['hand_gestures']:
            intents.append("ATTENTION")
            
        if "start_action" in raw_results['voice_commands']:
            intents.append("START")
            
        return {
            "raw_gestures": raw_results,
            "intents": intents
        }
