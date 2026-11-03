"""Comprobaciones pequeñas ejecutables también en Colab, sin pytest ni Git."""
from dataclasses import replace
from decimal import Decimal

from experiments.optimization.loader import load_problem
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.packing import _empty_layout
from app.modules.optimization.domain.problem import MaterialSource, OptimizationConfig
from app.modules.optimization.domain.raster_mask import RasterMask
from app.modules.optimization.domain.rotation import RasterCache
from sp006.beam import BeamSearch, SearchLimits
from sp006.validation import audit, verify_snapshot


def self_checks():
    rows = []
    def check(name, function):
        function()
        rows.append({"prueba": name, "resultado": "PASS"})

    check("Integridad SHA-256 de 22 fuentes/fixtures", verify_snapshot)

    def geometry():
        cfg = OptimizationConfig(resolution_mm=Decimal(1), margin_mm=Decimal(1), separation_mm=Decimal(1))
        layout = _empty_layout(RasterMask(1, 8, (255,) * 8), cfg)
        mask = RasterMask(1, 2, (3, 3))
        assert not layout.check(mask, 0, 1).is_valid
        placed = layout.place(mask, 1, 1)
        assert not placed.check(mask, 1, 1).is_valid
        assert not placed.check(mask, 1, 3).is_valid
        assert placed.check(mask, 1, 4).is_valid
        assert not any(layout.occupied)
    check("Margen, separación, superposición e inmutabilidad", geometry)

    def priority():
        problem = load_problem("EXP-SMALL-001")
        result = FirstFitOptimizer().optimize(problem)
        assert audit(result)["valid"]
        sheet = next(s for g in problem.groups for s in g.stock_candidates if s.source is MaterialSource.SHEET)
        invalid = replace(result, placements=(replace(result.placements[0], stock=sheet),))
        try:
            audit(invalid)
        except ValueError as error:
            assert "retazo factible" in str(error)
        else:
            raise AssertionError("No detectó violación de prioridad.")
    check("Rechazo de plancha cuando existe retazo factible", priority)

    def rotation():
        problem = load_problem("EXP-COMPLEX-001")
        cache = RasterCache()
        for unit in problem.units:
            orientations = cache.orientations(unit, problem.config.resolution_mm, problem.config.angular_step_deg)
            assert all(o.orientation.rotation_deg % 5 == 0 for o in orientations)
            signatures = {(o.orientation.mask.columns, o.orientation.mask.rows) for o in orientations}
            assert len(signatures) == len(orientations)
        assert any(o.orientation.rotation_deg % 90 != 0 for o in orientations)
    check("Rotación 5°, orientaciones no ortogonales y deduplicación", rotation)

    def limits():
        problem = load_problem("EXP-COMPLEX-001")
        for kwargs, reason in ((dict(max_expansions=1), "EXPANSION_LIMIT"),
            (dict(max_geometry_probes=1), "GEOMETRY_PROBE_LIMIT"),
            (dict(max_state_bytes=1), "STATE_MEMORY_LIMIT")):
            outcome = BeamSearch(SearchLimits(**kwargs)).optimize(problem)
            assert outcome.stop_reason == reason and outcome.processed == 0
            assert not outcome.result.placements
    check("Límites explícitos sin falso NO_FIT ni fallback a plancha", limits)
    return rows
