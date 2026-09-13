import { NavLink } from 'react-router-dom';

const links = [
  ['/', '01', 'Dashboard'], [' /gestures'.trim(), '02', 'Gestures'], [' /calibration'.trim(), '03', 'Calibration'],
  [' /settings'.trim(), '04', 'Settings'], [' /telemetry'.trim(), '05', 'Telemetry'], [' /about'.trim(), '06', 'About']
];

export default function Sidebar() {
  return <aside className="sidebar">
    <div className="brand"><span className="brand-mark">P</span><div><strong>PERCEPTA</strong><small>PERCEPTUAL COMPUTING</small></div></div>
    <nav>{links.map(([to, number, label]) => <NavLink key={to} to={to} end={to === '/'}><span>{number}</span>{label}</NavLink>)}</nav>
    <div className="sidebar-foot"><span className="status-dot active" /> LOCAL CONTROL PLANE</div>
  </aside>;
}
