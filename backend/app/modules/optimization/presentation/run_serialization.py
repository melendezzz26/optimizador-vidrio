"""Pure model-to-wire mapping for T1; no HTTP, event delivery or NDJSON encoder."""
from ..application.dto import OptimizationRun, Progress, RunStatus
from ..domain.problem import OptimizationConfig, Placement, PieceUnit, StockCandidate
from .run_schemas import ConfigV1, MetricsV1, PieceUnitV1, PlacementV1, RunResponseV1, StockV1


def config_response(config: OptimizationConfig) -> ConfigV1:
    return ConfigV1(resolucion_raster_mm=config.resolution_mm, margen_mm=config.margin_mm,
                    separacion_mm=config.separation_mm, paso_angular_grados=config.angular_step_deg)


def unit_reference(unit: PieceUnit) -> dict:
    return dict(id_pedido=unit.order_id, id_pieza=unit.piece_id, unit_index=unit.unit_index,
                id_tipo_vidrio=unit.glass_type_id, espesor_mm=unit.thickness_mm)


def unit_response(unit: PieceUnit) -> PieceUnitV1:
    return PieceUnitV1(**unit_reference(unit), tipo_forma=unit.shape_type,
                       geometria=dict(unit.geometry), area_mm2=unit.area_mm2)


def stock_response(stock: StockCandidate) -> StockV1:
    return StockV1(material_source=stock.source, material_id=stock.material_id,
                   stock_unit_index=stock.physical_unit_index, id_tipo_vidrio=stock.glass_type_id,
                   espesor_mm=stock.thickness_mm, geometria=dict(stock.geometry), area_mm2=stock.area_mm2)


def placement_response(placement: Placement, config: OptimizationConfig) -> PlacementV1:
    return PlacementV1(**unit_reference(placement.piece), material_source=placement.stock.source,
                       material_id=placement.stock.material_id, stock_unit_index=placement.stock.physical_unit_index,
                       x_mm=placement.x_mm, y_mm=placement.y_mm, rotation_deg=placement.rotation_deg,
                       resolution_mm=config.resolution_mm, geometria=dict(placement.geometry))


def progress_response(placed_units: int, total_units: int) -> dict:
    progress = Progress(placed_units=placed_units, total_units=total_units)
    return dict(placed_units=progress.placed_units, total_units=progress.total_units,
                progress_pct=progress.progress_pct)


def run_response(run: OptimizationRun) -> RunResponseV1:
    result, problem = run.result, run.result.problem
    metrics = None
    if result.metrics is not None:
        values = result.metrics
        # R4 time belongs to the metric contract; unfinished measurements stay null.
        if result.computation_time_ms is None:
            raise ValueError("Calculated metrics require computation_time_ms.")
        metrics = MetricsV1(aprovechamiento_pct=values.utilization_pct, merma_mm2=values.waste_mm2,
                            planchas_nuevas_usadas=values.new_sheets_used,
                            retazo_recuperable_mm2=values.recoverable_remnant_mm2,
                            area_material_total_mm2=values.material_area_mm2,
                            area_piezas_colocadas_mm2=values.placed_piece_area_mm2,
                            tiempo_computacional_ms=result.computation_time_ms)
    reason = {RunStatus.RUNNING: "PENDING", RunStatus.NO_SOLUTION: "NO_FIT",
              RunStatus.FAILED: "INTERRUPTED", RunStatus.COMPLETED: "NO_FIT"}[run.status]
    return RunResponseV1(
        schema_version=1, id_optimizacion=run.optimization_id, estado=run.status, metodo=result.method,
        order_ids=list(problem.order_ids), configuracion=config_response(problem.config),
        groups=[dict(id_tipo_vidrio=group.glass_type_id, espesor_mm=group.thickness_mm,
                     units=[unit_response(unit) for unit in group.units]) for group in problem.groups],
        placements=[placement_response(placement, problem.config) for placement in result.placements],
        materials_used=[stock_response(stock) for stock in result.materials_used],
        residual_regions=[dict(material_source=r.material_source, material_id=r.material_id,
            stock_unit_index=r.stock_unit_index, x_mm=r.x_mm, y_mm=r.y_mm,
            width_mm=r.width_mm, height_mm=r.height_mm, area_mm2=r.area_mm2) for r in run.residuals],
        unplaced_units=[dict(**unit_reference(unit), reason=reason) for unit in result.unplaced_units],
        **progress_response(result.placed_units, result.total_units), completo=result.complete,
        metrics_available=metrics is not None, metrics=metrics, tiempo_computacional_ms=result.computation_time_ms,
        confirmed=run.confirmed, confirmable=run.confirmable,
    )
