"""Optimization-owned transaction; shared ORM only in Infrastructure.

The legacy scalar Orders start method commits internally and is deliberately
not used. Geometry rules remain in Orders' public persisted-piece validator.
"""
from datetime import datetime, timezone
from sqlalchemy import select
from app.models import Pedido, Pieza, Configuracion, Optimizacion, OptimizacionPedido, EjecucionOptimizacion
from ..application.dto import OptimizationRun, RunStatus
from ..application.errors import RunError
from ..domain.problem import OptimizationConfig, OptimizationResult
from .run_snapshot import encode, decode


class SqlOrdersBatch:
    def __init__(self, session):
        self.session = session

    def lock_pending(self, order_ids):
        orders = self._lock(order_ids)
        if any(o.estado != "PENDIENTE" for o in orders):
            raise RunError("STATE_CONFLICT", "Todos los pedidos deben estar pendientes.")
        rows = self.session.scalars(select(Pieza).where(Pieza.id_pedido.in_(order_ids)).order_by(Pieza.id_pieza)).all()
        if {p.id_pedido for p in rows} != set(order_ids):
            raise RunError("INVALID_INPUT", "Todos los pedidos deben tener piezas válidas.")
        return [{k: getattr(p, k) for k in ("id_pedido", "id_pieza", "id_tipo_vidrio", "espesor_mm", "tipo_forma",
                                            "cantidad", "geometria", "area_mm2")} for p in rows]

    def _lock(self, order_ids):
        rows = self.session.scalars(select(Pedido).where(Pedido.id_pedido.in_(order_ids))
                                    .order_by(Pedido.id_pedido).with_for_update()).all()
        if len(rows) != len(order_ids):
            raise RunError("NOT_FOUND", "No se encontraron todos los pedidos seleccionados.")
        return rows

    def transition(self, order_ids, expected, target):
        rows = self._lock(order_ids)
        if any(o.estado != expected for o in rows):
            raise RunError("STATE_CONFLICT", "El estado del lote ha cambiado.")
        for row in rows:
            row.estado = target


class SqlRunRepository:
    def __init__(self, session):
        self.session = session

    def create(self, problem, configuration_id, actor_id):
        now = datetime.now(timezone.utc)
        row = Optimizacion(fecha_inicio=now, estado="EN_EJECUCION", id_pedido=problem.order_ids[0],
                           id_configuracion=configuration_id, id_usuario_ejecutor=actor_id,
                           criterio_seleccion_version="S1-FF-v1")
        self.session.add(row)
        self.session.flush()
        self.session.add_all([OptimizacionPedido(id_optimizacion=row.id_optimizacion, id_pedido=i) for i in problem.order_ids])
        result = OptimizationResult(problem=problem, placements=())
        self.session.add(EjecucionOptimizacion(id_optimizacion=row.id_optimizacion, metodo="FF", fecha_inicio=now,
                                              estado="EN_EJECUCION", completo=False, patron_resultado=encode(result)))
        return OptimizationRun(optimization_id=row.id_optimizacion, status=RunStatus.RUNNING, result=result)

    def get(self, optimization_id):
        row = self.session.get(Optimizacion, optimization_id)
        if row is None:
            raise RunError("NOT_FOUND", "No se encontró la optimización.")
        execution = self.session.scalar(select(EjecucionOptimizacion).where(
            EjecucionOptimizacion.id_optimizacion == optimization_id, EjecucionOptimizacion.metodo == "FF"))
        if execution is None or execution.patron_resultado is None:
            raise RunError("NOT_FOUND", "La corrida histórica no tiene un resultado FF versionado.")
        result = decode(execution.patron_resultado)
        links = tuple(self.session.scalars(select(OptimizacionPedido.id_pedido)
                      .where(OptimizacionPedido.id_optimizacion == optimization_id).order_by(OptimizacionPedido.id_pedido)))
        if links != result.problem.order_ids:
            raise RunError("INTERNAL_ERROR", "La trazabilidad de la corrida requiere revisión.")
        return OptimizationRun(optimization_id=optimization_id, status=RunStatus(row.estado), result=result)


class SqlRunUnitOfWork:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def __enter__(self):
        self.session = self.session_factory()
        self.orders = SqlOrdersBatch(self.session)
        self.runs = SqlRunRepository(self.session)
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()

    def configuration(self):
        configs = self.session.scalars(select(Configuracion).where(Configuracion.vigente.is_(True))).all()
        if len(configs) != 1:
            raise RunError("CONFIG_CONFLICT", "Se requiere una única configuración vigente completa.")
        c = configs[0]
        try:
            config = OptimizationConfig(resolution_mm=c.resolucion_raster_mm, margin_mm=c.margen_mm,
                                        separation_mm=c.separacion_mm, angular_step_deg=c.paso_angular_grados)
        except ValueError as exc:
            raise RunError("CONFIG_CONFLICT", "La configuración vigente está incompleta o es inválida.") from exc
        return c.id_configuracion, config
