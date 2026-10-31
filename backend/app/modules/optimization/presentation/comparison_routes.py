"""Rutas comparativas. Autor: Fabricio Melendez Quezada. Revisor: Andro Quispe."""
from typing import Annotated
from fastapi import APIRouter, Depends, Header, Path, Query, Response
from fastapi.responses import StreamingResponse

from ..application.comparisons import AcceptComparison
from ..application.comparison_confirmation import ConfirmComparison
from ..application.errors import RunError
from ..application.visual import mask_window
from .comparison_runtime import ComparisonRuntime
from .comparison_schemas import ComparisonSummary, ComparisonSelection, ComparisonRelease, ExecutionResponse, ComparisonConfirmation, ComparisonMaskPayload
from .comparison_serialization import comparison_response, execution_response
from .confirmation_serialization import confirmation_response
from .run_auth import run_permission
from .run_routes import RunRoute, get_run_admission, visual_response
from .run_schemas import RunRequestV1
from .visual_serialization import describe_record

_RUNTIME = ComparisonRuntime()
Id = Annotated[int, Path(gt=0, le=2147483647)]
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
router = APIRouter(prefix="/comparisons", route_class=RunRoute)


class ObservationResponse(StreamingResponse):
    def __init__(self, content, observer):
        super().__init__(content, media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
        self.observer = observer

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.observer.release()


def get_comparison_runtime():
    return _RUNTIME


def get_comparison_uow():
    from app.shared.database.session import SessionLocal
    from ..infrastructure.comparison_uow import SqlComparisonUnitOfWork
    return lambda: SqlComparisonUnitOfWork(SessionLocal)


def load(identifier, uow, runtime):
    with uow() as tx:
        return tx.comparisons.reconcile_stopped(identifier, supervisor_stopped=runtime.stopped(identifier))


@router.post("", status_code=201, response_model=ComparisonSummary)
def start(request: RunRequestV1, response: Response, key: Key,
          user=Depends(run_permission("optimization.execute")), uow=Depends(get_comparison_uow),
          runtime=Depends(get_comparison_runtime), admission=Depends(get_run_admission)):
    with uow() as tx:
        previous = tx.comparisons.find_by_key(user.user_id, key)
    if previous is not None:
        if previous.problem.order_ids != tuple(sorted(request.order_ids)):
            raise RunError("STATE_CONFLICT", "La clave de solicitud ya corresponde a otro lote.")
        response.headers["Location"] = f"/api/optimization/comparisons/{previous.comparison_id}"
        return comparison_response(load(previous.comparison_id, uow, runtime))
    lease, job, accepted = admission.acquire_comparison(user.user_id), None, None
    try:
        job = runtime.reserve()
        accepted = AcceptComparison(uow).execute(request.order_ids, user.user_id, key)
        wire = comparison_response(accepted)
        if accepted.terminal:
            runtime.abort(job)
            lease.release()
        else:
            runtime.start(job, accepted, uow, lease)
    except BaseException:
        if job is None or job.thread is None or not job.thread.is_alive():
            try:
                if accepted is not None:
                    with uow() as tx:
                        tx.comparisons.reconcile_stopped(accepted.comparison_id, supervisor_stopped=True)
            finally:
                if job is not None:
                    runtime.abort(job)
                lease.release()
        raise
    response.headers["Location"] = f"/api/optimization/comparisons/{accepted.comparison_id}"
    return wire


@router.get("/requests/{key}", response_model=ComparisonSummary)
def request_status(key: Annotated[str, Path(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")],
                   user=Depends(run_permission("optimization.view")), uow=Depends(get_comparison_uow),
                   runtime=Depends(get_comparison_runtime)):
    with uow() as tx:
        current = tx.comparisons.find_by_key(user.user_id, key)
    if current is None:
        raise RunError("NOT_FOUND", "No se encontró la solicitud comparativa.")
    return comparison_response(load(current.comparison_id, uow, runtime))


@router.get("/{comparison_id}", response_model=ComparisonSummary)
def get_comparison(comparison_id: Id, user=Depends(run_permission("optimization.view")),
                   uow=Depends(get_comparison_uow), runtime=Depends(get_comparison_runtime)):
    return comparison_response(load(comparison_id, uow, runtime))


@router.get("/{comparison_id}/executions/{execution_id}", response_model=ExecutionResponse)
def get_execution(comparison_id: Id, execution_id: Id, user=Depends(run_permission("optimization.view")),
                  uow=Depends(get_comparison_uow), runtime=Depends(get_comparison_runtime)):
    current = load(comparison_id, uow, runtime)
    execution = next((e for e in current.executions if e.execution_id == execution_id), None)
    if execution is None:
        raise RunError("NOT_FOUND", "La ejecución no pertenece a esta comparación.")
    return execution_response(current, execution)


@router.put("/{comparison_id}/selection", response_model=ComparisonSummary)
def select_execution(comparison_id: Id, request: ComparisonSelection, user=Depends(run_permission("optimization.execute")),
                     uow=Depends(get_comparison_uow)):
    with uow() as tx:
        current = tx.comparisons.select(comparison_id, request.execution_id, request.expected_version)
    return comparison_response(current)


@router.post("/{comparison_id}/confirm", response_model=ComparisonConfirmation)
def confirm(comparison_id: Id, request: ComparisonSelection, key: Key, user=Depends(run_permission("optimization.confirm")),
            uow=Depends(get_comparison_uow)):
    receipt = ConfirmComparison(uow).execute(comparison_id, request.execution_id, request.expected_version, key, user.user_id)
    with uow() as tx:
        current = tx.comparisons.get(comparison_id)
    return ComparisonConfirmation(comparison_id=comparison_id, execution_id=request.execution_id,
        version=current.version, receipt=confirmation_response(receipt))


@router.post("/{comparison_id}/release", response_model=ComparisonSummary)
def release(comparison_id: Id, request: ComparisonRelease, user=Depends(run_permission("optimization.execute")),
            uow=Depends(get_comparison_uow)):
    with uow() as tx:
        current = tx.comparisons.release(comparison_id, request.expected_version, user.user_id)
    return comparison_response(current)


@router.get("/{comparison_id}/events")
def events(comparison_id: Id, after_sequence: Annotated[int, Query(ge=0)] = 0,
           user=Depends(run_permission("optimization.view")), uow=Depends(get_comparison_uow), runtime=Depends(get_comparison_runtime)):
    load(comparison_id, uow, runtime)
    job = runtime.get(comparison_id)
    job.check_cursor(after_sequence)
    observer = job.observe()
    return ObservationResponse(job.lines(after_sequence, observer), observer)


@router.get("/{comparison_id}/executions/{execution_id}/visual")
def manifest(comparison_id: Id, execution_id: Id, offset: Annotated[int, Query(ge=0, le=1024)] = 0,
             user=Depends(run_permission("optimization.view")), uow=Depends(get_comparison_uow), runtime=Depends(get_comparison_runtime)):
    load(comparison_id, uow, runtime)
    import json
    data = json.dumps(runtime.get(comparison_id).manifest(execution_id, offset), separators=(",", ":"), allow_nan=False)
    if len(data.encode()) > 256 * 1024:
        raise RunError("INTERNAL_ERROR", "El manifiesto excede el tamaño permitido.")
    return Response(data, media_type="application/json")


@router.get("/{comparison_id}/executions/{execution_id}/visual/masks/{reference}")
def mask(comparison_id: Id, execution_id: Id, reference: Annotated[str, Path(pattern=r"^[a-f0-9]{32}$")],
         row_start: Annotated[int, Query(ge=0)] = 0, column_start: Annotated[int, Query(ge=0)] = 0,
         row_count: Annotated[int | None, Query(gt=0, le=256)] = None,
         column_count: Annotated[int | None, Query(gt=0, le=1024)] = None,
         user=Depends(run_permission("optimization.view")), uow=Depends(get_comparison_uow), runtime=Depends(get_comparison_runtime)):
    load(comparison_id, uow, runtime)
    job = runtime.get(comparison_id)
    method, session = job.session(execution_id)
    record = session.get(reference)
    data = mask_window(record, row_start=row_start, column_start=column_start, row_count=row_count, column_count=column_count)
    spans = data.pop("spans_by_row")
    return visual_response(ComparisonMaskPayload(**job.descriptor(method, describe_record(session, record)),
        geometria_original=dict(record.owner.geometry), geometria=dict(record.orientation.geometry), window=data, spans_by_row=spans))
