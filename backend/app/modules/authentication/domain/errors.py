"""Errores del módulo de autenticación. No dependen de HTTP ni de la base."""


class InvalidUsernameError(ValueError):
    """El usuario ingresado no tiene el formato de una letra y 8 dígitos."""


class InvalidCredentialsError(Exception):
    """El usuario no existe, no tiene un rol válido o la contraseña no coincide."""


class InactiveAccountError(Exception):
    """Las credenciales son correctas, pero la cuenta está desactivada."""


class SessionNotValidError(Exception):
    """La cuenta de una sesión abierta ya no existe o fue desactivada."""
