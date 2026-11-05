import { expect, test } from 'vitest';
import fixture from '../../../../../docs/contracts/optimization/comparison-v2.json';
import historical from '../../../../../docs/contracts/optimization/comparison-v1.json';
import { CATALOG_V2, METHODS_V2, validateMethods, parseComparisonV2,
  parseExecutionV2, parseComparisonEventV2 } from '../comparisonV2Contract';
import { parseComparison, parseExecution } from '../comparisonApi';
import { parseRun } from '../runContract';

test('backend fixture and frontend catalog share exact identities, names, order and capabilities', () => {
  expect(CATALOG_V2).toEqual(fixture.catalog);
  expect(METHODS_V2).toEqual(['FF', 'BF', 'WF', 'HF', 'M5', 'M6-BS']);
  expect(CATALOG_V2.map(m => m.label)).toEqual(['FF', 'BF', 'WF', 'HF', 'BRF', 'BS-2']);
  expect(CATALOG_V2.at(-1)).toMatchObject({ beam_width: 2, native_visual: false, observation: 'SEARCH_PROGRESS' });
  expect(Object.isFrozen(CATALOG_V2) && CATALOG_V2.every(Object.isFrozen)).toBe(true);
});

test.each([[], ['AUTO'], ['BRF'], ['BS-2'], ['FF', 'FF'], [true]])('invalid method selection %j is rejected', methods => {
  expect(() => validateMethods(methods)).toThrow();
});

test('profile catalogs remain separate and require a complete set explicitly', () => {
  expect(validateMethods(['WF', 'FF', 'BF'], { profile: 'comparison-v1', requireAll: true })).toEqual(['WF', 'FF', 'BF']);
  expect(() => validateMethods(['HF'], { profile: 'comparison-v1' })).toThrow();
  expect(() => validateMethods(['FF'], { requireAll: true })).toThrow();
});

test('shared accepted, completed, partial and failed examples round-trip without mutating bytes', () => {
  for (const name of ['accepted', 'completed', 'mixed']) expect(parseComparisonV2(fixture[name])).toEqual(fixture[name]);
  for (const response of Object.values(fixture.results)) {
    expect(parseExecutionV2(response, fixture.completed)).toEqual(response);
  }
  expect(parseExecutionV2(fixture.partial_result, fixture.mixed)).toEqual(fixture.partial_result);
  expect(parseExecutionV2(fixture.failed_result, fixture.mixed)).toEqual(fixture.failed_result);
  fixture.events.forEach(e => expect(parseComparisonEventV2(e, fixture.completed)).toEqual(e));
});

test('legacy parsers remain strict and v1 history is still accepted', () => {
  const old = parseComparison(historical.completed);
  old.executions.forEach(e => parseExecution(historical.results[e.execution_id], old, e));
  expect(() => parseComparison(fixture.completed)).toThrow();
  expect(() => parseComparisonV2(historical.completed)).toThrow();
  expect(() => parseRun(fixture.results['4301'].result)).toThrow();
});

test.each(['method', 'duplicate', 'id', 'selection', 'supervisor', 'outcome', 'diagnostic'])('inconsistent %s is rejected', mutation => {
  const data = structuredClone(fixture.completed);
  if (mutation === 'method') data.executions[0].method = 'AUTO';
  if (mutation === 'duplicate') data.executions[0].method = 'BF';
  if (mutation === 'id') data.executions[0].execution_id = data.executions[1].execution_id;
  if (mutation === 'selection') data.selected_execution_id = 999;
  if (mutation === 'supervisor') data.supervisor_stopped = false;
  if (mutation === 'outcome') data.executions[0].outcome = 'PARTIAL';
  if (mutation === 'diagnostic') data.executions[0].diagnostic.termination_reason = 'TIME_LIMIT';
  expect(() => parseComparisonV2(data)).toThrow();
});

test('array position never defines execution identity', () => {
  const data = structuredClone(fixture.completed);
  data.executions.reverse();
  expect(parseComparisonV2(data).executions[0].method).toBe('M6-BS');
  expect(parseExecutionV2(fixture.results['4301'], data).execution.method).toBe('FF');
  expect(() => parseExecutionV2(fixture.results['4301'], data, data.executions[0])).toThrow();
});

test('partial resource termination is not NO_FIT and failures do not fabricate metrics', () => {
  const data = structuredClone(fixture.partial_result);
  expect(data.execution.outcome).toBe('PARTIAL');
  expect(data.result.unplaced_units[0].reason).toBe('RESOURCE_LIMIT');
  data.result.unplaced_units[0].reason = 'NO_FIT';
  expect(() => parseExecutionV2(data, fixture.mixed)).toThrow();
  const failed = structuredClone(fixture.failed_result);
  failed.execution.result_available = true;
  expect(() => parseExecutionV2(failed, fixture.mixed)).toThrow();
});

test('M6 progress has no provisional placements and persisted results keep execution scope', () => {
  const event = structuredClone(fixture.events[1]);
  event.data.placements = [];
  expect(() => parseComparisonEventV2(event, fixture.completed)).toThrow();
  delete event.data.placements;
  event.presentation = 'OBSERVED';
  expect(() => parseComparisonEventV2(event, fixture.completed)).toThrow();
  const persisted = structuredClone(fixture.events.find(e => e.event === 'result_persisted'));
  persisted.data.execution_id += 1;
  expect(() => parseComparisonEventV2(persisted, fixture.completed)).toThrow();
});

test('v2 masks retain their comparison, execution and method identities', () => {
  const event = structuredClone(historical.events.find(e => e.event === 'piece_ready'));
  Object.assign(event, { profile: 'comparison-v2', schema_version: 2, presentation: 'OBSERVED',
    comparison_id: 43, execution_id: 4305, method: 'M5' });
  Object.assign(event.data.mask, { profile: 'comparison-v2', schema_version: 2,
    comparison_id: 43, id_optimizacion: 43, execution_id: 4305, method: 'M5' });
  expect(parseComparisonEventV2(event, fixture.completed).method).toBe('M5');
  event.data.mask.execution_id = 4306;
  expect(() => parseComparisonEventV2(event, fixture.completed)).toThrow();
});
