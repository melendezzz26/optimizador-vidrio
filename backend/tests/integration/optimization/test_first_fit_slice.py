"""Real persisted Orders -> public Inventory DTOs -> pure FF, no lifecycle writes."""
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models import (Pedido, Plancha, Optimizacion, EjecucionOptimizacion, MovimientoInventario)
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.application.first_fit import calculate_first_fit
from app.modules.optimization.domain.problem import OptimizationConfig
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter


def test_persisted_multiorder_pieces_produce_real_placements_without_db_mutations(session_factory, create_user):
    actor = create_user("O70000001")
    piece = dict(tipo_forma="RECTANGULO", cantidad=2, dimensiones={"width_mm": 2, "height_mm": 2},
                 geometria={"type": "RECTANGULO", "width_mm": 2, "height_mm": 2},
                 id_tipo_vidrio=7, espesor_mm=6, area_mm2=4)
    with session_factory() as session:
        orders = SQLAlchemyOrderRepository(session)
        ids = [orders.create_order(actor, [piece], id_cliente=41) for _ in range(2)]
        session.add(Plancha(id_plancha=5, id_tipo_vidrio=7, ancho_mm=4, alto_mm=2,
                           espesor_mm=6, cantidad=2, estado=True, fecha_registro=datetime.now(timezone.utc)))
        session.commit()
        snapshots = [p for identifier in ids for p in orders.get_order(identifier)["piezas"]]
    cfg = OptimizationConfig(resolution_mm=1, margin_mm=0, separation_mm=0, angular_step_deg=90)
    events = []
    result = calculate_first_fit(ids, snapshots, cfg,
                                 InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory)), events.append)
    assert result.complete and result.placed_units == result.total_units == 4
    assert [p.stock.physical_unit_index for p in result.placements] == [1, 1, 2, 2]
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(0, 0), (2, 0), (0, 0), (2, 0)]
    assert {p.piece.order_id for p in result.placements} == set(ids)
    assert [e.placed_units for e in events if e.kind == "piece_placed"] == [1, 2, 3, 4]
    with session_factory() as session:
        assert session.get(Plancha, 5).cantidad == 2
        assert all(session.get(Pedido, identifier).estado == "PENDIENTE" for identifier in ids)
        for model in (Optimizacion, EjecucionOptimizacion, MovimientoInventario):
            assert session.scalar(select(func.count()).select_from(model)) == 0
