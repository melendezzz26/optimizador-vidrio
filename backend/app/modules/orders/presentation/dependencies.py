from app.shared.database.session import SessionLocal
from fastapi import Depends
from sqlalchemy.orm import Session
from ..application.use_cases import CreateOrderUseCase
from app.modules.authentication.presentation.dependencies import get_database_session, require_permission
from ..application.ports import OrderRepositoryPort

from app.modules.orders.application.use_cases import CreateOrderUseCase

def get_order_repository(db: Session = Depends(get_database_session)) -> OrderRepositoryPort:
    from ..infrastructure.repositories import SQLAlchemyOrderRepository
    return SQLAlchemyOrderRepository(db)

def get_create_order_use_case(repo: OrderRepositoryPort = Depends(get_order_repository)) -> CreateOrderUseCase:
    return CreateOrderUseCase(repo)