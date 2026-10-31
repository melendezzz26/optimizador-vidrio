// Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '../../../src/index.css';
import App from '../../../src/App.jsx';
// Entrada exclusiva de regresión, excluida del build de producción.
createRoot(document.getElementById('root')).render(<StrictMode><App optimizationMode="legacy-first-fit" /></StrictMode>);
