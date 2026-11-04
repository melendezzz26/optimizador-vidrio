import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import comparisonV2 from '../../../../../docs/contracts/optimization/comparison-v2.json';
import comparisonV1 from '../../../../../docs/contracts/optimization/comparison-v1.json';
import { OptimizationPage } from '../OptimizationPage';
import { createFixturePendingOrdersSource } from '../pendingOrdersSource';
import { withPermissions } from '../../authentication/__tests__/permissionFixtures';

const user = withPermissions({ id_usuario: 1, usuario: 'Operario', rol: 'Operario' });
beforeEach(() => localStorage.clear());

function setupV2({ partial = false } = {}) {
  const current = structuredClone(partial ? comparisonV2.mixed : comparisonV2.completed);
  current.requested_pieces = structuredClone(comparisonV1.completed.requested_pieces).map(piece => ({ ...piece, cantidad: 2 }));
  const source = createFixturePendingOrdersSource([{ id_pedido: 1, cliente: 'Cliente de prueba',
    piezas: current.requested_pieces }]);
  const apiV2 = {
    methods: comparisonV2.catalog.map(method => method.code),
    catalog: comparisonV2.catalog,
    start: vi.fn(async () => structuredClone(current)),
    lookup: vi.fn(async () => structuredClone(current)),
    load: vi.fn(async () => structuredClone(current)),
    result: vi.fn(async (_, execution) => {
      if (execution.result_available === false) return structuredClone(comparisonV2.failed_result);
      if (execution.outcome === 'PARTIAL') return structuredClone(comparisonV2.partial_result);
      return structuredClone(comparisonV2.results[execution.execution_id]);
    }),
    manifest: vi.fn(async (_, execution) => ({ profile: 'comparison-v2', schema_version: 2,
      comparison_id: current.comparison_id, execution_id: execution.execution_id, method: execution.method,
      revision: 0, execution_sequence: 0, preparation_completed: false, processed_units: 0, evaluations: 0,
      phase: 'TERMINAL', current: null, last_orientation: null, ordered_units: [], total: 0, next_offset: null, items: [] })),
    observe: vi.fn(async () => {}),
    forExecution: vi.fn(() => ({ loadVisualMask: vi.fn() })),
    release: vi.fn(async value => ({ ...structuredClone(value), version: value.version + 1, released: true })),
  };
  const v1 = { start: vi.fn(), load: vi.fn(), lookup: vi.fn(), observe: vi.fn(), result: vi.fn(), manifest: vi.fn(),
    forExecution: vi.fn(), choose: vi.fn(), confirm: vi.fn(), release: vi.fn() };
  render(<OptimizationPage user={user} source={source} comparisonAdapter={v1} comparisonV2Adapter={apiV2} />);
  return { apiV2, v1 };
}

async function startV2() {
  fireEvent.click(await screen.findByRole('checkbox', { name: /Pedido #1/ }));
  fireEvent.change(screen.getByLabelText('Perfil'), { target: { value: 'comparison-v2' } });
  fireEvent.click(screen.getByRole('button', { name: 'Comparar con los seis motores' }));
  await screen.findByRole('tab', { name: 'Comparación' });
}

test('comparison-v2 reuses the workspace with seven dynamic tabs and never offers B08 actions', async () => {
  const { apiV2, v1 } = setupV2(); await startV2();
  const expectedTabs = ['Comparación', 'FF', 'BF', 'WF', 'HF', 'BRF', 'BS-2'];
  expect(screen.getAllByRole('tab')).toHaveLength(7);
  for (const label of expectedTabs) expect(screen.getByRole('tab', { name: new RegExp(label) })).toBeVisible();
  expect(apiV2.start).toHaveBeenCalledOnce();
  expect(v1.start).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  expect(screen.getByRole('table')).toHaveTextContent('Métricas de 6 motores');
  expect(screen.getByRole('table')).toHaveTextContent('Cobertura');
  expect(screen.getByRole('table')).toHaveTextContent('Retazos reutilizados');
  expect(screen.queryAllByRole('radio')).toHaveLength(0);
  expect(screen.queryByRole('button', { name: 'Confirmar distribución elegida' })).not.toBeInTheDocument();
  const lastTab = screen.getByRole('tab', { name: /BS-2/ });
  screen.getByRole('tab', { name: 'Comparación' }).focus();
  fireEvent.keyDown(screen.getByRole('tab', { name: 'Comparación' }), { key: 'End' });
  expect(lastTab).toHaveFocus();
});

test('partial M6 and failed HF remain independent and retain their actual diagnostics', async () => {
  setupV2({ partial: true }); await startV2();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  const table = screen.getByRole('table');
  expect(within(table).getByRole('row', { name: /Hole Filling/ })).toHaveTextContent('Fallido');
  expect(within(table).getByRole('row', { name: /Hole Filling/ })).toHaveTextContent('WORKER_STOPPED');
  expect(within(table).getByRole('row', { name: /M6-BS/ })).toHaveTextContent('Parcial');
  expect(within(table).getByRole('row', { name: /M6-BS/ })).toHaveTextContent('EXPANSION_LIMIT');
  fireEvent.click(screen.getByRole('tab', { name: /BS-2/ }));
  const beamPanel = screen.getByRole('tabpanel', { name: /BS-2/ });
  fireEvent.click(within(beamPanel).getByRole('button', { name: /Resultado/ }));
  expect(await within(beamPanel).findAllByText(/pendiente por límite de recursos/)).toHaveLength(2);
  expect(screen.queryByRole('radio')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Confirmar distribución elegida' })).not.toBeInTheDocument();
});

test('reloading a v2 comparison consults its durable ID without starting another comparison', async () => {
  const { apiV2 } = setupV2(); await startV2();
  await waitFor(() => expect(apiV2.result).toHaveBeenCalled());
  expect(apiV2.start).toHaveBeenCalledOnce();
  expect(apiV2.load).toHaveBeenCalledWith(43, expect.anything());
});

test('explicit idempotency-key recovery uses the v2 profile without starting a second comparison', async () => {
  const { apiV2, v1 } = setupV2(); await startV2();
  fireEvent.change(screen.getByLabelText('Recuperar por clave idempotente'), { target: { value: 'b07-recovery-key' } });
  fireEvent.click(screen.getByRole('button', { name: 'Recuperar', exact: true }));
  await screen.findByRole('tab', { name: 'Comparación' });
  await waitFor(() => expect(apiV2.lookup).toHaveBeenCalledWith('b07-recovery-key', expect.anything()));
  expect(apiV2.start).toHaveBeenCalledOnce();
  expect(v1.load).not.toHaveBeenCalled();
  expect(screen.getAllByRole('tab')).toHaveLength(7);
});
