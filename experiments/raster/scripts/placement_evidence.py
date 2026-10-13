"""Evidencia de TA-007: validación geométrica de colocaciones.

Usa el código real del backend (app.modules.optimization.domain.placement) y genera:
  - <caso>.svg: casos válidos e inválidos (T01: límites y superposición; T02: margen y separación);
  - comparacion-<config>.svg: la misma plancha llenada con dos configuraciones de margen y separación;
  - resumen.md: resultado de cada caso y tabla comparativa.

Uso, desde la raíz del repositorio y con el venv del backend activo:
    python experiments/raster/scripts/placement_evidence.py
"""
import platform
import sys
import time
from pathlib import Path

from raster_evidence import outline_svg, real_area

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.optimization.domain.placement import SheetLayout  # noqa: E402
from app.modules.optimization.domain.rasterizer import (  # noqa: E402
    rasterize_geometry,
    rasterize_material,
)

RESULTS = ROOT / "experiments" / "raster" / "results" / "placement"

# Casos gráficos: celdas de 20 mm para que se distingan a simple vista.
CASE_RESOLUTION = 20
SMALL_SHEET = {"type": "RECTANGULO", "width_mm": 600, "height_mm": 400}
CIRCLE_SCRAP = {"type": "CIRCUNFERENCIA", "radius_mm": 200}
PIECE = {"type": "RECTANGULO", "width_mm": 200, "height_mm": 120}  # 6 x 10 celdas
SMALL_PIECE = {"type": "RECTANGULO", "width_mm": 160, "height_mm": 100}  # 5 x 8 celdas

# (nombre, tarea, material, margen, separación, piezas ya colocadas, candidata, resultado esperado)
CASES = [
    ("01-valida", "T01", SMALL_SHEET, 0, 0, [(PIECE, 2, 2)], (PIECE, 2, 13), "VALIDA"),
    ("02-fuera-de-limite-plancha", "T01", SMALL_SHEET, 0, 0, [(PIECE, 2, 2)], (PIECE, 2, 25), "FUERA_DE_LIMITE"),
    ("03-superposicion", "T01", SMALL_SHEET, 0, 0, [(PIECE, 2, 2)], (PIECE, 5, 8), "SUPERPOSICION"),
    ("04-fuera-de-limite-retazo", "T01", CIRCLE_SCRAP, 0, 0, [], (SMALL_PIECE, 0, 6), "FUERA_DE_LIMITE"),
    ("05-valida-retazo", "T01", CIRCLE_SCRAP, 0, 0, [], (SMALL_PIECE, 7, 6), "VALIDA"),
    ("06-margen-insuficiente", "T02", SMALL_SHEET, 20, 20, [(PIECE, 2, 2)], (PIECE, 0, 15), "MARGEN_INSUFICIENTE"),
    ("07-separacion-insuficiente", "T02", SMALL_SHEET, 20, 20, [(PIECE, 2, 2)], (PIECE, 2, 12), "SEPARACION_INSUFICIENTE"),
    ("08-valida-con-margen-y-separacion", "T02", SMALL_SHEET, 20, 20, [(PIECE, 2, 2)], (PIECE, 2, 13), "VALIDA"),
]

# Comparación T02: misma plancha y misma pieza, dos configuraciones.
COMPARISON_RESOLUTION = 5  # Resolución por defecto (SP-001).
REAL_SHEET = {"type": "RECTANGULO", "width_mm": 2440, "height_mm": 1830}
COMPARISON_PIECE = {"type": "RECTANGULO", "width_mm": 600, "height_mm": 400}
CONFIGURATIONS = [
    ("A", "sin margen ni separación", 0, 0),
    ("B", "margen 20 mm y separación 10 mm", 20, 10),
]

COLORS = {
    "margin": "#fde68a",  # material dentro de la zona de margen
    "usable": "#e2e8f0",  # celdas usables
    "blocked": "#fed7aa",  # zona de separación alrededor de las piezas
    "occupied": "#93c5fd",  # piezas ya colocadas
    "valid": "#22c55e",
    "invalid": "#ef4444",
}


def bit(rows, row, column):
    return 0 <= row < len(rows) and (rows[row] >> column) & 1


def layout_runs(layout):
    """Clasifica cada celda del material y junta las celdas seguidas de una fila con el mismo tipo."""
    material = layout.material
    for row in range(material.row_count):
        start, current = 0, None
        for column in range(material.columns + 1):
            if column == material.columns:
                kind = None
            elif bit(layout.occupied, row, column):
                kind = "occupied"
            elif bit(layout.blocked, row, column):
                kind = "blocked"
            elif bit(layout.usable, row, column):
                kind = "usable"
            elif bit(material.rows, row, column):
                kind = "margin"
            else:
                kind = None
            if kind != current:
                if current is not None:
                    yield row, start, column - start, current
                start, current = column, kind


def rects(runs, size):
    return "".join(
        f'<rect x="{column * size}" y="{row * size}" width="{length * size}" height="{size}" fill="{COLORS[kind]}"/>'
        for row, column, length, kind in runs
    )


def write_svg(path, layout, geometry, title, placed, candidate=None, valid=None):
    """placed: (máscara, fila, columna) de las piezas ya colocadas, para dibujar su contorno."""
    size = layout.material.resolution_mm
    width = layout.material.width_mm
    height = layout.material.height_mm
    extra = [
        f'<g fill="none" stroke="#1d4ed8" stroke-width="{max(width / 400, size * 0.08)}">'
        + "".join(
            f'<rect x="{column * size}" y="{row * size}" width="{piece.columns * size}" height="{piece.row_count * size}"/>'
            for piece, row, column in placed
        )
        + "</g>"
    ]
    if candidate is not None:
        piece, row, column = candidate
        color = COLORS["valid" if valid else "invalid"]
        cells = [
            (row + offset, column + c)
            for offset, bits in enumerate(piece.rows)
            for c in range(piece.columns)
            if (bits >> c) & 1
        ]
        extra.append(
            f'<g fill="{color}" fill-opacity="0.55" stroke="{color}" stroke-width="{size * 0.08}">'
            + "".join(f'<rect x="{c * size}" y="{r * size}" width="{size}" height="{size}"/>' for r, c in cells)
            + "</g>"
        )
        width = max(width, (column + piece.columns) * size)
        height = max(height, (row + piece.row_count) * size)
    pad = max(2 * size, width / 40)
    font = max(width / 30, 14)
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{-pad} {-pad - font * 1.5} {width + 2 * pad} {height + 2 * pad + font * 1.5}">\n'
        f'<rect x="{-pad}" y="{-pad - font * 1.5}" width="{width + 2 * pad}" '
        f'height="{height + 2 * pad + font * 1.5}" fill="#ffffff"/>\n'
        f'<text x="0" y="{-pad * 0.6}" font-family="sans-serif" font-size="{font}">{title}</text>\n'
        f'<g shape-rendering="crispEdges">{rects(layout_runs(layout), size)}</g>\n'
        + "\n".join(extra)
        + f'\n<g fill="none" stroke="#111827" stroke-width="{max(size * 0.12, 2)}">{outline_svg(geometry)}</g>\n'
        "</svg>\n",
        encoding="utf-8",
    )


def run_cases(lines):
    lines += [
        "## Casos válidos e inválidos",
        "",
        f"Celdas de {CASE_RESOLUTION} mm. Posición = (fila, columna) de la esquina superior izquierda de la pieza.",
        "",
        "| Caso | Tarea | Material | Margen / separación (mm) | Posición | Esperado | Obtenido | ¿Coincide? |",
        "|---|---|---|---|---|---|---|---|",
    ]
    all_match = True
    for name, task, geometry, margin, separation, placed, candidate, expected in CASES:
        layout = SheetLayout.empty(
            rasterize_material(geometry, CASE_RESOLUTION), margin_mm=margin, separation_mm=separation
        )
        placed_masks = [(rasterize_geometry(g, CASE_RESOLUTION), r, c) for g, r, c in placed]
        for mask, r, c in placed_masks:
            layout = layout.place(mask, r, c)
        piece_geometry, row, column = candidate
        piece = rasterize_geometry(piece_geometry, CASE_RESOLUTION)
        result = layout.check(piece, row, column)
        obtained = "VALIDA" if result.is_valid else result.issue.value
        match = obtained == expected
        all_match &= match
        material = "plancha 600 × 400" if geometry is SMALL_SHEET else "retazo circular r = 200"
        lines.append(
            f"| {name} | {task} | {material} | {margin} / {separation} | ({row}, {column}) "
            f"| {expected} | {obtained} | {'Sí' if match else 'NO'} |"
        )
        write_svg(
            RESULTS / f"{name}.svg",
            layout,
            geometry,
            f"{name}: {obtained}",
            placed_masks,
            (piece, row, column),
            result.is_valid,
        )
    return all_match


def fill_by_scan(layout, piece):
    """Coloca copias de la pieza recorriendo filas y columnas; solo para ilustrar el validador.

    No es la heurística First Fit (TA-017): no hay rotación ni orden de piezas, y cada posición
    se prueba una sola vez porque colocar una pieza nunca vuelve válida una posición anterior.
    """
    material = layout.material
    placements = []
    for row in range(material.row_count - piece.row_count + 1):
        for column in range(material.columns - piece.columns + 1):
            if layout.check(piece, row, column).is_valid:
                layout = layout.place(piece, row, column)
                placements.append((row, column))
    return layout, placements


def count_valid_positions(layout, piece):
    material = layout.material
    return sum(
        layout.check(piece, row, column).is_valid
        for row in range(material.row_count - piece.row_count + 1)
        for column in range(material.columns - piece.columns + 1)
    )


def run_comparison(lines):
    piece = rasterize_geometry(COMPARISON_PIECE, COMPARISON_RESOLUTION)
    material = rasterize_material(REAL_SHEET, COMPARISON_RESOLUTION)
    sheet_area = real_area(REAL_SHEET)
    piece_area = real_area(COMPARISON_PIECE)
    lines += [
        "",
        "## Comparación de dos configuraciones (T02)",
        "",
        f"Plancha 2440 × 1830 mm, celdas de {COMPARISON_RESOLUTION} mm, piezas de 600 × 400 mm sin rotación.",
        "Se llena con un barrido por filas y columnas que coloca la pieza en cada posición válida.",
        "No es First Fit (TA-017): solo muestra cómo cambia el espacio aprovechable según la configuración.",
        "",
        "| Config. | Margen / separación (mm) | Celdas | Celdas usables | Posiciones válidas en plancha vacía "
        "| Piezas colocadas | Aprovechamiento | Tiempo del barrido (ms) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for key, label, margin, separation in CONFIGURATIONS:
        empty = SheetLayout.empty(material, margin_mm=margin, separation_mm=separation)
        positions = count_valid_positions(empty, piece)
        start = time.perf_counter_ns()
        layout, placements = fill_by_scan(empty, piece)
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        usable = sum(bits.bit_count() for bits in empty.usable)
        utilization = len(placements) * piece_area / sheet_area
        lines.append(
            f"| {key} ({label}) | {margin} / {separation} | {material.row_count} × {material.columns} "
            f"| {usable:,} | {positions:,} | {len(placements)} | {utilization:.1%} | {elapsed:.0f} |"
        )
        write_svg(
            RESULTS / f"comparacion-{key}.svg",
            layout,
            REAL_SHEET,
            f"Config. {key}: {label} · {len(placements)} piezas",
            [(piece, row, column) for row, column in placements],
        )


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Resumen de validación geométrica (TA-007)",
        "",
        f"- Python {platform.python_version()} · {platform.system()} {platform.release()}",
        "- Colores en los SVG: gris = usable; amarillo = zona de margen; azul = pieza colocada;",
        "  naranja = zona de separación; verde / rojo = pieza candidata válida / rechazada; línea negra = contorno real.",
        "",
    ]
    all_match = run_cases(lines)
    run_comparison(lines)
    (RESULTS / "resumen.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nArchivos en {RESULTS}")
    if not all_match:
        sys.exit("Algún caso no dio el resultado esperado.")


if __name__ == "__main__":
    main()