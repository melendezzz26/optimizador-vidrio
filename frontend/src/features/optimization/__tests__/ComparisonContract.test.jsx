// Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
import { expect, test } from 'vitest';
import fixture from '../../../../../docs/contracts/optimization/comparison-v1.json';
import { parseComparison, parseComparisonEvent, parseExecution } from '../comparisonApi';
import { parseRun } from '../runContract';

test('shared real-engine fixture is accepted without widening legacy FF', () => {
  const comparison = parseComparison(structuredClone(fixture.completed));
  for (const execution of comparison.executions) {
    const value = parseExecution(structuredClone(fixture.results[execution.execution_id]), comparison, execution);
    expect(value.result.metodo).toBe(execution.method);
  }
  fixture.events.forEach(e => parseComparisonEvent(structuredClone(e), comparison));
  expect(() => parseRun(fixture.results['2'].result)).toThrow();
});

test('cross-execution masks and results are rejected', () => {
  const comparison = fixture.completed;
  const event = structuredClone(fixture.events.find(e => e.data.mask));
  event.data.mask.execution_id += 1;
  expect(() => parseComparisonEvent(event, comparison)).toThrow();
  expect(() => parseExecution(structuredClone(fixture.results['2']), comparison, comparison.executions[0])).toThrow();
});
