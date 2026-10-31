"""Tres procesos spawn supervisados; cálculo independiente de la observación HTTP.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
Linux/procfs y RLIMIT_AS son requisitos explícitos de esta primera entrega.
La aplicación debe conservar su admisión hasta que este iterador cierre/join.
"""
from dataclasses import replace
from decimal import Decimal
import json
import multiprocessing as mp
import os
from pathlib import Path
from queue import Empty, Full, Queue
import sys
from threading import Event, Thread
import time

from ..application.comparison_contracts import METHODS, CalculatedExecution
from ..application.comparison_limits import DEFAULT_COMPARISON_BUDGET
from ..application.errors import RunError, TimeBudgetExceeded, WorkersNotStopped
from ..application.visual import OrientationSampler
from ..domain.first_fit import FirstFitOptimizer
from ..domain.best_fit import BestFitOptimizer
from ..domain.worst_fit import WorstFitOptimizer
from ..domain.metrics import calculate_metrics
from ..domain.metrics import ResidualRectangle
from .comparison_snapshot import canonical_json, decode_problem, decode_result, encode_problem, encode_result, problem_fingerprint
from .comparison_transport import pack_visual, unpack_visual
from .run_snapshot import json_value
from .process_lifecycle import process_identity, protect_against_parent_exit

ENGINES = {"FF": FirstFitOptimizer, "BF": BestFitOptimizer, "WF": WorstFitOptimizer}


def resident_bytes(pid):
    try:
        return int(Path(f"/proc/{pid}/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except (FileNotFoundError, ProcessLookupError):
        return 0


def available_memory():
    fields = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    available = int(fields["MemAvailable"].split()[0]) * 1024
    root = Path("/sys/fs/cgroup")
    if (root / "memory.max").is_file():
        limit = (root / "memory.max").read_text().strip()
        if limit != "max":
            available = min(available, int(limit) - int((root / "memory.current").read_text()))
    return available


def check_environment(budget=DEFAULT_COMPARISON_BUDGET):
    try:
        if sys.platform != "linux" or not resident_bytes(os.getpid()):
            raise ValueError("Linux procfs required")
        import resource
        if not hasattr(resource, "RLIMIT_AS"):
            raise ValueError("Address-space limit unavailable")
        if available_memory() < budget.aggregate_rss_bytes or resident_bytes(os.getpid()) > budget.supervisor_rss_bytes:
            raise RunError("RESOURCE_UNAVAILABLE", "El servidor no dispone de memoria para los tres motores. Intenta más tarde.")
    except (OSError, ValueError, KeyError, ImportError) as error:
        raise RunError("RESOURCE_UNAVAILABLE", "La plataforma no permite ejecutar los tres motores con supervisión de recursos.") from error


def calculation_worker(method, payload, minimums, connection, gate, budget, parent_identity=None):
    """Solo datos JSON/configuración y primitivas spawn, sin sesiones ni DB."""
    try:
        protect_against_parent_exit(parent_identity)
        import resource
        old_hard = resource.getrlimit(resource.RLIMIT_AS)[1]
        hard = budget.worker_address_bytes if old_hard == resource.RLIM_INFINITY else min(old_hard, budget.worker_address_bytes)
        resource.setrlimit(resource.RLIMIT_AS, (hard, hard))
        problem = decode_problem(json.loads(payload))
        def send(kind, data, *, maximum=budget.packet_bytes):
            raw = canonical_json(dict(method=method, kind=kind, payload=data), maximum_bytes=maximum).encode("utf-8")
            connection.send_bytes(raw)
        send("ready", dict(**process_identity(os.getpid()), input_sha256=problem_fingerprint(problem)))
        if not gate.wait(timeout=budget.startup_seconds):
            raise TimeBudgetExceeded()
        send("started", dict(pid=os.getpid(), monotonic_ns=time.monotonic_ns()))
        started, paused = time.perf_counter_ns(), 0
        sampler = OrientationSampler()
        def checkpoint():
            if (time.perf_counter_ns() - started - paused) / 1e9 > budget.calculation_seconds:
                raise TimeBudgetExceeded()
        def deliver(kind, value):
            nonlocal paused
            before = time.perf_counter_ns()
            try:
                if kind == "visual":
                    if value.kind == "orientation_testing" and not sampler.accept(value.unit):
                        return
                    data = pack_visual(value)
                else:
                    data = json_value(value)
                send(kind, data, maximum=budget.visual_packet_bytes)
            finally:
                paused += time.perf_counter_ns() - before
        result = ENGINES[method]().optimize(problem, lambda fact: deliver("milestone", fact),
            checkpoint=checkpoint, on_visual=lambda fact: deliver("visual", fact))
        result, residuals = calculate_metrics(result, *(Decimal(v) for v in minimums))
        checkpoint()
        elapsed = max(0, (time.perf_counter_ns() - started - paused) // 1_000_000)
        result = replace(result, computation_time_ms=elapsed)
        send("result", dict(snapshot=encode_result(result), residuals=json_value(residuals),
                            pid=os.getpid(), ended_ns=time.monotonic_ns()))
    except BaseException as error:
        code = ("MEMORY_BUDGET_EXCEEDED" if isinstance(error, MemoryError) else
                "TIME_BUDGET_EXCEEDED" if isinstance(error, TimeBudgetExceeded) else "EXECUTION_FAILED")
        try:
            connection.send_bytes(json.dumps(dict(method=method, kind="failed", payload={"code": code})).encode())
        except (OSError, MemoryError):
            pass
    finally:
        connection.close()


def _reader(connection, output, stop, maximum):
    try:
        while not stop.is_set():
            raw = connection.recv_bytes(maxlength=maximum)
            while not stop.is_set():
                try:
                    output.put(raw, timeout=.05)
                    break
                except Full:
                    pass
    except (EOFError, OSError):
        while not stop.is_set():
            try:
                output.put(None, timeout=.05)
                break
            except Full:
                pass
    finally:
        connection.close()


def _terminate(process):
    try:
        if process.pid is not None and process.is_alive():
            process.terminate()
    except ProcessLookupError:
        pass


class ComparisonProcessRunner:
    def __init__(self, budget=DEFAULT_COMPARISON_BUDGET, *, worker_target=calculation_worker):
        self.budget, self.worker_target = budget, worker_target
        self.last_report = None

    def preflight(self):
        check_environment(self.budget)

    @property
    def supervisor_identity(self):
        return process_identity(os.getpid())

    def calculate(self, problem, minimums, *, cancel=None):
        """Puerto de aplicación: hechos de dominio, sin exponer codecs al caso de uso."""
        stream, failed = self.events(problem, minimums, cancel=cancel), set()
        try:
            for packet in stream:
                method, kind, payload = packet["method"], packet["kind"], packet["payload"]
                if method in failed:
                    continue
                try:
                    if kind == "visual":
                        payload = unpack_visual(payload, problem)
                    elif kind == "result":
                        result = decode_result(payload["snapshot"], expected_method=method)
                        if result.problem != problem:
                            raise ValueError("Result input mismatch")
                        residuals = tuple(ResidualRectangle(**{k: Decimal(v) if k in (
                            "x_mm", "y_mm", "width_mm", "height_mm", "area_mm2") else v
                            for k, v in region.items()}) for region in payload["residuals"])
                        payload = CalculatedExecution(result=result, residuals=residuals)
                except (ValueError, TypeError, KeyError, ArithmeticError):
                    kind, payload = "failed", {"code": "EXECUTION_FAILED"}
                if kind == "failed":
                    failed.add(method)
                yield dict(method=method, kind=kind, payload=payload)
        finally:
            stream.close()

    def events(self, problem, minimums, *, cancel=None):
        """yield de hechos por método. El cierre siempre detiene/join los hijos.

        No abrir este iterador dentro de una transacción DB ni compartirlo entre
        consumidores. El supervisor de producto debe consumirlo aunque no haya
        ningún visor conectado. Los buffers de red pertenecen a otra capa.
        """
        self.preflight()
        budget, context = self.budget, mp.get_context("spawn")
        payload = canonical_json(encode_problem(problem))
        expected_hash = problem_fingerprint(problem)
        gate, stop = context.Event(), Event()
        processes, connections, readers, channels = {}, {}, {}, {}
        failure, worker_failures = [], {}
        began = time.monotonic()
        report = {"metric": "sampled_supervisor_and_workers_rss_plus_helper_reserve",
            "helper_reserve_bytes": budget.helper_reserve_bytes, "samples": 0,
            "maximum_rss_sum_bytes": 0, "supervisor_peak_rss_bytes": 0,
            "worker_peak_rss_bytes": {method: 0 for method in METHODS},
            "maximum_packet_bytes": 0, "maximum_queued_packets_per_worker": 0,
            "maximum_sample_gap_ms": 0, "all_workers_stopped": False}
        self.last_report = report
        ready, terminal = set(), set()
        monitor = None
        def watch():
            last_sample = time.monotonic()
            while not stop.wait(.025):
                now = time.monotonic()
                report["maximum_sample_gap_ms"] = max(report["maximum_sample_gap_ms"], (now - last_sample) * 1000)
                last_sample = now
                code = None
                if cancel is not None and cancel.is_set():
                    code = "WORKER_STOPPED"
                elif time.monotonic() - began > budget.global_seconds:
                    code = "TIME_BUDGET_EXCEEDED"
                elif not gate.is_set() and time.monotonic() - began > budget.startup_seconds:
                    code = "PROCESS_START_FAILED"
                try:
                    supervisor_rss = resident_bytes(os.getpid())
                    report["supervisor_peak_rss_bytes"] = max(report["supervisor_peak_rss_bytes"], supervisor_rss)
                    total = supervisor_rss + budget.helper_reserve_bytes
                    for method, process in list(processes.items()):
                        rss = resident_bytes(process.pid) if process.pid is not None else 0
                        total += rss
                        report["worker_peak_rss_bytes"][method] = max(report["worker_peak_rss_bytes"][method], rss)
                        if rss > budget.worker_address_bytes:
                            worker_failures[method] = "MEMORY_BUDGET_EXCEEDED"
                            _terminate(process)
                    if total > budget.aggregate_rss_bytes or supervisor_rss > budget.supervisor_rss_bytes:
                        code = "MEMORY_BUDGET_EXCEEDED"
                    report["samples"] += 1
                    report["maximum_rss_sum_bytes"] = max(report["maximum_rss_sum_bytes"], total)
                    report["maximum_queued_packets_per_worker"] = max(report["maximum_queued_packets_per_worker"],
                        *(q.qsize() for q in list(channels.values())))
                except (OSError, ValueError):
                    code = "WORKER_STOPPED"
                if code:
                    failure.append(code)
                    for process in list(processes.values()):
                        _terminate(process)
                    return
        try:
            for method in METHODS:
                receiving, sending = context.Pipe(duplex=False)
                connections[method] = receiving
                channels[method] = Queue(maxsize=budget.queued_packets_per_worker)
                process = context.Process(target=self.worker_target, name=f"comparison-{method}",
                    args=(method, payload, tuple(str(v) for v in minimums), sending, gate, budget, self.supervisor_identity))
                processes[method] = process
                try:
                    process.start()
                finally:
                    sending.close()
                reader = Thread(target=_reader, args=(receiving, channels[method], stop, budget.packet_bytes), daemon=True)
                readers[method] = reader
                reader.start()
            monitor = Thread(target=watch, daemon=True)
            monitor.start()
            while len(terminal) < 3:
                if failure:
                    for method in METHODS:
                        if method not in terminal:
                            terminal.add(method)
                            yield dict(method=method, kind="failed", payload={"code": failure[0]})
                    break
                received = False
                for method in METHODS:
                    if method in terminal:
                        continue
                    try:
                        raw = channels[method].get_nowait()
                    except Empty:
                        continue
                    received = True
                    if raw is not None:
                        report["maximum_packet_bytes"] = max(report["maximum_packet_bytes"], len(raw))
                    try:
                        if raw is None:
                            raise ValueError("Worker disconnected")
                        packet = json.loads(raw)
                        if (not isinstance(packet, dict) or set(packet) != {"method", "kind", "payload"}
                                or packet["method"] != method or not isinstance(packet["payload"], dict)
                                or packet["kind"] not in {"ready", "started", "visual", "milestone", "result", "failed"}):
                            raise ValueError("Invalid worker protocol")
                        if packet["kind"] == "ready":
                            if method in ready or packet["payload"]["input_sha256"] != expected_hash:
                                raise ValueError("Input mismatch")
                            ready.add(method)
                        elif packet["kind"] != "failed" and method not in ready:
                            raise ValueError("Worker not ready")
                    except (ValueError, TypeError, KeyError):
                        packet = dict(method=method, kind="failed", payload={"code": worker_failures.get(method, "WORKER_STOPPED")})
                        _terminate(processes[method])
                    if packet["kind"] in ("result", "failed"):
                        terminal.add(method)
                    yield packet
                    if len(ready | terminal) == 3:
                        gate.set()  # El consumidor ya pudo registrar los PID listos.
                if not received:
                    stop.wait(.005)
        finally:
            stop.set()
            gate.set()
            # Nunca liberar una admisión desde este punto hasta terminar los join.
            for process in processes.values():
                if process.pid is not None:
                    process.join(timeout=.5)
            for process in processes.values():
                _terminate(process)
            for process in processes.values():
                if process.pid is not None:
                    process.join(timeout=2)
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=2)
                    if process.is_alive():
                        raise WorkersNotStopped("A comparison worker could not be stopped")
            for reader in readers.values():
                reader.join(timeout=2)
                if reader.is_alive():
                    raise WorkersNotStopped("A comparison IPC reader could not be stopped")
            for connection in connections.values():
                connection.close()
            if monitor is not None:
                monitor.join(timeout=2)
            report["all_workers_stopped"] = True
            report["elapsed_ms_including_ipc_and_cleanup"] = (time.monotonic() - began) * 1000
