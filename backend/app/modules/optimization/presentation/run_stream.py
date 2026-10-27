"""Live NDJSON bridge with bounded buffering and cooperative disconnect handling.

The producer waits for acknowledgement of each yielded event. No replay: the
engine cannot advance to the next milestone before the consumer resumes. All
serialization/backpressure is inside the callback excluded by the engine clock.
"""
import asyncio
import anyio
from fastapi.responses import StreamingResponse
import logging
import time
from datetime import datetime, timezone
from queue import Queue, Empty, Full
from threading import Event, Thread
from typing import get_args

from ..application.errors import ExecutionInterrupted, ResultSaveFailed, TimeBudgetExceeded
from ..application.load_budget import DEFAULT_RUN_LOAD_BUDGET
from ..application.dto import RunStatus
from .run_schemas import (OptimizationStartedV1, GroupStartedV1, PieceStartedV1, PiecePlacedV1,
    GroupCompletedV1, MetricsCalculatedV1, OptimizationCompletedV1, OptimizationFailedV1)
from .run_serialization import (config_response, unit_reference, placement_response, stock_response,
                                progress_response, run_response)
from ..application.visual import MAX_EVENT_BYTES
from .visual_schemas import EVENT_TYPES, VisualPolicyV2
from .visual_serialization import VisualProjection

logger = logging.getLogger(__name__)


class RunStreamingResponse(StreamingResponse):
    def __init__(self, *args, stream=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream = stream

    async def stream_response(self, send):
        try:
            await super().stream_response(send)
        finally:
            # ASGI cancellation can happen in send(), while the generator is
            # suspended at yield. async-for does not close it in that case.
            # Shield cleanup so disconnect reaches the producer immediately.
            with anyio.CancelScope(shield=True):
                await self.body_iterator.aclose()
            if self.stream is not None:
                # TA-037: a stream that never started its worker frees its slot here.
                self.stream.release_if_idle()


class LiveRunStream:
    def __init__(self, unit_of_work, calculator, *, lease=None, visual_session=None,
                 time_budget_s=DEFAULT_RUN_LOAD_BUDGET.max_calculation_seconds, clock=time.monotonic):
        self.unit_of_work, self.calculator = unit_of_work, calculator
        # TA-037 T03: admission slot (L-10/L-11) and time budget (L-12).
        self.lease, self.time_budget_s, self.clock = lease, time_budget_s, clock
        self.worker_started = False
        self.visual_session = visual_session

    def release_if_idle(self):
        """Free the slot only if no worker owns it; a running worker frees it when it ends."""
        if not self.worker_started and self.lease is not None:
            self.lease.release()
        if not self.worker_started and self.visual_session is not None:
            self.visual_session.abort()

    async def lines(self, accepted):
        identifier, problem = accepted.optimization_id, accepted.result.problem
        result_url = f"/api/optimization/runs/{identifier}"
        queue, stopped = Queue(maxsize=1), Event()
        sequence, placements, group_bases = 0, [], {}
        clock = dict(started=None, delivery=0.0)  # L-12 excludes time spent delivering events
        group_totals = {g.key: len(g.units) for g in problem.groups}
        projection = VisualProjection(self.visual_session, lambda kind, data: send(EVENT_TYPES[kind], data),
                                      clock=self.clock) if self.visual_session is not None else None

        def line(schema, data):
            nonlocal sequence
            sequence += 1
            name = get_args(schema.model_fields['event'].annotation)[0]
            if projection is not None:
                schema = EVENT_TYPES[name]
                if name == 'optimization_started':
                    data = {**data, 'visual': VisualPolicyV2()}
                elif name in ('piece_started', 'piece_placed', 'optimization_completed'):
                    data = {**data, 'processed_units': projection.processed}
            payload = schema(schema_version=2 if projection is not None else 1,
                sequence=sequence, id_optimizacion=identifier,
                occurred_at=datetime.now(timezone.utc), event=name, data=data).model_dump_json() + '\n'
            if projection is not None and len(payload.encode('utf-8')) > MAX_EVENT_BYTES:
                raise ValueError('Visual event exceeds its byte budget.')
            return payload

        def send(schema, data, *, terminal=False):
            before = self.clock()
            try:
                deliver(schema, data, terminal)
            finally:
                clock["delivery"] += self.clock() - before

        def deliver(schema, data, terminal):
            payload, acknowledged = line(schema, data), Event()
            while not stopped.is_set():
                try:
                    queue.put((payload, acknowledged, terminal), timeout=0.1)
                    break
                except Full:
                    continue
            else:
                raise ExecutionInterrupted()
            while not acknowledged.wait(0.1):
                if stopped.is_set():
                    raise ExecutionInterrupted()

        def checkpoint():
            if stopped.is_set():
                raise ExecutionInterrupted()
            if self.clock() - clock["started"] - clock["delivery"] > self.time_budget_s:
                raise TimeBudgetExceeded()                                  # TA-037 L-12

        def milestone(event):
            if event.placement is not None:
                placements.append(event.placement)
            checkpoint()
            key = event.group_key
            material_key = dict(id_tipo_vidrio=key[0], espesor_mm=key[1])
            progress = progress_response(event.placed_units, event.total_units)
            if event.kind == "group_started":
                group_bases[key] = event.placed_units
                send(GroupStartedV1, {**material_key, "total_units": group_totals[key]})
            elif event.kind == "piece_started":
                send(PieceStartedV1, {**unit_reference(event.unit), **progress})
            elif event.kind == "piece_placed":
                send(PiecePlacedV1, {**placement_response(event.placement, problem.config).model_dump(),
                     **progress, "material": stock_response(event.placement.stock)})
            elif event.kind == "group_completed":
                send(GroupCompletedV1, {**material_key, "result_url": result_url,
                    **progress_response(event.placed_units - group_bases[key], group_totals[key])})

        def completed(run):
            if projection is not None:
                projection.processed = run.result.total_units
            response = run_response(run)
            send(MetricsCalculatedV1, dict(metrics_available=response.metrics_available, metrics=response.metrics))
            send(OptimizationCompletedV1, dict(estado=run.status.value, completo=run.result.complete,
                result_url=result_url, **progress_response(run.result.placed_units, run.result.total_units)), terminal=True)

        def produce():
            try:
                calculate()
            finally:
                if self.lease is not None:
                    self.lease.release()                                    # TA-037: always, once
                if self.visual_session is not None:
                    self.visual_session.finish()

        def visual(event):
            # Includes sampling/reference registration as well as delivery. The
            # nested send() duration is counted only once by this outer callback.
            before, previous = self.clock(), clock['delivery']
            try:
                projection(event)
            finally:
                clock['delivery'] = previous + self.clock() - before

        def calculate():
            clock["started"] = self.clock()
            try:
                kwargs = {'on_visual': visual} if projection is not None else {}
                run = self.calculator.execute(identifier, milestone, checkpoint=checkpoint, **kwargs)
                completed(run)
            except Exception as error:
                code = ("EXECUTION_INTERRUPTED" if isinstance(error, ExecutionInterrupted) else
                        "TIME_BUDGET_EXCEEDED" if isinstance(error, TimeBudgetExceeded) else
                        "RESULT_SAVE_FAILED" if isinstance(error, ResultSaveFailed) else "CALCULATION_FAILED")
                if isinstance(error, TimeBudgetExceeded):
                    logger.warning("First Fit run %s stopped after %s s (TIME_BUDGET_EXCEEDED)",
                                   identifier, self.time_budget_s)
                elif not isinstance(error, ExecutionInterrupted):
                    logger.exception("First Fit run %s failed (%s)", identifier, code)
                try:
                    with self.unit_of_work() as uow:
                        failed = uow.runs.fail(identifier, code, tuple(placements))
                    if failed.status is not RunStatus.FAILED:
                        # Persistence succeeded before a delivery/disconnect failure.
                        # Canonical GET remains authoritative; never overwrite it.
                        if not stopped.is_set():
                            completed(failed)
                        return
                except Exception:
                    logger.exception("Cannot record failure for run %s; reconciliation required", identifier)
                if not stopped.is_set():
                    try:
                        send(OptimizationFailedV1, dict(estado="FALLIDA", code=code,
                             message=(f"El cálculo superó el tiempo máximo de {self.time_budget_s} s y se detuvo. "
                                      "Divide la selección en lotes más pequeños."
                                      if code == "TIME_BUDGET_EXCEEDED" else
                                      "La ejecución no pudo completarse. Consulta el resultado o solicita revisión."),
                             result_url=result_url), terminal=True)
                    except ExecutionInterrupted:
                        pass

        started_line = line(OptimizationStartedV1, dict(metodo="FF", order_ids=list(problem.order_ids),
            total_units=len(problem.units), groups=[dict(id_tipo_vidrio=g.glass_type_id, espesor_mm=g.thickness_mm)
                                                   for g in problem.groups], configuracion=config_response(problem.config)))
        worker = Thread(target=produce, name=f"optimization-{identifier}", daemon=True)
        worker.start()
        self.worker_started = True  # after start(): if starting fails, release_if_idle frees the slot
        def next_item():
            try:
                return queue.get(timeout=0.1)
            except Empty:
                return None
        try:
            yield started_line
            while True:
                item = await asyncio.to_thread(next_item)
                if item is None:
                    if not worker.is_alive():
                        break
                    continue
                payload, acknowledgement, terminal = item
                yield payload
                acknowledgement.set()
                if terminal:
                    break
        finally:
            stopped.set()
            # Cooperative checks cover bases/orientations/sources, not each cell.
            await asyncio.to_thread(worker.join, 2)
