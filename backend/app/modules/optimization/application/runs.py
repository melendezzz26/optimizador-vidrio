"""Multipedido preflight. The unit of work owns exactly one commit/rollback."""
from .errors import RunError
from .load_budget import DEFAULT_RUN_LOAD_BUDGET, check_pieces, check_selection, check_stock
from .preparation import prepare_persisted_problem
from ..domain.problem import SPRINT_2_ANGULAR_STEP_DEG
from ..domain.rotation import discrete_angles


class AcceptRun:
    def __init__(self, unit_of_work, stock_counter=None, budget=DEFAULT_RUN_LOAD_BUDGET):
        # stock_counter=None keeps direct callers working; the HTTP route always injects it.
        self.unit_of_work, self.stock_counter, self.budget = unit_of_work, stock_counter, budget

    def execute(self, order_ids, actor_id):
        ids = tuple(order_ids)
        if not ids or any(type(i) is not int or not 0 < i <= 2147483647 for i in ids) or len(set(ids)) != len(ids):
            raise RunError("INVALID_INPUT", "Selecciona pedidos distintos y válidos.")
        ids = tuple(sorted(ids))
        check_selection(ids, self.budget)                                   # TA-037 P1
        with self.unit_of_work() as uow:
            configuration_id, config = uow.configuration()
            if config.angular_step_deg != SPRINT_2_ANGULAR_STEP_DEG:
                raise RunError(
                    "CONFIG_CONFLICT",
                    "Sprint 2 requiere una configuración vigente con paso angular de 5°. "
                    "Publica una nueva versión de configuración sin alterar el historial.",
                )
            pieces = uow.orders.lock_pending(ids)
            try:
                discrete_angles(config.angular_step_deg)
            except ValueError as exc:
                raise RunError("CONFIG_CONFLICT", "La configuración excede los límites seguros de cálculo.") from exc
            try:
                # TA-037 P3: limits on persisted rows, BEFORE expanding quantities.
                # Geometry (L-05) is checked once per piece with the same function as before.
                units_by_material = check_pieces(pieces, config, self.budget)
                if self.stock_counter is not None:                          # TA-037 P4
                    check_stock(units_by_material, {
                        key: self.stock_counter.count_compatible(key) for key in units_by_material
                    }, self.budget)
                problem = prepare_persisted_problem(ids, pieces, config)
            except ValueError as exc:
                raise RunError("INVALID_INPUT", "Las piezas o parámetros exceden las condiciones válidas de cálculo.") from exc
            run = uow.runs.create(problem, configuration_id, actor_id)
            uow.orders.transition(ids, "PENDIENTE", "EN_OPTIMIZACION")
        return run