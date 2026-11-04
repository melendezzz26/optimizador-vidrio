"""Generador determinista y reproducible de escenarios de capacidad progresiva (TA-044).

Autor: Luis Anthony Ibáñez Herrera.
Revisión: Andro Joseph Quispe Cesias / Wilder Fabricio Melendez Quezada.

Provee la matriz canónica de casos para evaluar el optimizador de NewGlass:
- 10 piezas (CAP-10)
- 25 piezas (CAP-25)
- 50 piezas (CAP-50)
- 75 piezas (CAP-75)
- 100 piezas (CAP-100)

Condiciones representativas:
- Múltiples geometrías: rectángulos, circunferencias y polígonos convexos.
- Grupos de materiales compatibles: Grupo 1 (Vidrio 1, 6mm) y Grupo 2 (Vidrio 2, 8mm).
- Stock mixto: retazos recuperables (RETAZO, prioridad 1) y planchas nuevas (PLANCHA).
- Totalmente reproducible: sin datos aleatorios en tiempo de ejecución.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.optimization.loader import build_problem

CAPACITY_DIR = Path(__file__).resolve().parent / "cases" / "capacity"
CAPACITY_SCENARIOS = (10, 25, 50, 75, 100)

# Catálogo canónico de geometrías de piezas
PIECE_SPECS = {
    # Grupo 1: id_tipo_vidrio=1, espesor_mm=6
    1: {"type": "RECTANGULO", "width_mm": 6, "height_mm": 4, "glass": 1, "thick": 6},
    2: {"type": "RECTANGULO", "width_mm": 8, "height_mm": 3, "glass": 1, "thick": 6},
    3: {"type": "CIRCUNFERENCIA", "radius_mm": 2, "glass": 1, "thick": 6},
    4: {"type": "CIRCUNFERENCIA", "radius_mm": 3, "glass": 1, "thick": 6},
    5: {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [6, 0], [0, 4]], "glass": 1, "thick": 6},
    6: {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 2], [3, 0], [6, 1], [5, 5], [1, 4]], "glass": 1, "thick": 6},

    # Grupo 2: id_tipo_vidrio=2, espesor_mm=8
    7: {"type": "RECTANGULO", "width_mm": 5, "height_mm": 3, "glass": 2, "thick": 8},
    8: {"type": "RECTANGULO", "width_mm": 7, "height_mm": 2, "glass": 2, "thick": 8},
    9: {"type": "CIRCUNFERENCIA", "radius_mm": 2, "glass": 2, "thick": 8},
    10: {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [7, 0], [5, 4], [2, 4]], "glass": 2, "thick": 8},
}

# Distribución canónica de cantidades para cada escala N
PIECE_DISTRIBUTIONS = {
    10: {1: 2, 3: 2, 5: 2, 7: 2, 10: 2},  # G1: 6 piezas, G2: 4 piezas -> Total 10
    25: {1: 4, 2: 3, 3: 4, 5: 4, 7: 3, 9: 3, 10: 4},  # G1: 15, G2: 10 -> Total 25
    50: {1: 7, 2: 6, 3: 6, 5: 6, 6: 5, 7: 6, 8: 4, 9: 5, 10: 5},  # G1: 30, G2: 20 -> Total 50
    75: {1: 10, 2: 9, 3: 9, 5: 9, 6: 8, 7: 8, 8: 7, 9: 7, 10: 8},  # G1: 45, G2: 30 -> Total 75
    100: {1: 14, 2: 12, 3: 12, 5: 12, 6: 10, 7: 11, 8: 9, 9: 10, 10: 10},  # G1: 60, G2: 40 -> Total 100
}


def create_piece_entry(piece_id: int, spec_id: int, quantity: int) -> dict[str, Any]:
    spec = PIECE_SPECS[spec_id]
    geom: dict[str, Any] = {"type": spec["type"]}
    if spec["type"] == "RECTANGULO":
        geom["width_mm"] = spec["width_mm"]
        geom["height_mm"] = spec["height_mm"]
    elif spec["type"] == "CIRCUNFERENCIA":
        geom["radius_mm"] = spec["radius_mm"]
    elif spec["type"] == "POLIGONO_CONVEXO":
        geom["vertices_mm"] = spec["vertices_mm"]

    return {
        "id_pedido": 1,
        "id_pieza": piece_id,
        "cantidad": quantity,
        "id_tipo_vidrio": spec["glass"],
        "espesor_mm": spec["thick"],
        "tipo_forma": spec["type"],
        "geometria": geom,
    }


def create_stock_entries(scale_n: int) -> list[dict[str, Any]]:
    """Genera inventario mixto: retazos prioritarios + planchas nuevas escaladas."""
    sheets_g1 = max(4, (scale_n * 6 // 10) // 2 + 2)
    sheets_g2 = max(3, (scale_n * 4 // 10) // 2 + 2)

    return [
        # Retazo 1 - Grupo 1 (Rectangular)
        {
            "material_id": 101,
            "quantity": 1,
            "source": "RETAZO",
            "glass_type_id": 1,
            "thickness_mm": 6,
            "geometry": {"type": "RECTANGULO", "width_mm": 12, "height_mm": 10},
        },
        # Retazo 2 - Grupo 1 (Poligonal convexo)
        {
            "material_id": 102,
            "quantity": 1,
            "source": "RETAZO",
            "glass_type_id": 1,
            "thickness_mm": 6,
            "geometry": {
                "type": "POLIGONO_CONVEXO",
                "vertices_mm": [[0, 0], [14, 0], [12, 10], [0, 8]],
            },
        },
        # Planchas nuevas - Grupo 1 (24x18 mm)
        {
            "material_id": 103,
            "quantity": sheets_g1,
            "source": "PLANCHA",
            "glass_type_id": 1,
            "thickness_mm": 6,
            "geometry": {"type": "RECTANGULO", "width_mm": 24, "height_mm": 18},
        },
        # Retazo 3 - Grupo 2 (Rectangular)
        {
            "material_id": 201,
            "quantity": 1,
            "source": "RETAZO",
            "glass_type_id": 2,
            "thickness_mm": 8,
            "geometry": {"type": "RECTANGULO", "width_mm": 10, "height_mm": 8},
        },
        # Planchas nuevas - Grupo 2 (20x16 mm)
        {
            "material_id": 202,
            "quantity": sheets_g2,
            "source": "PLANCHA",
            "glass_type_id": 2,
            "thickness_mm": 8,
            "geometry": {"type": "RECTANGULO", "width_mm": 20, "height_mm": 16},
        },
    ]


def generate_capacity_case(scale_n: int) -> dict[str, Any]:
    """Genera la estructura de datos completa para un caso de capacidad de escala N."""
    if scale_n not in CAPACITY_SCENARIOS:
        raise ValueError(f"Escala no soportada: {scale_n}. Debe ser una de {CAPACITY_SCENARIOS}")

    distribution = PIECE_DISTRIBUTIONS[scale_n]
    pieces = []
    piece_id = 1
    total_count = 0
    for spec_id, qty in distribution.items():
        pieces.append(create_piece_entry(piece_id, spec_id, qty))
        total_count += qty
        piece_id += 1

    assert total_count == scale_n, f"Error en conteo: esperado {scale_n}, obtenido {total_count}"

    stock = create_stock_entries(scale_n)

    return {
        "case_id": f"CAP-{scale_n}",
        "schema_version": 1,
        "rotation_allowed": True,
        "order_ids": [1],
        "config": {
            "resolution_mm": 1,
            "angular_step_deg": 5,
            "margin_mm": 1,
            "separation_mm": 1,
        },
        "residual_limits": {
            "minimum_width_mm": 1,
            "minimum_height_mm": 1,
        },
        "pieces": pieces,
        "stock": stock,
    }


def export_capacity_cases(output_dir: Path | None = None) -> list[Path]:
    """Exporta los 5 casos congelados a disco en formato JSON."""
    target_dir = output_dir or CAPACITY_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    generated_paths = []
    for n in CAPACITY_SCENARIOS:
        case_data = generate_capacity_case(n)
        file_path = target_dir / f"CAP-{n}.json"
        file_path.write_text(json.dumps(case_data, indent=2), encoding="utf-8")
        generated_paths.append(file_path)
    return generated_paths


def load_capacity_problem(scale_n: int, cases_dir: Path | None = None):
    """Carga y prepara el objeto OptimizationProblem para una escala N dada."""
    directory = cases_dir or CAPACITY_DIR
    file_path = directory / f"CAP-{scale_n}.json"
    if not file_path.exists():
        # Generar al vuelo si no existe
        case_data = generate_capacity_case(scale_n)
    else:
        case_data = json.loads(file_path.read_text(encoding="utf-8"))
    return build_problem(case_data)


if __name__ == "__main__":
    paths = export_capacity_cases()
    print(f"Exportados {len(paths)} casos de capacidad en {CAPACITY_DIR}:")
    for p in paths:
        print(f" - {p.name}")
