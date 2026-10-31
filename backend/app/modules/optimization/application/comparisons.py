"""Aceptación idempotente de un único snapshot comparativo, sin ejecutar motores.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
"""
from dataclasses import replace
import re

from .errors import RunError
from .load_budget import DEFAULT_RUN_LOAD_BUDGET, check_pieces, check_selection
from .preparation import prepare_persisted_problem
from ..domain.problem import SPRINT_2_ANGULAR_STEP_DEG


class AcceptComparison:
    def __init__(self, unit_of_work, budget=DEFAULT_RUN_LOAD_BUDGET):
        self.unit_of_work, self.budget = unit_of_work, budget

    def execute(self, order_ids, actor_id, idempotency_key):
        ids = tuple(order_ids)
        if (not ids or any(type(i) is not int or not 0 < i <= 2147483647 for i in (*ids, actor_id))
                or len(set(ids)) != len(ids) or not isinstance(idempotency_key, str)
                or re.fullmatch(r"[A-Za-z0-9_-]{8,64}", idempotency_key) is None):
            raise RunError("INVALID_INPUT", "Selecciona pedidos distintos y una clave de solicitud válida.")
        ids = tuple(sorted(ids))
        check_selection(ids, self.budget)
        with self.unit_of_work() as uow:
            previous = uow.comparisons.find_by_key(actor_id, idempotency_key)
            if previous is not None:
                if previous.problem.order_ids != ids:
                    raise RunError("STATE_CONFLICT", "La clave de solicitud ya identifica otro lote.")
                return previous
            configuration_id, config = uow.configuration()
            if config.angular_step_deg != SPRINT_2_ANGULAR_STEP_DEG:
                raise RunError("CONFIG_CONFLICT", "La comparación requiere un paso angular vigente de 5°.")
            pieces = uow.orders.lock_pending(ids)
            try:
                units_by_material = check_pieces(pieces, config, self.budget)
                stock = uow.stock.capture(units_by_material, self.budget)
                problem = prepare_persisted_problem(ids, pieces, config)
                problem = replace(problem, groups=tuple(replace(group, stock_candidates=stock[group.key])
                                                        for group in problem.groups))
            except ValueError as error:
                raise RunError("INVALID_INPUT", "Las piezas, parámetros o stock exceden las condiciones válidas.") from error
            result = uow.comparisons.create(problem, configuration_id, actor_id, idempotency_key, pieces)
            uow.orders.transition(ids, "PENDIENTE", "EN_OPTIMIZACION")
        return result
