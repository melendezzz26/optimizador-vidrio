from .errors import InvalidRasterInput, OptimizationNotFoundError, OptimizationStateError
from .ports import OptimizationOrders, RasterizedPiece
from .resource_policy import RasterBudget, positive_resolution
from ..domain.rasterizer import DEFAULT_RESOLUTION_MM, rasterize_geometry


def validate_id(value):
    if type(value) is not int or not 0 < value <= 2147483647:
        raise InvalidRasterInput("El identificador debe ser un entero positivo válido.")


class StartOptimizationUseCase:
    def __init__(self, orders: OptimizationOrders, budget: RasterBudget):
        self.orders = orders
        self.budget = budget

    def execute(self, id_pedido: int) -> dict:
        validate_id(id_pedido)
        order = self.orders.get_order(id_pedido)
        if order is None:
            raise OptimizationNotFoundError("Pedido no encontrado.")
        if order["estado"] != "PENDIENTE":
            raise OptimizationStateError("Solo un pedido PENDIENTE puede preparar la vista previa.")
        pieces = order.get("piezas", [])
        if not pieces:
            raise InvalidRasterInput("El pedido debe contener piezas válidas para preparar la vista previa.")
        for piece in pieces:
            if piece.get("id_pedido") != id_pedido:
                raise InvalidRasterInput("Las piezas persistidas no corresponden al pedido.")
            self.budget.check(piece.get("geometria"), DEFAULT_RESOLUTION_MM)
            self.orders.validate_piece(piece)
        # HU-015 prepares a preview, not a First Fit execution or reservation.
        return {"id_pedido": id_pedido, "estado": order["estado"]}


class RasterizeOrderPieceUseCase:
    def __init__(self, orders: OptimizationOrders, budget: RasterBudget):
        self.orders = orders
        self.budget = budget

    def execute(self, id_pedido: int, id_pieza: int, resolution_mm: float) -> RasterizedPiece:
        validate_id(id_pedido)
        validate_id(id_pieza)
        positive_resolution(resolution_mm)
        order = self.orders.get_order(id_pedido)
        if order is None:
            raise OptimizationNotFoundError("Pedido no encontrado.")
        if order["estado"] not in ("PENDIENTE", "EN_OPTIMIZACION"):
            raise OptimizationStateError("El pedido debe estar PENDIENTE o EN_OPTIMIZACION para rasterizar.")
        piece = next((p for p in order["piezas"]
                      if p["id_pieza"] == id_pieza and p["id_pedido"] == id_pedido), None)
        if piece is None:
            raise OptimizationNotFoundError("Pieza no encontrada en el pedido.")
        self.budget.check(piece.get("geometria"), resolution_mm)
        self.orders.validate_piece(piece)
        mask = rasterize_geometry(piece["geometria"], resolution_mm)
        return RasterizedPiece(piece, mask)
