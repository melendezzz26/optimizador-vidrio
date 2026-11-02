"""Figuras de las máscaras exactas; los dibujos no deciden factibilidad."""
from dataclasses import replace
from decimal import Decimal

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle
import numpy as np

from experiments.optimization.loader import load_problem
from app.modules.optimization.domain.rotation import RasterCache
from app.modules.optimization.domain.packing import _empty_layout
from sp006.validation import rebuild_result


def bits_array(rows, columns):
    return np.array([[(bits >> c) & 1 for c in range(columns)] for bits in rows])


def plot_layout(record):
    if "placements" not in record:
        fig, ax = plt.subplots(figsize=(8, 2))
        ax.text(0, .5, f"{record['method']}: {record['status']} — sin layout medido")
        ax.axis("off")
        return fig
    problem = load_problem(record["case_id"])
    result = rebuild_result(problem, record["placements"])
    stocks = [s for g in problem.groups for s in g.stock_candidates]
    missing = [u for u in problem.units if [u.piece_id, u.unit_index] in record["unplaced"]]
    panels = len(stocks) + bool(missing)
    cols = min(4, panels)
    rows = (panels + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4.6 * cols, 4.5 * rows),
                             squeeze=False, layout="constrained")
    cache = RasterCache()
    colors = plt.get_cmap("tab20").colors
    for ax, stock in zip(axes.flat, stocks):
        material = cache.material(stock, problem.config.resolution_mm)
        layout = _empty_layout(material, problem.config)
        image = np.zeros((material.row_count, material.columns))
        image[bits_array(material.rows, material.columns) == 1] = 1
        image[(bits_array(material.rows, material.columns) - bits_array(layout.usable, material.columns)) == 1] = 2
        selected = [p for p in result.placements if p.stock.identity == stock.identity]
        for i, p in enumerate(selected):
            mask = cache.orientations(replace(p.piece, geometry=p.geometry), problem.config.resolution_mm,
                                      Decimal(360))[0].orientation.mask
            r, c = int(p.y_mm), int(p.x_mm)  # Los fixtures oficiales conservan resolución 1 mm.
            for offset, bits in enumerate(mask.rows):
                for column in range(mask.columns):
                    if bits & (1 << column):
                        image[r + offset, c + column] = i + 3
            layout = layout.place(mask, r, c)
            ax.text(c + mask.columns / 2, r + mask.row_count / 2,
                    f"{p.piece.piece_id}.{p.piece.unit_index}\n{p.rotation_deg}°", fontsize=7,
                    ha="center", va="center", bbox=dict(facecolor="white", alpha=.7, edgecolor="none", pad=1))
        cmap = ListedColormap(["#253244", "#edf1f5", "#adb5bd", *colors])
        ax.imshow(image, cmap=cmap, vmin=0, vmax=22, interpolation="nearest", origin="upper",
                  extent=(0, material.columns, material.row_count, 0))
        # Separación reservada sobre celdas libres: naranja translúcido.
        blocked_only = bits_array(tuple(b & ~o & u for b, o, u in zip(
            layout.blocked, layout.occupied, layout.usable)), material.columns)
        ax.imshow(np.ma.masked_where(blocked_only == 0, blocked_only), cmap=ListedColormap(["#ee9b00"]),
                  alpha=.5, extent=(0, material.columns, material.row_count, 0), interpolation="nearest")
        for residual in record.get("residuals", []):
            if (residual["material_source"], residual["material_id"], residual["stock_unit_index"]) == tuple(
                    (stock.source.value, stock.material_id, stock.physical_unit_index)):
                ax.add_patch(Rectangle((float(residual["x_mm"]), float(residual["y_mm"])),
                    float(residual["width_mm"]), float(residual["height_mm"]), fill=False,
                    linestyle="--", linewidth=2, edgecolor="green"))
        ax.set_title(f"{stock.source.value} {stock.material_id}/{stock.physical_unit_index} "
                     f"{'usado' if selected else 'sin usar'}\nvidrio {stock.glass_type_id}, {stock.thickness_mm} mm")
        ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
        ax.set_aspect("equal")
    if missing:
        ax = axes.flat[len(stocks)]
        pending = set(u.identity for u in problem.units[record["processed_units"]:])
        ax.set_title(f"No colocadas: {len(missing)}")
        ax.axis("off")
        # Galería raster, con identidad, para cada unidad faltante.
        ncols = 4
        for index, unit in enumerate(missing):
            inset = ax.inset_axes([(index % ncols) / ncols, .85 - (index // ncols) * .15, .22, .12])
            mask = cache.base(unit, problem.config.resolution_mm).mask
            inset.imshow(bits_array(mask.rows, mask.columns), cmap="Reds", vmin=0, vmax=1)
            inset.set_title(f"{unit.piece_id}.{unit.unit_index} " + ("pend." if unit.identity in pending else "NO_FIT"), fontsize=6)
            inset.axis("off")
    for ax in list(axes.flat)[panels:]:
        fig.delaxes(ax)
    fig.suptitle(f"{record['case_id']} · {record['method']} · {record['status']} · {record['placed']}/{record['requested']}\n"
                 "Oscuro: exterior · gris: margen · naranja: separación · verde: recuperable\n"
                 f"Etiquetas: pieza.unidad / giro · No colocadas: {len(missing)}", fontsize=10)
    return fig


def plot_comparison(frame):
    # Una barra = mediana de repeticiones; valores faltantes se conservan como NaN.
    names = ["placed", "sheets_used", "utilization_pct", "elapsed_s", "peak_rss_mib", "waste_mm2"]
    labels = ["Unidades colocadas", "Planchas usadas", "Aprovechamiento (%)", "Tiempo de cálculo (s)",
              "RSS máximo observado (MiB)", "Merma (mm²)"]
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    grouped = frame.groupby(["case_id", "method"])[names].median()
    for ax, name, title in zip(axes.flat, names, labels):
        grouped[name].unstack("method").plot.bar(ax=ax, rot=0)
        ax.set_title(title); ax.set_xlabel("")
        ax.set_xticklabels([s.replace("EXP-", "").replace("-001", "") for s in grouped.index.levels[0]])
        ax.grid(axis="y", alpha=.25)
    fig.suptitle("Mediciones de este entorno CPU; no son tiempos del servidor de NewGlass")
    fig.tight_layout(rect=(0, 0, 1, .97))
    return fig


def descriptive_analysis(frame):
    lines = []
    for case_id, part in frame.groupby("case_id", sort=False):
        lines.append(f"{case_id}:")
        base = part[part.method.isin(["FF", "BF", "WF"])].groupby("method").median(numeric_only=True)
        for method in ("BS-2", "BS-3", "BS-4"):
            candidate = part[part.method == method]
            if candidate.empty or not candidate.status.isin(["COMPLETE", "PARTIAL_GEOMETRIC"]).all():
                lines.append(f"  {method}: comparación inconclusa por fallo o límite.")
                continue
            med = candidate.median(numeric_only=True)
            comparisons = []
            for b, baseline in base.iterrows():
                reference = part[part.method == b]
                if not reference.status.isin(["COMPLETE", "PARTIAL_GEOMETRIC"]).all():
                    comparisons.append(f"{b}: comparación inconclusa por fallo o límite del baseline")
                    continue
                comparisons.append(f"{b}: Δcolocadas={med.placed-baseline.placed:+.0f}, "
                                   f"Δaprovechamiento={med.utilization_pct-baseline.utilization_pct:+.3f} pp, "
                                   f"Δplanchas={med.sheets_used-baseline.sheets_used:+.0f}, "
                                   f"Δmerma={med.waste_mm2-baseline.waste_mm2:+.2f} mm², "
                                   f"Δrecuperable={med.recoverable_remnant_mm2-baseline.recoverable_remnant_mm2:+.2f} mm², "
                                   f"Δtiempo={med.elapsed_s-baseline.elapsed_s:+.4f} s")
            lines.append(f"  {method}: " + "; ".join(comparisons))
    lines.append("Un patrón distinto no demuestra mejora. Revisar completitud, fuentes, merma, costo y límites juntos.")
    return "\n".join(lines)
