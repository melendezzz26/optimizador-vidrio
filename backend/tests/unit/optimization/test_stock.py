from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest

from app.modules.inventory.application.dto import PlanchaData, RetazoData
from app.modules.optimization.application.stock import CompatibleStockCache, with_compatible_stock
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from tests.unit.optimization.test_preparation import CONFIG, piece
from app.modules.optimization.application.preparation import prepare_persisted_problem


NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def sheet(identifier=1, **changes):
    return replace(PlanchaData(id_plancha=identifier, ancho_mm=D(10), alto_mm=D(8),
                   espesor_mm=D(6), cantidad=1, estado=True, fecha_registro=NOW,
                   id_tipo_vidrio=1), **changes)


def remnant(identifier=1, **changes):
    return replace(RetazoData(id_retazo=identifier, codigo=f"R{identifier}", espesor_mm=D(6),
                   geometria={"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [8, 0], [0, 8]]},
                   area_mm2=D(32), estado=True, fecha_registro=NOW, id_tipo_vidrio=1,
                   id_ejecucion_origen=None), **changes)


class Inventory:
    def __init__(self, remnants=(), sheets=()):
        self.remnants, self.sheets = list(remnants), list(sheets)
        self.reads = 0
        self.calls = 0

    @contextmanager
    def read_transaction(self):
        self.reads += 1
        yield

    def list_retazos(self):
        self.calls += 1
        return self.remnants

    def list_planchas(self):
        self.calls += 1
        return self.sheets


@pytest.mark.parametrize("changes", [{"id_tipo_vidrio": 2}, {"espesor_mm": D("5.5")}, {"estado": False}])
def test_filter_material_and_inactive(changes):
    source = Inventory([remnant(**changes)], [sheet(**changes)])
    assert InventoryStockAdapter(source).list_compatible((1, D(6))) == ()


def test_zero_quantity_and_empty_catalogue():
    assert InventoryStockAdapter(Inventory(sheets=[sheet(cantidad=0)])).list_compatible((1, D(6))) == ()
    assert InventoryStockAdapter(Inventory()).list_compatible((1, D(6))) == ()


def test_priority_dates_ids_and_physical_units_no_collisions_or_mutation():
    old = NOW - timedelta(days=1)
    source = Inventory([remnant(4, fecha_registro=old), remnant(1), remnant(2)],
                       [sheet(8, fecha_registro=old), sheet(1), sheet(2, cantidad=3)])
    before = repr((source.remnants, source.sheets))
    adapter = InventoryStockAdapter(source)
    candidates = adapter.list_compatible((1, D(6)))
    assert [(c.source.value, c.material_id, c.physical_unit_index) for c in candidates] == [
        ("RETAZO", 2, 1), ("RETAZO", 1, 1), ("RETAZO", 4, 1),
        ("PLANCHA", 2, 1), ("PLANCHA", 2, 2), ("PLANCHA", 2, 3),
        ("PLANCHA", 1, 1), ("PLANCHA", 8, 1)]
    assert len({c.identity for c in candidates}) == len(candidates)
    assert candidates[0].geometry["type"] == "POLIGONO_CONVEXO"
    assert candidates[-1].area_mm2 == D(80)
    source.remnants.reverse(); source.sheets.reverse()
    assert adapter.list_compatible((1, D(6))) == candidates
    source.remnants.reverse(); source.sheets.reverse()
    assert repr((source.remnants, source.sheets)) == before


def test_run_local_cache_one_lookup_per_group_and_new_run_refreshes():
    source = Inventory(sheets=[sheet()])
    provider = InventoryStockAdapter(source)
    cache = CompatibleStockCache(provider)
    assert cache.list_compatible((1, D("6.0"))) is cache.list_compatible((1, D(6)))
    cache.list_compatible((1, D("5.5")))
    assert source.reads == 2 and source.calls == 4
    problem = prepare_persisted_problem([1], [piece(quantity=3)], CONFIG)
    result = with_compatible_stock(problem, provider)
    assert source.reads == 3
    assert len(result.groups[0].stock_candidates) == 1
    assert problem.groups[0].stock_candidates == ()
    source.sheets = []
    assert with_compatible_stock(problem, provider).groups[0].stock_candidates == ()


def test_provider_contract_cannot_inject_wrong_material():
    candidates = InventoryStockAdapter(Inventory(sheets=[sheet()])).list_compatible((1, D(6)))
    class BadProvider:
        def list_compatible(self, key):
            return candidates
    with pytest.raises(ValueError):
        CompatibleStockCache(BadProvider()).list_compatible((2, D(6)))
