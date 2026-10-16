"""Caller-owned PostgreSQL confirmation; no cross-module infrastructure imports.

Lock order: run -> FF execution -> associations -> Orders ASC -> sheets ASC ->
remnants ASC. Writes only flush; SqlRunUnitOfWork owns the SINGLE commit.
"""
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models import (Optimizacion, OptimizacionPedido, EjecucionOptimizacion, Plancha, Retazo,
                        MovimientoInventario, MaterialUtilizado, MetricaEjecucion)
from app.modules.inventory.domain.geometry import calculate_area_mm2
from app.modules.inventory.domain.exceptions import InvalidGeometryError
from ..application.confirmation import ConfirmationContext, CreatedRemnant
from ..application.errors import RunError
from ..domain.metrics import ResidualRectangle
from ..domain.problem import MaterialSource
from ..domain.rotation import raster_number, RasterPreparationError
from .run_snapshot import json_value, encode


class SqlConfirmationRepository:
    def __init__(self, session, runs):
        self.session, self.runs = session, runs
        self.locked, self.skipped = {}, []

    def lock_run(self, optimization_id):
        row = self.session.scalar(select(Optimizacion).where(Optimizacion.id_optimizacion == optimization_id)
                                  .with_for_update().execution_options(populate_existing=True))
        if row is None:
            raise RunError("NOT_FOUND", "No se encontró la optimización.")
        execution = self.session.scalar(select(EjecucionOptimizacion).where(
            EjecucionOptimizacion.id_optimizacion == optimization_id, EjecucionOptimizacion.metodo == "FF")
            .with_for_update().execution_options(populate_existing=True))
        if execution is None:
            raise RunError("NOT_CONFIRMABLE", "No hay ejecución FF confirmable.")
        self.session.scalars(select(OptimizacionPedido).where(OptimizacionPedido.id_optimizacion == optimization_id)
                             .order_by(OptimizacionPedido.id_pedido).with_for_update()).all()
        # Fence an already consumed run even if its receipt/order states were altered externally.
        movement = self.session.scalar(select(MovimientoInventario.id_movimiento).where(
            MovimientoInventario.id_optimizacion == optimization_id,
            MovimientoInventario.tipo_evento == "CONSUMO_OPTIMIZACION").limit(1))
        if movement is not None:
            raise RunError("ALREADY_CONFIRMED", "La optimización ya fue confirmada.")
        if (row.estado != "COMPLETADA" or execution.estado != "COMPLETADA" or not execution.completo
                or row.id_ejecucion_seleccionada != execution.id_ejecucion):
            raise RunError("NOT_CONFIRMABLE", "No hay una ejecución FF completa seleccionada para confirmar.")
        try:
            run = self.runs.get(optimization_id)
            snapshot = execution.patron_resultado
            residuals = tuple(ResidualRectangle(**{**r, **{k: Decimal(r[k]) for k in (
                "x_mm", "y_mm", "width_mm", "height_mm", "area_mm2")}}) for r in snapshot.get("residual_rectangles", []))
            minimum_width, minimum_height = self.runs.residual_limits(optimization_id)
        except RunError as exc:
            if exc.code in ("INTERNAL_ERROR", "NOT_FOUND"):
                raise RunError("NOT_CONFIRMABLE", "El resultado persistido requiere revisión antes de confirmar.") from exc
            raise
        except (ValueError, TypeError, KeyError) as exc:
            raise RunError("NOT_CONFIRMABLE", "El resultado persistido no es confirmable.") from exc
        return ConfirmationContext(run=run, execution_id=execution.id_ejecucion,
            minimum_width_mm=minimum_width, minimum_height_mm=minimum_height, residuals=residuals)

    def lock_and_revalidate(self, consumptions, context):
        for model, source, id_column in ((Plancha, MaterialSource.SHEET, Plancha.id_plancha),
                                         (Retazo, MaterialSource.REMNANT, Retazo.id_retazo)):
            selected = [c for c in consumptions if c.stock.source is source]
            ids = [c.stock.material_id for c in selected]
            if not ids:
                continue
            rows = self.session.scalars(select(model).where(id_column.in_(ids)).order_by(id_column)
                                        .with_for_update().execution_options(populate_existing=True)).all()
            by_id = {getattr(r, id_column.key): r for r in rows}
            for consumption in selected:
                stock = consumption.stock
                row = by_id.get(stock.material_id)
                compatible = row is not None and row.estado and (row.id_tipo_vidrio, row.espesor_mm) == stock.material_key
                if compatible and source is MaterialSource.SHEET:
                    compatible = (row.cantidad >= consumption.quantity
                        and row.ancho_mm == Decimal(str(stock.geometry['width_mm']))
                        and row.alto_mm == Decimal(str(stock.geometry['height_mm']))
                        and row.ancho_mm * row.alto_mm == stock.area_mm2)
                elif compatible:
                    compatible = row.geometria == json_value(stock.geometry) and row.area_mm2 == stock.area_mm2
                    # Boolean reactivation must NEVER allow a concrete remnant to be consumed twice.
                    previous = self.session.scalar(select(MovimientoInventario.id_movimiento).where(
                        MovimientoInventario.id_retazo == stock.material_id,
                        MovimientoInventario.tipo_evento == "CONSUMO_OPTIMIZACION").limit(1))
                    compatible = compatible and previous is None
                if not compatible:
                    raise RunError("STOCK_CONFLICT", "El stock utilizado cambió o ya no está disponible.")
                self.locked[(source, stock.material_id)] = row
        proposals = self.session.scalars(select(MaterialUtilizado).where(
            MaterialUtilizado.id_ejecucion == context.execution_id).order_by(MaterialUtilizado.id_material_utilizado)
            .with_for_update()).all()
        actual = {}
        for row in proposals:
            key = (MaterialSource.SHEET, row.id_plancha) if row.id_plancha is not None else (MaterialSource.REMNANT, row.id_retazo)
            actual[key] = actual.get(key, 0) + row.cantidad_utilizada
        expected = {(c.stock.source, c.stock.material_id): c.quantity for c in consumptions}
        if actual != expected:
            raise RunError("NOT_CONFIRMABLE", "Los materiales propuestos no corresponden al patrón persistido.")

    def consume(self, consumptions):
        for consumption in consumptions:
            stock = consumption.stock
            row = self.locked[(stock.source, stock.material_id)]
            if stock.source is MaterialSource.SHEET:
                row.cantidad -= consumption.quantity
                row.estado = row.cantidad > 0
            else:
                row.estado = False
        self.session.flush()

    def record_movements(self, consumptions, optimization_id, actor_id):
        for c in consumptions:
            sheet = c.stock.source is MaterialSource.SHEET
            self.session.add(MovimientoInventario(id_plancha=c.stock.material_id if sheet else None,
                id_retazo=None if sheet else c.stock.material_id, tipo_evento="CONSUMO_OPTIMIZACION",
                motivo=f"Confirmación First Fit de optimización {optimization_id}.",
                observacion="stock_unit_index=" + ",".join(str(i) for i in c.unit_indices),
                id_usuario=actor_id, id_optimizacion=optimization_id, cantidad_afectada=c.quantity,
                fecha=datetime.now(timezone.utc)))
        self.session.flush()

    def create_residuals(self, residuals, context):
        stocks = {s.identity: s for s in context.run.result.materials_used}
        created = []
        for r in residuals:
            source = stocks[(MaterialSource(r.material_source), r.material_id, r.stock_unit_index)]
            try:
                geometry = dict(type="RECTANGULO", width_mm=raster_number(r.width_mm), height_mm=raster_number(r.height_mm))
                area = calculate_area_mm2(geometry)  # Public Inventory rule, including NUMERIC(18,2) precision.
            except (InvalidGeometryError, RasterPreparationError):
                self.skipped.append({"source": json_value(r), "reason": "INVENTORY_GEOMETRY_NOT_PERSISTABLE"})
                continue
            marker = 'P' if source.source is MaterialSource.SHEET else 'R'
            code = f"FF-{context.run.optimization_id}-{marker}{source.material_id}-{source.physical_unit_index}"
            if self.session.scalar(select(Retazo.id_retazo).where(Retazo.codigo == code)) is not None:
                raise RunError("STATE_CONFLICT", "El código del retazo resultante ya existe; solicita revisión.")
            row = Retazo(codigo=code, id_tipo_vidrio=source.glass_type_id, espesor_mm=source.thickness_mm,
                geometria=geometry, area_mm2=area, estado=True, fecha_registro=datetime.now(timezone.utc),
                id_ejecucion_origen=context.execution_id)
            self.session.add(row)
            self.session.flush()
            created.append(CreatedRemnant(remnant_id=row.id_retazo, source=source, x_mm=r.x_mm, y_mm=r.y_mm,
                geometry=geometry, area_mm2=area, exact_area_mm2=r.area_mm2))
        return tuple(created)

    def mark_confirmed(self, context, receipt, actor_id):
        execution = self.session.get(EjecucionOptimizacion, context.execution_id)
        result = context.run.result
        if result.metrics is not None:
            recovered = sum((r.exact_area_mm2 for r in receipt.remnants_created), Decimal(0))
            m = result.metrics
            result = replace(result, metrics=replace(m, recoverable_remnant_mm2=recovered,
                             waste_mm2=m.material_area_mm2 - m.placed_piece_area_mm2 - recovered))
            row = self.session.scalar(select(MetricaEjecucion).where(MetricaEjecucion.id_ejecucion == context.execution_id))
            if row is None:
                raise RunError("NOT_CONFIRMABLE", "No se encontraron las métricas persistidas de la solución.")
            row.retazo_recuperable_mm2 = result.metrics.recoverable_remnant_mm2
            row.merma_mm2 = result.metrics.waste_mm2
        execution.patron_resultado = {**execution.patron_resultado, **encode(result), "confirmation": {
            "receipt_version": 1, "actor_id": actor_id, "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "receipt": json_value(receipt), "skipped_residuals": self.skipped}}
