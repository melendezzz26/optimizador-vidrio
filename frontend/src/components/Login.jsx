import './Login.css';

export const Login = () => {
  return (
    <div className="login-body-wrapper">      
      <div className="container">
        {/* Mitad Izquierda: Formulario limpio */}
        <div className="form-container">
          <form onSubmit={(e) => e.preventDefault()}>
            <h1>Iniciar sesión</h1>
            
            <input type="text" placeholder="Nombre de usuario" />
            <input type="password" placeholder="Contraseña" />
            
            <a href="#">¿Olvidaste tu contraseña?</a>
            <button>Ingresar</button>
          </form>
        </div>

        {/* Mitad Derecha: Panel decorativo celeste */}
        <div className="overlay-container">
          <div className="overlay-panel">
          </div>
        </div>
      </div>
    </div>
  );
};