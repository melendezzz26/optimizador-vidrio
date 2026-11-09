import { expect, test, vi } from 'vitest';
import { createComparisonApi } from '../comparisonApi';
import { createComparisonV2Api } from '../comparisonApiV2';

test.each([createComparisonApi, createComparisonV2Api])('solo conserva campos permitidos del 503', async create => {
  const response = { ok: false, status: 503, body: null, json: async () => ({ detail: {
    code: 'OPTIMIZER_BUSY', message: 'Ocupado', limit: { name: 'active_runs', actual: 1, maximum: 2, secret: 'do-not-show' },
    stack: 'do-not-show',
  } }) };
  const api = create({ fetchImpl: vi.fn().mockResolvedValue(response) });
  await expect(api.start([1], 'test-key-0001')).rejects.toMatchObject({
    admissionDiagnostic: { code: 'OPTIMIZER_BUSY', name: 'active_runs', actual: 1, maximum: 2 },
  });
  try { await api.start([1], 'test-key-0001'); } catch (error) {
    expect(JSON.stringify(error.admissionDiagnostic)).not.toContain('do-not-show');
  }
});
