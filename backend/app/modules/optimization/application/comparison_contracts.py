"""Identidad y lectura durable del agregado comparativo; sin decisión automática.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Protocol

from ..domain.problem import OptimizationProblem, OptimizationResult
from ..domain.metrics import ResidualRectangle

METHODS = ("FF", "BF", "WF")


def immutable_json(value):
    if isinstance(value, Mapping):
        return MappingProxyType({k: immutable_json(v) for k, v in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(immutable_json(v) for v in value)
    return value


@dataclass(frozen=True, kw_only=True)
class ComparisonExecution:
    execution_id: int
    method: str
    status: str
    result: OptimizationResult | None = None
    residuals: tuple[ResidualRectangle, ...] = ()
    failure_code: str | None = None

    @property
    def eligible(self):
        return self.status == "COMPLETADA" and self.result is not None and self.result.complete


@dataclass(frozen=True, kw_only=True)
class Comparison:
    comparison_id: int
    version: int
    status: str
    actor_id: int
    input_sha256: str
    problem: OptimizationProblem
    requested_pieces: tuple[Mapping, ...]
    configuration_id: int
    configuration_version: int
    minimum_width_mm: Decimal
    minimum_height_mm: Decimal
    executions: tuple[ComparisonExecution, ...]
    selected_execution_id: int | None = None
    workers_stopped: bool = False
    released: bool = False
    confirmation: Mapping | None = None

    def __post_init__(self):
        object.__setattr__(self, "requested_pieces", immutable_json(self.requested_pieces))
        object.__setattr__(self, "confirmation", immutable_json(self.confirmation))

    @property
    def terminal(self):
        return self.workers_stopped and self.status != "EN_EJECUCION"

    @property
    def incomplete(self):
        return any(e.status == "FALLIDA" for e in self.executions)


class ComparisonUnitOfWork(Protocol):
    orders: object
    comparisons: object
    stock: object
    def configuration(self): ...
    def __enter__(self) -> "ComparisonUnitOfWork": ...
    def __exit__(self, exc_type, exc, traceback): ...


@dataclass(frozen=True, kw_only=True)
class CalculatedExecution:
    result: OptimizationResult
    residuals: tuple[ResidualRectangle, ...]


@dataclass(frozen=True, kw_only=True)
class ComparisonSignal:
    comparison_id: int
    execution_id: int | None
    method: str | None
    kind: str
    payload: object
