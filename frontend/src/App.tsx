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

function App() {
  useWebSocket();

  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-content">
        <Header />
        <div className="content-area">
          <Routes>
            <Route path="/" element={<Dashboard />} />
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