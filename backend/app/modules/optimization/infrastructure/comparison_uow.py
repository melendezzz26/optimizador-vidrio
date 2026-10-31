"""Persistencia del agregado FF/BF/WF, separada del recorrido histórico FF.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
Bloqueo: comparación -> ejecuciones -> pedidos ASC. Solo el supervisor puede
cerrar la comparación después de detener/join sus procesos; HTTP no certifica
terminación. Una unidad de trabajo conserva un único commit/rollback.
"""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib

from sqlalchemy import select, text

from app.models import (Configuracion, EjecucionOptimizacion, MaterialUtilizado,
                        MetricaEjecucion, Optimizacion, OptimizacionPedido, Pieza, TipoVidrio)
from ..application.comparison_contracts import Comparison, ComparisonExecution, METHODS
from ..application.errors import RunError
from ..domain.metrics import ResidualRectangle
from ..domain.problem import MaterialSource
from .comparison_snapshot import (canonical_json, decode_problem, decode_result,
    encode_problem, encode_result, problem_fingerprint)
from .comparison_stock import SqlComparisonStock
from .run_snapshot import json_value
from .run_uow import SqlOrdersBatch, SqlRunUnitOfWork


def now():
    return datetime.now(timezone.utc)


class SqlComparisonOrders(SqlOrdersBatch):
    def lock_pending(self, order_ids):
        if any(o.estado != "PENDIENTE" for o in self._lock(order_ids)):
            raise RunError("STATE_CONFLICT", "Todos los pedidos deben estar pendientes.")
        rows = self.session.execute(select(Pieza, TipoVidrio.nombre).join(TipoVidrio,
            TipoVidrio.id_tipo_vidrio == Pieza.id_tipo_vidrio).where(Pieza.id_pedido.in_(order_ids))
            .order_by(Pieza.id_pieza)).all()
        if {p.id_pedido for p, _ in rows} != set(order_ids):
            raise RunError("INVALID_INPUT", "Todos los pedidos deben tener piezas válidas.")
        return [{**{k: getattr(p, k) for k in ("id_pedido", "id_pieza", "id_tipo_vidrio",
            "espesor_mm", "tipo_forma", "cantidad", "geometria", "dimensiones", "area_mm2")},
            "material_nombre": name} for p, name in rows]


class SqlComparisonRepository:
    def __init__(self, session):
        self.session = session

    def find_by_key(self, actor_id, key):
        # Serializa la clave, sin bloquear inventario. Una repetición concurrente
        # en READ COMMITTED observa el commit anterior antes de leer la fila.
        digest = hashlib.sha256(f"comparison:{actor_id}:{key}".encode()).digest()
        lock_id = int.from_bytes(digest[:8], "big", signed=True)
        self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
        identifier = self.session.scalar(select(Optimizacion.id_optimizacion).where(
            Optimizacion.id_usuario_ejecutor == actor_id, Optimizacion.comparison_key == key))
        return self.get(identifier) if identifier is not None else None

    def create(self, problem, configuration_id, actor_id, key, requested_pieces):
        config = self.session.get(Configuracion, configuration_id)
        snapshot = {"comparison_snapshot_version": 1, "input": encode_problem(problem),
            "input_sha256": problem_fingerprint(problem), "requested_pieces": json_value(requested_pieces),
            "configuration_version": config.version,
            "minimum_width_mm": str(config.ancho_min_retazo_mm),
            "minimum_height_mm": str(config.alto_min_retazo_mm)}
        canonical_json(snapshot)  # También acota la solicitud original enriquecida.
        row = Optimizacion(fecha_inicio=now(), estado="EN_EJECUCION", id_pedido=problem.order_ids[0],
            id_configuracion=configuration_id, id_usuario_ejecutor=actor_id, criterio_seleccion_version="CMP-v1",
            comparison_key=key, comparison_snapshot=snapshot, comparison_version=1)
        self.session.add(row)
        self.session.flush()
        self.session.add_all([OptimizacionPedido(id_optimizacion=row.id_optimizacion, id_pedido=i)
                              for i in problem.order_ids])
        self.session.add_all([EjecucionOptimizacion(id_optimizacion=row.id_optimizacion, metodo=method,
            fecha_inicio=row.fecha_inicio, estado="EN_EJECUCION", completo=False) for method in METHODS])
        self.session.flush()
        return self.get(row.id_optimizacion)

    def get(self, comparison_id):
        # Parent y tres ejecuciones se observan en un solo snapshot SQL.
        pairs = self.session.execute(select(Optimizacion, EjecucionOptimizacion).outerjoin(
            EjecucionOptimizacion, EjecucionOptimizacion.id_optimizacion == Optimizacion.id_optimizacion)
            .where(Optimizacion.id_optimizacion == comparison_id).execution_options(populate_existing=True)).all()
        if not pairs or pairs[0][0].comparison_snapshot is None:
            raise RunError("NOT_FOUND", "No se encontró la comparación.")
        row, snapshot = pairs[0][0], pairs[0][0].comparison_snapshot
        try:
            if type(snapshot.get("comparison_snapshot_version")) is not int or snapshot["comparison_snapshot_version"] != 1:
                raise ValueError("Unsupported comparison snapshot")
            problem = decode_problem(snapshot["input"])
            if problem_fingerprint(problem) != snapshot["input_sha256"]:
                raise ValueError("Input fingerprint mismatch")
            by_method = {e.metodo: e for _, e in pairs if e is not None}
            if set(by_method) != set(METHODS) or len(pairs) != 3:
                raise ValueError("Missing executions")
            executions = []
            for method in METHODS:
                execution = by_method[method]
                stored = execution.patron_resultado or {}
                result, residuals = None, ()
                if execution.estado == "COMPLETADA":
                    result = decode_result(stored["snapshot"], expected_method=method)
                    if result.problem != problem or execution.completo != result.complete:
                        raise ValueError("Result does not match common input")
                    if result.computation_time_ms is None or (result.placements and result.metrics is None):
                        raise ValueError("Result is missing calculated metrics/time")
                    residuals = tuple(ResidualRectangle(**{k: Decimal(v) if k in (
                        "x_mm", "y_mm", "width_mm", "height_mm", "area_mm2") else v
                        for k, v in region.items()}) for region in stored["residual_rectangles"])
                    if execution.id_ejecucion == row.id_ejecucion_seleccionada and snapshot.get("confirmation"):
                        created = snapshot["confirmation"]["receipt"]["remnants_created"]
                        persisted = {(r["source"]["source"], r["source"]["material_id"],
                                      r["source"]["physical_unit_index"]) for r in created}
                        residuals = tuple(r for r in residuals if
                            (r.material_source, r.material_id, r.stock_unit_index) in persisted)
                elif execution.completo or execution.estado not in ("EN_EJECUCION", "FALLIDA"):
                    raise ValueError("Invalid execution state")
                executions.append(ComparisonExecution(execution_id=execution.id_ejecucion, method=method,
                    status=execution.estado, result=result, residuals=residuals, failure_code=stored.get("failure_code")))
            stopped = snapshot.get("workers_stopped_at") is not None
            released = snapshot.get("released_at") is not None
            if stopped:
                if any(e.status == "EN_EJECUCION" for e in executions):
                    raise ValueError("Stopped comparison has active executions")
                expected = ("COMPLETADA" if any(e.eligible for e in executions) else
                            "FALLIDA" if any(e.status == "FALLIDA" for e in executions) else "SIN_SOLUCION")
                if row.estado != expected:
                    raise ValueError("Invalid aggregate state")
            elif row.estado != "EN_EJECUCION":
                raise ValueError("Aggregate closed before workers stopped")
            if row.id_ejecucion_seleccionada is not None and (not stopped or released or not any(
                e.execution_id == row.id_ejecucion_seleccionada and e.eligible for e in executions)):
                raise ValueError("Invalid selection")
            links = tuple(self.session.scalars(select(OptimizacionPedido.id_pedido).where(
                OptimizacionPedido.id_optimizacion == comparison_id).order_by(OptimizacionPedido.id_pedido)))
            if links != problem.order_ids:
                raise ValueError("Order links differ from snapshot")
            return Comparison(comparison_id=comparison_id, version=row.comparison_version, status=row.estado,
                actor_id=row.id_usuario_ejecutor, input_sha256=snapshot["input_sha256"], problem=problem,
                requested_pieces=tuple(snapshot["requested_pieces"]), configuration_id=row.id_configuracion,
                configuration_version=snapshot["configuration_version"],
                minimum_width_mm=Decimal(snapshot["minimum_width_mm"]),
                minimum_height_mm=Decimal(snapshot["minimum_height_mm"]), executions=tuple(executions),
                selected_execution_id=row.id_ejecucion_seleccionada, workers_stopped=stopped, released=released,
                confirmation=snapshot.get("confirmation"))
        except (ValueError, TypeError, KeyError, ArithmeticError) as error:
            raise RunError("INTERNAL_ERROR", "La trazabilidad de la comparación requiere revisión.") from error

    def _lock(self, comparison_id):
        row = self.session.scalar(select(Optimizacion).where(Optimizacion.id_optimizacion == comparison_id)
            .with_for_update().execution_options(populate_existing=True))
        if row is None or row.comparison_snapshot is None:
            raise RunError("NOT_FOUND", "No se encontró la comparación.")
        return row

    def _execution(self, comparison_id, execution_id):
        row = self.session.scalar(select(EjecucionOptimizacion).where(
            EjecucionOptimizacion.id_optimizacion == comparison_id,
            EjecucionOptimizacion.id_ejecucion == execution_id).with_for_update())
        if row is None:
            raise RunError("NOT_FOUND", "La ejecución no pertenece a la comparación.")
        return row

    def claim_supervisor(self, comparison_id, token, supervisor_identity=None):
        row = self._lock(comparison_id)
        if row.estado != "EN_EJECUCION" or row.comparison_snapshot.get("supervisor_token") is not None:
            return False
        if any(e.status != "EN_EJECUCION" for e in self.get(comparison_id).executions):
            return False
        row.comparison_snapshot = {**row.comparison_snapshot, "supervisor_token": token,
                                   "supervisor_identity": supervisor_identity}
        row.comparison_version += 1
        return True

    def record_worker(self, comparison_id, execution_id, identity):
        row = self._lock(comparison_id)
        self._execution(comparison_id, execution_id)
        if row.estado != "EN_EJECUCION" or not row.comparison_snapshot.get("supervisor_token"):
            raise RunError("STATE_CONFLICT", "La comparación no tiene un supervisor activo.")
        if (type(identity.get("pid")) is not int or identity["pid"] <= 0
                or not isinstance(identity.get("start_ticks"), str) or not identity["start_ticks"].isdigit()):
            raise RunError("STATE_CONFLICT", "No se pudo registrar el proceso de cálculo.")
        row.comparison_snapshot = {**row.comparison_snapshot, "worker_processes": {
            **row.comparison_snapshot.get("worker_processes", {}), str(execution_id): {
                "pid": identity["pid"], "start_ticks": identity["start_ticks"]}}}

    def save_result(self, comparison_id, execution_id, result, residuals):
        row = self._lock(comparison_id)
        current = self.get(comparison_id)
        execution = self._execution(comparison_id, execution_id)
        if current.workers_stopped or execution.estado != "EN_EJECUCION":
            raise RunError("STATE_CONFLICT", "La ejecución ya ha finalizado.")
        if result.method != execution.metodo or result.problem != current.problem:
            raise RunError("STATE_CONFLICT", "El resultado no corresponde a la entrada o al motor aceptado.")
        if result.computation_time_ms is None or (result.placements and result.metrics is None):
            raise RunError("STATE_CONFLICT", "El resultado debe incluir las métricas y el tiempo de cálculo.")
        execution.patron_resultado = {"snapshot": encode_result(result), "residual_rectangles": json_value(residuals)}
        execution.estado, execution.completo, execution.fecha_fin = "COMPLETADA", result.complete, now()
        row.comparison_version += 1
        quantities = {}
        for material in result.materials_used:
            key = material.source, material.material_id
            quantities[key] = quantities.get(key, 0) + 1
        for (source, identifier), quantity in quantities.items():
            self.session.add(MaterialUtilizado(id_ejecucion=execution_id,
                id_plancha=identifier if source is MaterialSource.SHEET else None,
                id_retazo=identifier if source is MaterialSource.REMNANT else None, cantidad_utilizada=quantity))
        if result.metrics is not None:
            m = result.metrics
            self.session.add(MetricaEjecucion(id_ejecucion=execution_id, area_material_total_mm2=m.material_area_mm2,
                area_piezas_colocadas_mm2=m.placed_piece_area_mm2, aprovechamiento_pct=m.utilization_pct,
                merma_mm2=m.waste_mm2, retazo_recuperable_mm2=m.recoverable_remnant_mm2,
                planchas_nuevas_usadas=m.new_sheets_used, tiempo_computacional_ms=result.computation_time_ms))
        self.session.flush()
        return self.get(comparison_id)

    def fail_execution(self, comparison_id, execution_id, code):
        row = self._lock(comparison_id)
        execution = self._execution(comparison_id, execution_id)
        if row.estado != "EN_EJECUCION" or execution.estado != "EN_EJECUCION":
            return self.get(comparison_id)
        allowed = {"EXECUTION_FAILED", "TIME_BUDGET_EXCEEDED", "MEMORY_BUDGET_EXCEEDED",
                   "RESULT_SAVE_FAILED", "WORKER_STOPPED", "PROCESS_START_FAILED"}
        execution.estado, execution.fecha_fin = "FALLIDA", now()
        execution.patron_resultado = {"failure_code": code if isinstance(code, str) and code in allowed else "EXECUTION_FAILED"}
        row.comparison_version += 1
        self.session.flush()
        return self.get(comparison_id)

    def finish_after_workers_stopped(self, comparison_id):
        """Solo tras join de los tres procesos; nunca desde una desconexión HTTP."""
        row = self._lock(comparison_id)
        current = self.get(comparison_id)
        if current.workers_stopped:
            return current
        if any(e.status == "EN_EJECUCION" for e in current.executions):
            raise RunError("STATE_CONFLICT", "Todavía hay ejecuciones sin resolver.")
        eligible = any(e.eligible for e in current.executions)
        SqlOrdersBatch(self.session).transition(current.problem.order_ids, "EN_OPTIMIZACION",
                                                "OPTIMIZADO" if eligible else "PENDIENTE")
        row.estado = "COMPLETADA" if eligible else "FALLIDA" if current.incomplete else "SIN_SOLUCION"
        row.fecha_fin = now()
        row.comparison_snapshot = {**row.comparison_snapshot, "workers_stopped_at": row.fecha_fin.isoformat()}
        row.comparison_version += 1
        self.session.flush()
        return self.get(comparison_id)

    def _editable(self, comparison_id, expected_version):
        row = self._lock(comparison_id)
        if type(expected_version) is not int or expected_version != row.comparison_version:
            raise RunError("STATE_CONFLICT", "La comparación cambió. Actualiza su estado antes de continuar.")
        current = self.get(comparison_id)
        if not current.terminal or current.released or current.confirmation is not None:
            raise RunError("STATE_CONFLICT", "La comparación no admite cambios en este estado.")
        return row, current

    def select(self, comparison_id, execution_id, expected_version):
        row, current = self._editable(comparison_id, expected_version)
        if type(execution_id) is not int or not any(e.execution_id == execution_id and e.eligible for e in current.executions):
            raise RunError("NOT_CONFIRMABLE", "Selecciona un resultado completo y guardado de esta comparación.")
        row.id_ejecucion_seleccionada = execution_id
        row.comparison_version += 1
        self.session.flush()
        return self.get(comparison_id)

    def release(self, comparison_id, expected_version, actor_id):
        row, current = self._editable(comparison_id, expected_version)
        if any(e.eligible for e in current.executions):
            SqlOrdersBatch(self.session).transition(current.problem.order_ids, "OPTIMIZADO", "PENDIENTE")
        row.comparison_snapshot = {**row.comparison_snapshot, "released_at": now().isoformat(),
            "released_by": actor_id, "released_selection_id": row.id_ejecucion_seleccionada}
        row.id_ejecucion_seleccionada = None
        row.comparison_version += 1
        self.session.flush()
        return self.get(comparison_id)


class SqlComparisonUnitOfWork(SqlRunUnitOfWork):
    def __enter__(self):
        super().__enter__()
        self.orders = SqlComparisonOrders(self.session)
        self.comparisons = SqlComparisonRepository(self.session)
        self.stock = SqlComparisonStock(self.session)
        from .comparison_confirmation import SqlComparisonConfirmationRepository
        self.comparison_confirmation = SqlComparisonConfirmationRepository(self.session, self.comparisons)
        return self
