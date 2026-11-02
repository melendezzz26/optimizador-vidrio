"""SVG de escala de grises para material libre y espacio de anclajes."""
from html import escape
from pathlib import Path

from .lab import AnchorMap, RasterRegion


def _svg_start(width: int, height: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f4f4f4"/>',
        f'<text x="12" y="20" font-family="sans-serif" font-size="14">{escape(title)}</text>',
    ]


def render_physical_map(layout, regions: tuple[RasterRegion, ...], path: Path, label: str) -> None:
    cell = 12
    left, top = 12, 38
    width = left * 2 + layout.material.columns * cell
    height = top + layout.material.row_count * cell + 46
    svg = _svg_start(width, height, f"{label} | material físico")
    region_types = {}
    for region in regions:
        for coordinate in region.cells:
            region_types[coordinate] = region.region_type
    colors = {
        "outside": "#d9d9d9",
        "exterior": "#ffffff",
        "internal_hole": "#969696",
        "clearance": "#575757",
        "occupied": "#111111",
    }
    for row in range(layout.material.row_count):
        for column in range(layout.material.columns):
            bit = 1 << column
            if not (layout.material.rows[row] & bit):
                color = colors["outside"]
            elif layout.occupied[row] & bit:
                color = colors["occupied"]
            elif layout.blocked[row] & bit:
                color = colors["clearance"]
            else:
                color = colors.get(region_types.get((row, column), "exterior"), "#ffffff")
            x, y = left + column * cell, top + row * cell
            svg.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{color}" stroke="#b5b5b5" stroke-width="0.35"/>')
    legend = [
        ("#111111", "Ocupado"), ("#575757", "Bloqueado por separación"),
        ("#ffffff", "Exterior libre"), ("#969696", "Hueco interno"),
        ("#d9d9d9", "Fuera del material"),
    ]
    x = left
    y = top + layout.material.row_count * cell + 20
    for color, name in legend:
        svg.append(f'<rect x="{x}" y="{y-10}" width="10" height="10" fill="{color}" stroke="#666"/>')
        svg.append(f'<text x="{x+14}" y="{y-1}" font-family="sans-serif" font-size="10">{escape(name)}</text>')
        x += 112 if len(name) < 18 else 154
    svg.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(svg), encoding="utf-8")


def render_anchor_map(anchor_map: AnchorMap, path: Path, label: str, selected_anchor=None) -> None:
    cell = 16
    left, top = 12, 38
    width = left * 2 + max(anchor_map.columns, 1) * cell
    height = top + max(anchor_map.rows, 1) * cell + 48
    svg = _svg_start(width, height, f"{label} | anclajes {anchor_map.unit.piece_id} a {anchor_map.rotation_deg}°")
    for row in range(anchor_map.rows):
        for column in range(anchor_map.columns):
            bit = 1 << column
            if anchor_map.pocket_rows[row] & bit:
                color = "#969696"
            elif anchor_map.exterior_rows[row] & bit:
                color = "#ffffff"
            elif anchor_map.domain_rows[row] & bit:
                color = "#c7c7c7"
            else:
                color = "#333333"
            x, y = left + column * cell, top + row * cell
            selected = selected_anchor == (row, column)
            stroke = "#000000" if selected else "#aaaaaa"
            stroke_width = "2" if selected else "0.5"
            svg.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{color}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
    y = top + anchor_map.rows * cell + 20
    for x, color, name in ((left, "#333333", "Inválido"), (left+90, "#ffffff", "Anclaje exterior"),
                           (left+220, "#969696", "Pocket"), (left+320, "#c7c7c7", "Fuera del dominio factible")):
        svg.append(f'<rect x="{x}" y="{y-10}" width="10" height="10" fill="{color}" stroke="#666"/>')
        svg.append(f'<text x="{x+14}" y="{y-1}" font-family="sans-serif" font-size="10">{escape(name)}</text>')
    svg.append(f'<text x="{left}" y="{height-8}" font-family="sans-serif" font-size="10">Cada celda es un origen raster; conectividad 4-conexa.</text>')
    svg.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(svg), encoding="utf-8")


def render_pocket_placement(layout, anchor_map: AnchorMap, selected_anchor,
                            pending_mask, path: Path, label: str) -> None:
    """Muestra el layout previo, la pieza HF colocada y el pocket de anclajes."""
    cell = 2
    margin = 12
    title_height = 32
    physical_width = layout.material.columns * cell
    physical_height = layout.material.row_count * cell
    anchor_width = max(anchor_map.columns, 1) * cell
    anchor_height = max(anchor_map.rows, 1) * cell
    gap = 24
    width = margin * 2 + physical_width + gap + anchor_width
    height = title_height + max(physical_height, anchor_height) + 64
    svg = _svg_start(width, height, f"{label} | placement dentro de pocket")
    physical_left, anchor_left, top = margin, margin + physical_width + gap, title_height
    svg.append(f'<text x="{physical_left}" y="{title_height-8}" font-family="sans-serif" font-size="12">Layout previo + pieza HF (gris)</text>')
    svg.append(f'<text x="{anchor_left}" y="{title_height-8}" font-family="sans-serif" font-size="12">Mapa de anclajes y pocket</text>')

    def append_runs(x, y, colors):
        if not colors:
            return
        run_start, run_color = 0, colors[0]
        for column in range(1, len(colors) + 1):
            next_color = colors[column] if column < len(colors) else None
            if next_color != run_color:
                if run_color is not None:
                    svg.append(
                        f'<rect x="{x + run_start * cell}" y="{y}" '
                        f'width="{(column-run_start) * cell}" height="{cell}" '
                        f'fill="{run_color}" stroke="#b5b5b5" stroke-width="0.2"/>'
                    )
                run_start, run_color = column, next_color

    for row in range(layout.material.row_count):
        colors = []
        for column in range(layout.material.columns):
            bit = 1 << column
            if not (layout.material.rows[row] & bit):
                color = "#d9d9d9"
            elif layout.occupied[row] & bit:
                color = "#111111"
            elif layout.blocked[row] & bit:
                color = "#666666"
            else:
                color = "#ffffff"
            colors.append(color)
        append_runs(physical_left, top + row * cell, colors)

    selected_row, selected_column = selected_anchor
    for row_offset, row_bits in enumerate(pending_mask.rows):
        remaining = row_bits
        while remaining:
            bit = remaining & -remaining
            start = bit.bit_length() - 1
            run_bits = remaining >> start
            run_length = (run_bits ^ (run_bits + 1)).bit_length() - 1
            x = physical_left + (selected_column + start) * cell
            y = top + (selected_row + row_offset) * cell
            svg.append(f'<rect x="{x}" y="{y}" width="{run_length * cell}" height="{cell}" fill="#999999" stroke="#222222" stroke-width="0.35"/>')
            remaining &= ~(((1 << run_length) - 1) << start)

    for row in range(anchor_map.rows):
        colors = []
        for column in range(anchor_map.columns):
            bit = 1 << column
            if anchor_map.pocket_rows[row] & bit:
                color = "#999999"
            elif anchor_map.exterior_rows[row] & bit:
                color = "#ffffff"
            elif anchor_map.domain_rows[row] & bit:
                color = "#cccccc"
            else:
                color = "#333333"
            colors.append(color)
        append_runs(anchor_left, top + row * cell, colors)
    selected_x = anchor_left + selected_column * cell
    selected_y = top + selected_row * cell
    svg.append(f'<rect x="{selected_x}" y="{selected_y}" width="{cell}" height="{cell}" fill="none" stroke="#000000" stroke-width="1.8"/>')

    legend_y = top + max(physical_height, anchor_height) + 18
    legend = (("#111111", "Piezas previas"), ("#999999", "Pieza HF / pocket"),
              ("#ffffff", "Exterior legal"), ("#333333", "Placement invalido"))
    x = margin
    for color, text in legend:
        svg.append(f'<rect x="{x}" y="{legend_y-9}" width="9" height="9" fill="{color}" stroke="#666666"/>')
        svg.append(f'<text x="{x+13}" y="{legend_y-1}" font-family="sans-serif" font-size="10">{text}</text>')
        x += 140
    svg.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(svg), encoding="utf-8")


def render_capability_comparison(runs: dict, path: Path) -> None:
    """Compara layouts finales con máscaras reales; solo HF marca su pocket."""
    methods = ("FF", "BF", "WF", "HF")
    first = runs["FF"]
    stocks = sorted(first["setup"].stocks_by_id.values(),
                    key=lambda item: item.source.value != "RETAZO")
    cell, margin, gap = 1.4, 16, 22
    stock_width = max(int(stock.geometry["width_mm"]) for stock in stocks) * cell
    stock_height = max(int(stock.geometry["height_mm"]) for stock in stocks) * cell
    panel_width = stock_width + 2 * margin
    panel_height = 84 + 2 * stock_height + gap + 42
    width = int(4 * panel_width + 5 * gap)
    height = int(panel_height + 52)
    svg = _svg_start(width, height, "HF-CAPABILITY-001 | caso controlado, no rendimiento general")
    svg.append('<text x="16" y="39" font-family="sans-serif" font-size="12">Gris claro: piezas previas; gris oscuro: inserto P11; negro: círculo posterior P12. Solo HF señala pocket y pieza insertada.</text>')

    def draw_mask(mask, column, row, origin_x, origin_y, color):
        for offset, bits in enumerate(mask.rows):
            remaining = bits
            while remaining:
                bit = remaining & -remaining
                start = bit.bit_length() - 1
                shifted = remaining >> start
                length = (shifted ^ (shifted + 1)).bit_length() - 1
                x = origin_x + (column + start) * cell
                y = origin_y + (row + offset) * cell
                svg.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{length * cell:.2f}" height="{cell:.2f}" fill="{color}"/>')
                remaining &= ~(((1 << length) - 1) << start)

    for method_index, method in enumerate(methods):
        run = runs[method]
        panel_x = gap + method_index * (panel_width + gap)
        svg.append(f'<rect x="{panel_x:.2f}" y="50" width="{panel_width:.2f}" height="{panel_height:.2f}" fill="#eeeeee" stroke="#333333" stroke-width="1"/>')
        svg.append(f'<text x="{panel_x + margin:.2f}" y="71" font-family="sans-serif" font-size="15">{escape(method)}</text>')
        for stock_index, stock in enumerate(stocks):
            source_x = panel_x + margin
            source_y = 99 + stock_index * (stock_height + gap + 20)
            source_name = "Retazo" if stock.source.value == "RETAZO" else "Plancha"
            svg.append(f'<text x="{source_x:.2f}" y="{source_y - 7:.2f}" font-family="sans-serif" font-size="11">{source_name} {stock.geometry["width_mm"]} × {stock.geometry["height_mm"]} mm</text>')
            svg.append(f'<rect x="{source_x:.2f}" y="{source_y:.2f}" width="{stock_width:.2f}" height="{stock_height:.2f}" fill="#ffffff" stroke="#222222" stroke-width="1"/>')
            source_placements = [
                placement for placement in run["result"].placements
                if placement.stock.identity == stock.identity
            ]
            if not source_placements:
                svg.append(f'<text x="{source_x + 9:.2f}" y="{source_y + 21:.2f}" font-family="sans-serif" font-size="11">Sin uso</text>')
            for placement in source_placements:
                oriented = next(
                    item for item in run["setup"].prepared.orientations(placement.piece)
                    if item.orientation.rotation_deg == placement.rotation_deg
                )
                mask = oriented.orientation.mask
                column = int(placement.x_mm / run["setup"].problem.config.resolution_mm)
                row = int(placement.y_mm / run["setup"].problem.config.resolution_mm)
                color = "#bdbdbd" if placement.piece.piece_id not in (11, 12) else (
                    "#686868" if placement.piece.piece_id == 11 else "#222222"
                )
                draw_mask(mask, column, row, source_x, source_y, color)
                if method == "HF" and placement.piece.piece_id == 11:
                    x = source_x + column * cell
                    y = source_y + row * cell
                    svg.append(
                        f'<rect x="{x:.2f}" y="{y:.2f}" '
                        f'width="{mask.columns * cell:.2f}" height="{mask.row_count * cell:.2f}" '
                        f'fill="none" stroke="#000000" stroke-width="2"/>'
                    )
                    svg.append(
                        f'<text x="{x + mask.columns * cell + 3:.2f}" y="{y + 12:.2f}" '
                        'font-family="sans-serif" font-size="11">P11 en pocket</text>'
                    )
            if method == "HF" and stock.source.value == "RETAZO":
                selected = run["diagnostics"]["selected_pockets"][0]
                min_row, min_column, max_row, max_column = selected["bbox_row_column"]
                x = source_x + min_column * cell
                y = source_y + min_row * cell
                svg.append(
                    f'<rect x="{x:.2f}" y="{y:.2f}" '
                    f'width="{(max_column - min_column + 1) * cell:.2f}" '
                    f'height="{(max_row - min_row + 1) * cell:.2f}" '
                    'fill="none" stroke="#000000" stroke-width="2" stroke-dasharray="3,2"/>'
                )
    svg.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(svg), encoding="utf-8")
