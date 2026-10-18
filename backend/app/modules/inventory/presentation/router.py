from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.inventory.application.dto import CreateTipoVidrio, CreatePlancha, UpdatePlancha, CreateRetazo, UpdateRetazo
from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.domain.exceptions import InventoryNotFoundError, InventoryConflictError, InventoryValidationError, InvalidGeometryError
from app.modules.inventory.presentation.dependencies import get_inventory_service, require_permission
from app.modules.inventory.presentation.schemas import (
    TipoVidrioCreate, TipoVidrioResponse,
    PlanchaCreate, PlanchaPatch, PlanchaResponse,
    RetazoCreate, RetazoPatch, RetazoResponse
)

router = APIRouter(prefix="/api/inventory", tags=["Inventario"])

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
    _ = Depends(require_permission("GESTIONAR_TIPOS_VIDRIO"))
):
    dto = CreateTipoVidrio(nombre=data.nombre, descripcion=data.descripcion)
    with handle_domain_exceptions():
        return service.create_tipo_vidrio(dto)

@router.get("/tipos-vidrio", response_model=list[TipoVidrioResponse], status_code=status.HTTP_200_OK)
def list_tipos_vidrio(
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("CONSULTAR_TIPOS_VIDRIO"))
):
    with handle_domain_exceptions():
        return service.list_tipos_vidrio()

# --- Planchas ---

@router.post("/planchas", response_model=PlanchaResponse, status_code=status.HTTP_201_CREATED)
def create_plancha(
    data: PlanchaCreate,
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("GESTIONAR_PLANCHAS"))
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
    _ = Depends(require_permission("CONSULTAR_STOCK"))
):
    with handle_domain_exceptions():
        return service.list_planchas()

@router.patch("/planchas/{id_plancha}", response_model=PlanchaResponse, status_code=status.HTTP_200_OK)
def update_plancha(
    id_plancha: int,
    data: PlanchaPatch,
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("GESTIONAR_PLANCHAS"))
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

# --- Retazos ---

@router.post("/retazos", response_model=RetazoResponse, status_code=status.HTTP_201_CREATED)
def create_retazo(
    data: RetazoCreate,
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("GESTIONAR_RETAZOS"))
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
    _ = Depends(require_permission("CONSULTAR_STOCK"))
):
    with handle_domain_exceptions():
        return service.list_retazos()

@router.patch("/retazos/{id_retazo}", response_model=RetazoResponse, status_code=status.HTTP_200_OK)
def update_retazo(
    id_retazo: int,
    data: RetazoPatch,
    service: InventoryService = Depends(get_inventory_service),
    _ = Depends(require_permission("GESTIONAR_RETAZOS"))
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
