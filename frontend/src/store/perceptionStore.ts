import { create } from 'zustand';
import { FaceDetection, HandDetection, CursorPosition, PerceptionResult } from '../types/perception';
import { wsService } from '../services/PerceptaWSService';

interface PerceptionState {
  face: FaceDetection | null;
  hand: HandDetection | null;
  cursor: CursorPosition;
  activeUserId: number;
  multiUserDetected: boolean;
  trackingLocked: boolean;
  faceEnabled: boolean;
  handEnabled: boolean;
  voiceEnabled: boolean;

  updateFromPerceptionResult: (result: PerceptionResult) => void;
  setFaceEnabled: (enabled: boolean) => void;
  setHandEnabled: (enabled: boolean) => void;
  setVoiceEnabled: (enabled: boolean) => void;
}

const savedModalities = (() => {
  try {
    const saved = JSON.parse(localStorage.getItem('percepta_modalities') || '{}');
    return { face: saved.face !== false, hand: saved.hand !== false, voice: saved.voice !== false };
  } catch {
    return { face: true, hand: true, voice: true };
  }
})();

export const usePerceptionStore = create<PerceptionState>((set) => ({
  face: null,
  hand: null,
  cursor: { x: 0, y: 0 },
  activeUserId: 0,
  multiUserDetected: false,
  trackingLocked: false,
  faceEnabled: savedModalities.face,
  handEnabled: savedModalities.hand,
  voiceEnabled: savedModalities.voice,

  updateFromPerceptionResult: (result) => set((state) => ({
    face: state.faceEnabled ? result.face : null,
    hand: state.handEnabled ? result.hand : null,
    cursor: result.cursor,
    activeUserId: result.active_user_id,
    multiUserDetected: result.multi_user_detected,
    trackingLocked: result.tracking_locked
  })),
  setFaceEnabled: (enabled) => set((state) => { const next = { ...state, faceEnabled: enabled }; localStorage.setItem('percepta_modalities', JSON.stringify({ face: enabled, hand: state.handEnabled, voice: state.voiceEnabled })); wsService.sendModalities(enabled, state.handEnabled, state.voiceEnabled); return next; }),
  setHandEnabled: (enabled) => set((state) => { const next = { ...state, handEnabled: enabled }; localStorage.setItem('percepta_modalities', JSON.stringify({ face: state.faceEnabled, hand: enabled, voice: state.voiceEnabled })); wsService.sendModalities(state.faceEnabled, enabled, state.voiceEnabled); return next; }),
  setVoiceEnabled: (enabled) => set((state) => { const next = { ...state, voiceEnabled: enabled }; localStorage.setItem('percepta_modalities', JSON.stringify({ face: state.faceEnabled, hand: state.handEnabled, voice: enabled })); wsService.sendModalities(state.faceEnabled, state.handEnabled, enabled); return next; })
}));