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
    """Safe public code/message; the underlying exception stays server-side.

    ``details`` holds extra public fields (TA-037: ``limit``), never internals.
    """
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details


class ResultSaveFailed(Exception):
    pass


class ExecutionInterrupted(Exception):
    pass
