"""TA-037 T02: presupuesto previo a la expansión (SPEC-TA-037 §5-§7), sin base de datos."""
import math
import time
from decimal import Decimal as D

import pytest

from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.load_budget import (
    DEFAULT_RUN_LOAD_BUDGET as BUDGET, LoadLimitExceeded, _fingerprint, check_pieces, check_selection,
    check_stock, estimate_raster_bytes,
)
from app.modules.optimization.domain.problem import OptimizationConfig, PieceUnit, geometry_snapshot
from app.modules.optimization.domain.rotation import RasterCache, _fingerprint as engine_fingerprint
from tests.unit.optimization.test_preparation import piece

CONFIG = OptimizationConfig(resolution_mm=1, margin_mm=0, separation_mm=0)  # 5°, operativo


def polygon(vertices, radius=100, dx=0, dy=0):
    return dict(type="POLIGONO_CONVEXO", vertices_mm=[
        [round(dx + radius + radius * math.cos(2 * math.pi * i / vertices), 3),
         round(dy + radius + radius * math.sin(2 * math.pi * i / vertices), 3)] for i in range(vertices)])


def row(identifier=1, quantity=1, geometry=None, **kwargs):
    data = piece(identifier=identifier, quantity=quantity, **kwargs)
    if geometry is not None:
        data["tipo_forma"], data["geometria"] = geometry["type"], geometry
    return data


def limit_of(error):
    assert error.value.code == "LOAD_LIMIT_EXCEEDED"
    return error.value.details["limit"]


def test_approved_v1_1_values():
    assert (BUDGET.max_orders, BUDGET.max_units, BUDGET.max_vertices, BUDGET.max_stock_units_per_material,
            BUDGET.max_raster_bytes) == (20, 150, 128, 50, 64 * 1024 * 1024)


# --- Fronteras exactas: el máximo se acepta y máximo + 1 se rechaza (RN-08) ---

def test_l01_orders_per_run_exact_and_plus_one():
    check_selection(tuple(range(1, 21)))
    with pytest.raises(LoadLimitExceeded) as error:
        check_selection(tuple(range(1, 22)))
    assert limit_of(error) == dict(name="orders_per_run", maximum=20, actual=21, scope=None)


@pytest.mark.parametrize("quantities", [[150], [100, 50], [1] * 150])
def test_l03_units_exact_limit_is_accepted(quantities):
    rows = [row(identifier=i + 1, quantity=q) for i, q in enumerate(quantities)]
    assert check_pieces(rows, CONFIG) == {(1, D(6)): 150}


@pytest.mark.parametrize("quantities", [[151], [100, 51], [1] * 151])
def test_l03_units_plus_one_is_rejected_across_rows(quantities):
    rows = [row(identifier=i + 1, quantity=q) for i, q in enumerate(quantities)]
    with pytest.raises(LoadLimitExceeded) as error:
        check_pieces(rows, CONFIG)
    assert limit_of(error) == dict(name="units_per_run", maximum=150, actual=151, scope=None)


def test_l03_maximum_persisted_quantity_is_rejected_without_proportional_work():
    started = time.perf_counter()
    with pytest.raises(LoadLimitExceeded) as error:
        check_pieces([row(quantity=2147483647)], CONFIG)
    assert time.perf_counter() - started < 1
    assert limit_of(error)["actual"] == 2147483647


def test_l04_vertices_exact_and_plus_one_with_piece_scope():
    check_pieces([row(geometry=polygon(128))], CONFIG)
    with pytest.raises(LoadLimitExceeded) as error:
        check_pieces([row(identifier=9, geometry=polygon(129))], CONFIG)
    assert limit_of(error) == dict(name="vertices_per_piece", maximum=128, actual=129, scope={"id_pieza": 9})
    assert "pieza 9" in error.value.message


def test_l05_geometry_extent_keeps_existing_value_error():
    """Misma función y mismo error que antes de TA-037: AcceptRun lo responde como INVALID_INPUT."""
    with pytest.raises(ValueError) as error:
        check_pieces([row(width=4001, height=10)], CONFIG)
    assert not isinstance(error.value, RunError)


def test_l07_stock_exact_and_plus_one_with_material_scope():
    units = {(7, D("6.00")): 3}
    check_stock(units, {(7, D("6.00")): 50})
    with pytest.raises(LoadLimitExceeded) as error:
        check_stock(units, {(7, D("6.00")): 51})
    assert limit_of(error) == dict(name="stock_units_per_material", maximum=50, actual=51,
                                   scope={"id_tipo_vidrio": 7, "espesor_mm": "6.00"})


def test_l13_two_large_distinct_shapes_fit_and_three_are_rejected():
    """Caso H-10 a 5°: el motor falla con 3 formas de ~1300 x 1000 y acepta 2."""
    sizes = [(1300, 1000), (1300, 1001), (1300, 1002)]
    rows = [row(identifier=i + 1, width=w, height=h) for i, (w, h) in enumerate(sizes)]
    check_pieces(rows[:2], CONFIG)
    with pytest.raises(LoadLimitExceeded) as error:
        check_pieces(rows, CONFIG)
    limit = limit_of(error)
    assert limit["name"] == "raster_memory" and limit["maximum"] == 64 * 1024 * 1024
    assert limit["actual"] > limit["maximum"]


def test_l13_repeated_shape_is_counted_once_like_the_engine():
    rows = [row(identifier=i + 1, width=1300, height=1000) for i in range(3)]
    check_pieces(rows, CONFIG)  # misma huella: la caché comparte las máscaras


# --- Orden, determinismo y frontera con la validación de negocio ---------

def test_only_the_first_violation_is_reported_in_spec_order():
    rows = [row(identifier=1, quantity=151, geometry=polygon(200))]
    with pytest.raises(LoadLimitExceeded) as error:
        check_pieces(rows, CONFIG)
    assert limit_of(error)["name"] == "units_per_run"


def test_same_request_is_rejected_by_the_same_limit_and_values():
    rows = [row(quantity=151)]
    results = []
    for _ in range(2):
        with pytest.raises(LoadLimitExceeded) as error:
            check_pieces(rows, CONFIG)
        results.append((error.value.message, error.value.details))
    assert results[0] == results[1]


@pytest.mark.parametrize("bad", [dict(cantidad="9999"), dict(cantidad=0), dict(espesor_mm=None),
                                 dict(id_tipo_vidrio="7")])
def test_invalid_business_data_is_left_to_existing_validation(bad):
    data = {**row(), **bad}
    check_pieces([data], CONFIG)  # no es un límite operativo: lo rechaza prepare_persisted_problem


@pytest.mark.parametrize("geometry", [None, {"type": "RECTANGULO"}, {"type": "OTRO"}])
def test_malformed_geometry_raises_value_error_not_a_crash(geometry):
    data = {**row(), "geometria": geometry}
    with pytest.raises(ValueError):
        check_pieces([data], CONFIG)


def test_messages_are_spanish_and_expose_no_internals():
    errors = [LoadLimitExceeded("orders_per_run", 20, 21), LoadLimitExceeded("units_per_run", 150, 180),
              LoadLimitExceeded("vertices_per_piece", 128, 140, {"id_pieza": 3}),
              LoadLimitExceeded("raster_memory", 1, 2),
              LoadLimitExceeded("stock_units_per_material", 50, 60, {"id_tipo_vidrio": 7, "espesor_mm": "6.00"})]
    for error in errors:
        assert error.message and not any(s in error.message for s in ("SELECT", "Traceback", "/", "_", "{"))
    assert errors[1].message.startswith("Los pedidos seleccionados suman 180 unidades")


# --- L-13 es una cota inferior fiel de la caché del motor --------------------

SHAPES = [dict(type="RECTANGULO", width_mm=1300, height_mm=1000), dict(type="RECTANGULO", width_mm=300, height_mm=200),
          dict(type="CIRCUNFERENCIA", radius_mm=150), polygon(8), polygon(128), polygon(5, radius=600)]


@pytest.mark.parametrize("geometry", SHAPES)
def test_l13_estimate_is_a_tight_lower_bound_of_the_real_cache(geometry):
    unit = PieceUnit(order_id=1, piece_id=1, unit_index=1, glass_type_id=1, thickness_mm=D(6),
                     geometry=geometry, area_mm2=D(1))
    cache = RasterCache()
    cache.orientations(unit, CONFIG.resolution_mm, CONFIG.angular_step_deg)
    estimate = estimate_raster_bytes([geometry_snapshot(geometry)], CONFIG)
    assert 0.9 * cache._cache_bytes <= estimate <= cache._cache_bytes


@pytest.mark.parametrize("pair", [
    (polygon(6), polygon(6, dx=50, dy=-20)),                                   # trasladado: misma huella
    (dict(type="RECTANGULO", width_mm=2, height_mm=3),
     dict(type="POLIGONO_CONVEXO", vertices_mm=[[0, 0], [2, 0], [2, 3], [0, 3]])),
    (dict(type="CIRCUNFERENCIA", radius_mm=2), dict(type="CIRCUNFERENCIA", radius_mm=2.0)),
])
def test_fingerprint_matches_the_engine(pair):
    snapshots = [geometry_snapshot(g) for g in pair]
    assert [_fingerprint(s) for s in snapshots] == [engine_fingerprint(s) for s in snapshots]
    assert _fingerprint(snapshots[0]) == _fingerprint(snapshots[1])