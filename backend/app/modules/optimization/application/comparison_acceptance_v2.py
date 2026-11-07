"""B05 atomic frozen-input acceptance. No process creation or inventory consumption."""
from dataclasses import replace
import re

from .comparison_v2_contracts import ComparisonInputV2
from .errors import RunError
from .geometric_preflight import validate_comparison_geometry
from .load_budget import DEFAULT_RUN_LOAD_BUDGET, check_selection, check_pieces
from .preparation import prepare_persisted_problem


class SnapshotConflict(RunError):
    def __init__(self):
        super().__init__("STATE_CONFLICT", "La captura entró en conflicto; recupera o reintenta la solicitud.")


class AcceptComparisonV2:
    def __init__(self, unit_of_work, authorize, budget=DEFAULT_RUN_LOAD_BUDGET):
        self.unit_of_work, self.authorize, self.budget = unit_of_work, authorize, budget

    @staticmethod
    def validate_request(order_ids, actor_id, key):
        ids = tuple(order_ids)
        if (not ids or any(type(i) is not int or not 0 < i <= 2147483647 for i in (*ids, actor_id))
            or len(set(ids)) != len(ids) or not isinstance(key, str) or re.fullmatch(r"[A-Za-z0-9_-]{8,64}",key) is None):
            raise RunError("INVALID_INPUT", "Lote o clave inválidos.")
        return tuple(sorted(ids))

    def execute(self, order_ids, actor_id, key):
        ids = self.validate_request(order_ids,actor_id,key)
        check_selection(ids, self.budget)
        for attempt in range(3):
            try:
                with self.unit_of_work() as tx:
                    tx.consistent_snapshot()
                    self.authorize(tx, actor_id)
                    previous = tx.comparisons_v2.find_by_key(actor_id, key)
                    if previous is not None:
                        if previous.problem.order_ids != ids:
                            raise RunError("STATE_CONFLICT", "La clave corresponde a otro lote.")
                        return previous
                    config_id, version, config, width, height = tx.captured_configuration()
                    if config.angular_step_deg != 5:
                        raise RunError("CONFIG_CONFLICT", "Se requiere paso angular vigente de 5°.")
                    pieces = tx.orders.lock_pending(ids)
                    try:
                        stock = tx.stock.capture(check_pieces(pieces, config, self.budget), self.budget)
                        problem = prepare_persisted_problem(ids, pieces, config)
                        problem = replace(problem, groups=tuple(replace(g,stock_candidates=stock[g.key]) for g in problem.groups))
                        validate_comparison_geometry(problem)
                        frozen = ComparisonInputV2(problem=problem,configuration_id=config_id,configuration_version=version,
                            requested_pieces=pieces,minimum_width_mm=width,minimum_height_mm=height)
                    except ValueError as error:
                        raise RunError("INVALID_INPUT", "La entrada excede las condiciones válidas.") from error
                    current = tx.comparisons_v2.create(frozen, actor_id, key, managed=True)
                    tx.orders.transition(ids,"PENDIENTE","EN_OPTIMIZACION")
                return current
            except SnapshotConflict:
                if attempt == 2: raise
