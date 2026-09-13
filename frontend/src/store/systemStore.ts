import { create } from 'zustand';
import { ConnectionStatus } from '../types/events';

interface SystemState {
  cameraPermission: 'unknown' | 'granted' | 'denied';
  micPermission: 'unknown' | 'granted' | 'denied';
  wsStatus: ConnectionStatus;
  connectionMessage: string | null;
  backendOnline: boolean;
  device: 'CUDA' | 'CPU' | null;
  modelName: string | null;
  interactionMode: 'browser' | 'windows' | 'linux' | 'macos';
  isProcessing: boolean;
  fps: number;
  inferenceMs: number;
    handModelLoaded: boolean;
    faceModelLoaded: boolean;
  startTime: number | null;
  
  setCameraPermission: (perm: 'unknown' | 'granted' | 'denied') => void;
  setMicPermission: (perm: 'unknown' | 'granted' | 'denied') => void;
  setWsStatus: (status: ConnectionStatus) => void;
  setConnectionMessage: (message: string | null) => void;
  setDevice: (device: 'CUDA' | 'CPU', modelName: string) => void;
  setFps: (fps: number, inferenceMs: number) => void;
    setModelStatus: (handLoaded: boolean, faceLoaded: boolean) => void;
  setProcessing: (isProcessing: boolean) => void;
  setInteractionMode: (mode: 'browser' | 'windows' | 'linux' | 'macos') => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  cameraPermission: 'unknown',
  micPermission: 'unknown',
  wsStatus: 'disconnected',
  connectionMessage: null,
  backendOnline: false,
  device: null,
  modelName: null,
  interactionMode: 'browser',
  isProcessing: false,
  fps: 0,
  inferenceMs: 0,
    handModelLoaded: false,
    faceModelLoaded: false,
  startTime: Date.now(),

  setCameraPermission: (perm) => set({ cameraPermission: perm }),
  setMicPermission: (perm) => set({ micPermission: perm }),
  setWsStatus: (status) => set({ wsStatus: status, backendOnline: status === 'connected' }),
  setConnectionMessage: (message) => set({ connectionMessage: message }),
  setDevice: (device, modelName) => set({ device, modelName }),
  setFps: (fps, inferenceMs) => set({ fps, inferenceMs }),
    setModelStatus: (handLoaded, faceLoaded) => set({ handModelLoaded: handLoaded, faceModelLoaded: faceLoaded }),
  setProcessing: (isProcessing) => set({ isProcessing }),
  setInteractionMode: (mode) => set({ interactionMode: mode })
}));
