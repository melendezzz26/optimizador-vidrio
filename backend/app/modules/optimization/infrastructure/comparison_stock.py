"""Una lectura SQL de stock para todos los materiales del snapshot común.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
Un UNION ALL conserva una única vista PostgreSQL de planchas y retazos. Primero
cuenta unidades, luego expande; ningún motor vuelve a consultar inventario.
"""
from decimal import Decimal
from sqlalchemy import Numeric, literal, null, select, tuple_, union_all
from sqlalchemy.dialects.postgresql import JSONB

from app.models import Plancha, Retazo
from ..application.load_budget import check_stock, DEFAULT_RUN_LOAD_BUDGET
from ..domain.problem import MaterialSource, StockCandidate
from .stock_adapter import _canonical_measure


class SqlComparisonStock:
    def __init__(self, session):
        self.session = session

    def capture(self, units_by_material, budget=DEFAULT_RUN_LOAD_BUDGET):
        keys = list(units_by_material)
        sheets = select(literal("PLANCHA").label("source"), Plancha.id_plancha.label("id"),
            Plancha.id_tipo_vidrio.label("glass"), Plancha.espesor_mm.label("thickness"),
            Plancha.cantidad.label("quantity"), Plancha.fecha_registro.label("date"),
            null().cast(JSONB).label("geometry"), (Plancha.ancho_mm * Plancha.alto_mm).label("area"),
            Plancha.ancho_mm.label("width"), Plancha.alto_mm.label("height")).where(
                Plancha.estado.is_(True), Plancha.cantidad > 0,
                tuple_(Plancha.id_tipo_vidrio, Plancha.espesor_mm).in_(keys))
        remnants = select(literal("RETAZO"), Retazo.id_retazo, Retazo.id_tipo_vidrio,
            Retazo.espesor_mm, literal(1), Retazo.fecha_registro, Retazo.geometria, Retazo.area_mm2,
            null().cast(Numeric), null().cast(Numeric)).where(Retazo.estado.is_(True),
                tuple_(Retazo.id_tipo_vidrio, Retazo.espesor_mm).in_(keys))
        rows = self.session.execute(union_all(sheets, remnants)).mappings().all()
        counts = {key: 0 for key in keys}
        for row in rows:
            counts[(row["glass"], row["thickness"])] += row["quantity"]
        check_stock(units_by_material, counts, budget)
        rows.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
        # Stable source priority, then date DESC/id DESC/physical unit ASC.
        rows.sort(key=lambda r: r["source"] == "PLANCHA")
        captured = {key: [] for key in keys}
        for row in rows:
            key = (row["glass"], Decimal(row["thickness"]))
            geometry = row["geometry"] if row["source"] == "RETAZO" else dict(type="RECTANGULO",
                width_mm=_canonical_measure(row["width"]), height_mm=_canonical_measure(row["height"]))
            for index in range(1, row["quantity"] + 1):
                captured[key].append(StockCandidate(source=MaterialSource(row["source"]),
                    material_id=row["id"], physical_unit_index=index, glass_type_id=key[0],
                    thickness_mm=key[1], geometry=geometry, area_mm2=row["area"]))
        return {key: tuple(value) for key, value in captured.items()}
