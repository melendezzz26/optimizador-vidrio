"""Observación acotada independiente del visor HTTP.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
Composición del supervisor, proyección visual y transporte; no busca colocaciones.
"""
from collections import deque
from itertools import islice
from datetime import datetime, timezone
from decimal import Decimal
import logging
from threading import Condition, Event, RLock, Thread
import time

from ..application.admission import OptimizerBusy
from ..application.comparison_calculation import CalculateComparison
from ..application.errors import RunError, WorkersNotStopped
from ..application.visual import MAX_EVENT_BYTES
from ..domain.problem import Placement
from ..infrastructure.visual_store import InMemoryVisualStore
from ..infrastructure.comparison_runner import ComparisonProcessRunner
from ..infrastructure.process_lifecycle import process_identity
from .comparison_schemas import ComparisonEvent, ComparisonMask
from .comparison_serialization import execution_summary, plain
from .run_serialization import unit_reference, stock_response, placement_response, progress_response
from .visual_serialization import VisualProjection, describe_record

logger = logging.getLogger(__name__)


class ComparisonVisualStore(InMemoryVisualStore):
    def can_retain(self, session, charged):
        return sum(s.charged_bytes for s in self.contexts) + charged <= self.max_bytes


class ComparisonJob:
    def __init__(self, budget):
        self.budget = budget
        self.store = ComparisonVisualStore(max_contexts=3, max_bytes=budget.retained_visual_bytes)
        self.sessions = {method: self.store.reserve() for method in ("FF", "BF", "WF")}
        self.condition = Condition(self.store.lock)
        self.records, self.record_bytes, self.sequence = deque(), 0, 0
        self.method_sequences = {method: 0 for method in self.sessions}
        self.orders = {method: [] for method in self.sessions}
        self.current = {method: None for method in self.sessions}
        self.last_orientation = {method: None for method in self.sessions}
        self.phases = {method: "PREPARING" for method in self.sessions}
        self.group_bases = {method: {} for method in self.sessions}
        self.finished, self.finished_at, self.unsafe = False, None, False
        self.thread, self.runner = None, None
        self.observers = 0
        self.cancel = Event()
        self.comparison = None

    def bind(self, comparison):
        self.comparison = comparison
        self.by_method = {e.method: e for e in comparison.executions}
        self.units = {(u.piece_id, u.unit_index): u for u in comparison.problem.units}
        self.stocks = {(s.source.value, s.material_id, s.physical_unit_index): s
                       for g in comparison.problem.groups for s in g.stock_candidates}
        self.group_totals = {g.key: len(g.units) for g in comparison.problem.groups}
        self.projections = {}
        for method, session in self.sessions.items():
            session.bind(comparison.comparison_id, comparison.problem.config.resolution_mm)
            self.projections[method] = VisualProjection(session, lambda kind, data, m=method: self.project(m, kind, data))
        self.emit(None, "comparison_accepted", {"version": comparison.version,
            "executions": [{"execution_id": e.execution_id, "method": e.method} for e in comparison.executions]})

    def envelope(self, method, kind, data, sequence, execution_sequence=None):
        return ComparisonEvent(comparison_id=self.comparison.comparison_id, sequence=sequence,
            execution_id=self.by_method[method].execution_id if method else None, method=method,
            execution_sequence=execution_sequence, timestamp=datetime.now(timezone.utc), event=kind, data=plain(data))

    def emit(self, method, kind, data):
        with self.condition:
            seq = self.sequence + 1
            method_seq = self.method_sequences[method] + 1 if method else None
            raw = self.envelope(method, kind, data, seq, method_seq).model_dump_json().encode() + b"\n"
            if len(raw) > MAX_EVENT_BYTES:
                raise RunError("INTERNAL_ERROR", "El evento visual excede su presupuesto.")
            self.sequence = seq
            if method:
                self.method_sequences[method] = method_seq
            self.records.append((seq, raw))
            self.record_bytes += len(raw)
            while self.record_bytes > self.budget.retained_event_bytes or len(self.records) > 4096:
                _, removed = self.records.popleft()
                self.record_bytes -= len(removed)
            self.condition.notify_all()

    def descriptor(self, method, data):
        return ComparisonMask(**data, comparison_id=self.comparison.comparison_id,
            execution_id=self.by_method[method].execution_id, method=method).model_dump(mode="json")

    def project(self, method, kind, data):
        data = dict(data)
        if "metodo" in data:
            data["metodo"] = method
        for name in ("mask", "material_mask"):
            if name in data:
                data[name] = self.descriptor(method, data[name])
        if kind in ("piece_rasterizing", "piece_ready", "orientation_testing", "source_selected", "piece_unplaced"):
            self.current[method] = plain({**data, "kind": kind})
        if kind in ("orientation_testing", "source_selected", "piece_unplaced"):
            self.phases[method] = "CALCULATING"
        if kind in ("orientation_testing", "source_selected"):
            self.last_orientation[method] = plain({**data, "kind": kind})
        self.emit(method, kind, data)

    def accept(self, signal):
        with self.condition:
            method, kind, data = signal.method, signal.kind, signal.payload
            if kind == "comparison_finished":
                self.comparison = data
                self.emit(None, kind, {"version": data.version, "status": data.status, "incomplete": data.incomplete})
            elif kind == "ready":
                self.emit(method, "engine_ready", {})
            elif kind == "started":
                self.emit(method, "engine_started", {})
            elif kind == "visual":
                if data.kind == "ordering_ready":
                    self.orders[method] = [unit_reference(u) for u in data.ordered_units]
                    self.phases[method] = "ORDERING"
                    self.emit(method, "ordering_ready", {"criterion": "area_desc_max_side_desc_order_piece_unit_asc",
                                                          "units": self.orders[method]})
                else:
                    self.projections[method](data)
            elif kind == "milestone":
                self.milestone(method, data)
            elif kind == "result_persisted":
                self.phases[method] = "RESULT"
                self.emit(method, kind, execution_summary(self.comparison, data).model_dump(mode="json"))
            elif kind == "failed":
                self.phases[method] = "FAILED"
                self.emit(method, "execution_failed", {"code": data.failure_code})

    def milestone(self, method, data):
        kind, key = data["kind"], (data["group_key"][0], Decimal(data["group_key"][1]))
        progress = progress_response(data["placed_units"], data["total_units"])
        if kind == "group_started":
            self.group_bases[method][key] = data["placed_units"]
            body = dict(id_tipo_vidrio=key[0], espesor_mm=key[1], total_units=self.group_totals[key])
        elif kind == "group_completed":
            body = dict(id_tipo_vidrio=key[0], espesor_mm=key[1], **progress_response(
                data["placed_units"] - self.group_bases[method][key], self.group_totals[key]))
            body["result_url"] = f"/api/optimization/comparisons/{self.comparison.comparison_id}/executions/{self.by_method[method].execution_id}"
        else:
            u = data["unit"]
            unit = self.units[(u["piece_id"], u["unit_index"])]
            body = dict(**unit_reference(unit), **progress, processed_units=self.sessions[method].processed)
            if kind == "piece_placed":
                p = data["placement"]
                s = p["stock"]
                stock = self.stocks[(s["source"], s["material_id"], s["physical_unit_index"])]
                placement = Placement(piece=unit, stock=stock, geometry=p["geometry"],
                    **{k: Decimal(p[k]) for k in ("x_mm", "y_mm", "rotation_deg")})
                body.update(placement_response(placement, self.comparison.problem.config).model_dump(), material=stock_response(stock))
        self.emit(method, kind, body)

    def session(self, execution_id):
        execution = next((e for e in self.by_method.values() if e.execution_id == execution_id), None)
        if execution is None:
            raise RunError("NOT_FOUND", "La ejecución no pertenece a esta comparación.")
        return execution.method, self.sessions[execution.method]

    def manifest(self, execution_id, offset):
        with self.condition:
            method, session = self.session(execution_id)
            items, total, next_offset = session.manifest(offset)
            return dict(profile="comparison-v1", schema_version=1, comparison_id=self.comparison.comparison_id,
                execution_id=execution_id, method=method, revision=session.revision,
                execution_sequence=self.method_sequences[method],
                preparation_completed=session.preparation_completed, processed_units=session.processed,
                evaluations=session.evaluations, phase=self.phases[method], current=self.current[method],
                last_orientation=self.last_orientation[method],
                ordered_units=plain(self.orders[method]), total=total, next_offset=next_offset,
                items=[self.descriptor(method, describe_record(session, r)) for r in items])

    def check_cursor(self, cursor):
        with self.condition:
            if cursor > self.sequence:
                raise RunError("INVALID_INPUT", "El cursor está por delante del trabajo.")
            if self.records and cursor < self.records[0][0] - 1:
                raise RunError("EVENT_CURSOR_EXPIRED", "El avance anterior ya no está retenido. Recupera el estado guardado.",
                               details={"latest_sequence": self.sequence})

    def observe(self):
        with self.condition:
            if self.observers >= 2:
                raise RunError("OPTIMIZER_BUSY", "Ya hay dos vistas de avance abiertas para este trabajo.")
            self.observers += 1
            return Observation(self)

    def lines(self, cursor, observer=None):
        while observer is None or not observer.closed:
            with self.condition:
                if self.records and cursor < self.records[0][0] - 1:
                    cursor = self.sequence
                    batch = [(cursor, self.envelope(None, "snapshot_required", {"latest_sequence": cursor}, cursor).model_dump_json().encode() + b"\n")]
                else:
                    batch = list(islice(((seq, raw) for seq, raw in self.records if seq > cursor), 16))
                if not batch:
                    if self.finished:
                        return
                    notified = self.condition.wait(timeout=10)
                    if notified:
                        continue
                    batch = [(cursor, self.envelope(None, "heartbeat", {}, max(1, cursor)).model_dump_json().encode() + b"\n")]
            for seq, raw in batch:
                cursor = seq
                yield raw

    def finish(self):
        with self.condition:
            for session in self.sessions.values():
                session.finish()
            self.finished, self.finished_at = True, time.monotonic()
            self.condition.notify_all()

    def dispose(self):
        with self.condition:
            for session in self.sessions.values():
                session.abort()
            self.records.clear()
            self.record_bytes = 0
            self.condition.notify_all()


class ComparisonRuntime:
    def __init__(self, runner_factory=ComparisonProcessRunner):
        self.runner_factory, self.lock, self.job = runner_factory, RLock(), None

    def reserve(self):
        with self.lock:
            if self.job is not None:
                if not self.job.finished:
                    raise OptimizerBusy("active_runs", 1, 1)
                with self.job.uow() as tx:
                    tx.comparisons.reconcile_stopped(self.job.comparison.comparison_id, supervisor_stopped=True)
                self.job.dispose()
                self.job = None
            runner = self.runner_factory()
            runner.preflight()
            self.job = ComparisonJob(runner.budget)
            self.job.runner = runner
            return self.job

    def abort(self, job):
        with self.lock:
            job.dispose()
            if self.job is job:
                self.job = None

    def start(self, job, comparison, uow, lease):
        job.bind(comparison)
        job.lease = lease
        job.uow = uow
        def work():
            safe = True
            try:
                CalculateComparison(uow, job.runner).execute(comparison.comparison_id, job.accept, cancel=job.cancel)
            except WorkersNotStopped:
                safe, job.unsafe = False, True
                logger.exception("Comparison termination requires reconciliation")
            except Exception:
                logger.exception("Comparison supervisor requires persisted-state reconciliation")
            finally:
                if safe:
                    job.finish()
                    lease.release()
        job.thread = Thread(target=work, name=f"comparison-supervisor-{comparison.comparison_id}", daemon=True)
        job.thread.start()

    def get(self, comparison_id):
        with self.lock:
            if (self.job is None or self.job.comparison is None or self.job.comparison.comparison_id != comparison_id
                    or self.job.finished_at is not None and time.monotonic() - self.job.finished_at >= 300):
                raise RunError("VISUAL_DATA_UNAVAILABLE", "El avance visual ya no está retenido. El resultado guardado se conserva.")
            return self.job

    def stopped(self, comparison_id):
        with self.lock:
            job = self.job
            if job is None or job.comparison is None or job.comparison.comparison_id != comparison_id:
                return False
        if job.thread is not None and job.thread.is_alive():
            return False
        if job.unsafe:
            owned = (job.runner.last_report or {}).get("owned_processes", {})
            if not owned:
                return False
            for identity in owned.values():
                actual = process_identity(identity["pid"])
                if actual is not None and (identity["start_ticks"] is None or actual == identity):
                    return False
            job.unsafe = False
            job.finish()
            job.lease.release()
        return job.finished

    def shutdown(self):
        job = self.job
        if job and job.thread and job.thread.is_alive():
            job.cancel.set()
            job.thread.join(timeout=15)


class Observation:
    def __init__(self, job):
        self.job, self.closed = job, False

    def release(self):
        with self.job.condition:
            if not self.closed:
                self.closed = True
                self.job.observers -= 1
                self.job.condition.notify_all()
