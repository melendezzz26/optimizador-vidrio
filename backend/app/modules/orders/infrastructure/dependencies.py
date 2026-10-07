from fastapi import Depends
from sqlalchemy.orm import Session
from app.shared.database import get_db
from .repositories import SQLAlchemyOrderRepository
from ..application.use_cases import CreateOrderUseCase
from app.modules.authentication.presentation.dependencies import get_current_user, require_permission

def get_order_repository(db: Session = Depends(get_db)) -> SQLAlchemyOrderRepository:
    return SQLAlchemyOrderRepository(db)

def get_create_order_use_case(repo: SQLAlchemyOrderRepository = Depends(get_order_repository)) -> CreateOrderUseCase:
    return CreateOrderUseCase(repo)
