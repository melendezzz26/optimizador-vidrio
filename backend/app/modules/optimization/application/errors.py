"""Errores seguros del flujo operacional, independientes de HTTP."""


class OptimizationNotFoundError(Exception):
    pass


class OptimizationStateError(Exception):
    pass


class InvalidRasterInput(ValueError):
    pass


class RasterBudgetExceeded(InvalidRasterInput):
    pass


class RunError(Exception):
    """Safe public code/message; the underlying exception stays server-side."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message
