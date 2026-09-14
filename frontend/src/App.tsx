import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import StatusBar from './components/layout/StatusBar';
import Dashboard from './pages/Dashboard';
import Gestures from './pages/Gestures';
import Calibration from './pages/Calibration';
import Settings from './pages/Settings';
import Telemetry from './pages/Telemetry';
import About from './pages/About';

import { useWebSocket } from './hooks/useWebSocket';
import { useCamera } from './hooks/useCamera';
import { useVoiceRecognition } from './hooks/useVoiceRecognition';
import { usePerceptionStore } from './store/perceptionStore';

function App() {
  // Initialize services
  useWebSocket();
  const { videoRef, startCamera } = useCamera();
  const { startListening, stopListening, supported } = useVoiceRecognition();
  const voiceEnabled = usePerceptionStore((state) => state.voiceEnabled);

  useEffect(() => {
    // Start camera on mount
    startCamera();
    // Auto-start voice listening on mount if enabled and the browser
    // supports the Web Speech API (Chrome/Edge only).
    if (voiceEnabled && supported) {
      startListening();
    }
  }, [startCamera, startListening, supported, voiceEnabled]);

  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-content">
        <Header startCamera={startCamera} startListening={startListening} stopListening={stopListening} />
        {!supported && (
          <div className="voice-unsupported-warning" style={{ background: '#3a2a1a', color: '#ffb86b', padding: '8px 16px', fontSize: '13px', textAlign: 'center' }}>
            ⚠ Voice control requires Chrome or Edge — Web Speech API is not supported in this browser.
          </div>
        )}
        <div className="content-area">
          <Routes>
            <Route path="/" element={<Dashboard videoRef={videoRef} />} />
            <Route path="/gestures" element={<Gestures />} />
            <Route path="/calibration" element={<Calibration />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/telemetry" element={<Telemetry />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </div>
        <StatusBar />
      </div>
    </div>
  );
}

export default App;