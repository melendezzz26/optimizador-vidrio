from app.modules.clients.domain.errors import InvalidClientDataError


def normalize_text(value: str, field: str) -> str:
    if not isinstance(value, str) or "\0" in value:
        raise InvalidClientDataError(f"{field} debe ser texto válido, sin caracteres nulos.")
    return value.strip()


def required_text(value: str, field: str) -> str:
    result = normalize_text(value, field)
    if not result:
        raise InvalidClientDataError(f"{field} no puede estar vacío.")
    return result


def optional_text(value: str | None, field: str) -> str | None:
    return None if value is None else normalize_text(value, field) or None
