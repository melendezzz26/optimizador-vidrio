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

    def execute(self, comparison_id, execution_id, expected_version, key, actor_id):
        if (any(type(i) is not int or not 0 < i <= 2147483647
                for i in (comparison_id, execution_id, expected_version, actor_id))
                or not isinstance(key, str) or re.fullmatch(r"[A-Za-z0-9_-]{8,64}", key) is None):
            raise RunError("INVALID_INPUT", "La solicitud de confirmación no es válida.")
        with self.unit_of_work() as uow:
            repository = uow.comparison_confirmation
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
