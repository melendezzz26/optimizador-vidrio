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
