"""Run observation contracts, independent of HTTP and persistence."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from ..domain.problem import OptimizationResult, positive_int
from ..domain.metrics import ResidualRectangle


class RunStatus(str, Enum):
    RUNNING = "EN_EJECUCION"
    COMPLETED = "COMPLETADA"
    NO_SOLUTION = "SIN_SOLUCION"
    FAILED = "FALLIDA"


@dataclass(frozen=True, kw_only=True)
class Progress:
    placed_units: int
    total_units: int

    def __post_init__(self):
        positive_int(self.total_units, "total_units")
        if type(self.placed_units) is not int or not 0 <= self.placed_units <= self.total_units:
            raise ValueError("placed_units must be between zero and total_units.")

    @property
    def progress_pct(self) -> Decimal:
        return Decimal(self.placed_units) / Decimal(self.total_units) * 100


@dataclass(frozen=True, kw_only=True)
class OptimizationRun:
    optimization_id: int
    status: RunStatus
    result: OptimizationResult
    confirmed: bool = False
    residuals: tuple[ResidualRectangle, ...] = ()

    def __post_init__(self):
        positive_int(self.optimization_id, "optimization_id")
        if not isinstance(self.status, RunStatus) or type(self.confirmed) is not bool:
            raise ValueError("Invalid run status or confirmation flag.")
        if self.status is RunStatus.COMPLETED and not self.result.complete:
            raise ValueError("COMPLETADA requires all requested units placed.")
        if self.status is RunStatus.NO_SOLUTION and self.result.complete:
            raise ValueError("SIN_SOLUCION requires unplaced units.")
        if self.confirmed and self.status is not RunStatus.COMPLETED:
            raise ValueError("Only a complete run can have been confirmed.")

    @property
    def confirmable(self) -> bool:
        # Eligibility snapshot only; confirmation must revalidate under locks.
        return self.status is RunStatus.COMPLETED and self.result.complete and not self.confirmed
