// Revisión del 08/11/2026: el orden de piezas acompaña a L-03 (800 unidades) en v1 y v2.
import { expect, test } from 'vitest';
import v1 from '../../../../../docs/contracts/optimization/comparison-v1.json';
import v2 from '../../../../../docs/contracts/optimization/comparison-v2.json';
import { createComparisonApi, parseComparisonEvent } from '../comparisonApi';
import { createComparisonV2Api } from '../comparisonApiV2';
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
])('ordering_ready %s acepta 800 unidades y rechaza 801', (_, fixture, parse) => {
  expect(parse(ordering(fixture, 800), fixture.completed).data.units).toHaveLength(800);
  expect(() => parse(ordering(fixture, 801), fixture.completed)).toThrow();
});

// Valid metadata exceeds the old 64 KiB bound and must survive chunking intact.
test.each([
  ['v1', v1, createComparisonApi],
  ['v2', v2, createComparisonV2Api],
])('ordering_ready %s atraviesa el stream con 800 referencias', async (_, fixture, create) => {
  const event = ordering(fixture, 800);
  const raw = new TextEncoder().encode(JSON.stringify(event) + '\n');
  expect(raw.length).toBeGreaterThan(65536);
  expect(raw.length).toBeLessThan(131072);
  const fetchImpl = async () => ({ ok: true, headers: { get: () => 'application/x-ndjson' },
    body: new ReadableStream({ start(controller) {
      for (let i = 0; i < raw.length; i += 1537) controller.enqueue(raw.slice(i, i + 1537));
      controller.close();
    } }),
  });
  const received = [];
  await create({ fetchImpl }).observe(fixture.completed, event.sequence - 1, value => received.push(value));
  expect(received).toHaveLength(1);
  expect(received[0].data.units).toHaveLength(800);
});
