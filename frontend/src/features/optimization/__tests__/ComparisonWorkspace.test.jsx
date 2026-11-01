// Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import fixture from '../../../../../docs/contracts/optimization/comparison-v1.json';
import { OptimizationPage } from '../OptimizationPage';
import { createFixturePendingOrdersSource } from '../pendingOrdersSource';
import { withPermissions } from '../../authentication/__tests__/permissionFixtures';

const user = withPermissions({ id_usuario: 1, usuario: 'Operario', rol: 'Operario' });
beforeEach(() => {
  localStorage.clear();
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ fillRect: vi.fn(), setTransform: vi.fn() });
});
function setup({ failStart = false, partial = false, partialFF = false, ambiguous = false } = {}) {
  let current = structuredClone(fixture.completed);
  if (partial || partialFF) {
    current.incomplete = true;
    const failed = partialFF ? 0 : 1;
    current.executions[failed] = { ...current.executions[failed], status: 'FALLIDA', complete: false, eligible: false,
      placed_units: 0, metrics: null, computation_time_ms: null, failure_code: 'EXECUTION_FAILED' };
  }
  const api = {
    start: vi.fn(async () => { if (ambiguous) throw Object.assign(new Error('Respuesta de aceptación interrumpida.'), { status: 0, code: 'NETWORK_ERROR' });
      if (failStart) throw Object.assign(new Error('Revisa la configuración.'), { status: 409, code: 'CONFIG_CONFLICT' }); return structuredClone(fixture.accepted); }),
    lookup: vi.fn(async () => structuredClone(current)),
    load: vi.fn(async () => structuredClone(current)),
    result: vi.fn(async (_, e) => structuredClone(fixture.results[e.execution_id])),
    manifest: vi.fn(async (_, e) => structuredClone(fixture.manifests[e.execution_id])),
    observe: vi.fn(async (_, cursor, callback) => { if (!partial && !partialFF) for (const e of fixture.events) if (e.sequence > cursor) callback(structuredClone(e)); }),
    forExecution: vi.fn(() => ({ loadVisualMask: vi.fn(async (_, descriptor) => structuredClone(fixture.masks[descriptor.mask_ref])) })),
    choose: vi.fn(async (_, id) => { current = { ...current, version: current.version + 1, selected_execution_id: id, confirmable: true }; return structuredClone(current); }),
    confirm: vi.fn(async () => { current = { ...current, version: current.version + 1, confirmed: true, confirmable: false, selection_allowed: false }; }),
    release: vi.fn(async () => { current = { ...current, version: current.version + 1, released: true, selection_allowed: false, confirmable: false }; return current; }),
  };
  const source = createFixturePendingOrdersSource([{ id_pedido: 1, cliente: 'Cliente de prueba', piezas: fixture.accepted.requested_pieces }]);
  const view = render(<OptimizationPage user={user} source={source} comparisonAdapter={api} />);
  return { api, source, ...view };
}
async function execute() {
  fireEvent.click(await screen.findByRole('checkbox', { name: /Pedido #1/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Comparar con los tres motores' }));
  await screen.findByRole('tab', { name: 'Comparación' });
  await waitFor(() => expect(screen.getByText('Comparación finalizada')).toBeVisible());
}

test('default workspace has four stable tabs, real phases and no automatic choice', async () => {
  const { api } = setup();
  await execute();
  expect(screen.getAllByRole('tab')).toHaveLength(4);
  const first = screen.getByRole('tabpanel', { name: /First Fit/ });
  await within(first).findByRole('heading', { name: 'Orden de procesamiento' }, { timeout: 3000 });
  await within(first).findByRole('heading', { name: 'Giros y colocación' }, { timeout: 3000 });
  await within(first).findByRole('heading', { name: 'Resultado de First Fit' }, { timeout: 3000 });
  fireEvent.click(within(first).getByRole('button', { name: /Orden de piezas/ }));
  expect(within(first).getByRole('list', { name: 'Fases del motor' })).toHaveTextContent('Máscaras');
  expect(within(first).getByText('Pedido #1 · Pieza #1 · unidad 3')).toBeVisible();
  fireEvent.click(within(first).getByRole('button', { name: /Giros y colocación/ }));
  expect(within(first).getByRole('img', { name: /Giro real/ })).toBeVisible();
  fireEvent.click(within(first).getByRole('button', { name: 'Pausar vista' }));
  fireEvent.click(screen.getByRole('tab', { name: /Best Fit/ }));
  fireEvent.click(screen.getByRole('tab', { name: /First Fit/ }));
  expect(within(first).getByRole('button', { name: 'Reanudar vista' })).toBeVisible();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  expect(screen.getAllByRole('radio').every(r => !r.checked)).toBe(true);
  expect(api.choose).not.toHaveBeenCalled();
  expect(api.start).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeDisabled();
});

test('manual BF selection, original measures and confirmation use the same work', async () => {
  const { api, source } = setup(); await execute();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  fireEvent.click(screen.getByLabelText('Elegir Best Fit'));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeEnabled());
  expect(api.choose.mock.calls[0][1]).toBe(2);
  fireEvent.click(screen.getByText(/Piezas y medidas solicitadas/));
  expect(screen.getByText('Medidas derivadas de la geometría guardada')).toBeVisible();
  expect(screen.getByText(/3 unidades · Material sintético/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar distribución elegida' }));
  expect(screen.getByRole('alertdialog')).toHaveTextContent('Best Fit');
  fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar corte' }));
  await waitFor(() => expect(api.confirm).toHaveBeenCalledTimes(1));
  expect(api.confirm.mock.calls[0][1]).toMatchObject({ executionId: 2, version: 6 });
  await screen.findByText(/Trabajo #1 confirmado/);
  expect(screen.queryByRole('tab')).not.toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Pedidos pendientes' })).toBeVisible();
  expect(screen.queryByRole('checkbox', { name: /Pedido #1/ })).not.toBeInTheDocument();
  const firstKey = api.start.mock.calls[0][1];
  act(() => {
    source.emit({ type: 'remove', id: 1 });
    source.emit({ type: 'upsert', order: { id_pedido: 2, cliente: 'Segundo pedido', piezas: [] } });
  });
  fireEvent.click(screen.getByRole('checkbox', { name: /Pedido #2/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Comparar con los tres motores' }));
  await waitFor(() => expect(api.start).toHaveBeenCalledTimes(2));
  expect(api.start.mock.calls[1][0]).toEqual([2]);
  expect(api.start.mock.calls[1][1]).not.toBe(firstKey);
});

test('reload recovers the saved comparison without starting another calculation', async () => {
  const { api, unmount } = setup(); await execute(); unmount();
  const source = createFixturePendingOrdersSource([]);
  render(<OptimizationPage user={user} source={source} comparisonAdapter={api} />);
  await screen.findByRole('tab', { name: 'Comparación' });
  expect(api.start).toHaveBeenCalledTimes(1);
  expect(api.load).toHaveBeenCalledWith(1, expect.anything());
});

test('configuration rejection retains selected orders and does not invent an execution', async () => {
  const { api } = setup({ failStart: true });
  fireEvent.click(await screen.findByRole('checkbox', { name: /Pedido #1/ }));
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Comparar con los tres motores' })));
  expect(screen.getByText('Revisa la configuración.')).toBeVisible();
  expect(screen.getByRole('checkbox', { name: /Pedido #1/ })).toBeChecked();
  expect(screen.queryByRole('tab')).not.toBeInTheDocument();
  expect(api.observe).not.toHaveBeenCalled();
});

test('failed engine has no fake zero metrics and successful results stay eligible', async () => {
  setup({ partial: true }); await execute();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  const row = within(screen.getByRole('table')).getByRole('row', { name: /Best Fit/ });
  expect(within(row).getByRole('radio')).toBeDisabled();
  expect(within(row).getAllByText('—')).toHaveLength(6);
  expect(screen.getByLabelText('Elegir Worst Fit')).toBeEnabled();
  expect(screen.getByText(/La comparación está incompleta/)).toBeVisible();
});

test('FF failure does not prevent confirming BF and returning to a clean pending selector', async () => {
  const { api } = setup({ partialFF: true });
  await execute();
  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  expect(screen.getByLabelText('Elegir First Fit')).toBeDisabled();
  fireEvent.click(screen.getByLabelText('Elegir Best Fit'));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar distribución elegida' }));
  fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar corte' }));
  await screen.findByText(/Trabajo #1 confirmado/);
  expect(api.confirm).toHaveBeenCalledTimes(1);
  expect(api.confirm.mock.calls[0][1].executionId).toBe(2);
  expect(screen.queryByRole('tab')).not.toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Pedidos pendientes' })).toHaveFocus();
});

test('ambiguous acceptance is recovered by request key without submitting another calculation', async () => {
  const { api } = setup({ ambiguous: true });
  fireEvent.click(await screen.findByRole('checkbox', { name: /Pedido #1/ }));
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Comparar con los tres motores' })));
  expect(screen.getByText('Respuesta de aceptación interrumpida.')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Recuperar estado' }));
  await screen.findByRole('tab', { name: 'Comparación' });
  expect(api.lookup).toHaveBeenCalledTimes(1);
  expect(api.start).toHaveBeenCalledTimes(1);
});
