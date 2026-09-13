import { useSystemStore } from '../../store/systemStore';

export default function StatusBar() {
  const { fps, inferenceMs, device, modelName, wsStatus, connectionMessage, handModelLoaded } = useSystemStore();
  return <footer className="status-bar"><span>PERCEPTA / {wsStatus.toUpperCase()} / HAND {handModelLoaded ? 'READY' : 'WAITING'}</span><span>{connectionMessage || `${device || 'NO DEVICE'} · ${modelName || 'awaiting backend'} · ${fps.toFixed(0)} FPS · ${inferenceMs.toFixed(0)} MS`}</span></footer>;
}
