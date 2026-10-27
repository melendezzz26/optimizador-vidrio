"""T1 run routes; legacy HU-015 routes keep their original error representation."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Query, Response
from sqlalchemy.exc import DBAPIError
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute

from ..application.runs import AcceptRun
from ..infrastructure.in_process_admission import InProcessRunAdmission
from ..application.errors import RunError
from .run_schemas import RunRequestV1, RunResponseV1, ConfirmResponseV1
from ..application.confirmation import ConfirmRun
from .confirmation_serialization import confirmation_response
from .run_serialization import run_response
from .run_stream import LiveRunStream, RunStreamingResponse
from .run_auth import run_permission
from ..application.visual import MAX_RESPONSE_BYTES, mask_window
from .visual_schemas import VisualManifestV2, VisualMaskV2
from .visual_serialization import describe_record

logger = logging.getLogger(__name__)


class RunRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def safe(request):
            try:
                return await handler(request)
            except RequestValidationError as error:
                raise HTTPException(422, detail=dict(code="INVALID_INPUT", message="La solicitud de optimización no es válida.")) from error
            except RunError as error:
                status = {"NOT_FOUND":404, "STATE_CONFLICT":409, "CONFIG_CONFLICT":409, "INVALID_INPUT":422,
                          "STOCK_CONFLICT":409, "ALREADY_CONFIRMED":409, "NOT_CONFIRMABLE":422,
                          "LOAD_LIMIT_EXCEEDED":422, "OPTIMIZER_BUSY":503,
                          "VISUAL_DATA_UNAVAILABLE":410}.get(error.code,500)
                # TA-037: public details (e.g. limit) only; internals stay in the server log.
                retry = getattr(error, "retry_after", None)
                raise HTTPException(status, detail=dict(code=error.code, message=error.message,
                                                        **(error.details or {})),
                                    headers={"Retry-After": str(retry)} if retry else None) from error
            except HTTPException as error:
                code = {401:"UNAUTHENTICATED",403:"FORBIDDEN",404:"NOT_FOUND",422:"INVALID_INPUT"}.get(error.status_code,"INTERNAL_ERROR")
                raise HTTPException(error.status_code, detail=dict(code=code, message=str(error.detail)), headers=error.headers) from error
            except DBAPIError as error:
                if getattr(error.orig, "sqlstate", None) in ("40001", "40P01", "55P03"):
                    raise HTTPException(409, detail=dict(code="STATE_CONFLICT", message="La operación entró en conflicto. Revisa el resultado antes de reintentar.")) from error
                logger.exception("Run database operation failed")
                raise HTTPException(500, detail=dict(code="INTERNAL_ERROR", message="No se pudo completar la operación.")) from error
            except Exception as error:
                logger.exception("Run operation failed")
                raise HTTPException(500, detail=dict(code="INTERNAL_ERROR", message="No se pudo completar la operación.")) from error
        return safe


def get_run_unit_of_work():
    from app.shared.database.session import SessionLocal
    from ..infrastructure.run_uow import SqlRunUnitOfWork
    return lambda: SqlRunUnitOfWork(SessionLocal)


def get_run_calculator(unit_of_work=Depends(get_run_unit_of_work)):
    from app.shared.database.session import SessionLocal
    from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
    from ..infrastructure.stock_adapter import InventoryStockAdapter
    from ..application.calculation import CalculateRun
    return CalculateRun(unit_of_work, InventoryStockAdapter(SqlAlchemyInventoryRepository(SessionLocal)))


def get_stock_counter(calculator=Depends(get_run_calculator)):
    """TA-037 P4: the calculator's own stock adapter, so counting and expansion share rules."""
    provider = calculator.stock_provider
    return provider if hasattr(provider, "count_compatible") else None


# TA-037 T03: one admission per web process (L-10/L-11). Valid for the single
# uvicorn process of the Procfile; scaling out requires an ADR (GAP-03).
_RUN_ADMISSION = InProcessRunAdmission()


def get_run_admission():
    return _RUN_ADMISSION


from ..infrastructure.visual_store import InMemoryVisualStore
_VISUAL_STORE = InMemoryVisualStore()


def get_visual_store():
    return _VISUAL_STORE


def get_stream_profile(request: Request):
    values = request.query_params.getlist('stream_profile')
    if len(values) > 1 or values and values[0] not in ('v1', 'visual-v2'):
        raise RunError('INVALID_INPUT', 'El perfil de avance solicitado no es válido.')
    return values[0] if values else 'v1'


router = APIRouter(prefix="/runs", route_class=RunRoute)


@router.post("", status_code=201, response_class=StreamingResponse,
    responses={201:{"content":{"application/x-ndjson":{}}}})
def start_run(request: RunRequestV1, user=Depends(run_permission("optimization.execute")),
              unit_of_work=Depends(get_run_unit_of_work), calculator=Depends(get_run_calculator),
              stock_counter=Depends(get_stock_counter), admission=Depends(get_run_admission),
              profile=Depends(get_stream_profile), visual_store=Depends(get_visual_store)):
    lease = admission.acquire(user.user_id)                                 # TA-037 P2: 503 if busy
    visual_session = None
    try:
        if profile == 'visual-v2':
            visual_session = visual_store.reserve()
        accepted = AcceptRun(unit_of_work, stock_counter).execute(request.order_ids, user.user_id)
        if visual_session is not None:
            visual_session.bind(accepted.optimization_id, accepted.result.problem.config.resolution_mm)
        kwargs = {'visual_session': visual_session} if visual_session is not None else {}
        stream = LiveRunStream(unit_of_work, calculator, lease=lease, **kwargs)
    except BaseException:
        lease.release()  # rejected or failed before streaming: the slot is free again
        if visual_session is not None:
            visual_session.abort()
        raise
    return RunStreamingResponse(stream.lines(accepted), stream=stream, status_code=201,
        media_type="application/x-ndjson", headers={"Location":f"/api/optimization/runs/{accepted.optimization_id}",
                                                 "Cache-Control":"no-cache", "X-Accel-Buffering":"no"})


@router.get("/{id_optimizacion}", response_model=RunResponseV1)
def get_run(id_optimizacion: Annotated[int, Path(gt=0, le=2147483647)],
            user=Depends(run_permission("optimization.view")), unit_of_work=Depends(get_run_unit_of_work)):
    with unit_of_work() as uow:
        run = uow.runs.get(id_optimizacion)
    return run_response(run)


def visual_response(model):
    payload = model.model_dump_json()
    if len(payload.encode('utf-8')) > MAX_RESPONSE_BYTES:
        raise RunError('INVALID_INPUT', 'El detalle solicitado es demasiado grande. Solicita una ventana menor.')
    return Response(payload, media_type='application/json', headers={'Cache-Control': 'no-store'})


@router.get('/{id_optimizacion}/visual', response_model=VisualManifestV2)
def get_visual_manifest(id_optimizacion: Annotated[int, Path(gt=0, le=2147483647)],
        offset: Annotated[int, Query(ge=0, le=1024)] = 0,
        limit: Annotated[int, Query(gt=0, le=64)] = 64,
        user=Depends(run_permission('optimization.view')), unit_of_work=Depends(get_run_unit_of_work),
        store=Depends(get_visual_store)):
    with unit_of_work() as uow:
        uow.runs.get(id_optimizacion)
    session = store.get(id_optimizacion)
    items, revision, next_offset = session.manifest(offset, limit)
    return visual_response(VisualManifestV2(schema_version=2, id_optimizacion=id_optimizacion,
        revision=revision, items=[describe_record(session, record) for record in items], next_offset=next_offset))


@router.get('/{id_optimizacion}/visual/masks/{mask_ref}', response_model=VisualMaskV2)
def get_visual_mask(id_optimizacion: Annotated[int, Path(gt=0, le=2147483647)],
        mask_ref: Annotated[str, Path(pattern=r'^[a-f0-9]{32}$')],
        row_start: Annotated[int, Query(ge=0)] = 0,
        row_count: Annotated[int | None, Query(gt=0, le=256)] = None,
        column_start: Annotated[int, Query(ge=0)] = 0,
        column_count: Annotated[int | None, Query(gt=0, le=1024)] = None,
        user=Depends(run_permission('optimization.view')), unit_of_work=Depends(get_run_unit_of_work),
        store=Depends(get_visual_store)):
    with unit_of_work() as uow:
        uow.runs.get(id_optimizacion)
    session = store.get(id_optimizacion)
    record = session.get(mask_ref)
    window = mask_window(record, row_start=row_start, row_count=row_count,
                         column_start=column_start, column_count=column_count)
    spans = window.pop('spans_by_row')
    return visual_response(VisualMaskV2(**describe_record(session, record), schema_version=2,
        geometria_original=dict(record.owner.geometry), geometria=dict(record.orientation.geometry),
        window=window, spans_by_row=spans))


async def require_empty_confirmation_body(request: Request):
    if (await request.body()).strip():
        raise RunError("INVALID_INPUT", "La confirmación no recibe un cuerpo de solicitud.")


@router.post("/{id_optimizacion}/confirm", response_model=ConfirmResponseV1)
def confirm_run(id_optimizacion: Annotated[int, Path(gt=0, le=2147483647)],
                user=Depends(run_permission("optimization.confirm")), unit_of_work=Depends(get_run_unit_of_work),
                no_body=Depends(require_empty_confirmation_body)):
    return confirmation_response(ConfirmRun(unit_of_work).execute(id_optimizacion, user.user_id))
