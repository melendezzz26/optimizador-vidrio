import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import comparisonV2 from '../../../../../docs/contracts/optimization/comparison-v2.json';
import comparisonV1 from '../../../../../docs/contracts/optimization/comparison-v1.json';
import { OptimizationPage } from '../OptimizationPage';
import { createFixturePendingOrdersSource } from '../pendingOrdersSource';
import { withPermissions } from '../../authentication/__tests__/permissionFixtures';

const user = withPermissions({ id_usuario: 1, usuario: 'Operario', rol: 'Operario' });
beforeEach(() => localStorage.clear());

function setupV2({ partial = false, lostResponse = false, conflict = false, actingUser = user } = {}) {
  const current = structuredClone(partial ? comparisonV2.mixed : comparisonV2.completed);
  current.requested_pieces = structuredClone(comparisonV1.completed.requested_pieces).map(piece => ({ ...piece, cantidad: 2 }));
  const source = createFixturePendingOrdersSource([{ id_pedido: 1, cliente: 'Cliente de prueba',
    piezas: current.requested_pieces }]);
  const apiV2 = {
    methods: comparisonV2.catalog.map(method => method.code),
    catalog: comparisonV2.catalog,
    start: vi.fn(async () => structuredClone(current)),
    lookup: vi.fn(async () => structuredClone(current)),
    choose: vi.fn(async (_, executionId) => {
      current.selected_execution_id = executionId; current.version++; current.confirmable = true;
      return structuredClone(current);
    }),
    confirm: vi.fn(async (_, operation) => {
      if (conflict) throw Object.assign(new Error('El stock cambió.'), { status: 409 });
      current.confirmed = true; current.confirmable = false; current.selection_allowed = false; current.version++;
      current.confirmation = { execution_id: current.selected_execution_id, key: operation.key, expected_version: operation.version,
        method: current.executions.find(e => e.execution_id === current.selected_execution_id).method };
      current.executions.forEach(e => { e.eligible = false; });
      if (lostResponse) throw Object.assign(new Error('Respuesta perdida.'), { status: 0 });
      return {};
    }),
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
  const view = render(<OptimizationPage user={actingUser} source={source} comparisonAdapter={v1} comparisonV2Adapter={apiV2} />);
  return { apiV2, v1, view };
}

async function startV2() {
  fireEvent.click(await screen.findByRole('checkbox', { name: /Pedido #1/ }));
  fireEvent.change(screen.getByLabelText('Perfil'), { target: { value: 'comparison-v2' } });
  fireEvent.click(screen.getByRole('button', { name: 'Comparar con los seis motores' }));
  await screen.findByRole('tab', { name: 'Comparación' });
}

test('comparison-v2 reuses seven dynamic tabs and requires a manual choice before confirmation', async () => {
  const { apiV2, v1 } = setupV2(); await startV2();
  const expectedTabs = ['Comparación', 'FF', 'BF', 'WF', 'HF', 'BRF', 'BS-2'];
  expect(screen.getAllByRole('tab')).toHaveLength(7);
  for (const label of expectedTabs) expect(screen.getByRole('tab', { name: new RegExp(label) })).toBeVisible();
  expect(apiV2.start).toHaveBeenCalledOnce();
  expect(v1.start).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  expect(screen.getByRole('table', { name: 'Métricas de 6 motores' })).toHaveTextContent('Métricas de 6 motores');
  expect(screen.getByRole('table', { name: 'Métricas de 6 motores' })).toHaveTextContent('Cobertura');
  expect(screen.getByRole('table', { name: 'Métricas de 6 motores' })).toHaveTextContent('Retazos reutilizados');
  expect(screen.getAllByRole('radio')).toHaveLength(6);
  expect(screen.queryAllByRole('radio', { checked: true })).toHaveLength(0);
  expect(screen.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeDisabled();
  const lastTab = screen.getByRole('tab', { name: /BS-2/ });
  screen.getByRole('tab', { name: 'Comparación' }).focus();
  fireEvent.keyDown(screen.getByRole('tab', { name: 'Comparación' }), { key: 'End' });
  expect(lastTab).toHaveFocus();
});

test.each([false, true])('manual v2 confirmation keeps history after reload, lost response=%s', async lostResponse => {
  const { apiV2, v1, view } = setupV2({ lostResponse }); await startV2();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  fireEvent.click(screen.getByRole('radio', { name: /Best Residual Fit/ }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar distribución elegida' }));
  expect(screen.getByRole('alertdialog')).toHaveTextContent('Best Residual Fit');
  fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar corte' }));
  await screen.findByText(/Trabajo #43 confirmado/);
  expect(apiV2.confirm).toHaveBeenCalledOnce(); expect(v1.confirm).not.toHaveBeenCalled();
  expect(screen.getAllByRole('tab')).toHaveLength(7);
  view.unmount();
  render(<OptimizationPage user={user} source={createFixturePendingOrdersSource([])} comparisonAdapter={v1} comparisonV2Adapter={apiV2} />);
  await screen.findByText('Corte confirmado');
  expect(apiV2.start).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  expect(screen.getByRole('radio', { name: /Best Residual Fit/ })).toBeChecked();
  expect(screen.getAllByRole('radio').every(r => r.disabled)).toBe(true);
});

test.each(comparisonV2.catalog)('a pending $code selection keeps its native radio checked and focused until the durable response arrives', async ({ name }) => {
  const { apiV2 } = setupV2(); await startV2();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  const choose = apiV2.choose.getMockImplementation();
  let releaseSelection;
  const response = new Promise(resolve => { releaseSelection = resolve; });
  apiV2.choose.mockImplementation(async (...args) => { await response; return choose(...args); });
  const radio = screen.getByRole('radio', { name: `Elegir ${name}`, exact: true });
  try {
    radio.focus();
    fireEvent.click(radio);
    expect(screen.getByRole('radio', { name: `Elegir ${name}`, exact: true })).toBe(radio);
    expect(radio).toBeChecked();
    expect(radio).toBeEnabled();
    expect(radio).toHaveFocus();
    expect(screen.getByRole('button', { name: 'Procesando…' })).toBeDisabled();
  } finally { releaseSelection(); }
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeEnabled());
  expect(radio).toBeChecked();
  expect(radio).toHaveFocus();
  expect(apiV2.choose).toHaveBeenCalledOnce();
});

test.each([0, 409])('failed selection status %s restores the last durable choice and never confirms', async status => {
  const { apiV2 } = setupV2(); await startV2();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  const previous = screen.getByRole('radio', { name: 'Elegir First Fit', exact: true });
  fireEvent.click(previous);
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeEnabled());
  let rejectSelection;
  apiV2.choose.mockReturnValueOnce(new Promise((_, reject) => { rejectSelection = reject; }));
  const next = screen.getByRole('radio', { name: 'Elegir Best Residual Fit', exact: true });
  fireEvent.click(next);
  expect(next).toBeChecked();
  expect(screen.getByRole('button', { name: 'Procesando…' })).toBeDisabled();
  rejectSelection(Object.assign(new Error('No se pudo guardar la elección.'), { status }));
  await screen.findByText('No se pudo guardar la elección.');
  await waitFor(() => expect(previous).toBeChecked());
  expect(next).not.toBeChecked();
  expect(apiV2.confirm).not.toHaveBeenCalled();
});

test('v2 conflict refreshes durable state and preserves the manual selection', async () => {
  const { apiV2 } = setupV2({ conflict: true }); await startV2();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  fireEvent.click(screen.getByRole('radio', { name: /Best Residual Fit/ }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar distribución elegida' }));
  fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar corte' }));
  await screen.findByText('El stock cambió.');
  await waitFor(() => expect(screen.getByRole('radio', { name: /Best Residual Fit/ })).toBeEnabled());
  expect(screen.getByRole('radio', { name: /Best Residual Fit/ })).toBeChecked();
  expect(apiV2.confirm).toHaveBeenCalledOnce();
});

test('a network failure before commit retains the same idempotent operation on retry', async () => {
  const { apiV2 } = setupV2(); await startV2();
  apiV2.confirm.mockRejectedValueOnce(Object.assign(new Error('Sin conexión.'), { status: 0 }));
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  fireEvent.click(screen.getByRole('radio', { name: /Best Residual Fit/ }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeEnabled());
  const submit = () => {
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar distribución elegida' }));
    fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar corte' }));
  };
  submit(); await screen.findByText('Sin conexión.');
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeEnabled());
  submit(); await screen.findByText(/Trabajo #43 confirmado/);
  expect(apiV2.confirm).toHaveBeenCalledTimes(2);
  expect(apiV2.confirm.mock.calls[0][1]).toEqual(apiV2.confirm.mock.calls[1][1]);
});

test('v2 confirmation requires the confirmation permission', async () => {
  setupV2({ actingUser: { ...user, permisos: user.permisos.filter(p => p !== 'optimization.confirm') } });
  await startV2(); fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  expect(screen.queryByRole('button', { name: 'Confirmar distribución elegida' })).not.toBeInTheDocument();
});

test('partial M6 and failed HF remain independent and retain their actual diagnostics', async () => {
  setupV2({ partial: true }); await startV2();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  const table = screen.getByRole('table', { name: 'Métricas de 6 motores' });
  expect(within(table).getByRole('row', { name: /Hole Filling/ })).toHaveTextContent('Fallido');
  expect(within(table).getByRole('row', { name: /Hole Filling/ })).toHaveTextContent('WORKER_STOPPED');
  expect(within(table).getByRole('row', { name: /M6-BS/ })).toHaveTextContent('Parcial');
  expect(within(table).getByRole('row', { name: /M6-BS/ })).toHaveTextContent('EXPANSION_LIMIT');
  fireEvent.click(screen.getByRole('tab', { name: /BS-2/ }));
  const beamPanel = screen.getByRole('tabpanel', { name: /BS-2/ });
  fireEvent.click(within(beamPanel).getByRole('button', { name: /Resultado/ }));
  expect(await within(beamPanel).findAllByText(/pendiente por límite de recursos/)).toHaveLength(2);
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  expect(screen.getByRole('radio', { name: /Hole Filling/ })).toBeDisabled();
  expect(screen.getByRole('radio', { name: /Beam Search/ })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeDisabled();
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
