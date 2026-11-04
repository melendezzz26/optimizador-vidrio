// TA-046 T02: medidas originales de cada forma, en mm (SPEC-TA-046 RN-08).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { describeOriginalMeasures, formatMm, polygonSides } from '../../src/features/optimization/originalMeasures.js';

test('rectángulo y círculo muestran las medidas ingresadas en mm', () => {
  assert.equal(describeOriginalMeasures({ tipo_forma: 'RECTANGULO', geometria: { type: 'RECTANGULO', width_mm: 800, height_mm: 600 } }), '800 × 600 mm');
  assert.equal(describeOriginalMeasures({ tipo_forma: 'CIRCUNFERENCIA', geometria: { type: 'CIRCUNFERENCIA', radius_mm: 150 } }), 'Radio 150 mm');
});

test('el polígono muestra cada lado calculado desde sus vértices, redondeado a 0,1 mm', () => {
  const parallelogram = { tipo_forma: 'POLIGONO_CONVEXO', geometria: { type: 'POLIGONO_CONVEXO', vertices_mm: [[0, 0], [120, 0], [40, 138.56], [-80, 138.56]] } };
  assert.equal(describeOriginalMeasures(parallelogram), '4 lados: 120 · 160 · 120 · 160 mm');
  const triangle = { tipo_forma: 'POLIGONO_CONVEXO', geometria: { type: 'POLIGONO_CONVEXO', vertices_mm: [[0, 0], [300, 0], [300, 400]] } };
  assert.equal(describeOriginalMeasures(triangle), '3 lados: 300 · 400 · 500 mm');
  assert.deepEqual(polygonSides([[0, 0], [3, 0], [3, 4]]), [3, 4, 5]);
});

test('el formato usa 0,1 mm y no inventa medidas que no existen', () => {
  assert.equal(formatMm(138.56), '138.6');
  assert.equal(formatMm('6.00'), '6');
  assert.equal(describeOriginalMeasures({ tipo_forma: 'POLIGONO_CONVEXO', geometria: { vertices_mm: [] } }), 'Medidas no disponibles');
});