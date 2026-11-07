"""TA-047: shared boundaries, exact TA-045 inputs and no feasibility search."""
from decimal import Decimal as D

import pytest

from app.modules.optimization.application.geometric_preflight import validate_comparison_geometry
from app.modules.optimization.domain.placement import SheetLayout
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.rotation import RasterCache, RasterPreparationError
from tests.unit.optimization.test_first_fit import config, piece, problem, stock
from tests.unit.optimization.test_load_budget import polygon


@pytest.mark.parametrize('candidates', [[], [stock(width=1, height=1)], [stock(width=4000, height=4000)]])
def test_validity_never_allocates_masks_searches_or_mutates(candidates, monkeypatch):
    value = problem([piece(width=4, height=2)], candidates,
        config(angular_step_deg=D(5), margin_mm=D('0.00000000000001'), separation_mm=D('1.000000000001')))
    before = repr(value)
    def forbidden(*args, **kwargs): pytest.fail('Preflight allocated or searched')
    monkeypatch.setattr(RasterCache, '_raster', forbidden)
    monkeypatch.setattr(SheetLayout, 'first_position', forbidden)
    validate_comparison_geometry(value)
    assert repr(value) == before


@pytest.mark.parametrize('candidate', [
    stock(width=4001), stock(width=2001),
    stock(source=MaterialSource.REMNANT, geometry=polygon(129)),
    stock(source=MaterialSource.REMNANT,
          geometry=dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [0.0000004, 0], [0.0000004, 4000]])),
])
def test_stock_uses_existing_extent_vertex_and_rn04_barrier(candidate):
    with pytest.raises(RasterPreparationError):
        validate_comparison_geometry(problem(candidates=[candidate], cfg=config(resolution_mm=D('0.5'))))


def test_exact_4000_cell_and_128_vertex_boundaries_are_valid():
    validate_comparison_geometry(problem(candidates=[stock(width=2000)], cfg=config(resolution_mm=D('0.5'))))
    validate_comparison_geometry(problem(candidates=[stock(source=MaterialSource.REMNANT, geometry=polygon(128))]))


def test_precision_loss_is_rejected_without_float_rounding():
    value = problem(cfg=config(resolution_mm=D('0.10000000000000000001')))
    with pytest.raises(RasterPreparationError, match='digit loss'):
        validate_comparison_geometry(value)


def test_orders_collinear_contour_does_not_acquire_inventory_stricter_rules():
    row = piece(width=4, height=4)
    row.update(tipo_forma='POLIGONO_CONVEXO',
        geometria=dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [2, 0], [4, 0], [4, 4], [0, 4]]))
    validate_comparison_geometry(problem([row]))


def test_diagonal_extents_do_not_reject_a_valid_maximum_base():
    # TA-016 skips unsupported rotated extents during search, retaining angle 0.
    validate_comparison_geometry(problem([piece(width=4000, height=4000)],
        [stock(width=4000, height=4000)], config(angular_step_deg=D(5))))
