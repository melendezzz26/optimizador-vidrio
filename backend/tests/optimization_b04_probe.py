"""Bounded early B04 feasibility gate. Real spawn, no DB or product coordinator.

From backend: python -m tests.optimization_b04_probe
Instrumentation wraps existing entry points only inside each disposable child.
"""
from dataclasses import asdict
import json
import multiprocessing as mp
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
METHODS = ("FF", "BF", "WF", "HF", "M5", "M6-BS")


def memory(pid):
    try:
        virtual, resident, *_ = (int(v) for v in Path(f"/proc/{pid}/statm").read_text().split())
        return dict(rss=resident * os.sysconf("SC_PAGE_SIZE"), virtual=virtual * os.sysconf("SC_PAGE_SIZE"))
    except FileNotFoundError:
        return dict(rss=0, virtual=0)


def child(method, payload, observed, budget, connection, parent):
    import resource
    from app.modules.optimization.infrastructure.process_lifecycle import protect_against_parent_exit, process_identity
    protect_against_parent_exit(parent)
    resource.setrlimit(resource.RLIMIT_AS, (budget["worker_address_bytes"], budget["worker_address_bytes"]))
    from app.modules.optimization.application import engine_execution as execution
    from app.modules.optimization.domain import packing, beam_search
    from app.modules.optimization.infrastructure.comparison_snapshot import decode_problem, canonical_json, problem_fingerprint
    from app.modules.optimization.infrastructure.comparison_v2_snapshot import encode_result_v3
    from app.modules.optimization.infrastructure.comparison_transport import pack_visual
    from app.modules.optimization.infrastructure.run_snapshot import json_value
    try:
        decoded = time.perf_counter_ns()
        problem = decode_problem(json.loads(payload))
        decode_ms = (time.perf_counter_ns() - decoded) / 1e6
        connection.send_bytes(json.dumps(dict(kind="ready", identity=process_identity(os.getpid()),
            input_sha256=problem_fingerprint(problem), memory=memory(os.getpid()))).encode())
        times = dict(preparation_ns=0, preparation_observer_ns=0, engine_ns=0, observation_ns=0,
                     metrics_ns=0, observation_serialization_ns=0, result_serialization_ns=0)
        counters = dict(events=0, observation_bytes=0)
        preparing, engine_active = False, False
        times["engine_observation_ns"] = 0
        for module in (packing, beam_search):
            original = module.prepare_run_geometry
            def preparation(*args, _original=original, **kwargs):
                nonlocal preparing
                start = time.perf_counter_ns()
                previous = preparing
                preparing = True
                try:
                    return _original(*args, **kwargs)
                finally:
                    preparing = previous
                    times["preparation_ns"] += time.perf_counter_ns() - start
            module.prepare_run_geometry = preparation
        original_metrics = execution.calculate_metrics
        def metrics(*args, **kwargs):
            start = time.perf_counter_ns()
            try:
                return original_metrics(*args, **kwargs)
            finally:
                times["metrics_ns"] += time.perf_counter_ns() - start
        execution.calculate_metrics = metrics
        cls = execution.BY_METHOD[method].optimizer_type
        entry = "run" if method == "M6-BS" else "optimize"
        original_engine = getattr(cls, entry)
        def engine(self, *args, **kwargs):
            nonlocal engine_active
            start = time.perf_counter_ns()
            engine_active = True
            try:
                return original_engine(self, *args, **kwargs)
            finally:
                engine_active = False
                times["engine_ns"] += time.perf_counter_ns() - start
        setattr(cls, entry, engine)
        def observe(fact):
            start = time.perf_counter_ns()
            value = pack_visual(fact.fact) if fact.kind == "visual" else json_value(fact.fact)
            raw = canonical_json(dict(scope=json_value(fact.scope), kind=fact.kind,
                presentation=fact.presentation, fact=value)).encode()
            duration = time.perf_counter_ns() - start
            times["observation_serialization_ns"] += duration
            times["observation_ns"] += duration
            if engine_active:
                times["engine_observation_ns"] += duration
            if preparing:
                times["preparation_observer_ns"] += duration
            counters["events"] += 1
            counters["observation_bytes"] += len(raw)
        start = time.perf_counter_ns()
        connection.send_bytes(json.dumps(dict(kind="started", monotonic=time.monotonic())).encode())
        def check():
            if (time.perf_counter_ns() - start) / 1e9 >= budget["calculation_seconds"]:
                raise execution.TimeBudgetExceeded()
        adapted = execution.EngineExecutionAdapter(method).execute(execution.ExecutionScope(
            comparison_id=43, execution_id=METHODS.index(method)+4301, method=method), problem,
            minimum_width_mm=1, minimum_height_mm=1, checkpoint=check,
            on_observation=observe if observed else None)
        execution_ms = (time.perf_counter_ns() - start) / 1e6
        serializing = time.perf_counter_ns()
        snapshot = encode_result_v3(adapted.payload)
        encoded = canonical_json(snapshot).encode()
        times["result_serialization_ns"] = time.perf_counter_ns() - serializing
        # Preparation includes its own callbacks; expose exclusive preparation and
        # engine remainder without counting observation twice.
        prep = times["preparation_ns"] - times["preparation_observer_ns"]
        body = times["engine_ns"] - times["preparation_ns"] - (
            times["engine_observation_ns"] - times["preparation_observer_ns"])
        record = dict(kind="result", method=method, input_sha256=problem_fingerprint(problem),
            identity=process_identity(os.getpid()), decode_ms=decode_ms, execution_wall_ms=execution_ms,
            preparation_exclusive_ms=prep/1e6, engine_body_exclusive_ms=max(0, body)/1e6,
            timings_ms={k.removesuffix("_ns"): v/1e6 for k,v in times.items()}, **counters,
            result_bytes=len(encoded), termination=adapted.payload.diagnostic.public(),
            complete=bool(adapted.payload.result and adapted.payload.result.complete),
            memory=memory(os.getpid()), maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            observer_error_type=adapted.observer_error_type, error_type=adapted.error_type)
        raw = json.dumps(record).encode()
        assert len(raw) <= budget["packet_bytes"]
        connection.send_bytes(raw)
    finally:
        connection.close()


def main():
    from app.modules.optimization.application.comparison_limits import DEFAULT_COMPARISON_BUDGET
    from app.modules.optimization.infrastructure.comparison_runner import check_environment
    from app.modules.optimization.infrastructure.process_lifecycle import process_identity
    check_environment()
    budget = asdict(DEFAULT_COMPARISON_BUDGET)
    fixture = json.loads((ROOT/'docs/evidence/sprint-02/TA-043/B03/adapter-validation.json').read_text())["problem"]
    payload = json.dumps(fixture)
    reports = []
    for observed in (False, True):
        began = time.monotonic()
        report = dict(observed=observed, records=[], maximum_active_workers=0,
                      sampled_maximum_aggregate_rss=0, sample_interval_ms=5, result="FAIL")
        for method in METHODS:
            receiving, sending = mp.get_context('spawn').Pipe(duplex=False)
            process = mp.get_context('spawn').Process(target=child,
                args=(method,payload,observed,budget,sending,process_identity(os.getpid())))
            launch = time.monotonic(); engine_started = None; result = None
            process.start(); sending.close()
            identity = process_identity(process.pid)
            report["maximum_active_workers"] = max(report["maximum_active_workers"], 1)
            try:
                while True:
                    now = time.monotonic()
                    aggregate = memory(os.getpid())["rss"] + memory(process.pid)["rss"] + budget["helper_reserve_bytes"]
                    report["sampled_maximum_aggregate_rss"] = max(report["sampled_maximum_aggregate_rss"],aggregate)
                    if aggregate > budget["aggregate_rss_bytes"] or memory(os.getpid())["rss"] > budget["supervisor_rss_bytes"]:
                        raise RuntimeError("MEMORY_BUDGET_EXCEEDED")
                    if now-began >= budget["global_seconds"]: raise RuntimeError("GLOBAL_TIME_LIMIT")
                    if engine_started is None and now-launch >= budget["startup_seconds"]: raise RuntimeError("PROCESS_START_FAILED")
                    if engine_started is not None and now-engine_started >= budget["calculation_seconds"]: raise RuntimeError("TIME_BUDGET_EXCEEDED")
                    if receiving.poll(.005):
                        packet = json.loads(receiving.recv_bytes(budget["packet_bytes"]))
                        if packet["kind"] == "ready":
                            assert packet["identity"] == identity
                            startup_ms = (time.monotonic()-launch)*1000
                        elif packet["kind"] == "started": engine_started = packet["monotonic"]
                        elif packet["kind"] == "result":
                            result = {**packet, "startup_ms":startup_ms, "spawn_to_result_ms":(time.monotonic()-launch)*1000}
                            break
                    elif not process.is_alive(): raise RuntimeError("WORKER_STOPPED")
            finally:
                closing = time.monotonic()
                process.join(timeout=.5)
                if process.is_alive(): process.terminate(); process.join(timeout=2)
                if process.is_alive(): process.kill(); process.join(timeout=2)
                assert not process.is_alive()
                receiving.close()
                if result is not None:
                    result.update(cleanup_ms=(time.monotonic()-closing)*1000, exitcode=process.exitcode,
                                  identity_after=process_identity(process.pid))
                    report["records"].append(result)
                process.close()
        report.update(total_ms=(time.monotonic()-began)*1000, all_workers_stopped=True)
        report["result"] = "PASS" if len(report["records"])==6 and all(r["complete"] and not r["error_type"]
            and not r["observer_error_type"] and r["exitcode"]==0 for r in report["records"]) else "FAIL"
        reports.append(report)
    result = dict(budget=budget, fixture=fixture, sequences=reports,
        decision="VIABLE" if all(r["result"]=="PASS" and r["total_ms"]<180000 for r in reports) else "NO VIABLE",
        scope="bounded preliminary spawn diagnosis, not the B05 coordinator")
    target=ROOT/'docs/evidence/sprint-02/TA-043/B04/early-feasibility.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(decision=result["decision"], sequences=[dict(observed=r["observed"],total_ms=r["total_ms"],
        peak_rss=r["sampled_maximum_aggregate_rss"],result=r["result"]) for r in reports])))
    return 0 if result["decision"]=="VIABLE" else 1


if __name__=='__main__':
    raise SystemExit(main())
