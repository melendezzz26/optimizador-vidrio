"""Detección experimental sobre layouts y máscaras raster existentes."""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from time import perf_counter_ns

from app.modules.orders.domain.geometry import GeometryValidator
from app.modules.optimization.domain.packing import _empty_layout
from app.modules.optimization.domain.placement import PlacementError, SheetLayout
from app.modules.optimization.domain.problem import (
    MaterialGroup,
    MaterialSource,
    OptimizationConfig,
    OptimizationProblem,
    PieceUnit,
    Placement,
    StockCandidate,
)
from app.modules.optimization.domain.preparation import prepare_group_units
from app.modules.optimization.domain.raster_mask import RasterMask
from app.modules.optimization.domain.run_geometry import prepare_run_geometry


DIAGNOSTIC_LABEL = "DIAGNÓSTICO HOLE FILLING — NO PERTENECE A TA-027"
REALISTIC_LABEL = "PEDIDO REALISTA HOLE FILLING - NO PERTENECE A TA-027"
CAPABILITY_LABEL = "CASO CONTROLADO HF - NO ES BENCHMARK GENERAL NI PERTENECE A TA-027"
CASE_DIR = Path(__file__).resolve().parent / "cases"


def _area(geometry) -> Decimal:
    kind = geometry["type"]
    if kind == "RECTANGULO":
        value = GeometryValidator.validate_rectangle(geometry["width_mm"], geometry["height_mm"])
    elif kind == "CIRCUNFERENCIA":
        value = GeometryValidator.validate_circle(geometry["radius_mm"])
    elif kind == "POLIGONO_CONVEXO":
        value = GeometryValidator.validate_convex_polygon(geometry["vertices_mm"])
    else:
        raise ValueError(f"Geometría experimental desconocida: {kind}")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def read_case(case_id: str) -> dict:
    if case_id.startswith("HF-DIAGNOSTIC-"):
        expected_label = DIAGNOSTIC_LABEL
    elif case_id.startswith("HF-REALISTIC-"):
        expected_label = REALISTIC_LABEL
    elif case_id.startswith("HF-CAPABILITY-"):
        expected_label = CAPABILITY_LABEL
    else:
        raise ValueError("El laboratorio solo acepta diagnósticos o pedidos realistas HF congelados.")
    data = json.loads((CASE_DIR / f"{case_id}.json").read_text(encoding="utf-8"))
    if data.get("case_id") != case_id or data.get("label") != expected_label:
        raise ValueError("El ID o la etiqueta del caso HF no coincide.")
    return data


@dataclass(frozen=True)
class DiagnosticSetup:
    data: dict
    problem: OptimizationProblem
    units_by_id: dict[int, PieceUnit]
    stocks_by_id: dict[int, StockCandidate]
    roles_by_id: dict[int, str]
    prepared: object
    layouts: dict
    seed_placements: tuple[Placement, ...]
    pending: tuple[PieceUnit, ...]


def prepare_case(case_id: str) -> DiagnosticSetup:
    """Construye snapshots y valida cada semilla con SheetLayout.check/place."""
    data = read_case(case_id)
    config = OptimizationConfig(**{
        name: Decimal(str(value)) for name, value in data["config"].items()
    })
    material = data["material"]
    glass_type_id = int(material["glass_type_id"])
    thickness = Decimal(str(material["thickness_mm"]))
    stocks_by_id = {}
    for row in data["stocks"]:
        source = MaterialSource(row["source"])
        stock = StockCandidate(
            source=source,
            material_id=int(row["material_id"]),
            physical_unit_index=int(row["physical_unit_index"]),
            glass_type_id=glass_type_id,
            thickness_mm=thickness,
            geometry=row["geometry"],
            area_mm2=_area(row["geometry"]),
        )
        if stock.material_id in stocks_by_id:
            raise ValueError("El diagnóstico repite material_id dentro de sus stocks.")
        stocks_by_id[stock.material_id] = stock

    units_by_id, roles_by_id = {}, {}
    for row in data["pieces"]:
        geometry = row["geometry"]
        unit = PieceUnit(
            order_id=1,
            piece_id=int(row["piece_id"]),
            unit_index=1,
            glass_type_id=glass_type_id,
            thickness_mm=thickness,
            geometry=geometry,
            area_mm2=_area(geometry),
        )
        if unit.piece_id in units_by_id:
            raise ValueError("El diagnóstico repite piece_id.")
        if row["role"] not in ("seed", "pending"):
            raise ValueError("Cada geometría debe ser semilla o pieza pendiente.")
        units_by_id[unit.piece_id] = unit
        roles_by_id[unit.piece_id] = row["role"]

    ordered_stocks = tuple(sorted(stocks_by_id.values(), key=lambda stock: stock.source is MaterialSource.SHEET))
    group = MaterialGroup(
        glass_type_id=glass_type_id,
        thickness_mm=thickness,
        units=tuple(units_by_id.values()),
        stock_candidates=ordered_stocks,
    )
    problem = OptimizationProblem(order_ids=(1,), config=config, groups=(group,))
    prepared = prepare_run_geometry(problem)
    layouts, seeds = {}, []
    for row in data["pieces"]:
        if row["role"] != "seed":
            continue
        unit = units_by_id[int(row["piece_id"])]
        stock = stocks_by_id[int(row["stock_material_id"])]
        layout = layouts.get(stock.identity)
        if layout is None:
            layout = _empty_layout(prepared.material(stock), config)
        angle = Decimal(str(row["rotation_deg"]))
        oriented = next((item for item in prepared.orientations(unit)
                         if item.orientation.rotation_deg == angle), None)
        if oriented is None:
            raise ValueError(f"La orientación de semilla {angle}° no pertenece a la grilla del motor.")
        row_index, column = _cell_index(row["y_mm"], config.resolution_mm), _cell_index(row["x_mm"], config.resolution_mm)
        valid = layout.check(oriented.orientation.mask, row_index, column)
        if not valid.is_valid:
            raise PlacementError(
                f"Semilla {unit.piece_id} inválida en el caso congelado: {valid.issue.value}."
            )
        layouts[stock.identity] = layout.place(oriented.orientation.mask, row_index, column)
        seeds.append(Placement(
            piece=unit,
            stock=stock,
            x_mm=Decimal(str(row["x_mm"])),
            y_mm=Decimal(str(row["y_mm"])),
            rotation_deg=angle,
            geometry=oriented.orientation.geometry,
        ))
    pending = tuple(sorted(
        (unit for unit in units_by_id.values() if roles_by_id[unit.piece_id] == "pending"),
        key=lambda unit: (-unit.area_mm2, unit.order_id, unit.piece_id, unit.unit_index),
    ))
    return DiagnosticSetup(
        data=data, problem=problem, units_by_id=units_by_id,
        stocks_by_id=stocks_by_id, roles_by_id=roles_by_id,
        prepared=prepared, layouts=layouts, seed_placements=tuple(seeds), pending=pending,
    )


def setup_from_problem(problem: OptimizationProblem, case_id: str) -> DiagnosticSetup:
    """Adapta un snapshot ya preparado a HF sin semillas, para benchmark oficial gated."""
    prepared = prepare_run_geometry(problem)
    all_units = tuple(unit for group in problem.groups for unit in group.units)
    units_by_id = {unit.piece_id: unit for unit in all_units}
    roles_by_id = {unit.piece_id: "pending" for unit in all_units}
    stocks_by_id = {
        index: stock
        for index, stock in enumerate(
            stock for group in problem.groups for stock in group.stock_candidates
        )
    }
    pending = tuple(
        unit
        for group in sorted(problem.groups, key=lambda item: item.key)
        for unit in prepare_group_units(group.units)
    )
    return DiagnosticSetup(
        data={"case_id": case_id, "label": "BENCHMARK OFICIAL SP-004 — EXP-HF"},
        problem=problem,
        units_by_id=units_by_id,
        stocks_by_id=stocks_by_id,
        roles_by_id=roles_by_id,
        prepared=prepared,
        layouts={},
        seed_placements=(),
        pending=pending,
    )


def _cell_index(value, resolution: Decimal) -> int:
    coordinate = Decimal(str(value)) / resolution
    if coordinate != coordinate.to_integral_value():
        raise ValueError("Las semillas deben alinearse a la resolución raster congelada.")
    return int(coordinate)


@dataclass(frozen=True)
class RasterRegion:
    region_type: str
    cells: tuple[tuple[int, int], ...]
    min_row: int
    min_column: int
    max_row: int
    max_column: int

    @property
    def area_cells(self) -> int:
        return len(self.cells)


@dataclass(frozen=True)
class AnchorMap:
    unit: PieceUnit
    stock: StockCandidate
    rotation_deg: Decimal
    rows: int
    columns: int
    domain_rows: tuple[int, ...]
    valid_rows: tuple[int, ...]
    exterior_rows: tuple[int, ...]
    pocket_rows: tuple[int, ...]
    pockets: tuple[RasterRegion, ...]
    positions_examined: int
    origin_generation_ns: int
    component_detection_ns: int


def _components(row_bits: tuple[int, ...], columns: int) -> tuple[RasterRegion, ...]:
    """Componentes 4-conexas deterministas sobre filas de bits."""
    remaining = list(row_bits)
    regions = []
    for start_row in range(len(remaining)):
        while remaining[start_row]:
            first = remaining[start_row] & -remaining[start_row]
            start_column = first.bit_length() - 1
            remaining[start_row] &= ~first
            stack = [(start_row, start_column)]
            cells = []
            while stack:
                row, column = stack.pop()
                cells.append((row, column))
                for next_row, next_column in (
                    (row - 1, column), (row, column - 1),
                    (row, column + 1), (row + 1, column),
                ):
                    if not (0 <= next_row < len(remaining) and 0 <= next_column < columns):
                        continue
                    bit = 1 << next_column
                    if remaining[next_row] & bit:
                        remaining[next_row] &= ~bit
                        stack.append((next_row, next_column))
            cells.sort()
            regions.append(RasterRegion(
                region_type="component",
                cells=tuple(cells),
                min_row=cells[0][0],
                min_column=min(column for _, column in cells),
                max_row=max(row for row, _ in cells),
                max_column=max(column for _, column in cells),
            ))
    return tuple(regions)


def physical_free_regions(layout: SheetLayout) -> tuple[RasterRegion, ...]:
    """Clasifica libre físico según conectividad 4-conexa con exterior del material."""
    material = layout.material
    width_mask = (1 << material.columns) - 1
    free_rows = tuple(mask & ~occupied for mask, occupied in zip(material.rows, layout.occupied))
    exterior_seed_rows = []
    for row, free in enumerate(free_rows):
        seed = free & 1
        seed |= free & (1 << (material.columns - 1))
        seed |= free & ~(material.rows[row] << 1)
        seed |= free & ~(material.rows[row] >> 1)
        seed |= free if row == 0 else free & ~material.rows[row - 1]
        seed |= free if row == material.row_count - 1 else free & ~material.rows[row + 1]
        exterior_seed_rows.append(seed & width_mask)
    exterior_seeds = tuple(exterior_seed_rows)
    result = []
    for component in _components(free_rows, material.columns):
        touches_exterior = any(
            exterior_seeds[row] & (1 << column) for row, column in component.cells
        )
        result.append(RasterRegion(
            region_type="exterior" if touches_exterior else "internal_hole",
            cells=component.cells,
            min_row=component.min_row,
            min_column=component.min_column,
            max_row=component.max_row,
            max_column=component.max_column,
        ))
    return tuple(result)


def _domain_boundary_rows(domain_rows: tuple[int, ...], columns: int) -> tuple[int, ...]:
    boundary = [0] * len(domain_rows)
    for row, bits in enumerate(domain_rows):
        if not bits:
            continue
        above = domain_rows[row - 1] if row > 0 else 0
        below = domain_rows[row + 1] if row + 1 < len(domain_rows) else 0
        left = bits << 1
        right = bits >> 1
        has_all_four_neighbors = bits & left & right & above & below
        boundary[row] = bits & ~has_all_four_neighbors
    return tuple(boundary)


def _exterior_reachable_rows(valid_rows: tuple[int, ...], boundary_rows: tuple[int, ...],
                             columns: int) -> tuple[int, ...]:
    """Flood-fill legal anchors from the domain edge with 4-connectivity and row bits."""
    from collections import deque

    reachable = [valid & boundary for valid, boundary in zip(valid_rows, boundary_rows)]
    queue = deque(row for row, bits in enumerate(reachable) if bits)
    queued = set(queue)
    while queue:
        row = queue.popleft()
        queued.discard(row)
        row_valid = valid_rows[row]
        expanded = reachable[row]
        while True:
            next_expanded = (expanded | (expanded << 1) | (expanded >> 1)) & row_valid
            if next_expanded == expanded:
                break
            expanded = next_expanded
        if expanded != reachable[row]:
            reachable[row] = expanded
        for neighbor in (row - 1, row + 1):
            if not 0 <= neighbor < len(valid_rows):
                continue
            added = expanded & valid_rows[neighbor] & ~reachable[neighbor]
            if added:
                reachable[neighbor] |= added
                if neighbor not in queued:
                    queued.add(neighbor)
                    queue.append(neighbor)
    width_mask = (1 << columns) - 1
    return tuple(bits & valid & width_mask for bits, valid in zip(reachable, valid_rows))


def _origin_columns(available: int, shape: int, all_origins: int,
                    row_cache: dict[tuple[int, int, int], int] | None = None) -> int:
    """Bit-parallel exact placement origins, following SheetLayout.first_position."""
    cache_key = (available, shape, all_origins)
    if row_cache is not None and cache_key in row_cache:
        return row_cache[cache_key]
    candidates = all_origins
    remaining = shape
    offset = 0
    while remaining:
        zeros = (remaining & -remaining).bit_length() - 1
        remaining >>= zeros
        offset += zeros
        length = (remaining ^ (remaining + 1)).bit_length() - 1
        windows, covered = available, 1
        while covered * 2 <= length:
            windows &= windows >> covered
            covered *= 2
        if length > covered:
            windows &= windows >> (length - covered)
        candidates &= windows >> offset
        if not candidates:
            if row_cache is not None:
                row_cache[cache_key] = 0
            return 0
        remaining >>= length
        offset += length
    if row_cache is not None:
        row_cache[cache_key] = candidates
    return candidates


def _valid_origin_rows(free_rows: tuple[int, ...], mask: RasterMask,
                       origin_rows: int, origin_columns: int,
                       row_cache: dict[tuple[int, int, int], int] | None = None) -> tuple[int, ...]:
    all_origins = (1 << origin_columns) - 1
    occupied_rows = tuple((offset, bits) for offset, bits in enumerate(mask.rows) if bits)
    result = []
    for row in range(origin_rows):
        candidates = all_origins
        for offset, shape in occupied_rows:
            candidates &= _origin_columns(free_rows[row + offset], shape, all_origins, row_cache)
            if not candidates:
                break
        result.append(candidates)
    return tuple(result)


def feasible_anchor_map(layout: SheetLayout, unit: PieceUnit, stock: StockCandidate, oriented,
                        row_cache: dict[tuple[int, int, int], int] | None = None) -> AnchorMap:
    """Genera el mapa con las filas bit del layout; el placement elegido usa check/place."""
    mask: RasterMask = oriented.orientation.mask
    rows = layout.material.row_count - mask.row_count + 1
    columns = layout.material.columns - mask.columns + 1
    if rows <= 0 or columns <= 0:
        return AnchorMap(unit, stock, oriented.orientation.rotation_deg, max(rows, 0), max(columns, 0),
                         (), (), (), (), (), 0, 0, 0)
    zeros = (0,) * layout.material.row_count
    check_started = perf_counter_ns()
    usable_rows = tuple(layout.usable)
    free_rows = tuple(usable & ~blocked for usable, blocked in zip(layout.usable, layout.blocked))
    domain_rows = _valid_origin_rows(usable_rows, mask, rows, columns, row_cache)
    valid_rows = _valid_origin_rows(free_rows, mask, rows, columns, row_cache)
    origin_generation_ns = perf_counter_ns() - check_started
    detection_started = perf_counter_ns()
    edge_rows = _domain_boundary_rows(domain_rows, columns)
    exterior_rows = _exterior_reachable_rows(valid_rows, edge_rows, columns)
    pocket_rows = tuple(valid & ~exterior for valid, exterior in zip(valid_rows, exterior_rows))
    pockets = [
        RasterRegion(
            region_type="pocket",
            cells=component.cells,
            min_row=component.min_row,
            min_column=component.min_column,
            max_row=component.max_row,
            max_column=component.max_column,
        )
        for component in _components(pocket_rows, columns)
    ]
    component_detection_ns = perf_counter_ns() - detection_started
    return AnchorMap(
        unit=unit, stock=stock, rotation_deg=oriented.orientation.rotation_deg,
        rows=rows, columns=columns, domain_rows=domain_rows, valid_rows=valid_rows,
        exterior_rows=exterior_rows, pocket_rows=pocket_rows,
        pockets=tuple(pockets), positions_examined=rows * columns,
        origin_generation_ns=origin_generation_ns,
        component_detection_ns=component_detection_ns,
    )
