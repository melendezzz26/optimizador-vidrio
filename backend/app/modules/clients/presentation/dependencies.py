from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.authentication.presentation.dependencies import get_database_session
from app.modules.clients.application.ports import ClientRepository


def get_client_repository(db: Session = Depends(get_database_session)) -> ClientRepository:
    # Mantener el arranque de la API sin importar engine ni abrir conexiones.
    from app.modules.clients.infrastructure.sqlalchemy_client_repository import SqlAlchemyClientRepository

    return SqlAlchemyClientRepository(db)
