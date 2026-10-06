# require_permission vive en autenticación para que la compartan todos los
# módulos; se reexporta aquí para no cambiar los imports de inventario.
from app.modules.authentication.presentation.dependencies import require_permission  # noqa: F401
from app.modules.inventory.application.service import InventoryService

def get_inventory_service() -> InventoryService:
    from app.shared.database.session import SessionLocal
    from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
    repository = SqlAlchemyInventoryRepository(SessionLocal)
    return InventoryService(repository)
