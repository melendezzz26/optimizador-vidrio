"""Hechos reales por IPC JSON; referencias al snapshot y máscaras por tramos.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
No transporta ORM, pickle de geometrías ni una máscara reconstruida por el motor.
"""
from dataclasses import fields
from decimal import Decimal

from ..domain.problem import Placement, geometry_snapshot
from ..domain.raster_mask import RasterMask
from ..domain.rotation import Orientation
from ..domain.visual_events import VisualEvent
from .run_snapshot import json_value


def unit_ref(unit):
    return [unit.order_id, unit.piece_id, unit.unit_index] if unit is not None else None


def stock_ref(stock):
    return [stock.source.value, stock.material_id, stock.physical_unit_index] if stock is not None else None


def pack_mask(mask):
    if mask is None:
        return None
    spans, count = [], 0
    for row in range(mask.row_count):
        runs = mask.row_runs(row)
        count += len(runs)
        if count > 65536:
            raise ValueError("Mask transport exceeds its span budget")
        spans.append(runs)
    return dict(resolution_mm=str(mask.resolution_mm), columns=mask.columns, spans=spans)


def unpack_mask(data):
    if data is None:
        return None
    columns, spans = data["columns"], data["spans"]
    if (type(columns) is not int or not 1 <= columns <= 4000 or not isinstance(spans, list)
            or not 1 <= len(spans) <= 4000 or sum(len(row) for row in spans) > 65536):
        raise ValueError("Invalid mask dimensions")
    rows = []
    for runs in spans:
        bits, previous = 0, 0
        for start, end in runs:
            if type(start) is not int or type(end) is not int or not previous <= start < end <= columns:
                raise ValueError("Invalid mask span")
            bits |= ((1 << (end - start)) - 1) << start
            previous = end
        rows.append(bits)
    return RasterMask(float(data["resolution_mm"]), columns, tuple(rows))


def pack_visual(fact):
    data = {field.name: getattr(fact, field.name) for field in fields(VisualEvent)}
    data.update(unit=unit_ref(fact.unit), stock=stock_ref(fact.stock),
                ordered_units=[unit_ref(unit) for unit in fact.ordered_units],
                material_mask=pack_mask(fact.material_mask))
    if fact.orientation is not None:
        data["orientation"] = dict(rotation_deg=str(fact.orientation.rotation_deg),
            geometry=json_value(fact.orientation.geometry), mask=pack_mask(fact.orientation.mask))
    if fact.placement is not None:
        p = fact.placement
        data["placement"] = dict(x_mm=str(p.x_mm), y_mm=str(p.y_mm), rotation_deg=str(p.rotation_deg),
                                  geometry=json_value(p.geometry))
    return json_value(data)


class VisualEncoder:
    """One material mask cache per disposable worker; no growing mask dictionary."""
    def __init__(self):
        self.key, self.mask = None, None

    def pack(self, fact):
        # Do not build spans for a repeated material only to throw them away.
        from dataclasses import replace
        key = stock_ref(fact.stock)[:2] if fact.stock is not None else None
        repeated = fact.material_mask is not None and key == self.key and fact.material_mask is self.mask
        value = pack_visual(replace(fact, material_mask=None) if repeated else fact)
        if fact.material_mask is not None:
            value['material_mask_ref'] = key
            self.key, self.mask = key, fact.material_mask
        return value


class VisualDecoder:
    """Validated indices and one material mask, scoped to exactly one execution."""
    def __init__(self, problem):
        self.problem = problem
        self.units = {(u.order_id, u.piece_id, u.unit_index): u for u in problem.units}
        self.stocks = {(s.source.value, s.material_id, s.physical_unit_index): s
            for group in problem.groups for s in group.stock_candidates}
        self.key, self.mask = None, None
        self.config = json_value(problem.config)

    def unpack(self, data):
        return unpack_visual(data, self.problem, decoder=self)


def unpack_visual(data, problem, *, decoder=None):
    units = decoder.units if decoder else {(u.order_id, u.piece_id, u.unit_index): u for u in problem.units}
    stocks = decoder.stocks if decoder else {(s.source.value, s.material_id, s.physical_unit_index): s
              for group in problem.groups for s in group.stock_candidates}
    value = dict(data)
    unit = units[tuple(value["unit"])] if value["unit"] is not None else None
    stock = stocks[tuple(value["stock"])] if value["stock"] is not None else None
    reference = value.pop('material_mask_ref', None)
    if reference is not None:
        if decoder is None or stock is None or reference != stock_ref(stock)[:2]:
            raise ValueError('Material mask reference belongs to another source')
        if value['material_mask'] is not None:
            decoder.key, decoder.mask = reference, unpack_mask(value['material_mask'])
        elif decoder.key != reference or decoder.mask is None:
            raise ValueError('Material mask reference was not declared by this execution')
        material_mask = decoder.mask
    else:
        material_mask = unpack_mask(value['material_mask'])
    value.update(unit=unit, stock=stock, ordered_units=tuple(units[tuple(u)] for u in value["ordered_units"]),
                 material_mask=material_mask)
    if value["config"] is not None:
        if value["config"] != (decoder.config if decoder else json_value(problem.config)):
            raise ValueError("Configuration differs from common input")
        value["config"] = problem.config
    if value["orientation"] is not None:
        o = value["orientation"]
        value["orientation"] = Orientation(Decimal(o["rotation_deg"]), geometry_snapshot(o["geometry"]), unpack_mask(o["mask"]))
    if value["placement"] is not None:
        p = value["placement"]
        value["placement"] = Placement(piece=unit, stock=stock, geometry=p["geometry"],
            **{k: Decimal(p[k]) for k in ("x_mm", "y_mm", "rotation_deg")})
    return VisualEvent(**value)
