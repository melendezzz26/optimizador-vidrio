"""Reconciliación de pedidos atascados en EN_OPTIMIZACION (cierre de observaciones S2, F6).

Decisión del equipo (07/11/2026): solo vuelven a PENDIENTE los pedidos sin ninguna
optimización vinculada (A) o con todas sus optimizaciones terminales y sin consumo
ni confirmación (B). C, D y E solo se informan. Por defecto no escribe (dry-run).

Por qué A y B son seguros sin detener el servicio: una corrida o comparación nueva
solo puede tomar pedidos PENDIENTE, así que nadie más puede adueñarse de un pedido
en EN_OPTIMIZACION. Al aplicar, el pedido se bloquea, se vuelve a clasificar dentro
de la misma transacción y el cambio usa la transición con estado esperado existente.
"""
from dataclasses import dataclass
from enum import Enum
import logging

from .errors import RunError

logger = logging.getLogger(__name__)

STUCK_STATE, TARGET_STATE = "EN_OPTIMIZACION", "PENDIENTE"
_TERMINAL = frozenset({"FALLIDA", "SIN_SOLUCION"})


class StuckCase(str, Enum):
    NO_OPTIMIZATION = "A"       # Sin optimización vinculada (p. ej. la vista previa HU-015 del 14 al 21/10).
    ALL_TERMINAL = "B"          # Todas terminales, sin consumo ni confirmación (p. ej. FF fallida antes de TA-049).
    OPEN_OPTIMIZATION = "C"     # Alguna optimización sigue EN_EJECUCION.
    ELIGIBLE_RESULT = "D"       # Optimización COMPLETADA sin liberar: debería estar OPTIMIZADO.
    CONSUMED = "E"              # Consumo de inventario o confirmación registrada.


REASONS = {
    StuckCase.NO_OPTIMIZATION: "Sin optimización vinculada.",
    StuckCase.ALL_TERMINAL: "Todas sus optimizaciones terminaron sin resultado vigente, consumo ni confirmación.",
    StuckCase.OPEN_OPTIMIZATION: ("Tiene una optimización EN_EJECUCION: usar scripts.recover_stopped_run "
                                  "(FF) o la recuperación de comparaciones; no se toca."),
    StuckCase.ELIGIBLE_RESULT: "Tiene una optimización COMPLETADA sin liberar (debería estar OPTIMIZADO); solo se informa.",
    StuckCase.CONSUMED: "Tiene consumo de inventario o confirmación; requiere revisión, no se toca.",
}
RECOVERABLE = frozenset({StuckCase.NO_OPTIMIZATION, StuckCase.ALL_TERMINAL})


@dataclass(frozen=True)
class LinkedOptimization:
    optimization_id: int
    status: str
    released: bool = False
    confirmed: bool = False
    consumed: bool = False


@dataclass(frozen=True)
class ReconciliationEntry:
    order_id: int
    case: StuckCase
    before: str
    after: str
    applied: bool
    reason: str
    optimizations: tuple[LinkedOptimization, ...]


def classify(links) -> StuckCase:
    """Prioridad: E (consumo) > C (abierta) > D (resultado vigente) > A > B."""
    links = tuple(links)
    if any(link.consumed or link.confirmed for link in links):
        return StuckCase.CONSUMED
    if any(link.status == "EN_EJECUCION" for link in links):
        return StuckCase.OPEN_OPTIMIZATION
    if any(link.status == "COMPLETADA" and not link.released for link in links):
        return StuckCase.ELIGIBLE_RESULT
    if not links:
        return StuckCase.NO_OPTIMIZATION
    if all(link.status in _TERMINAL or link.status == "COMPLETADA" and link.released for link in links):
        return StuckCase.ALL_TERMINAL
    raise ValueError("Estado de optimización desconocido")


class ReconcileStuckOrders:
    def __init__(self, unit_of_work):
        self.unit_of_work = unit_of_work

    def execute(self, *, apply=False, order_ids=None):
        with self.unit_of_work() as tx:
            candidates = tx.stuck_orders.stuck_order_ids(order_ids)
        return [self._one(order_id, apply) for order_id in candidates]

    def _one(self, order_id, apply):
        # Una transacción por pedido: un fallo no deshace lo ya reconciliado.
        with self.unit_of_work() as tx:
            before = tx.stuck_orders.order_state(order_id, lock=apply)
            links = tx.stuck_orders.linked_optimizations(order_id)
            if before != STUCK_STATE:
                return ReconciliationEntry(order_id, classify(links), before, before, False,
                                           "El estado cambió desde la lectura inicial; no se toca.", links)
            case = classify(links)
            recoverable = case in RECOVERABLE
            after = TARGET_STATE if recoverable else before
            if recoverable and apply:
                try:
                    tx.orders.transition((order_id,), STUCK_STATE, TARGET_STATE)
                except RunError:
                    return ReconciliationEntry(order_id, case, before, before, False,
                                               "El estado cambió durante la reconciliación; no se toca.", links)
            entry = ReconciliationEntry(order_id, case, before, after, recoverable and apply, REASONS[case], links)
        if entry.applied:
            # Después del commit: solo se registra lo que realmente cambió.
            logger.info("Pedido %s reconciliado: %s -> %s (caso %s, optimizaciones %s)", order_id, before,
                        after, case.value, [link.optimization_id for link in links] or "ninguna")
        return entry
