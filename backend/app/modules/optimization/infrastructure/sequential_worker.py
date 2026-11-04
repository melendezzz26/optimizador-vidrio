"""Disposable v2 engine worker. Only canonical JSON and spawn control primitives."""
from dataclasses import asdict
from decimal import Decimal
import json
import os
import time

from ..application.engine_execution import EngineExecutionAdapter, ExecutionScope
from ..application.visual import OrientationSampler
from .comparison_snapshot import canonical_json, decode_problem, problem_fingerprint
from .comparison_transport import pack_visual
from .comparison_v2_snapshot import encode_result_v3
from .run_snapshot import json_value
from .process_lifecycle import process_identity, protect_against_parent_exit


def calculation_worker_v2(scope_values, payload, minimums, connection, gate, started_clock,
                          budget, checkpoint_cancel, parent_identity, observed):
    try:
        protect_against_parent_exit(parent_identity)
        import resource
        old_hard = resource.getrlimit(resource.RLIMIT_AS)[1]
        hard = budget.worker_address_bytes if old_hard == resource.RLIM_INFINITY else min(old_hard, budget.worker_address_bytes)
        resource.setrlimit(resource.RLIMIT_AS, (hard, hard))
        scope = ExecutionScope(**scope_values)
        problem = decode_problem(json.loads(payload))
        def send(kind, data, maximum=budget.packet_bytes):
            raw = canonical_json(dict(scope=asdict(scope), kind=kind, data=data), maximum_bytes=maximum).encode()
            connection.send_bytes(raw)
        send("ready", dict(identity=process_identity(os.getpid()), input_sha256=problem_fingerprint(problem)))
        if not gate.wait(budget.startup_seconds):
            return
        started_clock.value = time.monotonic()
        send("started", dict(monotonic=started_clock.value))
        sampler = OrientationSampler()
        observations, observation_bytes = 0, 0
        def observe(fact):
            nonlocal observations, observation_bytes
            # Final layout travels once in the reliable terminal result packet.
            if fact.kind == "final_layout":
                return
            if fact.kind == "visual" and fact.fact.kind == "orientation_testing" and not sampler.accept(fact.fact.unit):
                return
            value = pack_visual(fact.fact) if fact.kind == "visual" else json_value(fact.fact)
            data = dict(kind=fact.kind, presentation=fact.presentation, fact=value)
            raw = canonical_json(dict(scope=asdict(scope), kind="observation", data=data),
                                 maximum_bytes=budget.visual_packet_bytes).encode()
            observations += 1
            observation_bytes += len(raw)
            connection.send_bytes(raw)
        # External process deadlines include callback/IPC blocking. Engine-native
        # checkpoints and M6 limits retain their own meanings, without paused clocks.
        def checkpoint():
            from ..application.errors import ExecutionInterrupted, TimeBudgetExceeded
            if checkpoint_cancel.is_set(): raise ExecutionInterrupted()
            if time.monotonic()-started_clock.value >= budget.calculation_seconds: raise TimeBudgetExceeded()
        adapted = EngineExecutionAdapter(scope.method).execute(scope, problem,
            minimum_width_mm=Decimal(minimums[0]), minimum_height_mm=Decimal(minimums[1]),
            checkpoint=checkpoint, on_observation=observe if observed else None)
        send("result", dict(snapshot=encode_result_v3(adapted.payload), residuals=json_value(adapted.residuals),
            observer_error_type=adapted.observer_error_type, error_type=adapted.error_type,
            observations=observations, observation_bytes=observation_bytes,
            engine_stop_reason=adapted.beam_outcome.stop_reason if adapted.beam_outcome else None,
            address_limit_bytes=hard, maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            ended_monotonic=time.monotonic()))
    except Exception as error:
        try:
            code = "MEMORY_BUDGET_EXCEEDED" if isinstance(error, MemoryError) else "EXECUTION_FAILED"
            connection.send_bytes(json.dumps(dict(scope=scope_values, kind="failed", data=dict(code=code))).encode())
        except (OSError, MemoryError):
            pass
    finally:
        connection.close()
