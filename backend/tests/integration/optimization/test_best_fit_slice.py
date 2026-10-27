"""Real read adapters and full database snapshot around BF simulation."""
from datetime import datetime, timezone
from decimal import Decimal as D
import pytest

from app.models import Plancha, Retazo
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.application.best_fit import calculate_best_fit
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import MaterialSource, OptimizationConfig
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
from tests.integration.optimization.test_worst_fit_slice import database_snapshot, sqlite_slice


@pytest.mark.parametrize("step", [5, 90])
def test_real_repositories_bf_simulation_leaves_every_table_unchanged(sqlite_slice, step):
    factory = sqlite_slice
    now = datetime.now(timezone.utc)
    with factory() as session:
        orders = SQLAlchemyOrderRepository(session)
        order_id = orders.create_order(1, [dict(
            tipo_forma="RECTANGULO", cantidad=3, dimensiones={"width_mm": 2, "height_mm": 2},
            geometria={"type": "RECTANGULO", "width_mm": 2, "height_mm": 2},
            id_tipo_vidrio=7, espesor_mm=6, area_mm2=4,
        )], id_cliente=41)
        session.add_all([Plancha(id_plancha=i, id_tipo_vidrio=7, ancho_mm=w, alto_mm=w,
                                espesor_mm=6, cantidad=2, estado=True, fecha_registro=now)
                         for i, w in [(5, 4), (6, 6)]])
        session.add(Retazo(id_retazo=9, codigo="BF-TEST-9", id_tipo_vidrio=7, espesor_mm=6,
                           geometria={"type": "RECTANGULO", "width_mm": 3, "height_mm": 3},
                           area_mm2=9, estado=True, fecha_registro=now, id_ejecucion_origen=None))
        session.commit()
        snapshots = orders.get_order(order_id)["piezas"]
    before = database_snapshot(factory)
    cfg = OptimizationConfig(resolution_mm=1, margin_mm=0, separation_mm=0, angular_step_deg=step)
    provider = InventoryStockAdapter(SqlAlchemyInventoryRepository(factory))
    result = calculate_best_fit([order_id], snapshots, cfg, provider)
    assert result.complete and result.method == "BF"
    assert [(p.stock.source, p.stock.material_id) for p in result.placements] == [
        (MaterialSource.REMNANT, 9), (MaterialSource.SHEET, 5), (MaterialSource.SHEET, 5),
    ]
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(0, 0), (0, 0), (2, 0)]
    assert result == calculate_best_fit([order_id], snapshots, cfg, provider)
    measured, _ = calculate_metrics(result, D(1), D(1))
    assert measured.method == "BF" and measured.metrics.placed_piece_area_mm2 == 12
    assert measured.metrics.material_area_mm2 == 25
    assert database_snapshot(factory) == before
