"""Atomic confirmation orchestration. Domain never imports Orders/Inventory ORM."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from .dto import OptimizationRun, RunStatus
from .errors import RunError
from ..domain.confirmation import consumption_groups, validate_stored_geometry
from ..domain.metrics import ResidualRectangle
from ..domain.problem import StockCandidate


@dataclass(frozen=True, kw_only=True)
class ConfirmationContext:
    run: OptimizationRun
    execution_id: int
    minimum_width_mm: Decimal
    minimum_height_mm: Decimal
    residuals: tuple[ResidualRectangle, ...]


@dataclass(frozen=True, kw_only=True)
class CreatedRemnant:
    remnant_id: int
    source: StockCandidate
    x_mm: Decimal
    y_mm: Decimal
    geometry: Mapping
    area_mm2: Decimal
    exact_area_mm2: Decimal


@dataclass(frozen=True, kw_only=True)
class ConfirmationResult:
    optimization_id: int
    order_ids: tuple[int, ...]
    materials_consumed: tuple[StockCandidate, ...]
    remnants_created: tuple[CreatedRemnant, ...]


def require_confirmable(run):
    if run.confirmed:
        raise RunError("ALREADY_CONFIRMED", "La optimización ya fue confirmada.")
    if run.status is not RunStatus.COMPLETED or not run.result.complete or run.result.placed_units != run.result.total_units:
        raise RunError("NOT_CONFIRMABLE", "La optimización no tiene una solución completa confirmable.")


class ConfirmRun:
    def __init__(self, unit_of_work):
        self.unit_of_work = unit_of_work

    def execute(self, optimization_id, actor_id):
        if any(type(i) is not int or not 0 < i <= 2147483647 for i in (optimization_id, actor_id)):
            raise RunError("INVALID_INPUT", "Identificador de confirmación inválido.")
        with self.unit_of_work() as uow:
            context = uow.confirmation.lock_run(optimization_id)
            run = context.run
            require_confirmable(run)
            uow.orders.require_state(run.result.problem.order_ids, "OPTIMIZADO")
            try:
                consumptions = consumption_groups(run.result)
                residuals = validate_stored_geometry(run.result, context.minimum_width_mm,
                                                    context.minimum_height_mm, context.residuals)
            except ValueError as exc:
                raise RunError("NOT_CONFIRMABLE", "El patrón persistido requiere revisión antes de confirmar.") from exc
            uow.confirmation.lock_and_revalidate(consumptions, context)
            uow.confirmation.consume(consumptions)
            uow.confirmation.record_movements(consumptions, optimization_id, actor_id)
            created = uow.confirmation.create_residuals(residuals, context)
            result = ConfirmationResult(optimization_id=optimization_id, order_ids=run.result.problem.order_ids,
                                        materials_consumed=run.result.materials_used, remnants_created=created)
            uow.confirmation.mark_confirmed(context, result, actor_id)
            uow.orders.transition(result.order_ids, "OPTIMIZADO", "CONFIRMADO")
        return result
