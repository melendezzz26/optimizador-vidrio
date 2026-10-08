import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from .schemas import CreateOrderRequest, CreateOrderResponse
from ..application.use_cases import CreateOrderUseCase
from ..domain.exceptions import InvalidOrderException, InvalidGeometryException
from ..infrastructure.dependencies import get_create_order_use_case
from app.modules.authentication.presentation.dependencies import require_permission
from app.modules.authentication.domain.user import AuthenticatedUser

class OrderRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def validate_request(request):
            try:
                return await handler(request)
            except RequestValidationError as error:
                # Overflowing JSON numbers (e.g. 1e400) parse as infinity.
                # Do not echo input: non-finite values cannot be JSON encoded.
                detail = [{key: item[key] for key in ("loc", "msg", "type")}
                          for item in error.errors()]
                raise HTTPException(status_code=422, detail=detail) from error

        return validate_request


router = APIRouter(prefix="/api/orders", tags=["Pedidos"], route_class=OrderRoute)
logger = logging.getLogger(__name__)

@router.post("", response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    request: CreateOrderRequest,
    user: AuthenticatedUser = Depends(require_permission("GESTIONAR_PEDIDOS")),
    use_case: CreateOrderUseCase = Depends(get_create_order_use_case),
):
    try:
        piezas_dict = [p.model_dump() for p in request.piezas]
        id_pedido = use_case.execute(
            id_usuario=user.user_id,
            id_tipo_vidrio=request.id_tipo_vidrio,
            espesor_mm=request.espesor_mm,
            piezas_raw=piezas_dict
        )
        return CreateOrderResponse(id_pedido=id_pedido, estado="PENDIENTE")
    except InvalidOrderException as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except InvalidGeometryException as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception("Order creation failed")
        raise HTTPException(status_code=500, detail="No se pudo guardar el pedido. Inténtalo otra vez.") from e
