"""TA-037 T02: conteo de stock sin expandir y defensa P5, sobre PostgreSQL real (CA-04)."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import MovimientoInventario, Optimizacion, Pedido, Plancha, Retazo
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter, StockLoadExceeded
from tests.integration.optimization.test_runs import prepared  # noqa: F401


def add_stock(session_factory):
    now = datetime.now(timezone.utc)
    with session_factory() as s:
        s.add_all([
            Plancha(id_plancha=6, ancho_mm=4, alto_mm=2, espesor_mm=6, cantidad=3, estado=True,
                    fecha_registro=now, id_tipo_vidrio=7),
            Plancha(id_plancha=7, ancho_mm=4, alto_mm=2, espesor_mm=6, cantidad=9, estado=False,   # inactiva
                    fecha_registro=now, id_tipo_vidrio=7),
            Plancha(id_plancha=8, ancho_mm=4, alto_mm=2, espesor_mm=5.5, cantidad=9, estado=True,    # otro espesor
                    fecha_registro=now, id_tipo_vidrio=7),
            Retazo(id_retazo=5, codigo="TA037-R5", id_tipo_vidrio=7, espesor_mm=6,
                   geometria={"type": "RECTANGULO", "width_mm": 3, "height_mm": 2},
                   area_mm2=Decimal(6), estado=True, fecha_registro=now),
            Retazo(id_retazo=6, codigo="TA037-R6", id_tipo_vidrio=7, espesor_mm=6,
                   geometria={"type": "RECTANGULO", "width_mm": 3, "height_mm": 2},
                   area_mm2=Decimal(6), estado=False, fecha_registro=now),                       # inactivo
        ])
        s.commit()


def test_count_matches_the_expanded_candidates_with_the_same_rules(session_factory, prepared):
    add_stock(session_factory)
    adapter = InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory))
    key = (7, Decimal(6))
    # Plancha 5 (2) + plancha 6 (3) + retazo 5 (1); inactivos, otro espesor y cantidad 0 no cuentan.
    assert adapter.count_compatible(key) == len(adapter.list_compatible(key)) == 6


def test_large_stock_row_is_rejected_at_acceptance_without_mutation(session_factory, prepared):
    actor, ids, uow = prepared
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = 100000
        s.commit()
    adapter = InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory))
    with pytest.raises(RunError) as error:
        AcceptRun(uow, adapter).execute(ids, actor)
    assert error.value.details["limit"]["actual"] == 100000
    with session_factory() as s:
        assert [s.get(Pedido, i).estado for i in ids] == ["PENDIENTE"] * 2
        assert s.scalar(select(func.count()).select_from(Optimizacion)) == 0
        assert s.get(Plancha, 5).cantidad == 100000
        assert s.scalar(select(func.count()).select_from(MovimientoInventario)) == 0


def test_p5_defense_fails_before_expanding_if_stock_grew_after_acceptance(session_factory, prepared):
    with session_factory() as s:
        s.get(Plancha, 5).cantidad = 51
        s.commit()
    adapter = InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory))
    with pytest.raises(StockLoadExceeded):
        adapter.list_compatible((7, Decimal(6)))
    assert InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory), max_units=51) \
        .list_compatible((7, Decimal(6)))[-1].physical_unit_index == 51