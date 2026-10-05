from fastapi import Depends, HTTPException, status

from app.core.permissions import tiene_permiso
from app.modules.authentication.domain.user import AuthenticatedUser
from app.modules.authentication.presentation.dependencies import get_current_user
from app.modules.inventory.application.service import InventoryService

def require_permission(permiso: str):
    def checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        # El rol es el vigente en la base, no el que traía el token.
        if not tiene_permiso(user.role, permiso):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"No tienes el permiso: {permiso}")
        return user
    return checker

def get_inventory_service() -> InventoryService:
    from app.shared.database.session import SessionLocal
    from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
    repository = SqlAlchemyInventoryRepository(SessionLocal)
    return InventoryService(repository)
