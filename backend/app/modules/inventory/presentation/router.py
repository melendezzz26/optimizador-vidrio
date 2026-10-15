from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.inventory.application.dto import CreateTipoVidrio, CreatePlancha, UpdatePlancha, CreateRetazo, UpdateRetazo
from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.domain.exceptions import InventoryNotFoundError, InventoryConflictError, InventoryValidationError, InvalidGeometryError
from app.modules.inventory.domain.writeoff import BajaManual
from app.modules.authentication.domain.user import AuthenticatedUser
from app.modules.inventory.presentation.dependencies import get_inventory_service, require_permission
from app.modules.inventory.presentation.schemas import (
    TipoVidrioCreate, TipoVidrioResponse,
    PlanchaCreate, PlanchaPatch, PlanchaResponse,
    RetazoCreate, RetazoPatch, RetazoResponse,
    BajaManualRequest, BajaPlanchaRequest, BajaManualResponse, MovimientoInventarioResponse,
    MovimientoHistorialResponse,
)

router = APIRouter(prefix="/api/inventory", tags=["Inventario"])


def _http_detail_response(description: str, example: str) -> dict:
    """Describe el formato HTTPException que ya devuelve Inventory."""
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"detail": {"type": "string"}},
                    "required": ["detail"],
                },
                "example": {"detail": example},
            }
        },
    }


def _validation_response(description: str) -> dict:
    """Documenta validación FastAPI y errores de validación del dominio."""
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {
                    "oneOf": [
                        {"$ref": "#/components/schemas/HTTPValidationError"},
                        {
                            "type": "object",
                            "properties": {"detail": {"type": "string"}},
                            "required": ["detail"],
                        },
                    ]
                }
            }
        },
    }


@contextmanager
def handle_domain_exceptions():
    try:
        yield
    except InventoryNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InventoryConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (InventoryValidationError, InvalidGeometryError) as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

# --- Tipos de Vidrio ---

@router.post("/tipos-vidrio", response_model=TipoVidrioResponse, status_code=status.HTTP_201_CREATED)
def create_tipo_vidrio(
    data: TipoVidrioCreate,
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("inventory.manage"))
):
    dto = CreateTipoVidrio(nombre=data.nombre, descripcion=data.descripcion)
    with handle_domain_exceptions():
        return service.create_tipo_vidrio(dto)

@router.get("/tipos-vidrio", response_model=list[TipoVidrioResponse], status_code=status.HTTP_200_OK)
def list_tipos_vidrio(
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("inventory.view"))
):
    with handle_domain_exceptions():
        return service.list_tipos_vidrio()

# --- Planchas ---

@router.post("/planchas", response_model=PlanchaResponse, status_code=status.HTTP_201_CREATED)
def create_plancha(
    data: PlanchaCreate,
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("inventory.manage"))
):
    dto = CreatePlancha(
        ancho_mm=data.ancho_mm, alto_mm=data.alto_mm, espesor_mm=data.espesor_mm,
        cantidad=data.cantidad, id_tipo_vidrio=data.id_tipo_vidrio
    )
    with handle_domain_exceptions():
        return service.create_plancha(dto)

@router.get("/planchas", response_model=list[PlanchaResponse], status_code=status.HTTP_200_OK)
def list_planchas(
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("inventory.view"))
):
    with handle_domain_exceptions():
        return service.list_planchas()


@router.get(
    "/planchas/{id_plancha}/movimientos",
    response_model=list[MovimientoHistorialResponse],
    status_code=status.HTTP_200_OK,
    responses={
        401: _http_detail_response("No autenticado.", "Debes iniciar sesión."),
        403: _http_detail_response(
            "Sin permiso para consultar stock.",
            "No tienes permiso para realizar esta acción.",
        ),
        404: _http_detail_response("Plancha inexistente.", "Plancha inexistente."),
        422: _validation_response("Validación del parámetro de ruta o del identificador."),
    },
)
def list_plancha_movements(
    id_plancha: int,
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("inventory.view")),
):
    with handle_domain_exceptions():
        movements = service.list_plancha_movements(id_plancha)
        return [
            MovimientoHistorialResponse.model_validate(item, from_attributes=True)
            for item in movements
        ]

@router.patch("/planchas/{id_plancha}", response_model=PlanchaResponse, status_code=status.HTTP_200_OK)
def update_plancha(
    id_plancha: int,
    data: PlanchaPatch,
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("inventory.manage"))
):
    dump = data.model_dump(exclude_unset=True)
    if not dump:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="PATCH vacío")
    for k, v in dump.items():
        if v is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Explicit null not allowed for {k}")

    dto = UpdatePlancha(
        ancho_mm=dump.get("ancho_mm"), alto_mm=dump.get("alto_mm"), espesor_mm=dump.get("espesor_mm"),
        cantidad=dump.get("cantidad"), estado=dump.get("estado"), id_tipo_vidrio=dump.get("id_tipo_vidrio")
    )
    with handle_domain_exceptions():
        return service.update_plancha(id_plancha, dto)


@router.post(
    "/planchas/{id_plancha}/baja",
    response_model=BajaManualResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: _http_detail_response("No autenticado.", "Debes iniciar sesión."),
        403: _http_detail_response(
            "Sin permiso para gestionar planchas.",
            "No tienes permiso para realizar esta acción.",
        ),
        404: _http_detail_response("Plancha inexistente.", "Plancha inexistente."),
        409: _http_detail_response(
            "La plancha no tiene stock disponible.",
            "La plancha no tiene stock disponible.",
        ),
        422: _validation_response("Validación del cuerpo, parámetro o regla de entrada."),
    },
)
def writeoff_plancha(
    id_plancha: int,
    data: BajaPlanchaRequest,
    service: InventoryService = Depends(get_inventory_service),
    actor: AuthenticatedUser = Depends(require_permission("inventory.manage")),
):
    with handle_domain_exceptions():
        command = BajaManual(
            tipo_evento=data.tipo_evento,
            motivo=data.motivo,
            observacion=data.observacion,
            cantidad_afectada=data.cantidad_afectada,
        )
        result = service.writeoff_plancha(
            id_plancha, command, id_usuario=actor.user_id,
        )
        return BajaManualResponse(
            estado=result.estado,
            cantidad=result.cantidad,
            movimiento=MovimientoInventarioResponse.model_validate(
                result.movimiento, from_attributes=True,
            ),
        )

# --- Retazos ---

@router.post("/retazos", response_model=RetazoResponse, status_code=status.HTTP_201_CREATED)
def create_retazo(
    data: RetazoCreate,
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("inventory.manage"))
):
    dto = CreateRetazo(
        codigo=data.codigo, espesor_mm=data.espesor_mm,
        geometria=data.geometria.model_dump(), id_tipo_vidrio=data.id_tipo_vidrio
    )
    with handle_domain_exceptions():
        return service.create_retazo(dto)

@router.get("/retazos", response_model=list[RetazoResponse], status_code=status.HTTP_200_OK)
def list_retazos(
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("inventory.view"))
):
    with handle_domain_exceptions():
        return service.list_retazos()


@router.get(
    "/retazos/{id_retazo}/movimientos",
    response_model=list[MovimientoHistorialResponse],
    status_code=status.HTTP_200_OK,
    responses={
        401: _http_detail_response("No autenticado.", "Debes iniciar sesión."),
        403: _http_detail_response(
            "Sin permiso para consultar stock.",
            "No tienes permiso para realizar esta acción.",
        ),
        404: _http_detail_response("Retazo inexistente.", "Retazo inexistente."),
        422: _validation_response("Validación del parámetro de ruta o del identificador."),
    },
)
def list_retazo_movements(
    id_retazo: int,
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("inventory.view")),
):
    with handle_domain_exceptions():
        movements = service.list_retazo_movements(id_retazo)
        return [
            MovimientoHistorialResponse.model_validate(item, from_attributes=True)
            for item in movements
        ]

@router.patch("/retazos/{id_retazo}", response_model=RetazoResponse, status_code=status.HTTP_200_OK)
def update_retazo(
    id_retazo: int,
    data: RetazoPatch,
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("inventory.manage"))
):
    dump = data.model_dump(exclude_unset=True)
    if not dump:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="PATCH vacío")
    for k, v in dump.items():
        if v is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Explicit null not allowed for {k}")

    geometria = None
    if "geometria" in dump:
        geometria = data.geometria.model_dump()

    dto = UpdateRetazo(
        codigo=dump.get("codigo"), espesor_mm=dump.get("espesor_mm"),
        geometria=geometria, estado=dump.get("estado"), id_tipo_vidrio=dump.get("id_tipo_vidrio")
    )
    with handle_domain_exceptions():
        return service.update_retazo(id_retazo, dto)


@router.post(
    "/retazos/{id_retazo}/baja",
    response_model=BajaManualResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: _http_detail_response("No autenticado.", "Debes iniciar sesión."),
        403: _http_detail_response(
            "Sin permiso para gestionar retazos.",
            "No tienes permiso para realizar esta acción.",
        ),
        404: _http_detail_response("Retazo inexistente.", "Retazo inexistente."),
        409: _http_detail_response(
            "El retazo ya tiene una baja manual registrada.",
            "El retazo ya tiene una baja manual registrada.",
        ),
        422: _validation_response("Validación del cuerpo, parámetro o regla de entrada."),
    },
)
def writeoff_retazo(
    id_retazo: int,
    data: BajaManualRequest,
    service: InventoryService = Depends(get_inventory_service),
    actor: AuthenticatedUser = Depends(require_permission("inventory.manage")),
):
    with handle_domain_exceptions():
        command = BajaManual(
            tipo_evento=data.tipo_evento,
            motivo=data.motivo,
            observacion=data.observacion,
        )
        result = service.writeoff_retazo(
            id_retazo, command, id_usuario=actor.user_id,
        )
        return BajaManualResponse(
            estado=result.estado,
            cantidad=result.cantidad,
            movimiento=MovimientoInventarioResponse.model_validate(
                result.movimiento, from_attributes=True,
            ),
        )
