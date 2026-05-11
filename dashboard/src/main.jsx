import React from 'react';
import ReactDOM from 'react-dom/client';
import BatteryDashboard from '../BatteryDashboard.jsx';
import './index.css';

// Set this to your raw GitHub URL OR keep relative for same-host hosting.
const DATA_URL =
  import.meta.env.VITE_DATA_URL ||
  '/current.json'; // served from publicDir in vite.config.js

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BatteryDashboard dataUrl={DATA_URL} />
  </React.StrictMode>
);
