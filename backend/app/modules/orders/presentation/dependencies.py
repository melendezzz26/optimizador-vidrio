from fastapi import Depends
from sqlalchemy.orm import Session
from ..application.use_cases import CreateOrderUseCase, GetOrderUseCase, ListOrdersUseCase, UpdateOrderUseCase, CancelOrderUseCase
from app.modules.authentication.presentation.dependencies import get_database_session, require_permission
from ..application.ports import OrderRepositoryPort
from ..application.ports import StockCandidateChecker
from app.modules.clients.application.ports import ClientLookup


def get_order_repository(db: Session = Depends(get_database_session)) -> OrderRepositoryPort:
    from ..infrastructure.repositories import SQLAlchemyOrderRepository
    return SQLAlchemyOrderRepository(db)

def get_client_lookup(db: Session = Depends(get_database_session)) -> ClientLookup:
    from app.modules.clients.infrastructure.sqlalchemy_client_repository import SqlAlchemyClientRepository
    return SqlAlchemyClientRepository(db)

def get_inventory_session_factory():
    """Return the shared session factory for Inventory's isolated read transaction."""
    from app.shared.database.session import SessionLocal

    return SessionLocal

def get_stock_candidate_checker(
    session_factory=Depends(get_inventory_session_factory),
) -> StockCandidateChecker:
    from ..infrastructure.stock_candidate_checker import InventoryStockCandidateChecker

    return InventoryStockCandidateChecker(session_factory)


def get_create_order_use_case(
    repo: OrderRepositoryPort = Depends(get_order_repository),
    clients: ClientLookup = Depends(get_client_lookup),
    stock_candidate_checker: StockCandidateChecker = Depends(get_stock_candidate_checker),
) -> CreateOrderUseCase:
    return CreateOrderUseCase(repo, clients, stock_candidate_checker)


def get_order_use_case(repo: OrderRepositoryPort = Depends(get_order_repository)) -> GetOrderUseCase:
    return GetOrderUseCase(repo)



def get_list_orders_use_case(repo: OrderRepositoryPort = Depends(get_order_repository)) -> ListOrdersUseCase:
    return ListOrdersUseCase(repo)

def get_update_order_use_case(repo: OrderRepositoryPort = Depends(get_order_repository)) -> UpdateOrderUseCase:
    return UpdateOrderUseCase(repo)

def get_cancel_order_use_case(repo: OrderRepositoryPort = Depends(get_order_repository)) -> CancelOrderUseCase:
    return CancelOrderUseCase(repo)
