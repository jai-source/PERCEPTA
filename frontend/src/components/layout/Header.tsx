import { useSystemStore } from '../../store/systemStore';

export default function Header() {
  const status = useSystemStore((state) => state.wsStatus);
  return <header className="header"><div><p className="eyebrow">PERCEPTUAL COMPUTING INTERFACE / CONTROL CENTER</p><h1>Live workspace</h1></div><div className="status-cluster"><span><i className={`status-dot ${status === 'connected' ? 'active' : 'inactive'}`} /> {status.toUpperCase()}</span><span>LOCAL CAMERA AGENT</span></div></header>;
}
