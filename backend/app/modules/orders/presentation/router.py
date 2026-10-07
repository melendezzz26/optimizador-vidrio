from fastapi import APIRouter, Depends, HTTPException, status
from .schemas import CreateOrderRequest, CreateOrderResponse
from ..application.use_cases import CreateOrderUseCase
from ..domain.exceptions import InvalidOrderException, InvalidGeometryException
from ..infrastructure.dependencies import get_create_order_use_case, get_current_user, require_permission
from app.modules.authentication.domain.user import AuthenticatedUser

router = APIRouter(prefix="/api/orders", tags=["Pedidos"])

@router.post("", response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    request: CreateOrderRequest,
    use_case: CreateOrderUseCase = Depends(get_create_order_use_case),
    user: AuthenticatedUser = Depends(require_permission("GESTIONAR_PEDIDOS"))
):
    try:
        piezas_dict = [p.dict() for p in request.piezas]
        id_pedido = use_case.execute(
            id_usuario=user.id_usuario,
            id_tipo_vidrio=request.id_tipo_vidrio,
            espesor_mm=request.espesor_mm,
            piezas_raw=piezas_dict
        )
        return CreateOrderResponse(id_pedido=id_pedido, estado="PENDIENTE")
    except InvalidOrderException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except InvalidGeometryException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
