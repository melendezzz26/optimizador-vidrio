"""T1 run routes; legacy HU-015 routes keep their original error representation."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy.exc import DBAPIError
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute

from ..application.runs import AcceptRun
from ..application.errors import RunError
from .run_schemas import RunRequestV1, RunResponseV1, ConfirmResponseV1
from ..application.confirmation import ConfirmRun
from .confirmation_serialization import confirmation_response
from .run_serialization import run_response
from .run_stream import LiveRunStream, RunStreamingResponse
from .run_auth import run_permission

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
                          "STOCK_CONFLICT":409, "ALREADY_CONFIRMED":409, "NOT_CONFIRMABLE":422}.get(error.code,500)
                raise HTTPException(status, detail=dict(code=error.code, message=error.message)) from error
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


router = APIRouter(prefix="/runs", route_class=RunRoute)


@router.post("", status_code=201, response_class=StreamingResponse,
    responses={201:{"content":{"application/x-ndjson":{}}}})
def start_run(request: RunRequestV1, user=Depends(run_permission("optimization.execute")),
              unit_of_work=Depends(get_run_unit_of_work), calculator=Depends(get_run_calculator)):
    accepted = AcceptRun(unit_of_work).execute(request.order_ids, user.user_id)
    return RunStreamingResponse(LiveRunStream(unit_of_work, calculator).lines(accepted), status_code=201,
        media_type="application/x-ndjson", headers={"Location":f"/api/optimization/runs/{accepted.optimization_id}",
                                                 "Cache-Control":"no-cache", "X-Accel-Buffering":"no"})


@router.get("/{id_optimizacion}", response_model=RunResponseV1)
def get_run(id_optimizacion: Annotated[int, Path(gt=0, le=2147483647)],
            user=Depends(run_permission("optimization.view")), unit_of_work=Depends(get_run_unit_of_work)):
    with unit_of_work() as uow:
        run = uow.runs.get(id_optimizacion)
    return run_response(run)


async def require_empty_confirmation_body(request: Request):
    if (await request.body()).strip():
        raise RunError("INVALID_INPUT", "La confirmación no recibe un cuerpo de solicitud.")


@router.post("/{id_optimizacion}/confirm", response_model=ConfirmResponseV1)
def confirm_run(id_optimizacion: Annotated[int, Path(gt=0, le=2147483647)],
                user=Depends(run_permission("optimization.confirm")), unit_of_work=Depends(get_run_unit_of_work),
                no_body=Depends(require_empty_confirmation_body)):
    return confirmation_response(ConfirmRun(unit_of_work).execute(id_optimizacion, user.user_id))
