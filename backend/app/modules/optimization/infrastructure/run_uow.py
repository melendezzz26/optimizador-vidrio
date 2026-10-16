"""Optimization-owned transaction; shared ORM only in Infrastructure.

The legacy scalar Orders start method commits internally and is deliberately
not used. Geometry rules remain in Orders' public persisted-piece validator.
"""
from dataclasses import replace
from datetime import datetime, timezone
from sqlalchemy import select
from app.models import Pedido, Pieza, Configuracion, Optimizacion, OptimizacionPedido, EjecucionOptimizacion, MaterialUtilizado, MetricaEjecucion
from ..application.dto import OptimizationRun, RunStatus
from ..application.errors import RunError
from ..domain.problem import OptimizationConfig, OptimizationResult, MaterialSource
from .run_snapshot import encode, decode, json_value


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
        config = self.session.get(Configuracion, configuration_id)
        snapshot = {**encode(result), "configuration_version": config.version,
                    "residual_minimum_width_mm": str(config.ancho_min_retazo_mm),
                    "residual_minimum_height_mm": str(config.alto_min_retazo_mm)}
        self.session.add(EjecucionOptimizacion(id_optimizacion=row.id_optimizacion, metodo="FF", fecha_inicio=now,
                                              estado="EN_EJECUCION", completo=False, patron_resultado=snapshot))
        return OptimizationRun(optimization_id=row.id_optimizacion, status=RunStatus.RUNNING, result=result)

    def get(self, optimization_id):
        # One statement snapshot: never mix a parent read before completion with
        # an execution read after completion under PostgreSQL READ COMMITTED.
        pair = self.session.execute(select(Optimizacion, EjecucionOptimizacion).outerjoin(
            EjecucionOptimizacion, (EjecucionOptimizacion.id_optimizacion == Optimizacion.id_optimizacion)
            & (EjecucionOptimizacion.metodo == "FF"))
            .where(Optimizacion.id_optimizacion == optimization_id)).first()
        if pair is None:
            raise RunError("NOT_FOUND", "No se encontró la optimización.")
        row, execution = pair
        if execution is None or not isinstance(execution.patron_resultado, dict) or execution.patron_resultado.get("snapshot_version") != 1:
            raise RunError("NOT_FOUND", "La corrida histórica no tiene un resultado FF versionado.")
        result = decode(execution.patron_resultado)
        links = tuple(self.session.scalars(select(OptimizacionPedido.id_pedido)
                      .where(OptimizacionPedido.id_optimizacion == optimization_id).order_by(OptimizacionPedido.id_pedido)))
        expected_execution_state = {"EN_EJECUCION": "EN_EJECUCION", "COMPLETADA": "COMPLETADA",
                                    "SIN_SOLUCION": "COMPLETADA", "FALLIDA": "FALLIDA"}[row.estado]
        expected_selection = execution.id_ejecucion if row.estado == "COMPLETADA" else None
        if (links != result.problem.order_ids or execution.estado != expected_execution_state
                or execution.completo != result.complete or row.id_ejecucion_seleccionada != expected_selection):
            raise RunError("INTERNAL_ERROR", "La trazabilidad de la corrida requiere revisión.")
        return OptimizationRun(optimization_id=optimization_id, status=RunStatus(row.estado), result=result)


    def residual_limits(self, optimization_id):
        from decimal import Decimal
        execution = self._execution(optimization_id)
        snapshot = execution.patron_resultado
        return Decimal(snapshot["residual_minimum_width_mm"]), Decimal(snapshot["residual_minimum_height_mm"])

    def _execution(self, optimization_id):
        return self.session.scalar(select(EjecucionOptimizacion).where(
            EjecucionOptimizacion.id_optimizacion == optimization_id, EjecucionOptimizacion.metodo == "FF"))

    def save_result(self, optimization_id, result, residuals):
        row = self.session.scalar(select(Optimizacion).where(Optimizacion.id_optimizacion == optimization_id).with_for_update())
        if row is None:
            raise RunError("NOT_FOUND", "No se encontró la optimización.")
        if row.estado != "EN_EJECUCION":
            raise RunError("STATE_CONFLICT", "La corrida ya ha finalizado.")
        original = self.get(optimization_id)
        # Only provider candidates may change after acceptance, never requested units/config.
        if result.problem.order_ids != original.result.problem.order_ids or result.problem.config != original.result.problem.config or result.problem.units != original.result.problem.units:
            raise RunError("STATE_CONFLICT", "El resultado no corresponde al snapshot aceptado.")
        SqlOrdersBatch(self.session).transition(result.problem.order_ids, "EN_OPTIMIZACION",
                                                "OPTIMIZADO" if result.complete else "PENDIENTE")
        execution = self._execution(optimization_id)
        now = datetime.now(timezone.utc)
        row.estado = "COMPLETADA" if result.complete else "SIN_SOLUCION"
        row.fecha_fin = execution.fecha_fin = now
        execution.estado, execution.completo = "COMPLETADA", result.complete
        execution.patron_resultado = {**execution.patron_resultado, **encode(result), "residual_rectangles": json_value(residuals)}
        row.id_ejecucion_seleccionada = execution.id_ejecucion if result.complete else None
        aggregated = {}
        for material in result.materials_used:
            key = material.source, material.material_id
            aggregated[key] = aggregated.get(key, 0) + 1
        for (source, identifier), quantity in aggregated.items():
            self.session.add(MaterialUtilizado(id_ejecucion=execution.id_ejecucion,
                id_plancha=identifier if source is MaterialSource.SHEET else None,
                id_retazo=identifier if source is MaterialSource.REMNANT else None, cantidad_utilizada=quantity))
        if result.metrics is not None:
            m = result.metrics
            self.session.add(MetricaEjecucion(id_ejecucion=execution.id_ejecucion,
                area_material_total_mm2=m.material_area_mm2, area_piezas_colocadas_mm2=m.placed_piece_area_mm2,
                aprovechamiento_pct=m.utilization_pct, merma_mm2=m.waste_mm2,
                retazo_recuperable_mm2=m.recoverable_remnant_mm2, planchas_nuevas_usadas=m.new_sheets_used,
                tiempo_computacional_ms=result.computation_time_ms))
        return OptimizationRun(optimization_id=optimization_id, status=RunStatus(row.estado), result=result)


    def fail(self, optimization_id, code, placements=()):
        row = self.session.scalar(select(Optimizacion).where(Optimizacion.id_optimizacion == optimization_id).with_for_update())
        if row is None:
            raise RunError("NOT_FOUND", "No se encontró la optimización.")
        if row.estado != "EN_EJECUCION":
            return self.get(optimization_id)  # A late disconnect cannot overwrite a committed terminal result.
        original = self.get(optimization_id)
        stocks = {p.stock.identity: p.stock for p in placements}
        problem = replace(original.result.problem, groups=tuple(replace(g, stock_candidates=tuple(
            s for s in stocks.values() if s.material_key == g.key)) for g in original.result.problem.groups))
        result = OptimizationResult(problem=problem, placements=tuple(placements))
        execution = self._execution(optimization_id)
        row.estado, execution.estado = "FALLIDA", "FALLIDA"
        row.fecha_fin = execution.fecha_fin = datetime.now(timezone.utc)
        row.id_ejecucion_seleccionada = None
        execution.completo = result.complete
        execution.patron_resultado = {**execution.patron_resultado, **encode(result), "failure_code": code}
        # Orders stay EN_OPTIMIZACION: explicit reconciliation, never automatic NO_FIT.
        return OptimizationRun(optimization_id=optimization_id, status=RunStatus.FAILED, result=result)


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
                try:
                    self.session.commit()
                except Exception:
                    self.session.rollback()
                    raise
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
