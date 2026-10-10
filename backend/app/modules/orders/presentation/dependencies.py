from fastapi import Depends
from sqlalchemy.orm import Session
from ..application.use_cases import CreateOrderUseCase, GetOrderUseCase, ListOrdersUseCase, UpdateOrderUseCase
from app.modules.authentication.presentation.dependencies import get_database_session, require_permission
from ..application.ports import OrderRepositoryPort


def get_order_repository(db: Session = Depends(get_database_session)) -> OrderRepositoryPort:
    from ..infrastructure.repositories import SQLAlchemyOrderRepository
    return SQLAlchemyOrderRepository(db)

def get_create_order_use_case(repo: OrderRepositoryPort = Depends(get_order_repository)) -> CreateOrderUseCase:
    return CreateOrderUseCase(repo)


def get_order_use_case(repo: OrderRepositoryPort = Depends(get_order_repository)) -> GetOrderUseCase:
    return GetOrderUseCase(repo)

def get_list_orders_use_case(repo: OrderRepositoryPort = Depends(get_order_repository)) -> ListOrdersUseCase:
    return ListOrdersUseCase(repo)

def get_update_order_use_case(repo: OrderRepositoryPort = Depends(get_order_repository)) -> UpdateOrderUseCase:
    return UpdateOrderUseCase(repo)