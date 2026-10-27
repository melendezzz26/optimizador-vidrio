"""TA-021: orchestration contracts; geometry remains covered by the engine suites."""
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal as D
from itertools import permutations
from unittest.mock import Mock

import pytest

from app.modules.optimization.application import comparison
from app.modules.optimization.application.comparison import ComparisonFailed, compare_methods
from app.modules.optimization.domain.best_fit import BestFitOptimizer, BestFitResult
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import MaterialSource, OptimizationResult
from app.modules.optimization.domain.rotation import RasterCache
from app.modules.optimization.domain.placement import SheetLayout
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from tests.unit.optimization.test_first_fit import config, piece, problem, stock


METHODS = (("FF", FirstFitOptimizer), ("WF", WorstFitOptimizer))
ALL_METHODS = (("FF", FirstFitOptimizer), ("BF", BestFitOptimizer), ("WF", WorstFitOptimizer))


def compare(prepared, methods=METHODS, **kwargs):
    return compare_methods(prepared, methods, minimum_width_mm=D(1), minimum_height_mm=D(1), **kwargs)


def functional(entries):
    # Dataclass equality includes placements, problem, metrics and residuals;
    # derived completeness/unplaced units follow from the same immutable data.
    return {entry.method: (replace(entry.result, computation_time_ms=None), entry.residuals) for entry in entries}


def direct(prepared, methods=METHODS):
    return {code: calculate_metrics(factory().optimize(prepared), D(1), D(1)) for code, factory in methods}


def representative_cases():
    cfg = config(angular_step_deg=D(5))
    yield problem([piece(width=2, height=2)], [stock(1, width=4, height=4), stock(2, width=6, height=4)], cfg)
    yield problem([piece(width=2, height=2, quantity=3)],
                  [stock(1, width=2, height=2, physical=i) for i in (1, 2)] +
                  [stock(9, width=2, height=2, source=MaterialSource.REMNANT)], cfg)
    yield problem([piece(width=3, height=2)], [stock(9, width=1, height=1, source=MaterialSource.REMNANT),
                                           stock(1, width=2, height=3)], cfg)
    yield problem([piece(width=2, height=2, quantity=2)], [stock(1, width=7, height=4)],
                  config(angular_step_deg=D(5), margin_mm=D(1), separation_mm=D(1)))
    triangle = stock(9, width=4, height=4, source=MaterialSource.REMNANT,
                     geometry=dict(type="POLIGONO_CONVEXO", vertices_mm=[[0, 0], [4, 0], [0, 4]]))
    polygon = piece(2) | dict(tipo_forma="POLIGONO_CONVEXO", area_mm2=D(2),
                             geometria=dict(type="POLIGONO_CONVEXO", vertices_mm=[[-2, -2], [0, -2], [-2, 0]]))
    yield problem([polygon, piece(1, width=1, height=1)], [triangle], cfg)
    yield problem([piece(1, order=2, glass=2), piece(2, order=1, thickness="5.5"), piece(3, order=2)],
                  [stock(1, glass=2), stock(2, thickness="5.5"), stock(3)], cfg)
    yield problem([piece(1, width=20, height=20), piece(2, width=2, height=2)], [stock()], cfg)
    yield problem(candidates=[], cfg=cfg)


@pytest.mark.parametrize("prepared", list(representative_cases()))
def test_direct_results_both_orders_and_repetitions_preserve_the_entire_input(prepared):
    before = repr(prepared)
    expected = direct(prepared)
    for order in permutations(METHODS):
        for _ in range(2):
            entries = compare(prepared, iter(order))
            assert tuple(entry.method for entry in entries) == tuple(code for code, _ in order)
            assert functional(entries) == expected
            assert repr(prepared) == before
            assert all(p.piece.material_key == p.stock.material_key for entry in entries for p in entry.result.placements)


def test_single_method_output_is_frozen_and_input_geometry_is_deeply_immutable():
    prepared = next(representative_cases())
    entries = compare(prepared, METHODS[:1])
    assert isinstance(entries, tuple) and len(entries) == 1
    with pytest.raises(FrozenInstanceError):
        entries[0].method = "WF"
    with pytest.raises(TypeError):
        prepared.units[0].geometry["width_mm"] = 99
    polygon = list(representative_cases())[4].units[0].geometry
    with pytest.raises(TypeError):
        polygon["vertices_mm"][0][0] = 99


def test_policies_remain_distinct_and_zero_or_partial_placement_is_a_valid_result():
    ff, wf = compare(next(representative_cases()))
    assert ff.result.placements[0].stock.material_id == 1
    assert wf.result.placements[0].stock.material_id == 2
    for prepared in (problem(candidates=[]), problem([piece(width=99, height=99)])):
        entries = compare(prepared)
        assert len(entries) == 2
        assert all(not e.result.complete and e.result.unplaced_units == prepared.units for e in entries)
        assert all(e.result.metrics is None and not e.residuals for e in entries)
    entries = compare(list(representative_cases())[-2])
    assert all(not e.result.complete and e.result.placed_units == 1 and e.result.metrics is not None for e in entries)


@pytest.mark.parametrize("invalid", [
    None, (), (("FF", FirstFitOptimizer), ("FF", WorstFitOptimizer)),
    (("", FirstFitOptimizer),), ((" FF", FirstFitOptimizer),), ((1, FirstFitOptimizer),),
    (("WF", None),), (("WF", object()),), (("WF",),), ("WF",),
])
def test_invalid_collection_fails_before_even_initializing_a_valid_method(invalid):
    factory = Mock(return_value=FirstFitOptimizer())
    entries = None if invalid is None else (("VALID", factory), *invalid) if invalid else invalid
    with pytest.raises(ValueError):
        compare(problem(), entries)
    factory.assert_not_called()


def test_unavailable_optimizer_is_rejected_before_any_optimize_call():
    optimizer = Mock()
    with pytest.raises(ValueError, match="no available optimizer"):
        compare(problem(), (("FF", lambda: optimizer), ("WF", object)))
    optimizer.optimize.assert_not_called()


@pytest.mark.parametrize("invalid", [-1, D("NaN"), D("Infinity"), 1.0, True, None])
@pytest.mark.parametrize("parameter", ["minimum_width_mm", "minimum_height_mm"])
def test_metric_parameters_are_validated_before_execution(parameter, invalid):
    factory = Mock()
    values = dict(minimum_width_mm=1, minimum_height_mm=1) | {parameter: invalid}
    with pytest.raises(ValueError):
        compare_methods(problem(), (("FF", factory),), **values)
    factory.assert_not_called()


def test_extensible_collection_uses_fresh_state_per_invocation_without_a_registry():
    class ExtraResult(OptimizationResult):
        @property
        def method(self):
            return "EXTRA"

    instances = []

    class ExtraOptimizer:
        def __init__(self):
            self.calls = 0
            instances.append(self)

        def optimize(self, prepared):
            self.calls += 1
            assert self.calls == 1
            result = FirstFitOptimizer().optimize(prepared)
            return ExtraResult(problem=result.problem, placements=result.placements)

    for _ in range(2):
        entries = compare(problem(), METHODS + (("EXTRA", ExtraOptimizer),))
        assert tuple(e.method for e in entries) == ("FF", "WF", "EXTRA")
        assert entries[-1].result.method == "EXTRA" and entries[-1].result.metrics is not None
    assert len(instances) == 2


@pytest.mark.parametrize("stage", ["initialization", "optimization", "metrics"])
def test_technical_failure_identifies_method_preserves_cause_and_never_returns_a_truncated_success(monkeypatch, stage):
    prepared = problem()
    before, original = repr(prepared), RuntimeError("synthetic failure")
    executed = []

    def factory(code, real):
        def create():
            if code == "WF" and stage == "initialization":
                raise original
            class Optimizer:
                def optimize(self, value):
                    executed.append(code)
                    if code == "WF" and stage == "optimization":
                        raise original
                    return real().optimize(value)
            return Optimizer()
        return create

    def metrics(result, width, height):
        if result.method == "WF" and stage == "metrics":
            raise original
        return calculate_metrics(result, width, height)

    monkeypatch.setattr(comparison, "calculate_metrics", metrics)
    methods = (("FF", factory("FF", FirstFitOptimizer)), ("WF", factory("WF", WorstFitOptimizer)),
               ("LATER", Mock()))
    with pytest.raises(ComparisonFailed) as error:
        compare(prepared, methods)
    assert (error.value.method, error.value.stage, error.value.__cause__) == ("WF", stage, original)
    assert executed == ([] if stage == "initialization" else ["FF", "WF"])
    assert repr(prepared) == before
    monkeypatch.setattr(comparison, "calculate_metrics", calculate_metrics)
    assert functional(compare(prepared)) == direct(prepared)


@pytest.mark.parametrize("wrong_stage", ["optimization", "metrics"])
def test_method_identity_is_checked_before_and_after_metrics(monkeypatch, wrong_stage):
    if wrong_stage == "optimization":
        methods = (("WF", FirstFitOptimizer),)
    else:
        methods = METHODS[:1]
        monkeypatch.setattr(comparison, "calculate_metrics", lambda result, *args: (
            WorstFitOptimizer().optimize(result.problem), ()))
    with pytest.raises(ComparisonFailed) as error:
        compare(problem(), methods)
    assert error.value.stage == "result contract" and isinstance(error.value.__cause__, ValueError)


def test_common_minima_are_captured_once_and_duration_covers_only_optimization_and_metrics(monkeypatch):
    external = dict(width=D(1), height=D(1))
    now, minima = [0], []

    def factory(real):
        def create():
            now[0] += 100_000_000  # Construction is outside the timed calculation.
            class Optimizer:
                def optimize(self, prepared):
                    now[0] += 2_000_000
                    external.update(width=D(99), height=D(99))
                    return real().optimize(prepared)
            return Optimizer()
        return create

    def metrics(result, width, height):
        minima.append((width, height))
        now[0] += 3_000_000
        return calculate_metrics(result, width, height)

    monkeypatch.setattr(comparison, "calculate_metrics", metrics)
    prepared = problem()
    entries = compare_methods(prepared, tuple((code, factory(real)) for code, real in METHODS),
                              minimum_width_mm=external["width"], minimum_height_mm=external["height"], clock=lambda: now[0])
    assert minima == [(D(1), D(1))] * 2 and external["width"] == 99
    assert all(e.result.computation_time_ms == 5 for e in entries)
    assert functional(entries) == direct(prepared)


@pytest.mark.parametrize("candidate_count", [8, 80])
def test_first_fit_remains_lazy_including_common_metrics(monkeypatch, candidate_count):
    original, visited = RasterCache._raster, []
    first_position, searches = SheetLayout.first_position, []

    def raster(self, geometry, resolution, *, material=False):
        if material:
            visited.append(dict(geometry))
        return original(self, geometry, resolution, material=material)

    def position(self, mask):
        searches.append(True)
        return first_position(self, mask)

    monkeypatch.setattr(RasterCache, "_raster", raster)
    monkeypatch.setattr(SheetLayout, "first_position", position)
    prepared = problem(candidates=[stock(i) for i in range(1, candidate_count + 1)])
    assert compare(prepared, METHODS[:1])[0].result.complete
    # One shared material base and one for metrics, independent of quantity.
    # Search still stops on the first source despite preparing all its peers.
    assert len(visited) == 2 and visited[0] == visited[1]
    assert searches == [True]


@pytest.mark.parametrize("prepared", list(representative_cases()))
def test_real_three_methods_match_direct_runs_in_all_six_orders_repeatedly(prepared):
    before, expected = repr(prepared), direct(prepared, ALL_METHODS)
    orders = tuple(permutations(ALL_METHODS))
    assert len(orders) == 6
    for order in orders:
        for _ in range(3):
            entries = compare(prepared, order)
            assert tuple(e.method for e in entries) == tuple(code for code, _ in order)
            assert functional(entries) == expected
            assert all(e.method == e.result.method for e in entries)
            assert repr(prepared) == before


def test_default_composition_uses_real_best_fit_and_preserves_its_type_through_metrics(monkeypatch):
    prepared = problem([piece(width=2, height=2)],
                       [stock(1, width=6, height=4), stock(2, width=4, height=4), stock(3, width=3, height=3)],
                       config(angular_step_deg=D(5)))
    observed = []
    def metrics(result, *args):
        observed.append((result.method, type(result)))
        return calculate_metrics(result, *args)
    monkeypatch.setattr(comparison, "calculate_metrics", metrics)
    entries = compare_methods(prepared, minimum_width_mm=1, minimum_height_mm=1)
    assert comparison.DEFAULT_METHODS == ALL_METHODS
    assert tuple(e.method for e in entries) == ("FF", "BF", "WF")
    assert [e.result.placements[0].stock.material_id for e in entries] == [1, 3, 1]
    assert ("BF", BestFitResult) in observed and isinstance(entries[1].result, BestFitResult)
    assert entries[1].result.metrics is not None
    assert functional(entries) == direct(prepared, ALL_METHODS)


@pytest.mark.parametrize("stage", ["optimization", "metrics"])
def test_best_fit_failure_is_explicit_and_does_not_run_later_methods_or_contaminate_retry(monkeypatch, stage):
    prepared = next(representative_cases())
    before, original, executed = repr(prepared), RuntimeError("synthetic BF failure"), []
    class FailingBestFit(BestFitOptimizer):
        def optimize(self, value):
            result = super().optimize(value)
            if stage == "optimization":
                raise original
            return result
    class LaterWorstFit(WorstFitOptimizer):
        def optimize(self, value):
            executed.append("WF")
            return super().optimize(value)
    def metrics(result, *args):
        if result.method == "BF" and stage == "metrics":
            raise original
        return calculate_metrics(result, *args)
    monkeypatch.setattr(comparison, "calculate_metrics", metrics)
    with pytest.raises(ComparisonFailed) as error:
        compare(prepared, (("FF", FirstFitOptimizer), ("BF", FailingBestFit), ("WF", LaterWorstFit)))
    assert error.value.method == "BF" and error.value.stage == stage and error.value.__cause__ is original
    assert not executed and repr(prepared) == before
    monkeypatch.setattr(comparison, "calculate_metrics", calculate_metrics)
    assert functional(compare(prepared, ALL_METHODS)) == direct(prepared, ALL_METHODS)


def test_external_changes_do_not_change_captured_stock_geometry_quantities_or_minima(monkeypatch):
    rows, candidates = [piece(width=2, height=2, quantity=2)], [stock(width=4, height=4)]
    captured = problem(rows, candidates, config(angular_step_deg=D(5)))
    minima, seen = dict(width=D(1), height=D(1)), []
    class ExternalChangeFirstFit(FirstFitOptimizer):
        def optimize(self, value):
            rows[0]["cantidad"] = 999
            rows[0]["geometria"]["width_mm"] = 999
            candidates.clear()
            minima.update(width=D(999), height=D(999))
            return super().optimize(value)
    def metrics(result, width, height):
        seen.append((width, height))
        return calculate_metrics(result, width, height)
    monkeypatch.setattr(comparison, "calculate_metrics", metrics)
    entries = compare_methods(captured, (("FF", ExternalChangeFirstFit), *ALL_METHODS[1:]),
                              minimum_width_mm=minima["width"], minimum_height_mm=minima["height"])
    assert functional(entries) == direct(captured, ALL_METHODS)
    assert seen == [(D(1), D(1))] * 3
    assert captured.units[0].geometry["width_mm"] == 2 and len(captured.units) == 2
    assert len(captured.groups[0].stock_candidates) == 1
