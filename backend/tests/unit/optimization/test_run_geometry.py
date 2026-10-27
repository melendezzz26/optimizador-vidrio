"""HU-017 T02: a base barrier and restartable lazy search, shared by FF/BF/WF."""
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal as D
from unittest.mock import patch

import pytest

from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.placement import SheetLayout
from app.modules.optimization.domain.problem import MaterialSource
from app.modules.optimization.domain.rasterizer import rasterize_geometry, rasterize_material
from app.modules.optimization.domain.rotation import RasterCache, RasterPreparationError
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from tests.unit.optimization.test_first_fit import config, piece, problem, stock

METHODS = [FirstFitOptimizer, BestFitOptimizer, WorstFitOptimizer]


def prepare(value, **kwargs):
    from app.modules.optimization.domain.run_geometry import prepare_run_geometry
    return prepare_run_geometry(value, **kwargs)


@pytest.mark.parametrize('optimizer', METHODS)
def test_all_piece_and_material_bases_exist_before_first_position(optimizer, monkeypatch):
    original_raster = RasterCache._raster
    original_position = SheetLayout.first_position
    allocated, searches = [], []
    value = problem([piece(1, width=3, height=2), piece(2, width=1, height=1)],
                    [stock(1, width=4, height=4), stock(2, width=5, height=4)])

    def raster(self, geometry, resolution, *, material=False):
        allocated.append((material, geometry['type']))
        return original_raster(self, geometry, resolution, material=material)

    def position(self, mask):
        assert sum(not material for material, _ in allocated) >= 2
        assert sum(material for material, _ in allocated) == 2
        searches.append(True)
        return original_position(self, mask)

    monkeypatch.setattr(RasterCache, '_raster', raster)
    monkeypatch.setattr(SheetLayout, 'first_position', position)
    assert optimizer().optimize(value).complete
    assert searches


def test_quantities_and_identical_geometries_share_immutable_bases():
    value = problem([piece(1, width=3, height=2, quantity=3), piece(2, width=3, height=2)],
                    [stock(1), stock(2)])
    with patch('app.modules.optimization.domain.rotation.rasterize_geometry', wraps=rasterize_geometry) as raster:
        prepared = prepare(value)
    assert raster.call_count == 1
    assert prepared.piece_bases[(1, 1)] is prepared.piece_bases[(1, 2)]
    assert prepared.material_bases[value.groups[0].stock_candidates[0].identity] is prepared.material_bases[value.groups[0].stock_candidates[1].identity]
    with pytest.raises(TypeError):
        prepared.piece_bases[(1, 1)] = None
    with pytest.raises(FrozenInstanceError):
        prepared.config.resolution_mm = D(2)


def test_normalized_base_retains_original_geometry_and_one_fractional_resolution():
    polygon = piece(1) | dict(tipo_forma='POLIGONO_CONVEXO', area_mm2=D(4),
        geometria=dict(type='POLIGONO_CONVEXO', vertices_mm=[[-3, -2], [1, -2], [-3, 0]]))
    value = problem([polygon], [stock()], config(resolution_mm=D('0.5')))
    before = repr(value)
    prepared = prepare(value)
    base = prepared.piece_bases[(1, 1)]
    assert base.rotation_deg == 0 and prepared.coordinate_decimals == 6
    assert min(x for x, _ in base.geometry['vertices_mm']) == 0
    assert min(y for _, y in base.geometry['vertices_mm']) == 0
    assert base.mask == rasterize_geometry(dict(base.geometry), 0.5)
    assert base.mask.resolution_mm == 0.5
    assert all(mask.resolution_mm == 0.5 for mask in prepared.material_bases.values())
    assert next(iter(prepared.orientations(value.units[0]))).orientation is base
    assert repr(value) == before


def test_irregular_material_base_is_authoritative_interior_not_bbox():
    triangle = stock(8, width=4, height=4, source=MaterialSource.REMNANT,
                     geometry=dict(type='POLIGONO_CONVEXO', vertices_mm=[[-2, -2], [2, -2], [-2, 2]]))
    prepared = prepare(problem([piece(width=1, height=1)], [triangle]))
    mask = prepared.material_bases[triangle.identity]
    assert mask == rasterize_material(dict(triangle.geometry), 1)
    assert mask.occupied_cells < mask.columns * mask.row_count
    assert not mask.is_occupied(3, 3)


def test_validate_all_geometries_before_allocating_or_searching():
    value = problem([piece(1), piece(2, width=4001, height=1)])
    cache = RasterCache()
    with pytest.raises(RasterPreparationError), patch.object(SheetLayout, 'first_position') as position:
        prepare(value, cache=cache)
    assert cache._cache_bytes == 0
    position.assert_not_called()


def test_base_cache_budget_accepts_exact_limit_and_rejects_one_byte_over():
    value = problem()
    measured = RasterCache()
    prepare(value, cache=measured)
    required = measured._cache_bytes
    prepare(value, cache=RasterCache(max_cache_bytes=required))
    with pytest.raises(RasterPreparationError), patch.object(SheetLayout, 'first_position') as position:
        prepare(value, cache=RasterCache(max_cache_bytes=required - 1))
    position.assert_not_called()


def test_lazy_orientation_budget_failure_is_technical_not_silently_omitted():
    value = problem([piece(width=3, height=2)], cfg=config(angular_step_deg=D(45)))
    cache = RasterCache()
    prepare(value, cache=cache)
    cache.max_cache_bytes = cache._cache_bytes
    view = cache.iter_orientations(value.units[0], D(1), D(45))
    iterator = iter(view)
    assert next(iterator).orientation.rotation_deg == 0
    with pytest.raises(RasterPreparationError):
        next(iterator)


def test_orientation_view_restarts_and_reuses_cache_without_eager_generation():
    unit = problem([piece(width=3, height=2)]).units[0]
    cache = RasterCache()
    with patch('app.modules.optimization.domain.rotation.rasterize_geometry', wraps=rasterize_geometry) as raster:
        view = cache.iter_orientations(unit, D(1), D(90))
        assert raster.call_count == 0
        assert next(iter(view)).orientation.rotation_deg == 0
        assert raster.call_count == 1
        first = list(view)
        assert [entry.orientation.rotation_deg for entry in first] == [0, 90]
        assert raster.call_count == 4
        assert list(view) == first and raster.call_count == 4
        assert cache.orientations(unit, D(1), D(90)) == tuple(first)


def test_ff_stops_at_first_fit_without_generating_later_angles_or_layouts(monkeypatch):
    from app.modules.optimization.domain import packing, rotation
    original = rotation.oriented_geometry
    angles = []

    def oriented(geometry, angle):
        angles.append(angle)
        return original(geometry, angle)

    monkeypatch.setattr(rotation, 'oriented_geometry', oriented)
    with patch.object(packing, '_empty_layout', wraps=packing._empty_layout) as layouts:
        result = FirstFitOptimizer().optimize(problem(candidates=[stock(1), stock(2)], cfg=config(angular_step_deg=D(5))))
    assert result.placements[0].stock.material_id == 1
    assert angles and set(angles) == {D(0)}
    assert layouts.call_count == 1


@pytest.mark.parametrize('optimizer', METHODS)
def test_exhausting_infeasible_remnant_does_not_exhaust_sheet_orientations(optimizer):
    value = problem([piece(width=3, height=2)],
                    [stock(8, width=1, height=1, source=MaterialSource.REMNANT), stock(1, width=3, height=2)])
    result = optimizer().optimize(value)
    assert result.complete and result.placements[0].stock.source is MaterialSource.SHEET
    assert result.placements[0].rotation_deg == 0


@pytest.mark.parametrize('optimizer', [BestFitOptimizer, WorstFitOptimizer])
def test_each_source_restarts_at_first_orientation_and_preserves_ties(optimizer):
    result = optimizer().optimize(problem([piece(width=3, height=2)],
        [stock(99, width=2, height=3), stock(1, width=3, height=2)]))
    assert result.complete and result.placements[0].stock.material_id == 99
    assert result.placements[0].rotation_deg == 90


@pytest.mark.parametrize('optimizer', METHODS)
def test_checkpoint_can_stop_base_preparation_before_any_search(optimizer):
    class Stopped(RuntimeError):
        pass

    def checkpoint():
        raise Stopped()

    with patch.object(SheetLayout, 'first_position') as position, pytest.raises(Stopped):
        optimizer().optimize(problem(), checkpoint=checkpoint)
    position.assert_not_called()


def test_configuration_is_frozen_while_lazy_rotations_use_same_resolution():
    values = dict(resolution_mm=D('0.5'), margin_mm=D(1), separation_mm=D(2), angular_step_deg=D(90))
    value = problem([piece(width=3, height=2)], cfg=config(**values))
    prepared = prepare(value)
    values.update(resolution_mm=D(5), angular_step_deg=D(5))
    assert prepared.config == value.config
    assert prepared.config.resolution_mm == D('0.5')
    assert {entry.orientation.mask.resolution_mm for entry in prepared.orientations(value.units[0])} == {0.5}
