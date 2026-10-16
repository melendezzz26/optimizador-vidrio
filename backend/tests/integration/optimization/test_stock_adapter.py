from datetime import datetime, timezone
from decimal import Decimal

import sqlalchemy as sa

from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository


def test_real_inventory_dto_reads_are_readonly_and_expand_physical_units(session_factory):
    from app.models import Plancha, Retazo, MovimientoInventario

    now = datetime.now(timezone.utc)
    with session_factory() as session:
        session.add_all([
            Plancha(id_plancha=5, id_tipo_vidrio=7, ancho_mm=10, alto_mm=8,
                    espesor_mm=6, cantidad=2, estado=True, fecha_registro=now),
            Plancha(id_plancha=6, id_tipo_vidrio=7, ancho_mm=10, alto_mm=8,
                    espesor_mm=5.5, cantidad=4, estado=True, fecha_registro=now),
            Retazo(id_retazo=5, codigo="T4-R5", id_tipo_vidrio=7, espesor_mm=6,
                   geometria={"type": "CIRCUNFERENCIA", "radius_mm": 2},
                   area_mm2=Decimal("12.57"), estado=True, fecha_registro=now),
        ])
        session.commit()
    adapter = InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory))
    actual = adapter.list_compatible((7, Decimal(6)))
    assert [(c.source.value, c.material_id, c.physical_unit_index) for c in actual] == [
        ("RETAZO", 5, 1), ("PLANCHA", 5, 1), ("PLANCHA", 5, 2)]
    assert actual == adapter.list_compatible((7, Decimal(6)))
    with session_factory() as session:
        assert session.get(Plancha, 5).cantidad == 2
        assert session.get(Retazo, 5).estado is True
        assert session.scalar(sa.select(sa.func.count()).select_from(MovimientoInventario)) == 0
