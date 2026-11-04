"""B02 opt-in persistence. No runner, admission, HTTP routes or stock consumption."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import re

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models import (Configuracion, EjecucionOptimizacion, MaterialUtilizado,
                        MetricaEjecucion, Optimizacion, OptimizacionPedido)
from ..application.comparison_catalog import METHODS_V2
from ..application.comparison_persistence_contracts import (
    PersistedComparisonV2, PersistedExecutionV2, VisualReferenceV2,
)
from ..application.comparison_v2_contracts import ComparisonInputV2, ExecutionPayloadV2
from ..application.errors import RunError
from ..application.supervision_contracts import runtime_metadata, identity
from ..domain.metrics import ResidualRectangle
from ..domain.problem import MaterialSource
from .comparison_snapshot import canonical_json
from .comparison_uow import SqlComparisonRepository, SqlComparisonUnitOfWork, now
from .comparison_v2_snapshot import (encode_comparison_input_v2, decode_comparison_input_v2,
                                     encode_result_v3, decode_result_v3)
from .run_snapshot import json_value


def _utc(value):
    stamp = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(stamp, datetime) or stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
        raise ValueError("Persisted stop marker requires UTC")
    return stamp


class SqlComparisonV2Repository:
    def __init__(self, session):
        self.session = session
        self.legacy = SqlComparisonRepository(session)

    def find_by_key(self, actor_id, key):
        lock_id = int.from_bytes(hashlib.sha256(f"comparison:{actor_id}:{key}".encode()).digest()[:8], "big", signed=True)
        self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
        identifier = self.session.scalar(select(Optimizacion.id_optimizacion).where(
            Optimizacion.id_usuario_ejecutor == actor_id, Optimizacion.comparison_key == key))
        return self.get(identifier) if identifier is not None else None

    def create(self, frozen: ComparisonInputV2, actor_id, key, *, managed=False):
        if (not isinstance(frozen, ComparisonInputV2) or type(actor_id) is not int
                or not 0 < actor_id <= 2147483647 or not isinstance(key, str)
                or re.fullmatch(r"[A-Za-z0-9_-]{8,64}", key) is None):
            raise RunError("INVALID_INPUT", "Entrada o identidad de comparación inválida.")
        previous = self.find_by_key(actor_id, key)
        encoded = encode_comparison_input_v2(frozen)
        if previous is not None:
            if encoded != encode_comparison_input_v2(self._input(previous)):
                raise RunError("STATE_CONFLICT", "La clave identifica otra entrada congelada.")
            return previous
        config = self.session.get(Configuracion, frozen.configuration_id)
        if config is None or config.version != frozen.configuration_version:
            raise RunError("CONFIG_CONFLICT", "La configuración no corresponde al snapshot.")
        row = Optimizacion(fecha_inicio=now(), estado="EN_EJECUCION", id_pedido=frozen.problem.order_ids[0],
            id_configuracion=frozen.configuration_id, id_usuario_ejecutor=actor_id,
            criterio_seleccion_version="CMP-v2", comparison_key=key, comparison_version=1,
            comparison_snapshot={**encoded, "runtime": (dict(runtime_version=1, supervisor_stopped_at=None,
                supervisor=None, workers={}) if managed else {"supervisor_stopped_at": None})})
        self.session.add(row)
        self.session.flush()
        self.session.add_all([OptimizacionPedido(id_optimizacion=row.id_optimizacion, id_pedido=i)
                              for i in frozen.problem.order_ids])
        for method in METHODS_V2:
            execution = EjecucionOptimizacion(id_optimizacion=row.id_optimizacion, metodo=method,
                fecha_inicio=row.fecha_inicio, estado="EN_EJECUCION", completo=False)
            self.session.add(execution)
            self.session.flush()
            execution.patron_resultado = self._record(row.id_optimizacion, execution, "QUEUED", None, (), ())
        self.session.flush()
        return self.get(row.id_optimizacion)

    @staticmethod
    def _input(current):
        return ComparisonInputV2(problem=current.problem, methods=current.methods,
            configuration_id=current.configuration_id, configuration_version=current.configuration_version,
            requested_pieces=current.requested_pieces, minimum_width_mm=current.minimum_width_mm,
            minimum_height_mm=current.minimum_height_mm)

    @staticmethod
    def _record(comparison_id, execution, dispatch, payload, residuals, references):
        value = dict(profile="comparison-v2", comparison_id=comparison_id,
            execution_id=execution.id_ejecucion, method=execution.metodo, dispatch_state=dispatch,
            snapshot=encode_result_v3(payload) if payload is not None else None,
            residual_rectangles=json_value(residuals), visual_references=[r.record() for r in references])
        canonical_json(value)
        return value

    def get_compatible(self, identifier):
        """Internal read dispatcher; preserves original legacy DTOs and never recalculates."""
        row = self.session.get(Optimizacion, identifier, populate_existing=True)
        if row is None:
            raise RunError("NOT_FOUND", "No se encontró la optimización.")
        if row.comparison_snapshot is None:
            from .run_uow import SqlRunRepository
            return SqlRunRepository(self.session).get(identifier)
        version = row.comparison_snapshot.get("comparison_snapshot_version")
        if type(version) is int and version == 1:
            return self.legacy.get(identifier)
        return self.get(identifier)

    def get(self, identifier):
        pairs = self.session.execute(select(Optimizacion, EjecucionOptimizacion).outerjoin(
            EjecucionOptimizacion, EjecucionOptimizacion.id_optimizacion == Optimizacion.id_optimizacion)
            .where(Optimizacion.id_optimizacion == identifier).execution_options(populate_existing=True)).all()
        if not pairs or pairs[0][0].comparison_snapshot is None:
            raise RunError("NOT_FOUND", "No se encontró la comparación v2.")
        row, stored = pairs[0][0], pairs[0][0].comparison_snapshot
        if stored.get("comparison_snapshot_version") == 1:
            raise RunError("STATE_CONFLICT", "La comparación pertenece al perfil comparison-v1.")
        try:
            frozen = decode_comparison_input_v2({k: v for k, v in stored.items() if k != "runtime"})
            if row.criterio_seleccion_version != "CMP-v2" or row.id_configuracion != frozen.configuration_id:
                raise ValueError("Aggregate profile/configuration identity mismatch")
            runtime = stored["runtime"]
            runtime_metadata(runtime, [e.id_ejecucion for _, e in pairs if e is not None])
            stopped = runtime["supervisor_stopped_at"] is not None
            if stopped:
                if row.fecha_fin is None or _utc(runtime["supervisor_stopped_at"]) != row.fecha_fin:
                    raise ValueError("Inconsistent supervisor stop marker")
            by_method = {e.metodo: e for _, e in pairs if e is not None}
            if len(pairs) != len(frozen.methods) or set(by_method) != set(frozen.methods):
                raise ValueError("Missing or inconsistent execution identities")
            executions = tuple(self._read_execution(identifier, by_method[method], frozen.problem)
                               for method in frozen.methods)
            if stopped and any(e.dispatch_state != "TERMINATED" for e in executions):
                raise ValueError("Stopped aggregate contains active execution")
            expected_status = ("EN_EJECUCION" if not stopped else
                "COMPLETADA" if any(e.eligible for e in executions) else
                "FALLIDA" if any(e.status == "FALLIDA" for e in executions) else "SIN_SOLUCION")
            if row.estado != expected_status:
                raise ValueError("Aggregate state does not match persisted executions")
            selected = next((e for e in executions if e.execution_id == row.id_ejecucion_seleccionada), None)
            if row.id_ejecucion_seleccionada is not None and (not stopped or selected is None or not selected.eligible):
                raise ValueError("Selected execution is not an eligible owned result")
            links = tuple(self.session.scalars(select(OptimizacionPedido.id_pedido).where(
                OptimizacionPedido.id_optimizacion == identifier).order_by(OptimizacionPedido.id_pedido)))
            if links != frozen.problem.order_ids or row.id_pedido != links[0]:
                raise ValueError("Order ownership differs from the frozen input")
            return PersistedComparisonV2(comparison_id=identifier, version=row.comparison_version,
                status=row.estado, actor_id=row.id_usuario_ejecutor, input_sha256=stored["input_sha256"],
                problem=frozen.problem, requested_pieces=frozen.requested_pieces, methods=frozen.methods,
                configuration_id=frozen.configuration_id, configuration_version=frozen.configuration_version,
                minimum_width_mm=frozen.minimum_width_mm, minimum_height_mm=frozen.minimum_height_mm,
                executions=executions, selected_execution_id=row.id_ejecucion_seleccionada, workers_stopped=stopped,
                runtime=runtime)
        except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError) as error:
            raise RunError("INTERNAL_ERROR", "La trazabilidad persistida v2 requiere revisión.") from error

    @staticmethod
    def _references(values, comparison_id, execution_id, method):
        references = tuple(VisualReferenceV2.from_record(v) if isinstance(v, dict) else v for v in values)
        if any(not isinstance(r, VisualReferenceV2) or (r.comparison_id, r.execution_id, r.method) != (
            comparison_id, execution_id, method) for r in references):
            raise ValueError("Cross-execution visual reference")
        if len({r.mask_ref for r in references}) != len(references):
            raise ValueError("Duplicate visual reference")
        return references

    def _read_execution(self, comparison_id, row, problem):
        data = row.patron_resultado
        if not isinstance(data, dict) or set(data) != {"profile", "comparison_id", "execution_id", "method",
                "dispatch_state", "snapshot", "residual_rectangles", "visual_references"}:
            raise ValueError("Invalid execution envelope")
        if (data["profile"], data["comparison_id"], data["execution_id"], data["method"]) != (
            "comparison-v2", comparison_id, row.id_ejecucion, row.metodo):
            raise ValueError("Execution snapshot belongs to another owner")
        refs = self._references(data["visual_references"], comparison_id, row.id_ejecucion, row.metodo)
        payload = decode_result_v3(data["snapshot"], expected_method=row.metodo) if data["snapshot"] is not None else None
        result = payload.result if payload else None
        if payload is None:
            if (data["dispatch_state"] not in ("QUEUED", "STARTING", "RUNNING") or row.estado != "EN_EJECUCION"
                    or row.completo or row.fecha_fin is not None or data["residual_rectangles"]):
                raise ValueError("Active execution contains terminal state")
        else:
            if data["dispatch_state"] != "TERMINATED" or row.fecha_fin is None:
                raise ValueError("Terminal result lacks its stop state")
            if row.estado != ("COMPLETADA" if result is not None else "FALLIDA") or row.completo != bool(result and result.complete):
                raise ValueError("SQL state/completeness differs from durable result")
            if result is not None and (result.problem != problem or result.computation_time_ms is None
                                      or result.placements and result.metrics is None):
                raise ValueError("Result differs from frozen input or lacks calculated metrics/time")
        residuals = tuple(ResidualRectangle(**{k: Decimal(v) if k in (
            "x_mm", "y_mm", "width_mm", "height_mm", "area_mm2") else v for k, v in item.items()})
            for item in data["residual_rectangles"])
        used = {(s.source.value, s.material_id, s.physical_unit_index) for s in result.materials_used} if result else set()
        if any((r.material_source, r.material_id, r.stock_unit_index) not in used for r in residuals):
            raise ValueError("Residual references an unowned source")
        return PersistedExecutionV2(execution_id=row.id_ejecucion, method=row.metodo, status=row.estado,
            result=result, residuals=residuals, diagnostic=payload.diagnostic if payload else None,
            failure_code=payload.diagnostic.termination_reason if payload and result is None else None,
            dispatch_state=data["dispatch_state"], visual_references=refs)

    def _writable(self, comparison_id, expected_version):
        row = self.legacy._lock(comparison_id)
        current = self.get(comparison_id)
        if type(expected_version) is not int or current.version != expected_version or current.terminal:
            raise RunError("STATE_CONFLICT", "La comparación cambió o ya está cerrada.")
        return row, current

    def set_dispatch_state(self, comparison_id, execution_id, state, expected_version):
        row, _ = self._writable(comparison_id, expected_version)
        execution = self.legacy._execution(comparison_id, execution_id)
        data = execution.patron_resultado
        if (data["dispatch_state"], state) not in (("QUEUED", "STARTING"), ("STARTING", "RUNNING")):
            raise RunError("STATE_CONFLICT", "Transición de despacho inválida.")
        execution.patron_resultado = {**data, "dispatch_state": state}
        row.comparison_version += 1
        self.session.flush()
        return self.get(comparison_id)

    def save_execution(self, comparison_id, execution_id, payload: ExecutionPayloadV2, residuals, expected_version):
        row, current = self._writable(comparison_id, expected_version)
        execution = self.legacy._execution(comparison_id, execution_id)
        if (execution.estado != "EN_EJECUCION" or not isinstance(payload, ExecutionPayloadV2)
                or payload.method != execution.metodo or payload.diagnostic is None
                or payload.result is not None and (payload.result.problem != current.problem
                    or execution.patron_resultado["dispatch_state"] != "RUNNING")):
            raise RunError("STATE_CONFLICT", "Resultado, motor o despacho no corresponde a la ejecución.")
        previous = next(e for e in current.executions if e.execution_id == execution_id)
        execution.patron_resultado = self._record(comparison_id, execution, "TERMINATED", payload,
                                                residuals, previous.visual_references)
        execution.estado = "COMPLETADA" if payload.result is not None else "FALLIDA"
        execution.completo = bool(payload.result and payload.result.complete)
        execution.fecha_fin = now()
        row.comparison_version += 1
        if payload.result is not None:
            self._result_rows(execution_id, payload.result)
        self.session.flush()
        return self.get(comparison_id)

    def _result_rows(self, execution_id, result):
        quantities = {}
        for stock in result.materials_used:
            key = stock.source, stock.material_id
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

    def save_visual_references(self, comparison_id, execution_id, references, expected_version):
        row, _ = self._writable(comparison_id, expected_version)
        execution = self.legacy._execution(comparison_id, execution_id)
        try:
            refs = self._references(references, comparison_id, execution_id, execution.metodo)
        except (TypeError, ValueError) as error:
            raise RunError("STATE_CONFLICT", "La referencia visual no pertenece a esta ejecución.") from error
        data = {**execution.patron_resultado, "visual_references": [r.record() for r in refs]}
        canonical_json(data)
        execution.patron_resultado = data
        row.comparison_version += 1
        self.session.flush()
        return self.get(comparison_id)

    def get_visual_reference(self, comparison_id, execution_id, mask_ref):
        current = self.get(comparison_id)
        execution = next((e for e in current.executions if e.execution_id == execution_id), None)
        reference = next((r for r in execution.visual_references if r.mask_ref == mask_ref), None) if execution else None
        if reference is None:
            raise RunError("NOT_FOUND", "La referencia visual no pertenece a esta ejecución.")
        return reference

    def record_supervisor_stopped(self, comparison_id, stopped_at, expected_version):
        """Persist an internally observed fact; obtaining process proof belongs to B05."""
        row, current = self._writable(comparison_id, expected_version)
        if any(e.dispatch_state != "TERMINATED" for e in current.executions):
            raise RunError("STATE_CONFLICT", "Todavía hay ejecuciones sin resolver.")
        stamp = _utc(stopped_at)
        row.comparison_snapshot = {**row.comparison_snapshot, "runtime": {
            **row.comparison_snapshot["runtime"], "supervisor_stopped_at": stamp.isoformat()}}
        row.estado = ("COMPLETADA" if any(e.eligible for e in current.executions) else
                      "FALLIDA" if any(e.status == "FALLIDA" for e in current.executions) else "SIN_SOLUCION")
        row.fecha_fin = stamp
        row.comparison_version += 1
        self.session.flush()
        return self.get(comparison_id)

    def claim_supervisor(self, comparison_id, token, owner):
        row = self.legacy._lock(comparison_id)
        current = self.get(comparison_id)
        runtime = row.comparison_snapshot["runtime"]
        if (current.terminal or runtime.get("runtime_version") != 1 or runtime["supervisor"] is not None
            or any(e.dispatch_state != "QUEUED" for e in current.executions)):
            return False
        updated = {**runtime, "supervisor": dict(token=token, identity=identity(owner))}
        runtime_metadata(updated, [e.execution_id for e in current.executions])
        row.comparison_snapshot = {**row.comparison_snapshot, "runtime": updated}
        row.comparison_version += 1
        self.session.flush()
        return True

    def require_supervisor(self, comparison_id, token):
        row = self.legacy._lock(comparison_id)
        current = self.get(comparison_id)
        owner = current.runtime.get("supervisor")
        if owner is None or owner["token"] != token:
            raise RunError("STATE_CONFLICT", "La comparación tiene otro dueño o no tiene identidad verificable.")
        return row, current

    def record_worker(self, comparison_id, execution_id, token, worker):
        row, current = self.require_supervisor(comparison_id, token)
        self.legacy._execution(comparison_id, execution_id)
        runtime = row.comparison_snapshot["runtime"]
        key = str(execution_id)
        workers = dict(runtime["workers"])
        if key in workers and workers[key] is not None and workers[key] != worker:
            raise RunError("STATE_CONFLICT", "La identidad del worker no puede sustituirse.")
        workers[key] = identity(worker) if worker is not None else None
        row.comparison_snapshot = {**row.comparison_snapshot, "runtime": {**runtime, "workers": workers}}
        row.comparison_version += 1
        self.session.flush()
        return self.get(comparison_id)


class SqlComparisonPersistenceUnitOfWork(SqlComparisonUnitOfWork):
    def __enter__(self):
        super().__enter__()
        self.comparisons_v2 = SqlComparisonV2Repository(self.session)
        return self

    def consistent_snapshot(self):
        self.session.connection(execution_options={"isolation_level": "REPEATABLE READ"})

    def captured_configuration(self):
        from ..domain.problem import OptimizationConfig
        rows = self.session.scalars(select(Configuracion).where(Configuracion.vigente.is_(True))).all()
        if len(rows) != 1:
            raise RunError("CONFIG_CONFLICT", "Se requiere una configuración vigente única.")
        c = rows[0]
        self._captured_config = c
        try:
            config = OptimizationConfig(resolution_mm=c.resolucion_raster_mm, margin_mm=c.margen_mm,
                separation_mm=c.separacion_mm, angular_step_deg=c.paso_angular_grados)
        except (ValueError, TypeError) as error:
            raise RunError("CONFIG_CONFLICT", "La configuracion vigente no es valida.") from error
        return c.id_configuracion, c.version, config, c.ancho_min_retazo_mm, c.alto_min_retazo_mm

    def unfinished(self):
        return list(self.session.scalars(select(Optimizacion.id_optimizacion).where(
            Optimizacion.estado == "EN_EJECUCION").order_by(Optimizacion.id_optimizacion)))

    def recover_historical(self, comparison_id):
        row = self.session.get(Optimizacion, comparison_id)
        if row.comparison_snapshot and row.comparison_snapshot.get("comparison_snapshot_version") == 1:
            return self.comparisons.reconcile_stopped(comparison_id).terminal
        return None

    def __exit__(self, exc_type, exc, traceback):
        from ..application.comparison_acceptance_v2 import SnapshotConflict
        def conflict(error):
            return isinstance(error, DBAPIError) and (getattr(error.orig, "sqlstate", None) in ("40001", "40P01")
                or getattr(error.orig, "sqlstate", None) == "23505" and getattr(
                    getattr(error.orig, "diag", None), "constraint_name", None) == "uq_optimizaciones_comparison_key")
        try:
            result = super().__exit__(exc_type, exc, traceback)
        except DBAPIError as error:
            if conflict(error): raise SnapshotConflict() from error
            raise
        if conflict(exc): raise SnapshotConflict() from exc
        return result
