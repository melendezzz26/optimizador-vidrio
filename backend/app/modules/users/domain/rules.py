"""Reglas de los datos de un usuario (SPEC-HU-003, sección 4 y RN-02)."""
import re
import unicodedata

from .errors import InvalidUserDataError

MAX_NAME_LENGTH = 100
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # límite de bcrypt

# [0-9] y no \d: solo dígitos ASCII, igual que la restricción de la base.
_DNI_PATTERN = re.compile(r"[0-9]{8}")


def normalize_name(value: str, field: str) -> str:
    """Quita los espacios sobrantes de nombres o apellidos y comprueba su tamaño."""
    if not isinstance(value, str):
        raise InvalidUserDataError(f"El campo {field} es obligatorio.")
    normalized = " ".join(value.split())
    if not normalized:
        raise InvalidUserDataError(f"El campo {field} es obligatorio.")
    if len(normalized) > MAX_NAME_LENGTH:
        raise InvalidUserDataError(
            f"El campo {field} admite como máximo {MAX_NAME_LENGTH} caracteres."
        )
    return normalized


def validate_dni(dni: str) -> str:
    if not isinstance(dni, str) or not _DNI_PATTERN.fullmatch(dni):
        raise InvalidUserDataError("El DNI debe tener exactamente 8 dígitos.")
    return dni


def validate_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidUserDataError(
            f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
        )
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise InvalidUserDataError(
            f"La contraseña no puede ocupar más de {MAX_PASSWORD_BYTES} bytes."
        )
    return password


def generate_access_username(first_names: str, dni: str) -> str:
    """Usuario de acceso: inicial del primer nombre, sin tilde y en mayúscula, más el DNI.

    Ejemplo: "Álvaro" con DNI 71234567 genera ``A71234567``.
    """
    name = normalize_name(first_names, "nombres")
    # NFD separa la letra de su tilde ("Á" -> "A" + tilde); se conserva la letra.
    initial = unicodedata.normalize("NFD", name[0])[0].upper()
    if not ("A" <= initial <= "Z"):
        raise InvalidUserDataError(
            "El nombre debe empezar con una letra para generar el usuario."
        )
    return f"{initial}{validate_dni(dni)}"
