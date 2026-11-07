// HU-018: lógica pura de la importación masiva (SPEC-HU-018 §6 y §8).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  addImportedPieces, blockingReason, canAddToOrder, describeMeasures, isBlankGroup, revalidationBody, rowsToPieces,
} from '../../src/features/orders/bulkImportModel.js';

const valid = (fila, tipo_forma, medidas, cantidad = 1) => ({
  fila, texto: `fila ${fila}`, estado: 'VALIDO', tipo_forma, cantidad, medidas, causas: [],
});
const observed = fila => ({
  fila, texto: 'C,0,150', estado: 'OBSERVADO', tipo_forma: 'CIRCUNFERENCIA', cantidad: null, medidas: null,
  causas: ['Cantidad debe ser un entero mayor a 0'],
});
const rectangle = valid(2, 'RECTANGULO', { width_mm: 800, height_mm: 600 }, 3);
const circle = valid(3, 'CIRCUNFERENCIA', { radius_mm: 150 }, 2);
const polygon = valid(4, 'POLIGONO_CONVEXO', { vertices_mm: [[0, 0], [120, 0], [40, 138.56], [-80, 138.56]] });
const preview = filas => ({ archivo: 'piezas.csv', filas });
const material = { tipo_vidrio_id: '7', espesor: '5.5' };

test('describe las medidas de cada forma en mm y sin medidas en filas observadas', () => {
  assert.equal(describeMeasures(rectangle), '800 × 600 mm');
  assert.equal(describeMeasures(circle), 'Radio 150 mm');
  assert.equal(describeMeasures(polygon), '4 lados');
  assert.equal(describeMeasures(observed(5)), '—');
});

test('CA-07: con filas observadas o sin material no se puede agregar al pedido', () => {
  assert.equal(blockingReason(null, material), 'Carga un archivo con piezas.');
  assert.equal(blockingReason(preview([rectangle, observed(5)]), material), 'Corrige 1 fila observada para continuar.');
  assert.equal(blockingReason(preview([observed(5), observed(6)]), material), 'Corrige 2 filas observadas para continuar.');
  assert.equal(blockingReason(preview([rectangle]), { tipo_vidrio_id: '7', espesor: '' }), 'Elige el tipo de vidrio y el espesor.');
  assert.equal(canAddToOrder(preview([rectangle, observed(5)]), material), false);
  assert.equal(canAddToOrder(preview([rectangle, circle, polygon]), material), true);
});

test('las filas válidas pasan al formato del formulario sin conversiones', () => {
  const rows = [rectangle, circle, polygon];
  const before = JSON.stringify(rows);
  assert.deepEqual(rowsToPieces(rows), [
    { tipo_forma: 'RECTANGULO', cantidad: 3, dimensiones: { width_mm: 800, height_mm: 600 } },
    { tipo_forma: 'CIRCUNFERENCIA', cantidad: 2, dimensiones: { radius_mm: 150 } },
    { tipo_forma: 'POLIGONO_CONVEXO', cantidad: 1, dimensiones: { vertices: [[0, 0], [120, 0], [40, 138.56], [-80, 138.56]] } },
  ]);
  assert.equal(JSON.stringify(rows), before);
});

test('la revalidación envía todas las filas con su número original y el texto corregido', () => {
  assert.deepEqual(revalidationBody(preview([rectangle, observed(5)]), { 5: 'C,2,150' }), {
    archivo: 'piezas.csv',
    filas: [{ fila: 2, texto: 'fila 2' }, { fila: 5, texto: 'C,2,150' }],
  });
});

const blank = { id: 'group-0', tipo_vidrio_id: '', espesor: '', piezas: [{ id: 0, tipo_forma: 'RECTANGULO', cantidad: 1, dimensiones: { width_mm: '', height_mm: '' } }] };
const pieces = [{ id: 10, tipo_forma: 'CIRCUNFERENCIA', cantidad: 2, dimensiones: { radius_mm: 150 } }];

test('el borrador vacío del formulario se reemplaza por el grupo importado', () => {
  assert.equal(isBlankGroup(blank), true);
  assert.deepEqual(addImportedPieces([blank], material, pieces, 'group-1'),
    [{ id: 'group-1', tipo_vidrio_id: '7', espesor: '5.5', piezas: pieces }]);
});

test('con el mismo vidrio y espesor las piezas se suman a ese grupo, sin duplicarlo', () => {
  const existing = { id: 'group-3', tipo_vidrio_id: '7', espesor: '5.5', piezas: [{ id: 1, tipo_forma: 'RECTANGULO', cantidad: 1, dimensiones: { width_mm: 10, height_mm: 10 } }] };
  const other = { ...existing, id: 'group-4', tipo_vidrio_id: '8', espesor: '4' };
  const result = addImportedPieces([existing, other], { tipo_vidrio_id: 7, espesor: '5.50' }, pieces, 'group-9');
  assert.deepEqual(result.map(group => group.id), ['group-3', 'group-4']);
  assert.deepEqual(result[0].piezas.map(piece => piece.id), [1, 10]);
  assert.equal(result[1], other);
});

test('un grupo con datos escritos no se descarta aunque le falte el material', () => {
  const started = { ...blank, piezas: [{ ...blank.piezas[0], dimensiones: { width_mm: '100', height_mm: '' } }] };
  assert.equal(isBlankGroup(started), false);
  assert.deepEqual(addImportedPieces([started], material, pieces, 'group-1').map(group => group.id), ['group-0', 'group-1']);
});