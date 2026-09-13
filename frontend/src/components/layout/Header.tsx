import { useSystemStore } from '../../store/systemStore';
import { usePerceptionStore } from '../../store/perceptionStore';
import { wsService } from '../../services/PerceptaWSService';

export default function Header({ startCamera, startListening, stopListening }: { startCamera: () => void; startListening: () => void; stopListening: () => void }) {
  const status = useSystemStore((state) => state.wsStatus);
  const camera = useSystemStore((state) => state.cameraPermission);
  const mic = useSystemStore((state) => state.micPermission);
  const { faceEnabled, handEnabled, voiceEnabled, setFaceEnabled, setHandEnabled, setVoiceEnabled } = usePerceptionStore();
  const updateModalities = (next: { face: boolean; hand: boolean; voice: boolean }) => {
    setFaceEnabled(next.face);
    setHandEnabled(next.hand);
    setVoiceEnabled(next.voice);
    wsService.sendModalities(next.face, next.hand, next.voice);
    if (next.voice) startListening(); else stopListening();
  };
  return <header className="header"><div><p className="eyebrow">PERCEPTUAL COMPUTING INTERFACE / CONTROL CENTER</p><h1>Live workspace</h1></div><div className="header-actions"><div className="modality-controls"><button className={faceEnabled ? 'selected' : ''} onClick={() => updateModalities({ face: !faceEnabled, hand: handEnabled, voice: voiceEnabled })}>FACE</button><button className={handEnabled ? 'selected' : ''} onClick={() => updateModalities({ face: faceEnabled, hand: !handEnabled, voice: voiceEnabled })}>HAND</button><button className={voiceEnabled ? 'selected' : ''} onClick={() => updateModalities({ face: faceEnabled, hand: handEnabled, voice: !voiceEnabled })}>VOICE</button><button className="camera-action" onClick={startCamera}>START CAMERA</button></div><div className="status-cluster"><span><i className={`status-dot ${status === 'connected' ? 'active' : status === 'error' ? 'error' : 'inactive'}`} /> {status.toUpperCase()}</span><span>CAM {camera === 'granted' ? 'READY' : 'WAITING'}</span><span>MIC {mic === 'granted' ? 'READY' : 'WAITING'}</span></div></div></header>;
}
