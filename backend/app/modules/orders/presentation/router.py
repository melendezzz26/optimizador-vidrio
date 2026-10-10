import logging

from fastapi import APIRouter, Depends, HTTPException, Path, status, Query
from datetime import date
from typing import Optional
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from .schemas import CreateOrderRequest, CreateOrderResponse, OrderResponse
from ..application.use_cases import CreateOrderUseCase, GetOrderUseCase, ListOrdersUseCase, UpdateOrderUseCase, CancelOrderUseCase
from ..domain.exceptions import (
    InvalidOrderException,
    InvalidGeometryException,
    OrderNotFoundException,
    OrderStateConflictException,
)
from .dependencies import get_create_order_use_case, get_order_use_case, get_list_orders_use_case, get_update_order_use_case, get_cancel_order_use_case
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

permiso_gestionar_pedidos = require_permission("GESTIONAR_PEDIDOS")

@router.post("", response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)

def create_order(
    request: CreateOrderRequest,
    user: AuthenticatedUser = Depends(permiso_gestionar_pedidos),
    use_case: CreateOrderUseCase = Depends(get_create_order_use_case),
):
    try:
        piezas_dict = [p.model_dump() for p in request.piezas]
        id_pedido = use_case.execute(
            id_usuario=user.user_id,
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

@router.get("")
def list_orders(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Registros por página"),
    estado: Optional[str] = Query(None, description="Filtrar por estado del pedido"),
    cliente: Optional[str] = Query(None, description="Filtrar por nombre de cliente"),
    fecha: Optional[date] = Query(None, description="Filtrar por fecha exacta (YYYY-MM-DD)"),
    user: AuthenticatedUser = Depends(permiso_gestionar_pedidos),
    use_case: ListOrdersUseCase = Depends(get_list_orders_use_case)
):
    try:
        return use_case.execute(page=page, limit=limit, estado=estado, cliente=cliente, fecha=fecha)
    except Exception as e:
        logger.exception("Order list retrieval failed")
        raise HTTPException(status_code=500, detail="No se pudieron cargar los pedidos.") from e

@router.get("/{id_pedido}", response_model=OrderResponse)
def get_order(
    id_pedido: int = Path(gt=0, le=2147483647),
    user: AuthenticatedUser = Depends(permiso_gestionar_pedidos),
    use_case: GetOrderUseCase = Depends(get_order_use_case),
):
    try:
        return use_case.execute(id_pedido)
    except OrderNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Order retrieval failed")
        raise HTTPException(status_code=500, detail="No se pudo consultar el pedido. Inténtalo otra vez.") from e

@router.put("/{id_pedido}", status_code=status.HTTP_200_OK)
def update_order(
    request: CreateOrderRequest,
    id_pedido: int = Path(gt=0, le=2147483647),
    user: AuthenticatedUser = Depends(permiso_gestionar_pedidos),
    use_case: UpdateOrderUseCase = Depends(get_update_order_use_case),
):
    try:
        piezas_dict = [p.model_dump() for p in request.piezas]
        use_case.execute(id_pedido=id_pedido, piezas_raw=piezas_dict)
        return {"message": "Pedido actualizado exitosamente", "id_pedido": id_pedido}
    except OrderNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except OrderStateConflictException as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except InvalidOrderException as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except InvalidGeometryException as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception("Order update failed")
        raise HTTPException(status_code=500, detail="No se pudo actualizar el pedido. Inténtalo otra vez.") from e

@router.delete("/{id_pedido}", status_code=status.HTTP_200_OK)
def delete_order(
    id_pedido: int = Path(gt=0, le=2147483647),
    user: AuthenticatedUser = Depends(permiso_gestionar_pedidos),
    use_case: CancelOrderUseCase = Depends(get_cancel_order_use_case),
):
    try:
        use_case.execute(id_pedido=id_pedido)
        return {"message": "Pedido cancelado exitosamente", "id_pedido": id_pedido}
    except OrderNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except OrderStateConflictException as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except InvalidOrderException as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception("Order cancellation failed")
        raise HTTPException(status_code=500, detail="No se pudo cancelar el pedido.") from e
