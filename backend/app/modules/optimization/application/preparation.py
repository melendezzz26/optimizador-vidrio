"""Bridge existing Orders snapshots to pure preparation; no batch persistence."""
from decimal import Decimal

from app.modules.orders.application.persisted_pieces import validate_persisted_piece

from ..domain.preparation import PieceSnapshot, prepare_problem
from ..domain.problem import PieceUnit


def prepare_persisted_problem(order_ids, pieces, config):
    snapshots = []
    for piece in pieces:
        validate_persisted_piece(piece)
        # Persisted NUMERIC values or JSON numeric representations; never Decimal(float).
        snapshots.append(PieceSnapshot(quantity=piece["cantidad"], unit=PieceUnit(
            order_id=piece["id_pedido"], piece_id=piece["id_pieza"], unit_index=1,
            glass_type_id=piece["id_tipo_vidrio"], thickness_mm=Decimal(str(piece["espesor_mm"])),
            geometry=piece["geometria"], area_mm2=Decimal(str(piece["area_mm2"])),
        )))
    return prepare_problem(order_ids, snapshots, config)
