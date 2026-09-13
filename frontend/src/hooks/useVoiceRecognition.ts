import { useCallback, useEffect } from 'react';
import { voiceService } from '../services/VoiceService';
import { wsService } from '../services/PerceptaWSService';
import { useEventStore } from '../store/eventStore';
import { useSystemStore } from '../store/systemStore';
import { usePerceptionStore } from '../store/perceptionStore';

export function useVoiceRecognition() {
  const setPermission = useSystemStore((state) => state.setMicPermission);
  const addVoiceEvent = useEventStore((state) => state.addVoiceEvent);
  const voiceEnabled = usePerceptionStore((state) => state.voiceEnabled);

  useEffect(() => {
    voiceService.onCommand((command, transcript, confidence) => {
      if (voiceEnabled) {
        addVoiceEvent(command.replace('VOICE_', ''), confidence);
        wsService.sendVoiceCommand(command, transcript, confidence);
      }
    });
    voiceService.onListeningChange((listening) => setPermission(listening ? 'granted' : 'unknown'));
  }, [addVoiceEvent, setPermission, voiceEnabled]);

  const startListening = useCallback(() => voiceService.start(), []);
  const stopListening = useCallback(() => voiceService.stop(), []);
  return { startListening, stopListening, supported: voiceService.isSupported() };
}
