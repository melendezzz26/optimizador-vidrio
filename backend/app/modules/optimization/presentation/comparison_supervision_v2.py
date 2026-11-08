"""B05 composition/lifecycle, deliberately no router or HTTP serialization."""
from collections import deque
from datetime import datetime, timezone
import logging
import os
from threading import Event, RLock, Thread, current_thread
import time
from uuid import uuid4

from ..application.comparison_acceptance_v2 import AcceptComparisonV2
from ..application.comparison_calculation_v2 import CalculateComparisonV2, fail_pending
from ..application.comparison_persistence_contracts import VisualReferenceV2
from ..application.errors import RunError, WorkersNotStopped
from ..application.visual import MAX_COMPARISON_EVENT_BYTES as MAX_EVENT_BYTES
from ..infrastructure.comparison_snapshot import canonical_json
from ..infrastructure.comparison_transport import unpack_visual
from ..infrastructure.process_lifecycle import process_identity
from ..infrastructure.sequential_runner import SequentialProcessRunner
from ..infrastructure.visual_store import InMemoryVisualStore
from ..infrastructure.run_snapshot import json_value

logger = logging.getLogger(__name__)


def authorize_actor(tx, actor_id):
    # Existing public RBAC factories/guard; no alternative permission rules.
    from app.modules.authentication.presentation.dependencies import get_user_reader, get_permission_reader, require_permission
    actor = get_user_reader(tx.session).find_by_id(actor_id)
    if actor is None or not actor.is_active:
        raise RunError("FORBIDDEN", "No tienes acceso a esta operación.")
    require_permission("optimization.execute")(user=actor,permission_reader=get_permission_reader(tx.session),db=None)


class SharedVisualStore(InMemoryVisualStore):
    def can_retain(self, session, charged):
        return sum(s.charged_bytes for s in self.contexts)+charged <= self.max_bytes


class SupervisedJob:
    def __init__(self, comparison, runner, uow, lease, sink):
        self.comparison, self.runner, self.uow, self.lease = comparison,runner,uow,lease
        self.token, self.identity = uuid4().hex, process_identity(os.getpid())
        self.cancel, self.closed = Event(), Event()
        self.thread = self.reaper = None
        self.unsafe, self.error_type, self.sink = False,None,sink
        self.safe_to_retire = False
        self.timeline, self.events, self.event_bytes = [],deque(),0
        self.lock = RLock()
        budget = runner.policy.budget
        self.store = SharedVisualStore(max_contexts=len(comparison.methods),max_bytes=budget.retained_visual_bytes)
        self.sessions = {e.execution_id:self.store.reserve() for e in comparison.executions}
        for session in self.sessions.values(): session.bind(comparison.comparison_id,comparison.problem.config.resolution_mm)
        self.event_limit = budget.retained_event_bytes

    def mark(self, kind):
        with self.lock: self.timeline.append(dict(kind=kind,monotonic=time.monotonic(),thread=current_thread().name))

    def accept(self, signal):
        data = signal.payload
        visual_fact = None
        with self.lock:
            if signal.kind == "observation":
                data = {**data,"fact":dict(data["fact"])}
                if data["kind"] == "visual":
                    fact = data.pop('decoded_visual', None)
                    if fact is None: fact = unpack_visual(data["fact"],self.comparison.problem)
                    visual_fact = fact
                    session = self.sessions[signal.execution_id]
                    previous = session.revision
                    piece = session.register("PIECE",fact.unit,fact.orientation) if fact.orientation is not None else None
                    material = session.material(fact.stock,fact.material_mask) if fact.material_mask is not None else None
                    if session.revision != previous:
                        references = tuple(VisualReferenceV2(comparison_id=signal.comparison_id,
                            execution_id=signal.execution_id,method=signal.method,mask_ref=ref) for ref in session.records)
                        with self.uow() as tx:
                            tx.comparisons_v2.save_supervised_visual_references(
                                signal.comparison_id,signal.execution_id,references,self.token)
                    if data["fact"].get("orientation") is not None:
                        data["fact"]["orientation"] = dict(rotation_deg=str(fact.orientation.rotation_deg),
                            geometry=json_value(fact.orientation.geometry),mask_ref=piece.reference if piece else None)
                    data["fact"]["material_mask"] = dict(mask_ref=material.reference) if material else None
            elif signal.kind in ("result_persisted","execution_failed"):
                self.mark(signal.kind)
                data = dict(status=data.status,complete=bool(data.result and data.result.complete),
                    diagnostic=data.diagnostic.public())
            if visual_fact is not None: self.record_visual(signal, data, visual_fact)
            else: self.record(signal, data)
        if self.sink is not None: self.sink(signal)

    def record(self, signal, data):
        """Single retention owner; B06 may project this slot into its wire envelope."""
        raw = canonical_json(dict(comparison_id=signal.comparison_id,execution_id=signal.execution_id,
            method=signal.method,kind=signal.kind,data=data),maximum_bytes=MAX_EVENT_BYTES).encode()
        self.events.append(raw); self.event_bytes += len(raw)
        while self.event_bytes > self.event_limit or len(self.events)>4096:
            self.event_bytes -= len(self.events.popleft())

    def record_visual(self, signal, data, fact):
        self.record(signal, data)

    def dispose(self):
        with self.lock:
            for session in self.sessions.values(): session.abort()
            self.events.clear(); self.event_bytes=0


class ComparisonV2Coordinator:
    """One web-process owner; shares the exact admission object with FF/v1."""
    def __init__(self, unit_of_work, admission, *, authorize=authorize_actor, runner_factory=SequentialProcessRunner,
                 retention=None, job_factory=None):
        self.uow, self.admission, self.authorize, self.runner_factory = unit_of_work,admission,authorize,runner_factory
        self.lock, self.job = RLock(),None
        self.recovery_lease, self.recovery_errors = None,{}
        self.retention = retention
        self.job_factory = job_factory

    def start(self, order_ids, actor_id, key, *, sink=None):
        order_ids = AcceptComparisonV2.validate_request(order_ids,actor_id,key)
        with self.lock:
            with self.uow() as tx:
                self.authorize(tx,actor_id)
                previous = tx.comparisons_v2.find_by_key(actor_id,key)
            if previous is not None:
                if previous.problem.order_ids != tuple(sorted(order_ids)):
                    raise RunError("STATE_CONFLICT", "La clave corresponde a otro lote.")
                if not previous.terminal and (self.job is None or self.job.comparison.comparison_id != previous.comparison_id):
                    self.recover_pending()
                return previous
            lease = self.admission.acquire_comparison(actor_id)
            accepted = None
            try:
                runner = self.runner_factory(); runner.preflight()
                if self.job is not None:
                    if not self.job.closed.is_set(): raise WorkersNotStopped("Previous owner has not closed")
                accepted = AcceptComparisonV2(self.uow,self.authorize).execute(order_ids,actor_id,key)
                if self.job is not None:
                    self.job.dispose()
                job = (self.job_factory or SupervisedJob)(accepted,runner,self.uow,lease,sink)
                self.job = job
                with self.uow() as tx:
                    if not tx.comparisons_v2.claim_supervisor(accepted.comparison_id,job.token,job.identity):
                        raise RunError("STATE_CONFLICT", "La comparación ya tiene supervisor.")
                if self.retention is not None:
                    self.retention.replace(job)
                def work():
                    job.mark("supervisor_started")
                    try:
                        CalculateComparisonV2(self.uow,runner).execute(accepted.comparison_id,job.token,
                            cancel=job.cancel,observer=job.accept)
                    except Exception as error:
                        job.error_type=type(error).__name__
                        job.unsafe=isinstance(error,WorkersNotStopped)
                        logger.exception("V2 supervisor stopped with an error")
                    finally: job.mark("supervisor_returning")
                job.thread=Thread(target=work,name=f"comparison-v2-supervisor-{accepted.comparison_id}",daemon=True)
                job.thread.start()
                job.reaper=Thread(target=self._reap,args=(job,),name=f"comparison-v2-owner-{accepted.comparison_id}",daemon=True)
                job.reaper.start()
                return accepted
            except BaseException:
                if self.job is not None and self.job.lease is lease:
                    job=self.job
                    if job.thread is not None and job.thread.is_alive():
                        job.cancel.set()  # Keep lease; external recovery/shutdown must reap.
                    else:
                        self._close(job)
                elif accepted is None:
                    lease.release()
                else:
                    # Acceptance committed but allocating its local owner failed.
                    # Keep the reservation until durable ownership can be resolved.
                    self.recovery_lease = lease
                    self.recovery_errors = {accepted.comparison_id: "UnclaimedAcceptedComparison"}
                raise

    def _reap(self, job):
        job.thread.join()
        self._close(job)

    def reconcile(self, identifier):
        """B06 read/recovery port; delegates exclusively to the verified B05 owner."""
        with self.lock:
            job = self.job
            if job is not None and job.comparison.comparison_id == identifier:
                if job.thread is not None and job.thread.is_alive():
                    return True
                return self._close(job)
            return self.recover_pending()

    def _close(self, job):
        with self.lock:
            if job.closed.is_set(): return True
            if job.thread is not None and (job.thread is current_thread() or job.thread.is_alive()): return False
            job.mark("supervisor_joined")
            report=job.runner.last_report
            if report is not None and not report.get("all_workers_stopped"):
                job.unsafe=True; return False
            try:
                with self.uow() as tx:
                    _, current=tx.comparisons_v2.require_supervisor(job.comparison.comparison_id,job.token)
                known=current.runtime['workers']
                for execution_id, worker in known.items():
                    if worker is None:
                        state=(report or {}).get('executions',{})
                        own=next((s for s in state.values() if s['scope']['execution_id']==int(execution_id)),None)
                        if own is None: raise WorkersNotStopped("Unregistered spawn remains ambiguous")
                        if own.get('dispatched'):
                            actual=own.get('identity')
                            if actual is None or process_identity(actual['pid'])==actual:
                                raise WorkersNotStopped("Unregistered spawn remains ambiguous")
                            with self.uow() as tx:
                                tx.comparisons_v2.record_worker(current.comparison_id,int(execution_id),job.token,actual)
                    elif process_identity(worker['pid'])==dict(worker): raise WorkersNotStopped("Worker is still alive")
                job.mark("processes_verified")
                fail_pending(self.uow,current.comparison_id,job.token,"RESULT_SAVE_FAILED" if job.error_type else "WORKER_STOPPED")
                with self.uow() as tx:
                    _, current=tx.comparisons_v2.require_supervisor(current.comparison_id,job.token)
                    if not current.terminal:
                        tx.orders.transition(current.problem.order_ids,"EN_OPTIMIZACION",
                            "OPTIMIZADO" if any(e.eligible for e in current.executions) else "PENDIENTE")
                        current=tx.comparisons_v2.record_supervisor_stopped(current.comparison_id,
                            datetime.now(timezone.utc),current.version)
                job.comparison=current; job.mark("safe_close_committed")
                for session in job.sessions.values(): session.finish()
                job.safe_to_retire=True
                job.lease.release(); job.mark("admission_released")
                job.unsafe=False; job.closed.set()
                return True
            except Exception as error:
                job.unsafe=True; job.error_type=type(error).__name__
                logger.exception("V2 closure uncertain: admission remains reserved")
                return False

    def shutdown(self):
        job=self.job
        if job is None: return
        job.cancel.set()
        if job.thread is not None and job.thread is not current_thread(): job.thread.join(timeout=15)
        self._close(job)
        if job.reaper is not None and job.reaper is not current_thread(): job.reaper.join(timeout=15)

    def recover_pending(self):
        """No recalculation or killing. Unknown identities keep global admission blocked."""
        with self.lock:
            if self.recovery_lease is None:
                self.recovery_lease=self.admission.acquire_comparison(0)
            try:
                with self.uow() as tx: identifiers=tx.unfinished()
                if identifiers:
                    self.runner_factory().preflight()  # No PID proof on an unsupported platform.
            except Exception as error:
                self.recovery_errors={0:type(error).__name__}
                logger.exception("Recovery cannot read durable ownership: admission remains reserved")
                return False
            errors={}
            for identifier in identifiers:
                try:
                    with self.uow() as tx:
                        historical = tx.recover_historical(identifier)
                        if historical is not None:
                            if not historical: raise WorkersNotStopped("Historical owner remains unverified")
                            continue
                        current=tx.comparisons_v2.get(identifier)
                    owner=current.runtime.get('supervisor')
                    if owner is None or process_identity(owner['identity']['pid'])==dict(owner['identity']):
                        raise WorkersNotStopped("Owner is alive or unknown")
                    for worker in current.runtime['workers'].values():
                        if worker is None or process_identity(worker['pid'])==dict(worker):
                            raise WorkersNotStopped("Worker identity is alive or ambiguous")
                    if current.runtime['workers']:
                        # The previous process' join report is gone. Dead root PIDs
                        # cannot exclude unregistered/orphaned descendants after a crash.
                        raise WorkersNotStopped("Restart requires external descendant-closure evidence")
                    fail_pending(self.uow,identifier,owner['token'],"WORKER_STOPPED")
                    with self.uow() as tx:
                        _, current=tx.comparisons_v2.require_supervisor(identifier,owner['token'])
                        tx.orders.transition(current.problem.order_ids,"EN_OPTIMIZACION",
                            "OPTIMIZADO" if any(e.eligible for e in current.executions) else "PENDIENTE")
                        tx.comparisons_v2.record_supervisor_stopped(identifier,datetime.now(timezone.utc),current.version)
                except Exception as error: errors[identifier]=type(error).__name__
            self.recovery_errors=errors
            if not errors:
                self.recovery_lease.release(); self.recovery_lease=None
            return not errors


_coordinator=None


def get_comparison_v2_coordinator():
    global _coordinator
    if _coordinator is None:
        from app.shared.database.session import SessionLocal
        from ..infrastructure.comparison_v2_uow import SqlComparisonPersistenceUnitOfWork
        from .run_routes import get_run_admission
        from .comparison_retention import COMPARISON_RETENTION
        from .comparison_http_runtime_v2 import HttpComparisonJob
        _coordinator=ComparisonV2Coordinator(lambda:SqlComparisonPersistenceUnitOfWork(SessionLocal),get_run_admission(),
            retention=COMPARISON_RETENTION, job_factory=HttpComparisonJob)
    return _coordinator
