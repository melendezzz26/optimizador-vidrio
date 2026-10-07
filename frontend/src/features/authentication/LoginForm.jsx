import { useId, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { USERNAME_HINT, isValidUsername, normalizeUsername } from './username';
import './LoginForm.css';

// Formulario de inicio de sesión. Recibe onSignIn(usuario, contraseña) y muestra sus errores.
export function LoginForm({ onSignIn, notice = '' }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const id = useId();

  const usernameId = `${id}-username`;
  const passwordId = `${id}-password`;
  const hintId = `${id}-username-hint`;
  const usernameErrorId = `${id}-username-error`;
  const passwordErrorId = `${id}-password-error`;

  function validate(normalizedUsername) {
    const errors = {};
    if (!normalizedUsername) errors.username = 'Ingresa tu usuario.';
    else if (!isValidUsername(normalizedUsername)) errors.username = 'El usuario debe tener una letra seguida de 8 dígitos.';
    if (!password) errors.password = 'Ingresa tu contraseña.';
    return errors;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (isSubmitting) return;

    const normalizedUsername = normalizeUsername(username);
    const errors = validate(normalizedUsername);
    setFieldErrors(errors);
    setFormError('');
    // Con errores de formato no se llama a la API.
    if (Object.keys(errors).length > 0) return;

    setIsSubmitting(true);
    try {
      await onSignIn(normalizedUsername, password);
    } catch (error) {
      // Se conserva lo escrito para que la persona pueda corregirlo.
      setFormError(error.message);
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-screen">
      <div className="login-card">
        <form className="login-form" onSubmit={handleSubmit} noValidate aria-busy={isSubmitting}>
          <h1 className="login-title">Iniciar sesión</h1>
          <p className="login-intro">Ingresa tu usuario y tu contraseña. Ambos campos son obligatorios.</p>

          <div className="login-field">
            <label htmlFor={usernameId}>Usuario</label>
            <input
              id={usernameId}
              className="login-input login-input-username"
              name="username"
              type="text"
              autoComplete="username"
              autoCapitalize="characters"
              spellCheck={false}
              maxLength={20}
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              aria-invalid={fieldErrors.username ? true : undefined}
              aria-describedby={fieldErrors.username ? `${hintId} ${usernameErrorId}` : hintId}
            />
            <p id={hintId} className="login-hint">{USERNAME_HINT}</p>
            {fieldErrors.username && (
              <p id={usernameErrorId} className="login-field-error">{fieldErrors.username}</p>
            )}
          </div>

          <div className="login-field">
            <label htmlFor={passwordId}>Contraseña</label>
            <div className="login-password">
              <input
                id={passwordId}
                className="login-input"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                maxLength={128}
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                aria-invalid={fieldErrors.password ? true : undefined}
                aria-describedby={fieldErrors.password ? passwordErrorId : undefined}
              />
              <button
                type="button"
                className="login-password-toggle"
                onClick={() => setShowPassword((visible) => !visible)}
                aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                aria-pressed={showPassword}
              >
                {showPassword ? <EyeOff aria-hidden="true" size={20} /> : <Eye aria-hidden="true" size={20} />}
              </button>
            </div>
            {fieldErrors.password && (
              <p id={passwordErrorId} className="login-field-error">{fieldErrors.password}</p>
            )}
          </div>

          {formError && <p className="login-alert" role="alert">{formError}</p>}
          {!formError && notice && <p className="login-notice" role="status">{notice}</p>}

          <button type="submit" className="login-submit" disabled={isSubmitting}>
            {isSubmitting ? 'Ingresando…' : 'Ingresar'}
          </button>
        </form>

        <div className="login-image" aria-hidden="true" />
      </div>
    </main>
  );
}
