"""Errores de dominio del inventario, independientes del transporte HTTP."""


class InvalidGeometryError(ValueError):
    """La geometría no cumple el contrato de retazos TA-003."""


class InventoryValidationError(ValueError):
    """Los datos incumplen una regla de negocio de inventario."""


class InventoryNotFoundError(LookupError):
    """No existe el recurso de inventario solicitado o referenciado."""


class InventoryConflictError(Exception):
    """Un nombre o código de inventario ya está en uso."""
