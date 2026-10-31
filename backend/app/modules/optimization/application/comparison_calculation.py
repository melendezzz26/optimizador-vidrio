"""Supervisor de producto: guardar cada motor y cerrar solo después del join.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
El consumidor de eventos no controla ni cancela el cálculo. Ninguna conexión DB
permanece abierta durante la búsqueda. La notificación de guardado sigue al commit.
"""
import logging
from uuid import uuid4

from .comparison_contracts import ComparisonSignal
from .errors import RunError, WorkersNotStopped

logger = logging.getLogger(__name__)


class CalculateComparison:
    def __init__(self, unit_of_work, runner):
        self.unit_of_work, self.runner = unit_of_work, runner

    def execute(self, comparison_id, on_event=None, *, lease=None, cancel=None):
        safe_to_release, claimed = True, False
        current, stream, observer_failed = None, None, False
        def emit(execution, kind, payload):
            nonlocal observer_failed
            if on_event is not None and not observer_failed:
                signal = ComparisonSignal(comparison_id=comparison_id,
                    execution_id=execution.execution_id if execution else None,
                    method=execution.method if execution else None, kind=kind, payload=payload)
                try:
                    on_event(signal)
                except Exception:
                    observer_failed = True
                    logger.exception("Comparison observer failed; calculation continues")
        try:
            with self.unit_of_work() as tx:
                current = tx.comparisons.get(comparison_id)
                claimed = tx.comparisons.claim_supervisor(comparison_id, uuid4().hex,
                    getattr(self.runner, "supervisor_identity", None))
            if not claimed:
                return current  # No recalcular un trabajo iniciado ni uno terminal.
            by_method = {e.method: e for e in current.executions}
            try:
                stream = self.runner.calculate(current.problem,
                    (current.minimum_width_mm, current.minimum_height_mm), cancel=cancel)
                for packet in stream:
                    execution = by_method[packet["method"]]
                    if packet["kind"] == "result":
                        calculated = packet["payload"]
                        try:
                            with self.unit_of_work() as tx:
                                saved = tx.comparisons.save_result(comparison_id, execution.execution_id,
                                    calculated.result, calculated.residuals)
                            emit(execution, "result_persisted", next(e for e in saved.executions
                                if e.execution_id == execution.execution_id))
                        except Exception:
                            logger.exception("Comparison result could not be saved")
                            with self.unit_of_work() as tx:
                                failed = tx.comparisons.fail_execution(comparison_id, execution.execution_id, "RESULT_SAVE_FAILED")
                            emit(execution, "failed", next(e for e in failed.executions if e.execution_id == execution.execution_id))
                    elif packet["kind"] == "failed":
                        with self.unit_of_work() as tx:
                            failed = tx.comparisons.fail_execution(comparison_id, execution.execution_id, packet["payload"]["code"])
                        emit(execution, "failed", next(e for e in failed.executions if e.execution_id == execution.execution_id))
                    else:
                        if packet["kind"] == "ready":
                            with self.unit_of_work() as tx:
                                tx.comparisons.record_worker(comparison_id, execution.execution_id, packet["payload"])
                        emit(execution, packet["kind"], packet["payload"])
            finally:
                if stream is not None:
                    stream.close()  # El runner termina/join también ante fallo de DB.
            with self.unit_of_work() as tx:
                current = tx.comparisons.get(comparison_id)
                for execution in current.executions:
                    if execution.status == "EN_EJECUCION":
                        tx.comparisons.fail_execution(comparison_id, execution.execution_id, "WORKER_STOPPED")
                current = tx.comparisons.finish_after_workers_stopped(comparison_id)
            emit(None, "comparison_finished", current)
            return current
        except WorkersNotStopped:
            safe_to_release = False
            raise
        except Exception as error:
            if claimed:
                code = "MEMORY_BUDGET_EXCEEDED" if isinstance(error, RunError) and error.code == "RESOURCE_UNAVAILABLE" else "EXECUTION_FAILED"
                with self.unit_of_work() as tx:
                    current = tx.comparisons.get(comparison_id)
                    for execution in current.executions:
                        if execution.status == "EN_EJECUCION":
                            tx.comparisons.fail_execution(comparison_id, execution.execution_id, code)
                    current = tx.comparisons.finish_after_workers_stopped(comparison_id)
                emit(None, "comparison_finished", current)
                return current
            raise
        finally:
            if lease is not None and safe_to_release:
                lease.release()
