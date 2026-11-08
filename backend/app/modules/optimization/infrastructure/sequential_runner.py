"""TA-043/B04: one bounded spawn worker at a time; no DB, lease or HTTP lifecycle.

    The internal owner must drain/close events even with no browser. An independent
    watchdog enforces wall deadlines/RSS even while the consumer is stalled. B05
    must certify its own supervisor termination before releasing shared admission.
"""
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
import json
import logging
import multiprocessing as mp
import os
import signal
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread, Lock
import time

from ..application.comparison_catalog import METHODS_V2
from ..application.comparison_v2_contracts import ExecutionDiagnostic, ExecutionPayloadV2
from ..application.engine_execution import ExecutionScope
from ..application.errors import RunError, WorkersNotStopped
from ..application.sequential_policy import SequentialPolicy, ObservationRetention
from ..domain.metrics import ResidualRectangle
from .comparison_runner import check_environment, resident_bytes, _reader
from .comparison_snapshot import canonical_json, encode_problem, problem_fingerprint
from .comparison_transport import VisualDecoder
from .comparison_v2_snapshot import decode_result_v3
from .process_lifecycle import process_identity
from .sequential_worker import calculation_worker_v2

logger = logging.getLogger(__name__)


def resource_statistics(report, state, budget):
    """Small, durable counters. Never include input geometry, credentials or PIDs."""
    return dict(runtime_supervisor_peak_rss_bytes=report['supervisor_peak_rss'],
        runtime_worker_peak_rss_bytes=state.get('peak_rss', 0),
        runtime_worker_peak_virtual_bytes=state.get('peak_virtual', 0),
        runtime_aggregate_peak_rss_bytes=report['maximum_aggregate_rss'],
        runtime_supervisor_limit_bytes=budget.supervisor_rss_bytes,
        runtime_worker_address_limit_bytes=budget.worker_address_bytes,
        runtime_aggregate_limit_bytes=budget.aggregate_rss_bytes,
        runtime_limit_supervisor_rss=int(report.get('limit_supervisor_rss', False)),
        runtime_limit_aggregate_rss=int(report.get('limit_aggregate_rss', False)),
        runtime_worker_allocation_failed=int(state.get('allocation_failed', False)),
        runtime_not_started_global=int(bool(report.get('global_reason')) and not state.get('engine_started', False)))


def with_resources(terminal, report, state, budget):
    statistics = {**terminal.payload.diagnostic.statistics, **resource_statistics(report, state, budget)}
    return replace(terminal, payload=replace(terminal.payload, diagnostic=replace(
        terminal.payload.diagnostic, statistics=statistics)))


@dataclass(frozen=True, kw_only=True)
class ProcessExecution:
    scope: ExecutionScope
    payload: ExecutionPayloadV2
    residuals: tuple[ResidualRectangle, ...] = ()
    dispatched: bool = False
    engine_started: bool = False

    @property
    def never_started(self):
        return not self.engine_started


def failed(scope, reason, *, dispatched=False, engine_started=False):
    return ProcessExecution(scope=scope, payload=ExecutionPayloadV2(method=scope.method, result=None,
        diagnostic=ExecutionDiagnostic(origin="SUPERVISOR", termination_reason=reason, statistics={})),
        dispatched=dispatched, engine_started=engine_started)


def descendants(pid):
    owned, pending = {}, [pid]
    while pending:
        parent = pending.pop()
        try:
            children = Path(f"/proc/{parent}/task/{parent}/children").read_text().split()
        except FileNotFoundError:
            continue
        for value in children:
            identifier = int(value)
            identity = process_identity(identifier)
            if identity is not None and identifier not in owned:
                owned[identifier] = identity
                pending.append(identifier)
    return owned


def signal_owned(identities, sig):
    for pid, identity in identities.items():
        if process_identity(pid) == identity:
            try: os.kill(pid, sig)
            except ProcessLookupError: pass


class SequentialProcessRunner:
    def __init__(self, policy=SequentialPolicy(), *, worker_target=calculation_worker_v2):
        self.policy, self.worker_target = policy, worker_target
        self.last_report = None
        self.retention = None
        self._active = Lock()

    def preflight(self):
        check_environment(self.policy.budget)

    def calculate(self, scopes, problem, minimums, **kwargs):
        stream = self.events(scopes, problem, minimums, **kwargs)
        try:
            return tuple(packet["data"] for packet in stream if packet["kind"] == "result")
        finally:
            stream.close()

    def events(self, *args, **kwargs):
        if not self._active.acquire(blocking=False):
            raise RunError("OPTIMIZER_BUSY", "Esta primitiva ya tiene una secuencia activa.")
        previous_report = self.last_report
        try:
            yield from self._events(*args, **kwargs)
        finally:
            # This is only an instance guard, never the shared application lease.
            # Keep it closed if any owned process/thread could not be stopped.
            if self.last_report is previous_report or self.last_report["all_workers_stopped"]:
                self._active.release()

    def _events(self, scopes, problem, minimums, *, cancel=None, observed=True, retain_observations=True, lifecycle=False):
        scopes = tuple(scopes)
        if (len(scopes) != 6 or any(not isinstance(s, ExecutionScope) for s in scopes)
            or tuple(s.method for s in scopes) != METHODS_V2 or len({s.comparison_id for s in scopes}) != 1
            or len({s.execution_id for s in scopes}) != 6):
            raise ValueError("Runner requires the owned ordered six-execution scope")
        if type(observed) is not bool or type(retain_observations) is not bool or type(lifecycle) is not bool:
            raise ValueError("Observation flag must be explicit boolean")
        self.preflight()
        budget, context = self.policy.budget, mp.get_context("spawn")
        began = time.monotonic()
        payload = canonical_json(encode_problem(problem), maximum_bytes=budget.packet_bytes)
        expected_hash = problem_fingerprint(problem)
        minimums = tuple(str(v) for v in minimums)
        if len(minimums) != 2 or any(not Decimal(v).is_finite() or Decimal(v) < 0 for v in minimums):
            raise ValueError("Frozen residual thresholds are required")
        self.retention = ObservationRetention(budget)
        report = dict(maximum_active_workers=0, maximum_queued_packets=0, maximum_packet_bytes=0,
            maximum_aggregate_rss=0, supervisor_peak_rss=0, maximum_worker_virtual=0, samples=0,
            maximum_sample_gap_ms=0, budget=asdict(budget), all_workers_stopped=False,
            global_reason=None, executions={s.method: dict(scope=asdict(s), state="QUEUED", dispatched=False,
            engine_started=False, identity=None) for s in scopes})
        self.last_report = report
        abort = None
        cleanup_verified = True
        try:
            for scope in scopes:
                if abort is None:
                    abort = ("CANCELLED" if cancel is not None and cancel.is_set() else
                             "GLOBAL_TIME_LIMIT" if time.monotonic()-began >= budget.global_seconds else None)
                state = report["executions"][scope.method]
                if abort:
                    report["global_reason"] = abort
                    state.update(state="TERMINATED", reason=abort)
                    yield dict(scope=scope, kind="result", data=with_resources(failed(scope, abort), report, state, budget))
                    continue
                receiving, sending = context.Pipe(duplex=False)
                gate, started_clock = context.Event(), context.Value('d', 0)
                checkpoint_cancel = context.Event()
                owned_descendants = {}
                channel, stop = Queue(maxsize=budget.queued_packets_per_worker), Event()
                process = context.Process(target=self.worker_target, name=f"comparison-v2-{scope.method}", args=(
                    asdict(scope), payload, minimums, sending, gate, started_clock, budget, checkpoint_cancel,
                    process_identity(os.getpid()), observed))
                launched, reason = time.monotonic(), []
                state["launched_monotonic"] = launched
                state["queue_ms"] = (launched-began)*1000
                finished = None
                reader = monitor = None
                ready, terminal = False, None
                visual_decoder = VisualDecoder(problem)
                cleanup_verified = False
                def enforce():
                    last = time.monotonic()
                    while not stop.wait(.025):
                        now = time.monotonic()
                        report["maximum_sample_gap_ms"] = max(report["maximum_sample_gap_ms"],(now-last)*1000)
                        last = now
                        code = self.policy.expired(now, began, launched, started_clock.value)
                        global_stop = code == "GLOBAL_TIME_LIMIT"
                        if cancel is not None and cancel.is_set(): code, global_stop = "CANCELLED", True
                        try:
                            parent_rss = resident_bytes(os.getpid())
                            worker_rss = resident_bytes(process.pid)
                            owned_descendants.update(descendants(process.pid))
                            state["descendants"] = list(owned_descendants.values())
                            virtual = int(Path(f"/proc/{process.pid}/statm").read_text().split()[0])*os.sysconf("SC_PAGE_SIZE")
                            total = parent_rss + worker_rss + sum(resident_bytes(pid) for pid, identity in
                                owned_descendants.items() if process_identity(pid)==identity) + budget.helper_reserve_bytes
                            state["peak_rss"] = max(state.get("peak_rss",0),worker_rss)
                            state["peak_virtual"] = max(state.get("peak_virtual",0),virtual)
                            report["supervisor_peak_rss"] = max(report["supervisor_peak_rss"],parent_rss)
                            report["maximum_worker_virtual"] = max(report["maximum_worker_virtual"],virtual)
                            report["maximum_aggregate_rss"] = max(report["maximum_aggregate_rss"],total)
                            report["maximum_queued_packets"] = max(report["maximum_queued_packets"],channel.qsize())
                            report["samples"] += 1
                            if total > budget.aggregate_rss_bytes or parent_rss > budget.supervisor_rss_bytes:
                                if code is None:
                                    report['limit_supervisor_rss'] = parent_rss > budget.supervisor_rss_bytes
                                    report['limit_aggregate_rss'] = total > budget.aggregate_rss_bytes
                                    report['memory_at_stop'] = dict(supervisor_rss_bytes=parent_rss,
                                        worker_rss_bytes=worker_rss, worker_virtual_bytes=virtual, aggregate_rss_bytes=total)
                                    code, global_stop = "MEMORY_BUDGET_EXCEEDED", True
                        except (FileNotFoundError, ProcessLookupError):
                            pass
                        except (OSError, ValueError):
                            code, global_stop = "WORKER_STOPPED", True
                        if code:
                            state["limit_detected_monotonic"] = now
                            checkpoint_cancel.set()
                            reason.append((code,global_stop))
                            if global_stop:
                                report["global_reason"] = code
                                for pending in report["executions"].values():
                                    if pending["state"] == "QUEUED": pending.update(state="TERMINATED",reason=code)
                            if process.is_alive(): process.terminate()
                            return
                try:
                    if lifecycle: yield dict(scope=scope,kind="dispatching",data={})
                    launched = time.monotonic()  # The global clock still includes intent persistence.
                    process.start()
                    state.update(state="STARTING",dispatched=True,identity=process_identity(process.pid))
                    report["maximum_active_workers"] = max(report["maximum_active_workers"],int(process.is_alive()))
                    sending.close()
                    reader = Thread(target=_reader,args=(receiving,channel,stop,budget.packet_bytes),daemon=True)
                    monitor = Thread(target=enforce,daemon=True)
                    reader.start(); monitor.start()
                    if lifecycle: yield dict(scope=scope,kind="spawned",data=dict(identity=state["identity"]))
                    while terminal is None:
                        if reason:
                            code, global_stop = reason[0]
                            finished = state["limit_detected_monotonic"]
                            if global_stop: abort = code
                            terminal = failed(scope,code,dispatched=True,engine_started=bool(started_clock.value))
                            break
                        try:
                            raw = channel.get(timeout=.01)
                        except Empty:
                            continue
                        if reason:
                            continue  # The watchdog's cause precedes EOF or a queued packet.
                        try:
                            if raw is None: raise ValueError("Worker disconnected")
                            report["maximum_packet_bytes"] = max(report["maximum_packet_bytes"],len(raw))
                            packet = json.loads(raw)
                            if (set(packet) != {"scope","kind","data"} or ExecutionScope(**packet["scope"]) != scope
                                or not isinstance(packet["data"],dict)):
                                raise ValueError("Worker scope/protocol mismatch")
                            kind, data = packet["kind"], packet["data"]
                            if kind == "ready":
                                if ready or data["identity"] != state["identity"] or data["input_sha256"] != expected_hash:
                                    raise ValueError("Worker identity/input mismatch")
                                ready = True
                                state["startup_ms"] = (time.monotonic()-launched)*1000
                                if not lifecycle: gate.set()
                                yield dict(scope=scope,kind=kind,data=data)
                                if lifecycle: gate.set()  # B05 committed identity/hash before engine start.
                            elif kind == "failed":
                                state['allocation_failed'] = data.get('code') == 'MEMORY_BUDGET_EXCEEDED'
                                terminal = failed(scope,data["code"],dispatched=True,engine_started=bool(started_clock.value))
                            elif not ready:
                                raise ValueError("Worker not ready")
                            elif kind == "started":
                                if state["engine_started"] or not started_clock.value or data["monotonic"] != started_clock.value:
                                    raise ValueError("Worker start mismatch")
                                state.update(state="RUNNING",engine_started=True)
                                yield dict(scope=scope,kind=kind,data=data)
                            elif kind == "observation":
                                if not started_clock.value or len(raw)>budget.visual_packet_bytes:
                                    raise ValueError("Invalid visual packet")
                                if data["kind"] == "visual":
                                    data = {**data, 'decoded_visual': visual_decoder.unpack(data['fact'])}
                                elif data["kind"] not in ("milestone","search_progress"):
                                    raise ValueError("Invalid observation type")
                                if scope.method == "M6-BS" and (data["kind"] != "search_progress" or data["presentation"] != "PROVISIONAL"):
                                    raise ValueError("Exploratory placements are not final")
                                if retain_observations:
                                    self.retention.append("visual" if data["kind"]=="visual" else "event",scope,raw)
                                yield dict(scope=scope,kind=kind,data=data)
                            elif kind == "result":
                                finished = time.monotonic()
                                value = decode_result_v3(data["snapshot"],expected_method=scope.method)
                                if not started_clock.value or value.result is not None and value.result.problem != problem:
                                    raise ValueError("Result belongs to another input")
                                residuals = tuple(ResidualRectangle(**{k:Decimal(v) if k in (
                                    "x_mm","y_mm","width_mm","height_mm","area_mm2") else v
                                    for k,v in item.items()}) for item in data["residuals"])
                                state["worker_report"] = {k:v for k,v in data.items() if k not in ("snapshot","residuals")}
                                state['allocation_failed'] = data.get('error_type') == 'MemoryError'
                                terminal = ProcessExecution(scope=scope,payload=value,residuals=residuals,
                                    dispatched=True,engine_started=True)
                            else: raise ValueError("Unknown worker packet")
                        except (ValueError,TypeError,KeyError,ArithmeticError):
                            code, global_stop = reason[0] if reason else ("EXECUTION_FAILED",False)
                            if global_stop: abort = code
                            terminal = failed(scope,code,dispatched=True,engine_started=bool(started_clock.value))
                except (OSError,RuntimeError) as error:
                    state["error_type"] = type(error).__name__
                    terminal = failed(scope,"PROCESS_START_FAILED",dispatched=process.pid is not None,
                                      engine_started=bool(started_clock.value))
                finally:
                    closing = time.monotonic()
                    stop.set(); gate.set(); sending.close()
                    if monitor is not None: monitor.join(timeout=2)
                    if process.pid is not None:
                        owned_descendants.update(descendants(process.pid))
                        signal_owned(owned_descendants,signal.SIGTERM)
                        process.join(timeout=.5)
                        if process.is_alive(): process.terminate(); process.join(timeout=2)
                        if process.is_alive(): process.kill(); process.join(timeout=2)
                        if process.is_alive(): raise WorkersNotStopped("V2 worker did not stop")
                        state["identity_after"] = process_identity(process.pid)
                        state["exitcode"] = process.exitcode
                        signal_owned(owned_descendants,signal.SIGKILL)
                        until=time.monotonic()+2
                        while any(process_identity(pid)==identity for pid,identity in owned_descendants.items()) and time.monotonic()<until:
                            time.sleep(.01)
                        state["descendants_after"]=[identity for pid,identity in owned_descendants.items() if process_identity(pid)==identity]
                        if state["descendants_after"]: raise WorkersNotStopped("V2 descendant did not stop")
                    if reader is not None:
                        reader.join(timeout=2)
                        if reader.is_alive(): raise WorkersNotStopped("V2 reader did not stop")
                    receiving.close()
                    if monitor is not None:
                        monitor.join(timeout=2)
                        if monitor.is_alive(): raise WorkersNotStopped("V2 watchdog did not stop")
                    state["cleanup_ms"] = (time.monotonic()-closing)*1000
                    state["elapsed_ms"] = (time.monotonic()-launched)*1000
                    state["execution_external_wall_ms"] = ((finished or closing)-started_clock.value)*1000 if started_clock.value else None
                    state["stopped_monotonic"] = time.monotonic()
                    process.close()
                    cleanup_verified = True
                state.update(state="TERMINATED",reason=terminal.payload.diagnostic.termination_reason,
                             engine_started=terminal.engine_started)
                terminal = with_resources(terminal, report, state, budget)
                logger.warning('comparison_resource_execution %s', json.dumps(dict(
                    comparison_id=scope.comparison_id, method=scope.method,
                    reason=terminal.payload.diagnostic.termination_reason,
                    dispatched=terminal.dispatched, engine_started=terminal.engine_started,
                    wall_ms=round(state['elapsed_ms']), statistics=dict(terminal.payload.diagnostic.statistics))))
                yield dict(scope=scope,kind="result",data=terminal)
        finally:
            report["elapsed_ms"] = (time.monotonic()-began)*1000
            report["all_workers_stopped"] = cleanup_verified
            for state in report["executions"].values():
                if state["state"] != "TERMINATED":
                    state.update(state="TERMINATED",reason="CANCELLED")
            report["retained_bytes"] = dict(self.retention.bytes)
            report["evicted_observations"] = dict(self.retention.evicted)
            logger.warning('comparison_resource_summary %s', json.dumps(dict(
                comparison_id=scopes[0].comparison_id, supervisor_peak_rss_bytes=report['supervisor_peak_rss'],
                aggregate_peak_rss_bytes=report['maximum_aggregate_rss'], budget=asdict(budget),
                global_reason=report['global_reason'], memory_at_stop=report.get('memory_at_stop'),
                all_workers_stopped=report['all_workers_stopped'])))
