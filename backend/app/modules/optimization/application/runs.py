"""Multipedido preflight. The unit of work owns exactly one commit/rollback."""
from .errors import RunError
from .preparation import prepare_persisted_problem
from ..domain.rotation import discrete_angles, raster_number
from .resource_policy import DEFAULT_RASTER_BUDGET


class AcceptRun:
    def __init__(self, unit_of_work):
        self.unit_of_work = unit_of_work

    def execute(self, order_ids, actor_id):
        ids = tuple(order_ids)
        if not ids or any(type(i) is not int or not 0 < i <= 2147483647 for i in ids) or len(set(ids)) != len(ids):
            raise RunError("INVALID_INPUT", "Selecciona pedidos distintos y válidos.")
        ids = tuple(sorted(ids))
        with self.unit_of_work() as uow:
            configuration_id, config = uow.configuration()
            pieces = uow.orders.lock_pending(ids)
            try:
                discrete_angles(config.angular_step_deg)
            except ValueError as exc:
                raise RunError("CONFIG_CONFLICT", "La configuración excede los límites seguros de cálculo.") from exc
            try:
                problem = prepare_persisted_problem(ids, pieces, config)
                for unit in problem.units:
                    geometry = dict(unit.geometry)
                    if unit.shape_type == "POLIGONO_CONVEXO":
                        geometry["vertices_mm"] = [list(p) for p in geometry["vertices_mm"]]
                    DEFAULT_RASTER_BUDGET.check(geometry, raster_number(config.resolution_mm))
            except ValueError as exc:
                raise RunError("INVALID_INPUT", "Las piezas o parámetros exceden las condiciones válidas de cálculo.") from exc
            run = uow.runs.create(problem, configuration_id, actor_id)
            uow.orders.transition(ids, "PENDIENTE", "EN_OPTIMIZACION")
        return run
