"""Live NDJSON bridge with bounded buffering and cooperative disconnect handling.

The producer waits for acknowledgement of each yielded event. No replay: the
engine cannot advance to the next milestone before the consumer resumes. All
serialization/backpressure is inside the callback excluded by the engine clock.
"""
import asyncio
import anyio
from fastapi.responses import StreamingResponse
import logging
from datetime import datetime, timezone
from queue import Queue, Empty, Full
from threading import Event, Thread
from typing import get_args

from ..application.errors import ExecutionInterrupted, ResultSaveFailed
from ..application.dto import RunStatus
from .run_schemas import (OptimizationStartedV1, GroupStartedV1, PieceStartedV1, PiecePlacedV1,
    GroupCompletedV1, MetricsCalculatedV1, OptimizationCompletedV1, OptimizationFailedV1)
from .run_serialization import (config_response, unit_reference, placement_response, stock_response,
                                progress_response, run_response)

logger = logging.getLogger(__name__)


class RunStreamingResponse(StreamingResponse):
    async def stream_response(self, send):
        try:
            await super().stream_response(send)
        finally:
            # ASGI cancellation can happen in send(), while the generator is
            # suspended at yield. async-for does not close it in that case.
            # Shield cleanup so disconnect reaches the producer immediately.
            with anyio.CancelScope(shield=True):
                await self.body_iterator.aclose()


class LiveRunStream:
    def __init__(self, unit_of_work, calculator):
        self.unit_of_work, self.calculator = unit_of_work, calculator

    async def lines(self, accepted):
        identifier, problem = accepted.optimization_id, accepted.result.problem
        result_url = f"/api/optimization/runs/{identifier}"
        queue, stopped = Queue(maxsize=1), Event()
        sequence, placements, group_bases = 0, [], {}
        group_totals = {g.key: len(g.units) for g in problem.groups}

        def line(schema, data):
            nonlocal sequence
            sequence += 1
            return schema(schema_version=1, sequence=sequence, id_optimizacion=identifier,
                occurred_at=datetime.now(timezone.utc), event=get_args(schema.model_fields["event"].annotation)[0], data=data).model_dump_json() + "\n"

        def send(schema, data, *, terminal=False):
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

        def milestone(event):
            if event.placement is not None:
                placements.append(event.placement)
            if stopped.is_set():
                raise ExecutionInterrupted()
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
            response = run_response(run)
            send(MetricsCalculatedV1, dict(metrics_available=response.metrics_available, metrics=response.metrics))
            send(OptimizationCompletedV1, dict(estado=run.status.value, completo=run.result.complete,
                result_url=result_url, **progress_response(run.result.placed_units, run.result.total_units)), terminal=True)

        def produce():
            try:
                run = self.calculator.execute(identifier, milestone)
                completed(run)
            except Exception as error:
                code = ("EXECUTION_INTERRUPTED" if isinstance(error, ExecutionInterrupted) else
                        "RESULT_SAVE_FAILED" if isinstance(error, ResultSaveFailed) else "CALCULATION_FAILED")
                if not isinstance(error, ExecutionInterrupted):
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
                             message="La ejecución no pudo completarse. Consulta el resultado o solicita revisión.",
                             result_url=result_url), terminal=True)
                    except ExecutionInterrupted:
                        pass

        started_line = line(OptimizationStartedV1, dict(metodo="FF", order_ids=list(problem.order_ids),
            total_units=len(problem.units), groups=[dict(id_tipo_vidrio=g.glass_type_id, espesor_mm=g.thickness_mm)
                                                   for g in problem.groups], configuracion=config_response(problem.config)))
        worker = Thread(target=produce, name=f"optimization-{identifier}", daemon=True)
        worker.start()
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
            # Cooperative cancellation occurs at milestones, not per rejected cell.
            await asyncio.to_thread(worker.join, 2)
