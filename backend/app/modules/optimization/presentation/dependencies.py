from fastapi import Depends

from app.modules.orders.presentation.dependencies import get_order_repository
from ..application.resource_policy import DEFAULT_RASTER_BUDGET
from ..application.use_cases import StartOptimizationUseCase, RasterizeOrderPieceUseCase
from ..infrastructure.orders_adapter import OrdersOptimizationAdapter


def get_optimization_orders(repository=Depends(get_order_repository)):
    return OrdersOptimizationAdapter(repository)


def get_start_use_case(orders=Depends(get_optimization_orders)):
    return StartOptimizationUseCase(orders, DEFAULT_RASTER_BUDGET)


def get_rasterize_use_case(orders=Depends(get_optimization_orders)):
    return RasterizeOrderPieceUseCase(orders, DEFAULT_RASTER_BUDGET)
