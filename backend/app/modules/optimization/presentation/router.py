import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from app.modules.authentication.presentation.dependencies import require_permission
from ..application.errors import InvalidRasterInput, OptimizationNotFoundError, OptimizationStateError
from ..domain.raster_mask import RasterizationError
from .dependencies import get_start_use_case, get_rasterize_use_case
from .schemas import StartRequest, StartResponse, RasterizeRequest, RasterizeResponse
from .serialization import raster_response

logger = logging.getLogger(__name__)


class OptimizationRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe_validation(request):
            try:
                return await handler(request)
            except RequestValidationError as error:
                detail = [{key: item[key] for key in ("loc", "msg", "type")}
                          for item in error.errors()]
                raise HTTPException(422, detail=detail) from error

        return safe_validation


router = APIRouter(prefix="/api/optimization", tags=["Optimización"], route_class=OptimizationRoute)
execute_permission = require_permission("optimization.execute")


def invoke(operation):
    try:
        return operation()
    except OptimizationNotFoundError as error:
        raise HTTPException(404, detail=str(error)) from error
    except OptimizationStateError as error:
        raise HTTPException(409, detail=str(error)) from error
    except (InvalidRasterInput, RasterizationError) as error:
        raise HTTPException(422, detail=str(error)) from error
    except Exception as error:
        logger.exception("Optimization operation failed")
        raise HTTPException(500, detail="No se pudo completar la operación. Inténtalo otra vez.") from error


@router.post("/start", response_model=StartResponse)
def start_optimization(request: StartRequest, user=Depends(execute_permission),
                       use_case=Depends(get_start_use_case)):
    return invoke(lambda: use_case.execute(request.id_pedido))


@router.post("/rasterize", response_model=RasterizeResponse)
def rasterize_order_piece(request: RasterizeRequest, user=Depends(execute_permission),
                          use_case=Depends(get_rasterize_use_case)):
    def calculate():
        result = use_case.execute(request.id_pedido, request.id_pieza, request.resolution_mm)
        # Preflight acota filas/vértices/bytes antes del cálculo. Esta codificación
        # compacta es exactamente la medida por el benchmark.
        return Response(raster_response(result).model_dump_json(), media_type="application/json")
    return invoke(calculate)


# New T1 transport is isolated from the historical HU-015 error contract.
from .run_routes import router as run_router  # noqa: E402
router.include_router(run_router)
