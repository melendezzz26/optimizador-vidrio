from app.modules.orders.application.ports import OrderMutationResult, OrderOptimizationPort
from app.modules.orders.application.persisted_pieces import validate_persisted_piece

from ..application.errors import InvalidRasterInput, OptimizationNotFoundError, OptimizationStateError


class OrdersOptimizationAdapter:
    def __init__(self, repository: OrderOptimizationPort):
        self.repository = repository

    def get_order(self, id_pedido):
        return self.repository.get_order(id_pedido)

    def validate_piece(self, piece):
        try:
            validate_persisted_piece(piece)
        except (ValueError, TypeError, OverflowError) as error:
            raise InvalidRasterInput("La pieza persistida no tiene una geometría o metadatos válidos.") from error

    def start_pending(self, id_pedido, validate):
        result = self.repository.start_optimization(id_pedido, validate)
        if result is OrderMutationResult.NOT_FOUND:
            raise OptimizationNotFoundError("Pedido no encontrado.")
        if result is OrderMutationResult.STATE_CONFLICT:
            raise OptimizationStateError("Solo un pedido PENDIENTE puede iniciar optimización.")
        if result is not OrderMutationResult.UPDATED:
            raise RuntimeError("Orders no confirmó la transición.")
