"""Pruebas unitarias de conformidad de escenarios de capacidad (TA-044 - T01).

Autor: Luis Anthony Ibáñez Herrera.
Revisión: Andro Joseph Quispe Cesias / Wilder Fabricio Melendez Quezada.

Valida que la matriz progresiva de capacidad (10, 25, 50, 75, 100 piezas)
cumple rigurosamente las reglas de dominio e invariantes de NewGlass:
- Validez geométrica según GeometryValidator.
- Contratos inmutables de OptimizationProblem y PieceUnit.
- Multi-material sin mezcla indebida.
- Existencia de retazos y planchas estándar.
- Ejecución smoke de FirstFit sobre el lote inicial.
"""
from decimal import Decimal
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.orders.domain.geometry import GeometryValidator
from app.modules.optimization.domain.problem import MaterialSource, OptimizationProblem
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from experiments.optimization.capacity_scenarios import (
    CAPACITY_SCENARIOS,
    generate_capacity_case,
    load_capacity_problem,
)


@pytest.mark.parametrize("scale_n", CAPACITY_SCENARIOS)
def test_capacity_scenario_generation_and_contract(scale_n: int):
    """Verifica que cada escenario escala_n genere un OptimizationProblem válido."""
    problem = load_capacity_problem(scale_n)
    assert isinstance(problem, OptimizationProblem)
    assert len(problem.units) == scale_n

    # Verificar que existan exactamente los 2 grupos de materiales
    expected_material_keys = {(1, Decimal("6")), (2, Decimal("8"))}
    actual_material_keys = {group.key for group in problem.groups}
    assert actual_material_keys == expected_material_keys

    # Verificar presencia de formas variadas
    shapes_found = {unit.shape_type for unit in problem.units}
    assert "RECTANGULO" in shapes_found
    assert "CIRCUNFERENCIA" in shapes_found
    assert "POLIGONO_CONVEXO" in shapes_found

    # Verificar stock mixto (retazos y planchas)
    for group in problem.groups:
        sources = {stock.source for stock in group.stock_candidates}
        assert MaterialSource.REMNANT in sources, f"El grupo {group.key} debe tener retazos"
        assert MaterialSource.SHEET in sources, f"El grupo {group.key} debe tener planchas"

        # Verificar que ningún candidato de stock pertenezca a otro material
        for stock in group.stock_candidates:
            assert stock.material_key == group.key


@pytest.mark.parametrize("scale_n", CAPACITY_SCENARIOS)
def test_capacity_scenario_geometry_validation(scale_n: int):
    """Asegura que ninguna geometría sea ficticia o matemáticamente inválida."""
    case_data = generate_capacity_case(scale_n)

    # Validar piezas
    for piece in case_data["pieces"]:
        geom = piece["geometria"]
        shape = geom["type"]
        if shape == "RECTANGULO":
            area = GeometryValidator.validate_rectangle(geom["width_mm"], geom["height_mm"])
        elif shape == "CIRCUNFERENCIA":
            area = GeometryValidator.validate_circle(geom["radius_mm"])
        elif shape == "POLIGONO_CONVEXO":
            area = GeometryValidator.validate_convex_polygon(geom["vertices_mm"])
        else:
            pytest.fail(f"Forma no reconocida: {shape}")
        assert area > 0

    # Validar stock
    for stock in case_data["stock"]:
        geom = stock["geometry"]
        shape = geom["type"]
        if shape == "RECTANGULO":
            area = GeometryValidator.validate_rectangle(geom["width_mm"], geom["height_mm"])
        elif shape == "POLIGONO_CONVEXO":
            area = GeometryValidator.validate_convex_polygon(geom["vertices_mm"])
        else:
            pytest.fail(f"Forma de stock no soportada: {shape}")
        assert area > 0


def test_capacity_cap10_smoke_execution():
    """Ejecuta First Fit sobre CAP-10 para verificar que el pipeline opera limpiamente."""
    problem = load_capacity_problem(10)
    optimizer = FirstFitOptimizer()
    result = optimizer.optimize(problem)

    assert result.method == "FF"
    assert result.total_units == 10
    assert result.placed_units > 0
    assert len(result.materials_used) > 0

    # Verificar que las colocaciones respeten invariante de material
    for placement in result.placements:
        assert placement.piece.material_key == placement.stock.material_key
