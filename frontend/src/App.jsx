import { Login } from './components/Login';
import NuevoPedido from "./pages/NuevoPedido";
import './App.css'; // Mantenemos los estilos globales por defecto si existen

function App() {
  return (
    <div className="app-container">
      <Login />
        
      <NuevoPedido />
    
    </div>
  );
}

export default App;