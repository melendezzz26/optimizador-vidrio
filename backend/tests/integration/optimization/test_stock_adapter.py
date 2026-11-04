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


def test_filtered_repository_mixed_inventory(session_factory):
    from app.models import Plancha, Retazo

    now = datetime.now(timezone.utc)
    with session_factory.begin() as session:
        for identifier, glass, thickness, active, quantity in [
            (1, 7, 6, True, 2), (2, 9, 6, True, 1), (3, 7, 5.5, True, 1),
            (4, 8, 4, True, 1), (5, 7, 6, False, 1), (6, 7, 6, True, 0),
        ]:
            session.add(Plancha(id_plancha=identifier, id_tipo_vidrio=glass, ancho_mm=10, alto_mm=8,
                                espesor_mm=thickness, cantidad=quantity, estado=active, fecha_registro=now))
            session.add(Retazo(id_retazo=identifier, codigo=f"TA050-{identifier}", id_tipo_vidrio=glass,
                               espesor_mm=thickness, geometria={"type": "RECTANGULO", "width_mm": 10, "height_mm": 8},
                               area_mm2=80, estado=active, fecha_registro=now))
    repo = SqlAlchemyInventoryRepository(session_factory)
    with repo.read_transaction():
        assert [r.id_retazo for r in repo.list_retazos_compatibles(7, Decimal(6))] == [6, 1]
        assert [s.id_plancha for s in repo.list_planchas_compatibles(7, Decimal(6))] == [1]
        assert repo.list_retazos_compatibles(7, Decimal(8)) == []
        assert repo.list_planchas_compatibles(7, Decimal(8)) == []
    candidates = InventoryStockAdapter(repo).list_compatible((7, Decimal(6)))
    assert [(c.source.value, c.material_id, c.physical_unit_index) for c in candidates] == [
        ("RETAZO", 6, 1), ("RETAZO", 1, 1), ("PLANCHA", 1, 1), ("PLANCHA", 1, 2)]
