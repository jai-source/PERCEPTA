import { useEffect } from 'react';
import { wsService } from '../services/PerceptaWSService';
import { useEventStore } from '../store/eventStore';
import { usePerceptionStore } from '../store/perceptionStore';
import { useSystemStore } from '../store/systemStore';

const TRACE_PIPELINE = import.meta.env.VITE_TRACE_PIPELINE !== 'false';

export function useWebSocket() {
  const updatePerception = usePerceptionStore((state) => state.updateFromPerceptionResult);
  const addEvents = useEventStore((state) => state.addEvents);
  const setStatus = useSystemStore((state) => state.setWsStatus);
  const setConnectionMessage = useSystemStore((state) => state.setConnectionMessage);
  const setDevice = useSystemStore((state) => state.setDevice);
  const setFps = useSystemStore((state) => state.setFps);
  const setProcessing = useSystemStore((state) => state.setProcessing);
  const setModelStatus = useSystemStore((state) => state.setModelStatus);

  useEffect(() => {
    const configuredUrl = import.meta.env.VITE_WS_URL;
    const url = configuredUrl || `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`;
    wsService.onStatusChange(setStatus);
    wsService.onMessage(setConnectionMessage);
    wsService.onPerception((result) => {
      updatePerception(result);
      addEvents(result.events || []);
      setDevice(result.device, result.model_name);
      setFps(result.fps, result.inference_ms);
      setProcessing(true);
      setModelStatus(Boolean(result.hand_model?.loaded), Boolean(result.face_model?.loaded));
      if (TRACE_PIPELINE && result.trace_frame_id !== undefined) {
        requestAnimationFrame(() => console.log(`[PERCEPTA_TRACE] stage=8 frame=${result.trace_frame_id} ts=${Date.now()} ui_updated`));
      }
    });
    wsService.connect(url);
    return () => wsService.disconnect();
  }, [addEvents, setConnectionMessage, setDevice, setFps, setModelStatus, setProcessing, setStatus, updatePerception]);
}
