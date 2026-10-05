"""Errores de dominio del inventario, independientes del transporte HTTP."""


class InvalidGeometryError(ValueError):
    """La geometría no cumple el contrato de retazos TA-003."""
