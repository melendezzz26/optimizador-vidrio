"""Confirmar exclusivamente el resultado elegido; reusar revalidación de stock.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
"""
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from app.models import EjecucionOptimizacion, MetricaEjecucion, MovimientoInventario, OptimizacionPedido
from ..application.confirmation import ConfirmationContext, ConfirmationResult, CreatedRemnant
from ..application.dto import OptimizationRun, RunStatus
from ..application.errors import RunError
from ..domain.problem import StockCandidate, MaterialSource
from .confirmation_adapter import SqlConfirmationRepository
from .comparison_snapshot import encode_result
from .run_snapshot import json_value


def decode_receipt(value):
    def stock(values):
        return StockCandidate(**{**values, "source": MaterialSource(values["source"]),
            "thickness_mm": Decimal(values["thickness_mm"]), "area_mm2": Decimal(values["area_mm2"])})
    created = tuple(CreatedRemnant(**{**r, "source": stock(r["source"]),
        **{k: Decimal(r[k]) for k in ("x_mm", "y_mm", "area_mm2", "exact_area_mm2")}})
        for r in value["remnants_created"])
    return ConfirmationResult(optimization_id=value["optimization_id"], order_ids=tuple(value["order_ids"]),
        materials_consumed=tuple(stock(s) for s in value["materials_consumed"]), remnants_created=created)


class SqlComparisonConfirmationRepository(SqlConfirmationRepository):
    def __init__(self, session, comparisons):
        super().__init__(session, None)
        self.comparisons = comparisons

    def lock_comparison(self, comparison_id, execution_id, expected_version, key):
        row = self.comparisons._lock(comparison_id)
        current = self.comparisons.get(comparison_id)
        confirmation = current.confirmation
        if confirmation is not None:
            if (confirmation.get("key") == key and confirmation.get("execution_id") == execution_id
                    and confirmation.get("expected_version") == expected_version):
                try:
                    if type(confirmation.get("receipt_version")) is not int or confirmation["receipt_version"] != 1:
                        raise ValueError("Unsupported confirmation receipt")
                    receipt = decode_receipt(confirmation["receipt"])
                    if receipt.optimization_id != comparison_id or receipt.order_ids != current.problem.order_ids:
                        raise ValueError("Receipt differs from accepted orders")
                    return receipt
                except (ValueError, KeyError, TypeError, ArithmeticError) as error:
                    raise RunError("NOT_CONFIRMABLE", "El recibo persistido requiere revisión.") from error
            raise RunError("ALREADY_CONFIRMED", "Esta comparación ya fue confirmada.")
        if row.comparison_version != expected_version:
            raise RunError("STATE_CONFLICT", "La comparación o su selección cambió. Actualiza el resultado.")
        execution = next((e for e in current.executions if e.execution_id == execution_id), None)
        if (not current.terminal or current.released or current.selected_execution_id != execution_id
                or execution is None or not execution.eligible):
            raise RunError("NOT_CONFIRMABLE", "Selecciona un resultado completo y guardado antes de confirmar.")
        self.comparisons._execution(comparison_id, execution_id)
        self.session.scalars(select(OptimizacionPedido).where(OptimizacionPedido.id_optimizacion == comparison_id)
            .order_by(OptimizacionPedido.id_pedido).with_for_update()).all()
        if self.session.scalar(select(MovimientoInventario.id_movimiento).where(
                MovimientoInventario.id_optimizacion == comparison_id,
                MovimientoInventario.tipo_evento == "CONSUMO_OPTIMIZACION").limit(1)) is not None:
            raise RunError("ALREADY_CONFIRMED", "La comparación ya tiene consumos registrados.")
        self.key, self.expected_version = key, expected_version
        self.method_name = {"FF": "First Fit", "BF": "Best Fit", "WF": "Worst Fit"}[execution.method]
        run = OptimizationRun(optimization_id=comparison_id, status=RunStatus.COMPLETED,
                              result=execution.result, residuals=execution.residuals)
        return ConfirmationContext(run=run, execution_id=execution_id, minimum_width_mm=current.minimum_width_mm,
                                   minimum_height_mm=current.minimum_height_mm, residuals=execution.residuals)

    def mark_confirmed(self, context, receipt, actor_id):
        execution = self.session.get(EjecucionOptimizacion, context.execution_id)
        result = context.run.result
        if result.metrics is not None:
            recovered = sum((r.exact_area_mm2 for r in receipt.remnants_created), Decimal(0))
            m = result.metrics
            result = replace(result, metrics=replace(m, recoverable_remnant_mm2=recovered,
                waste_mm2=m.material_area_mm2 - m.placed_piece_area_mm2 - recovered))
            metric = self.session.scalar(select(MetricaEjecucion).where(MetricaEjecucion.id_ejecucion == context.execution_id))
            if metric is None:
                raise RunError("NOT_CONFIRMABLE", "No se encontraron las métricas de la solución elegida.")
            metric.retazo_recuperable_mm2 = result.metrics.recoverable_remnant_mm2
            metric.merma_mm2 = result.metrics.waste_mm2
        row = self.comparisons._lock(context.run.optimization_id)
        confirmation = {
            "receipt_version": 1, "key": self.key, "expected_version": self.expected_version,
            "execution_id": context.execution_id, "method": result.method, "actor_id": actor_id,
            "confirmed_at": datetime.now(timezone.utc).isoformat(), "receipt": json_value(receipt),
            "skipped_residuals": self.skipped}
        # Inventory consulta el origen por ejecución; conservar ese contrato de lectura.
        execution.patron_resultado = {**execution.patron_resultado, "snapshot": encode_result(result), "confirmation": confirmation}
        row.comparison_snapshot = {**row.comparison_snapshot, "confirmation": confirmation}
        row.comparison_version += 1
