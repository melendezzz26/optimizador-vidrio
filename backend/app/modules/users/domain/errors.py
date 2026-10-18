"""Errores del módulo de usuarios. No dependen de HTTP ni de la base."""


class InvalidUserDataError(ValueError):
    """Algún dato del usuario no cumple las reglas (nombre, DNI, contraseña o rol)."""


class RoleNotFoundError(InvalidUserDataError):
    """El rol indicado no existe."""


class DuplicateDniError(Exception):
    """Ya existe un usuario con ese DNI."""


class UserNotFoundError(Exception):
    """No existe un usuario con ese identificador."""


class SelfModificationError(Exception):
    """Un Administrador intentó desactivarse o cambiar su propio rol."""
