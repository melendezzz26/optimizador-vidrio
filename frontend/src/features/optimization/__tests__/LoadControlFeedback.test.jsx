// TA-037 T04: feedback comprensible para trabajo demasiado grande, servidor ocupado y tiempo máximo.
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { OptimizationPage } from '../OptimizationPage';
import shared from '../contractV1Fixture.json';
import { RunApiError, createBackendRunAdapter } from '../runApi';
import { runErrorFeedback } from '../optimizationModel';
import { withPermissions } from '../../authentication/__tests__/permissionFixtures';
import { createFixturePendingOrdersSource } from '../pendingOrdersSource';
import { createFixtureAdapter, fixtureOrders } from '../firstFitFixture';

const user = withPermissions({ rol: 'Operario', nombre: 'Operario local' });
beforeEach(() => vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ fillRect: vi.fn(), setTransform: vi.fn() }));
afterEach(() => vi.restoreAllMocks());

const click = name => fireEvent.click(screen.getByRole('button', { name, exact: true }));
const tooLarge = new RunApiError('Los pedidos seleccionados suman 180 unidades y el máximo por cálculo es 150. Divide la selección en lotes más pequeños.',
  422, 'LOAD_LIMIT_EXCEEDED', { limit: { name: 'units_per_run', maximum: 150, actual: 180, scope: null } });
const busy = new RunApiError('El optimizador está atendiendo otros cálculos. Intenta nuevamente en unos segundos.',
  503, 'OPTIMIZER_BUSY', { limit: { name: 'active_runs', maximum: 2, actual: 2, scope: null }, retryAfter: 15 });

// Adaptador de fixture cuyo POST de ejecución responde con el error indicado (o deja enviar eventos).
function mount(failure) {
  const calls = { opened: 0, listener: null };
  const adapter = { ...createFixtureAdapter(), createEventSource: () => ({
    subscribe(listener, failed) { calls.opened++; calls.listener = listener; if (failure && calls.opened === 1) failed(failure); },
    dispose: vi.fn(),
  }) };
  render(<OptimizationPage user={user} source={createFixturePendingOrdersSource(fixtureOrders)} adapter={adapter} />);
  return calls;
}
async function prepareAndRun() {
  fireEvent.click(screen.getByLabelText('Seleccionar todos'));
  await act(async () => click('Revisar vidrios y piezas'));
  act(() => click('Calcular distribución'));
}

test('422 LOAD_LIMIT_EXCEEDED: aviso de "divide el lote", selección conservada, foco en el aviso y sin progreso falso', async () => {
  mount(tooLarge);
  await prepareAndRun();
  const notice = document.querySelector('[data-error-kind="load_limit"]');
  expect(screen.getByRole('alert')).toHaveTextContent('El trabajo es demasiado grande para un solo cálculo');
  expect(notice).toHaveTextContent('suman 180 unidades y el máximo por cálculo es 150');
  expect(notice).toHaveTextContent('Los pedidos siguen pendientes y no se usó inventario');
  expect(notice).toHaveFocus();
  expect(screen.getByText('2 pedidos seleccionados')).toBeVisible();
  expect(screen.getByRole('checkbox', { name: /#21/ })).toBeChecked();
  expect(screen.getByRole('button', { name: 'Calcular distribución', exact: true })).toBeEnabled();
  expect(screen.queryByRole('heading', { name: 'Progreso de optimización' })).not.toBeInTheDocument();
  expect(screen.queryByText('No se pudo calcular el corte')).not.toBeInTheDocument();
});

test('503 OPTIMIZER_BUSY: aviso de "intenta más tarde", no se presenta como un cálculo fallido', async () => {
  mount(busy);
  await prepareAndRun();
  const notice = document.querySelector('[data-error-kind="busy"]');
  expect(notice).toHaveTextContent('El optimizador está ocupado');
  expect(notice).toHaveTextContent('Vuelve a presionar «Calcular distribución» en 15 segundos');
  expect(notice.querySelector('[role="status"]')).not.toBeNull();  // advertencia, no error
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(notice).toHaveFocus();
  expect(screen.queryByText('No se pudo calcular el corte')).not.toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Progreso de optimización' })).not.toBeInTheDocument();
});

test('después de 503 se puede reintentar y el aviso desaparece al iniciar la nueva ejecución', async () => {
  const calls = mount(busy);
  await prepareAndRun();
  act(() => click('Calcular distribución'));
  expect(calls.opened).toBe(2);
  expect(document.querySelector('[data-error-kind]')).toBeNull();
  expect(screen.getByRole('heading', { name: 'Progreso de optimización' })).toBeVisible();
});

test('TIME_BUDGET_EXCEEDED en el stream muestra el aviso de tiempo máximo', async () => {
  const calls = mount();
  await prepareAndRun();
  act(() => calls.listener({ ...shared.failed_event, sequence: 1, id_optimizacion: 301,
    data: { ...shared.failed_event.data, code: 'TIME_BUDGET_EXCEEDED',
      message: 'El cálculo superó el tiempo máximo de 120 s y se detuvo. Divide la selección en lotes más pequeños.' } }));
  const notice = document.querySelector('[data-error-kind="time_budget"]');
  expect(notice).toHaveTextContent('El cálculo superó el tiempo máximo');
  expect(notice).toHaveTextContent('No se consumió inventario');
  expect(notice).toHaveFocus();
});

test('otros errores conservan la presentación genérica de siempre', async () => {
  const calls = mount();
  await prepareAndRun();
  act(() => calls.listener({ ...shared.failed_event, sequence: 1, id_optimizacion: 301,
    data: { ...shared.failed_event.data, message: 'Fallo del proceso' } }));
  expect(screen.getByRole('alert')).toHaveTextContent('Fallo del proceso');
  expect(document.querySelector('[data-error-kind]')).toBeNull();
});

test('el adaptador HTTP conserva limit y Retry-After sin reintentar por su cuenta', async () => {
  const body = { detail: { code: 'OPTIMIZER_BUSY', message: busy.message, limit: busy.limit } };
  const fetchImpl = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 503, headers: { 'Retry-After': '15' } }));
  const adapter = createBackendRunAdapter({ token: 'test', fetchImpl });
  const failure = await new Promise(resolve => adapter.createEventSource({ order_ids: [21] }).subscribe(() => {}, resolve));
  expect(failure).toMatchObject({ status: 503, code: 'OPTIMIZER_BUSY', retryAfter: 15, limit: busy.limit });
  expect(fetchImpl).toHaveBeenCalledOnce();
});

test('el modelo decide el aviso; un mensaje sin código no se clasifica', () => {
  expect(runErrorFeedback({ error: '', errorKind: 'busy' })).toBeNull();
  expect(runErrorFeedback({ error: 'x', errorKind: 'busy', retryAfter: null }).hint).toContain('15 segundos');
  expect(runErrorFeedback({ error: 'x', errorKind: null })).toMatchObject({ kind: null, variant: 'error', hint: null });
});