"""Evidencia de TA-005 / TA-006: rasterización de las piezas del pedido.

Usa el código real del backend (app.modules.optimization.domain.rasterizer) y genera:
  - resumen.md: área real frente a área rasterizada por figura y resolución;
  - <figura>-<resolución>mm.svg: la máscara (celdas grises) con el contorno real encima (rojo).

Uso, desde la raíz del repositorio y con el venv del backend activo:
    python experiments/raster/scripts/raster_evidence.py

Los archivos se escriben en experiments/raster/results/ (ignorada por git).
Solo biblioteca estándar; no se conecta a ninguna base de datos.
"""
import math
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.optimization.domain.rasterizer import rasterize_geometry  # noqa: E402

RESULTS = ROOT / "experiments" / "raster" / "results"
RESOLUTIONS_MM = [1, 2, 5, 10, 20]
SVG_RESOLUTIONS_MM = [5, 20]
REPETITIONS = 5

HEXAGON = [[250, 0], [750, 0], [1000, 433], [750, 866], [250, 866], [0, 433]]
CASES = [
    ("rectangulo", {"type": "RECTANGULO", "width_mm": 800, "height_mm": 600}),
    ("rectangulo-802", {"type": "RECTANGULO", "width_mm": 802, "height_mm": 600}),
    ("circunferencia", {"type": "CIRCUNFERENCIA", "radius_mm": 500}),
    ("hexagono", {"type": "POLIGONO_CONVEXO", "vertices_mm": HEXAGON}),
    ("triangulo-hu007", {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [600, 0], [300, -450]]}),
    ("tira", {"type": "RECTANGULO", "width_mm": 1500, "height_mm": 30}),
]


def real_area(geometry):
    if geometry["type"] == "RECTANGULO":
        return geometry["width_mm"] * geometry["height_mm"]
    if geometry["type"] == "CIRCUNFERENCIA":
        return math.pi * geometry["radius_mm"] ** 2
    vertices = geometry["vertices_mm"]
    pairs = zip(vertices, vertices[1:] + vertices[:1])
    return abs(sum(ax * by - bx * ay for (ax, ay), (bx, by) in pairs)) / 2


def outline_svg(geometry):
    """Contorno real de la figura, trasladado al origen como lo hace el rasterizador."""
    if geometry["type"] == "CIRCUNFERENCIA":
        r = geometry["radius_mm"]
        return f'<circle cx="{r}" cy="{r}" r="{r}"/>'
    if geometry["type"] == "RECTANGULO":
        w, h = geometry["width_mm"], geometry["height_mm"]
        vertices = [[0, 0], [w, 0], [w, h], [0, h]]
    else:
        vertices = geometry["vertices_mm"]
    min_x = min(x for x, _ in vertices)
    min_y = min(y for _, y in vertices)
    points = " ".join(f"{x - min_x},{y - min_y}" for x, y in vertices)
    return f'<polygon points="{points}"/>'


def write_svg(path, geometry, mask):
    res = mask.resolution_mm
    cells = []
    for row, bits in enumerate(mask.rows):
        for column in range(mask.columns):
            if (bits >> column) & 1:
                cells.append(f'<rect x="{column * res}" y="{row * res}" width="{res}" height="{res}"/>')
    margin = res
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{-margin} {-margin} {mask.width_mm + 2 * margin} {mask.height_mm + 2 * margin}">\n'
        f'<g fill="#cbd5e1" stroke="#64748b" stroke-width="{res * 0.05}">{"".join(cells)}</g>\n'
        f'<g fill="none" stroke="#dc2626" stroke-width="{max(res * 0.2, 1)}">{outline_svg(geometry)}</g>\n'
        "</svg>\n",
        encoding="utf-8",
    )


def median_ms(geometry, resolution):
    rasterize_geometry(geometry, resolution)  # Calentamiento descartado.
    samples = []
    for _ in range(REPETITIONS):
        start = time.perf_counter_ns()
        rasterize_geometry(geometry, resolution)
        samples.append((time.perf_counter_ns() - start) / 1_000_000)
    return statistics.median(samples)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Resumen de rasterización (TA-005 / TA-006)",
        "",
        f"- Python {platform.python_version()} · {platform.system()} {platform.release()}",
        f"- Regla conservadora · {REPETITIONS} repeticiones · tiempo = mediana (perf_counter_ns)",
        "",
        "| Figura | Resolución (mm) | Filas x columnas | Celdas ocupadas | Área real (mm²) | Área raster (mm²) | Error | Tiempo (ms) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, geometry in CASES:
        area = real_area(geometry)
        for resolution in RESOLUTIONS_MM:
            mask = rasterize_geometry(geometry, resolution)
            error = mask.area_mm2 / area - 1
            lines.append(
                f"| {name} | {resolution} | {mask.row_count} x {mask.columns} | {mask.occupied_cells:,} "
                f"| {area:,.0f} | {mask.area_mm2:,.0f} | {error:+.3%} | {median_ms(geometry, resolution):.2f} |"
            )
            if resolution in SVG_RESOLUTIONS_MM:
                write_svg(RESULTS / f"{name}-{resolution}mm.svg", geometry, mask)

    (RESULTS / "resumen.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nArchivos en {RESULTS}")


if __name__ == "__main__":
    main()