export function pieceRaster(snapshot, orderId, pieceId) {
  return snapshot.rasters?.[`${orderId}:${pieceId}`] ?? snapshot.rasters?.[pieceId];
}
export function validInspectionRaster(raster) {
  return Boolean(raster && Number.isFinite(raster.resolution_mm) && raster.resolution_mm > 0
    && Number.isInteger(raster.columns) && raster.columns > 0 && Number.isInteger(raster.row_count) && raster.row_count > 0
    && Array.isArray(raster.spans_by_row) && raster.spans_by_row.length > 0
    && raster.spans_by_row.every(({ row, runs }) => Number.isInteger(row) && row >= 0 && row < raster.row_count
      && Array.isArray(runs) && runs.every(run => Array.isArray(run) && run.length === 2
        && run.every(Number.isInteger) && run[0] >= 0 && run[1] > run[0] && run[1] <= raster.columns)));
}
export function groupRasterReady(snapshot, group) {
  return group.units.length > 0 && group.units.every(u => validInspectionRaster(pieceRaster(snapshot, u.id_pedido, u.id_pieza)));
}
