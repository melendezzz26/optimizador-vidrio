"""Confirmación manual versionada e idempotente, dentro de una transacción.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
"""
import re

from .confirmation import ConfirmationResult, require_confirmable
from .errors import RunError
from ..domain.confirmation import consumption_groups, validate_stored_geometry


class ConfirmComparison:
    def __init__(self, unit_of_work):
        self.unit_of_work = unit_of_work

    def repository(self, uow, comparison_id, actor_id):
        return uow.comparison_confirmation

    def execute(self, comparison_id, execution_id, expected_version, key, actor_id):
        if (any(type(i) is not int or not 0 < i <= 2147483647
                for i in (comparison_id, execution_id, expected_version, actor_id))
                or not isinstance(key, str) or re.fullmatch(r"[A-Za-z0-9_-]{8,64}", key) is None):
            raise RunError("INVALID_INPUT", "La solicitud de confirmación no es válida.")
        with self.unit_of_work() as uow:
            repository = self.repository(uow, comparison_id, actor_id)
            context = repository.lock_comparison(comparison_id, execution_id, expected_version, key)
            if isinstance(context, ConfirmationResult):
                return context
            require_confirmable(context.run)
            uow.orders.require_state(context.run.result.problem.order_ids, "OPTIMIZADO")
            try:
                consumptions = consumption_groups(context.run.result)
                residuals = validate_stored_geometry(context.run.result, context.minimum_width_mm,
                                                    context.minimum_height_mm, context.residuals)
            except ValueError as error:
                raise RunError("NOT_CONFIRMABLE", "El patrón persistido requiere revisión antes de confirmar.") from error
            repository.lock_and_revalidate(consumptions, context)
            repository.consume(consumptions)
            repository.record_movements(consumptions, comparison_id, actor_id)
            created = repository.create_residuals(residuals, context)
            receipt = ConfirmationResult(optimization_id=comparison_id, order_ids=context.run.result.problem.order_ids,
                materials_consumed=context.run.result.materials_used, remnants_created=created)
            repository.mark_confirmed(context, receipt, actor_id)
            uow.orders.transition(receipt.order_ids, "OPTIMIZADO", "CONFIRMADO")
        return receipt


class ConfirmComparisonV2(ConfirmComparison):
    """Same inventory transaction, with ownership and safe closure checked under lock."""

    def repository(self, uow, comparison_id, actor_id):
        uow.comparisons_v2.legacy._lock(comparison_id)
        current = uow.comparisons_v2.get_owned(comparison_id, actor_id)
        if not current.terminal or not current.supervisor_stopped:
            raise RunError("NOT_CONFIRMABLE", "La comparación todavía no acredita cierre seguro.")
        return uow.comparison_confirmation_v2
