import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pieceRaster, validInspectionRaster, groupRasterReady } from '../../src/features/optimization/rasterInspectionModel.js';
const raster = { resolution_mm: 100, columns: 4, row_count: 3, spans_by_row: [{ row: 0, runs: [[0, 4]] }] };
test('inspection accepts bounded span masks but rejects malformed resolution and out-of-grid runs', () => {
  assert.equal(validInspectionRaster(raster), true);
  for (const patch of [{ resolution_mm: NaN }, { columns: 0 }, { row_count: 2.5 }, { spans_by_row: [{ row: 3, runs: [[0, 1]] }] },
    { spans_by_row: [{ row: 0, runs: [[0, 5]] }] }, { spans_by_row: [{ row: 0, runs: [[2, 1]] }] }]) {
    assert.equal(validInspectionRaster({ ...raster, ...patch }), false);
  }
});
test('order and piece keys take precedence, and all group units require prepared masks', () => {
  const snapshot = { rasters: { '21:1': raster, 1: { ...raster, columns: 7 } } };
  assert.equal(pieceRaster(snapshot, 21, 1), raster);
  const group = { units: [{ id_pedido: 21, id_pieza: 1 }] };
  assert.equal(groupRasterReady(snapshot, group), true);
  group.units.push({ id_pedido: 21, id_pieza: 2 });
  assert.equal(groupRasterReady(snapshot, group), false);
});
