"""Usuario de acceso: una letra mayúscula seguida de 8 dígitos (por ejemplo F71234567)."""
import re
from dataclasses import dataclass

from .errors import InvalidUsernameError

# [0-9] y no \d: solo se aceptan dígitos ASCII, igual que la restricción de la base.
_PATTERN = re.compile(r"[A-Z][0-9]{8}")
_FORMAT_MESSAGE = "El usuario debe tener una letra seguida de 8 dígitos."


@dataclass(frozen=True)
class Username:
    """Usuario de acceso ya validado.

    Si existe un objeto Username, su valor cumple el formato: no hay forma de
    construirlo con un valor inválido. Así el resto del módulo no repite la
    validación ni puede olvidarla.
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _PATTERN.fullmatch(self.value):
            raise InvalidUsernameError(_FORMAT_MESSAGE)

    @classmethod
    def parse(cls, raw: object) -> "Username":
        """Normaliza lo que escribió la persona y lo valida.

        Quita los espacios exteriores y pasa a mayúsculas, de modo que
        ``f71234567`` y `` F71234567 `` identifican la misma cuenta.
        """
        if not isinstance(raw, str):
            raise InvalidUsernameError(_FORMAT_MESSAGE)
        return cls(raw.strip().upper())

    def __str__(self) -> str:
        return self.value
