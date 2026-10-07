"""Dependencias de FastAPI del módulo de usuarios."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.authentication.presentation.dependencies import (
    get_database_session,
    require_permission,
)
from app.modules.users.application.ports import UserRepository

# Permiso de la matriz que protege todas las rutas del módulo (RN-01).
require_user_management = require_permission("GESTIONAR_USUARIOS")


def get_user_repository(db: Session = Depends(get_database_session)) -> UserRepository:
    """Único punto donde se elige la implementación real del repositorio."""
    # Import diferido: la base y los modelos se cargan al atender la petición,
    # no al arrancar la API (regla que comprueba test_lazy_db_import).
    from app.modules.users.infrastructure.sqlalchemy_user_repository import (
        SqlAlchemyUserRepository,
    )

    return SqlAlchemyUserRepository(db)
