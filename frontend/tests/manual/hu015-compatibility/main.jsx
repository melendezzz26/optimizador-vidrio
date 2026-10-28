import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '../../../src/index.css';
import App from '../../../src/App.jsx';

// Standalone Vite test entry, excluded from the production build. Exercise the
// historical authenticated UI without putting a second flow in main navigation.
createRoot(document.getElementById('root')).render(
  <StrictMode><App optimizationMode="hu015" /></StrictMode>,
);
