import { Login } from './components/Login';
import './App.css'; // Mantenemos los estilos globales por defecto si existen

function App() {
  return (
    <div className="app-container">
      {/* Aquí estamos renderizando el componente que creaste */}
      <Login />
    </div>
  );
}

export default App;