"""Errores seguros del flujo operacional, independientes de HTTP."""


class OptimizationNotFoundError(Exception):
    pass


class OptimizationStateError(Exception):
    pass


class InvalidRasterInput(ValueError):
    pass


class RasterBudgetExceeded(InvalidRasterInput):
    pass
