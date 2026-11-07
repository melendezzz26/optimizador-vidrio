// Revisión del 04/11/2026: el orden de piezas acompaña a L-03 (300 unidades) en v1 y v2.
import { expect, test } from 'vitest';
import v1 from '../../../../../docs/contracts/optimization/comparison-v1.json';
import v2 from '../../../../../docs/contracts/optimization/comparison-v2.json';
import { parseComparisonEvent } from '../comparisonApi';
import { parseComparisonEventV2 } from '../comparisonV2Contract';

const units = count => Array.from({ length: count }, (_, i) => ({
  id_tipo_vidrio: 1, espesor_mm: '6', id_pedido: 1, id_pieza: 1, unit_index: i + 1,
}));

function ordering(fixture, count) {
  // Reutiliza la identidad de un evento real de ejecución del fixture compartido.
  const base = fixture.events.find(e => e.method !== null && e.event !== 'search_progress');
  const event = { ...structuredClone(base), event: 'ordering_ready',
    data: { criterion: 'area_desc_max_side_desc_order_piece_unit_asc', units: units(count) } };
  if ('presentation' in base) event.presentation = 'OBSERVED';
  return event;
}

test.each([
  ['v1', v1, parseComparisonEvent],
  ['v2', v2, parseComparisonEventV2],
])('ordering_ready %s acepta 300 unidades y rechaza 301', (_, fixture, parse) => {
  expect(parse(ordering(fixture, 300), fixture.completed).data.units).toHaveLength(300);
  expect(() => parse(ordering(fixture, 301), fixture.completed)).toThrow();
});
