"""Lecturas para reconciliar pedidos atascados (S2, F6). La transición la hace SqlOrdersBatch."""
from sqlalchemy import or_, select

from app.models import EjecucionOptimizacion, MovimientoInventario, Optimizacion, OptimizacionPedido, Pedido
from ..application.order_reconciliation import STUCK_STATE, LinkedOptimization
from .run_uow import SqlRunUnitOfWork


class SqlStuckOrdersRepository:
    def __init__(self, session):
        self.session = session

    def stuck_order_ids(self, order_ids=None):
        query = select(Pedido.id_pedido).where(Pedido.estado == STUCK_STATE).order_by(Pedido.id_pedido)
        if order_ids:
            query = query.where(Pedido.id_pedido.in_(tuple(order_ids)))
        return tuple(self.session.scalars(query))

    def order_state(self, order_id, *, lock):
        query = select(Pedido.estado).where(Pedido.id_pedido == order_id).execution_options(populate_existing=True)
        if lock:
            query = query.with_for_update()
        return self.session.scalar(query)

    def linked_optimizations(self, order_id):
        linked = select(OptimizacionPedido.id_optimizacion).where(OptimizacionPedido.id_pedido == order_id)
        rows = self.session.execute(select(Optimizacion.id_optimizacion, Optimizacion.estado,
                                           Optimizacion.comparison_snapshot)
            .where(or_(Optimizacion.id_optimizacion.in_(linked), Optimizacion.id_pedido == order_id))
            .order_by(Optimizacion.id_optimizacion)).all()
        ids = [row.id_optimizacion for row in rows]
        if not ids:
            return ()
        consumed = set(self.session.scalars(select(MovimientoInventario.id_optimizacion).where(
            MovimientoInventario.id_optimizacion.in_(ids),
            MovimientoInventario.tipo_evento == "CONSUMO_OPTIMIZACION")))
        # FF guarda el recibo en la ejecución; las comparaciones, además, en su snapshot.
        confirmed = {execution.id_optimizacion for execution in self.session.execute(
            select(EjecucionOptimizacion.id_optimizacion, EjecucionOptimizacion.patron_resultado)
            .where(EjecucionOptimizacion.id_optimizacion.in_(ids))).all()
            if isinstance(execution.patron_resultado, dict) and "confirmation" in execution.patron_resultado}
        return tuple(LinkedOptimization(
            optimization_id=row.id_optimizacion, status=row.estado,
            released=bool(row.comparison_snapshot and row.comparison_snapshot.get("released_at")),
            confirmed=row.id_optimizacion in confirmed or bool(
                row.comparison_snapshot and row.comparison_snapshot.get("confirmation")),
            consumed=row.id_optimizacion in consumed) for row in rows)


class SqlStuckOrdersUnitOfWork(SqlRunUnitOfWork):
    """Reutiliza la sesión, el commit/rollback y SqlOrdersBatch (tx.orders) de las corridas."""
    def __enter__(self):
        super().__enter__()
        self.stuck_orders = SqlStuckOrdersRepository(self.session)
        return self
