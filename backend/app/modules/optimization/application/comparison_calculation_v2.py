"""B05 six-method supervisor body. Never closes the aggregate or releases a lease."""
from dataclasses import replace
import logging

from .comparison_contracts import ComparisonSignal
from .comparison_v2_contracts import ExecutionDiagnostic, ExecutionPayloadV2
from .engine_execution import ExecutionScope
from .errors import WorkersNotStopped

logger = logging.getLogger(__name__)


class CalculateComparisonV2:
    def __init__(self, unit_of_work, runner):
        self.unit_of_work, self.runner = unit_of_work, runner

    def execute(self, comparison_id, token, *, cancel=None, observer=None):
        observer_failed = False
        def emit(execution, kind, data):
            nonlocal observer_failed
            if observer is None or observer_failed:
                return
            try:
                observer(ComparisonSignal(comparison_id=comparison_id,
                    execution_id=execution.execution_id if execution else None,
                    method=execution.method if execution else None, kind=kind, payload=data))
            except Exception:
                observer_failed = True
                logger.exception("V2 observer disconnected; calculation continues")
        with self.unit_of_work() as tx:
            _, current = tx.comparisons_v2.require_supervisor(comparison_id, token)
        scopes = tuple(ExecutionScope(comparison_id=comparison_id,execution_id=e.execution_id,method=e.method)
                       for e in current.executions)
        stream = self.runner.events(scopes,current.problem,(current.minimum_width_mm,current.minimum_height_mm),
            cancel=cancel,retain_observations=False,lifecycle=True)
        try:
            for packet in stream:
                scope, kind, data = packet["scope"],packet["kind"],packet["data"]
                execution = next(e for e in current.executions if e.execution_id==scope.execution_id)
                if execution.method != scope.method:
                    raise ValueError("Execution identity changed")
                if kind == "observation":
                    emit(execution,kind,data)
                    continue
                if kind == "result":
                    payload = data.payload
                    statistics = {**payload.diagnostic.statistics,"runtime_dispatched":int(data.dispatched),
                                  "runtime_engine_started":int(data.engine_started)}
                    payload = replace(payload,diagnostic=replace(payload.diagnostic,statistics=statistics))
                    try:
                        with self.unit_of_work() as tx:
                            _, fresh = tx.comparisons_v2.require_supervisor(comparison_id,token)
                            saved = tx.comparisons_v2.save_execution(comparison_id,scope.execution_id,
                                payload,data.residuals,fresh.version)
                    except Exception:
                        logger.exception("V2 execution save failed; preserving other methods")
                        with self.unit_of_work() as tx:
                            _, fresh = tx.comparisons_v2.require_supervisor(comparison_id,token)
                            own = next(e for e in fresh.executions if e.execution_id==scope.execution_id)
                            saved = fresh
                            if own.status == "EN_EJECUCION":
                                saved = tx.comparisons_v2.save_execution(comparison_id,scope.execution_id,
                                    ExecutionPayloadV2(method=scope.method,result=None,diagnostic=ExecutionDiagnostic(
                                        origin="SUPERVISOR",termination_reason="RESULT_SAVE_FAILED",statistics=statistics)),(),fresh.version)
                    own = next(e for e in saved.executions if e.execution_id==scope.execution_id)
                    emit(execution,"result_persisted" if own.result is not None else "execution_failed",own)
                    continue
                with self.unit_of_work() as tx:
                    _, fresh = tx.comparisons_v2.require_supervisor(comparison_id,token)
                    execution = next(e for e in fresh.executions if e.execution_id==scope.execution_id)
                    if execution.method != scope.method:
                        raise ValueError("Execution identity changed")
                    if kind == "dispatching":
                        fresh = tx.comparisons_v2.record_worker(comparison_id,scope.execution_id,token,None)
                        tx.comparisons_v2.set_dispatch_state(comparison_id,scope.execution_id,"STARTING",fresh.version)
                    elif kind == "spawned":
                        tx.comparisons_v2.record_worker(comparison_id,scope.execution_id,token,data["identity"])
                    elif kind == "ready":
                        if data["input_sha256"] != current.input_sha256:
                            raise ValueError("Worker input differs from common snapshot")
                    elif kind == "started":
                        tx.comparisons_v2.set_dispatch_state(comparison_id,scope.execution_id,"RUNNING",fresh.version)
                    else:
                        raise ValueError("Unknown process event")
                # Leaving the UoW above committed. Final layout never masquerades as persistence.
                emit(execution,kind,data)
        finally:
            stream.close()
        if not self.runner.last_report or not self.runner.last_report["all_workers_stopped"]:
            raise WorkersNotStopped("V2 process closure remains unverified")
        return observer_failed


def fail_pending(unit_of_work, comparison_id, token, reason):
    """Used after a closed stream; existing durable results are never overwritten."""
    with unit_of_work() as tx:
        _, current = tx.comparisons_v2.require_supervisor(comparison_id,token)
        for execution in current.executions:
            if execution.status == "EN_EJECUCION":
                current = tx.comparisons_v2.save_execution(comparison_id,execution.execution_id,
                    ExecutionPayloadV2(method=execution.method,result=None,diagnostic=ExecutionDiagnostic(
                        origin="SUPERVISOR",termination_reason=reason,statistics={})),(),current.version)
        return current
