import { useEffect, useState } from 'react';
import DashboardPanel from '../components/DashboardPanel';

type Status = { modes: Record<string, boolean>; fps: number; device: string; errors: string[]; gestures: Record<string, string>; events: Array<{ event_type: string; modality: string; timestamp: number }>; camera_connected?: boolean };

export default function Dashboard() {
  const [status, setStatus] = useState<Status>({ modes: {}, fps: 0, device: 'unknown', errors: [], gestures: {}, events: [], camera_connected: false });
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  useEffect(() => {
    const socket = new WebSocket(`ws://${window.location.host}/ws`);
    socket.onmessage = (event) => { const data = JSON.parse(event.data); if (data.type === 'status') setStatus(data); };
    const timer = window.setInterval(() => {
      const url = `/api/preview.jpg?t=${Date.now()}`;
      fetch(url).then((response) => {
        if (!response.ok) throw new Error('preview unavailable');
        setPreviewUrl(url);
      }).catch(() => setPreviewUrl(null));
    }, 200);
    return () => { window.clearInterval(timer); socket.close(); };
  }, []);
  const toggle = async (mode: string) => {
    await fetch('/api/modes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ [mode]: !status.modes[mode] }) });
  };
  return <div className="page dashboard-page">
    <div className="page-intro"><div><p className="eyebrow">SESSION / LOCAL AGENT</p><h2>Perceptual field</h2></div><span className="connection-pill connected">● BACKGROUND AGENT</span></div>
    <div style={{ background: '#19352e', padding: 12, marginBottom: 16 }}>Running in background — works with this window minimized</div>
    <div className="modality-controls">{['head', 'hand', 'voice'].map((mode) => <button key={mode} className={status.modes[mode] ? 'selected' : ''} onClick={() => toggle(mode)}>{mode.toUpperCase()}</button>)}</div>
    <div className="dashboard-grid">
      <DashboardPanel title="Agent status" eyebrow="01 / LOCAL PROCESS"><div className="sensor-list"><p>Device: {status.device}</p><p>Loop FPS: {status.fps}</p><p>Head: {status.gestures.head || 'IDLE'}</p><p>Hand: {status.gestures.hand || 'IDLE'}</p><p>Voice: {status.gestures.voice || 'IDLE'}</p>{status.errors.map((error) => <p key={error} style={{ color: '#ff8b8b' }}>{error}</p>)}</div></DashboardPanel>
      <DashboardPanel title="Event stream" eyebrow="02 / OS ACTIONS"><div className="event-list">{status.events.slice().reverse().map((event, index) => <div className="event-row" key={`${event.timestamp}-${index}`}><time>{new Date(event.timestamp * 1000).toLocaleTimeString()}</time><b>{event.event_type}</b><span>{event.modality}</span></div>)}</div></DashboardPanel>
      <DashboardPanel title="Preview" eyebrow="03 / CAMERA"><div style={{ width: 320, maxWidth: '100%' }}><div style={{ marginBottom: 8, color: status.camera_connected ? '#7ee2b8' : '#ffb86b' }}>{status.camera_connected ? '● CAMERA CONNECTED' : '○ CAMERA DISCONNECTED'}</div>{previewUrl ? <img src={previewUrl} alt="Latest local camera preview" style={{ width: 320, maxWidth: '100%' }} /> : <div style={{ width: 320, height: 240, maxWidth: '100%', display: 'grid', placeItems: 'center', background: '#18211f', color: '#9aa9a5' }}>Camera preview unavailable</div>}</div></DashboardPanel>
    </div>
  </div>;
}
