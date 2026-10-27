"""TA-037 T03: admisión acotada de ejecuciones (SPEC-TA-037 L-10, L-11 y §7.2).

Contrato independiente de HTTP y de la implementación. Una plaza se toma antes de
aceptar la ejecución y se libera una sola vez, cuando termina el hilo de cálculo.
"""
from typing import Protocol

from .errors import RunError

RETRY_AFTER_SECONDS = 15

_MESSAGES = {
    "active_runs": "El optimizador está atendiendo otros cálculos. Intenta nuevamente en unos segundos.",
    "active_runs_per_user": "Ya tienes un cálculo en curso. Espera a que termine o revisa su resultado.",
}


class AdmissionLease(Protocol):
    def release(self) -> None:
        """Idempotente: liberar dos veces no libera otra plaza."""


class RunAdmission(Protocol):
    def acquire(self, user_id: int) -> AdmissionLease:
        """Toma una plaza o lanza OptimizerBusy, sin esperar."""


class OptimizerBusy(RunError):
    """503 OPTIMIZER_BUSY: la misma solicitud puede funcionar más tarde (Retry-After)."""

    def __init__(self, name: str, maximum: int, actual: int):
        self.retry_after = RETRY_AFTER_SECONDS
        super().__init__("OPTIMIZER_BUSY", _MESSAGES[name], details={
            "limit": dict(name=name, maximum=maximum, actual=actual, scope=None),
        })