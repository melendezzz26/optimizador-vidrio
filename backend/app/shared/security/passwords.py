"""Hash y verificación de contraseñas con bcrypt."""
import bcrypt

# bcrypt solo procesa los primeros 72 bytes; aceptar más daría una falsa seguridad.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de la contraseña. Nunca se guarda el texto plano."""
    encoded = password.encode("utf-8")
    if not 1 <= len(encoded) <= MAX_PASSWORD_BYTES:
        raise ValueError("La contraseña debe ocupar entre 1 y 72 bytes UTF-8.")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Indica si la contraseña corresponde al hash. Nunca lanza una excepción."""
    encoded = password.encode("utf-8")
    if not 1 <= len(encoded) <= MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        # El hash guardado no tiene formato bcrypt válido.
        return False
