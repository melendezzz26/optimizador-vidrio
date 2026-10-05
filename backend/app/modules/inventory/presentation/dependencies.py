from fastapi import Depends, HTTPException, status

from app.core.permissions import tiene_permiso
from app.routers.auth import usuario_actual
from app.modules.inventory.application.service import InventoryService

def require_permission(permiso: str):
    def checker(payload: dict = Depends(usuario_actual)) -> dict:
        rol = payload.get("rol")
        if not rol or not tiene_permiso(rol, permiso):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"No tienes el permiso: {permiso}")
        return payload
    return checker

def get_inventory_service() -> InventoryService:
    from app.shared.database.session import SessionLocal
    from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
    repository = SqlAlchemyInventoryRepository(SessionLocal)
    return InventoryService(repository)
