import { RefCallback, useCallback, useEffect, useRef } from 'react';
import { frameService } from '../services/FrameService';
import { wsService } from '../services/PerceptaWSService';
import { useSystemStore } from '../store/systemStore';

export function useCamera() {
  const streamRef = useRef<MediaStream | null>(null);
  const videoElementRef = useRef<HTMLVideoElement | null>(null);
  const setPermission = useSystemStore((state) => state.setCameraPermission);

  const attachVideo = useCallback(async (element: HTMLVideoElement | null) => {
    videoElementRef.current = element;
    if (element && streamRef.current) {
      element.srcObject = streamRef.current;
      await element.play().catch(() => undefined);
      frameService.setVideo(element);
      frameService.start((frame) => wsService.sendFrame(frame));
    }
  }, []);

  const startCamera = useCallback(async () => {
    if (streamRef.current) {
      await attachVideo(videoElementRef.current);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 }, audio: false });
      streamRef.current = stream;
      setPermission('granted');
      await attachVideo(videoElementRef.current);
    } catch {
      setPermission('denied');
    }
  }, [attachVideo, setPermission]);

  const stopCamera = useCallback(() => {
    frameService.stop();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoElementRef.current) videoElementRef.current.srcObject = null;
  }, []);

  useEffect(() => stopCamera, [stopCamera]);
  return { videoRef: attachVideo as RefCallback<HTMLVideoElement>, startCamera, stopCamera };
}
