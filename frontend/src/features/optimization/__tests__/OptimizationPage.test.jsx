import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import * as ordersApi from '../../orders/ordersApi';
import { OptimizationPage } from '../OptimizationPage';
import shared from '../contractV1Fixture.json';
import { withPermissions } from '../../authentication/__tests__/permissionFixtures';
import { createFixturePendingOrdersSource, createPendingOrdersSource } from '../pendingOrdersSource';
import { createFixtureAdapter, fixtureOrders, fixtureRun, newFixtureOrder, prepareFixture, sheetToContainer } from '../firstFitFixture';
const user = withPermissions({ rol: 'Operario', nombre: 'Operario local' });
beforeEach(() => {
  vi.useFakeTimers();
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ fillRect: vi.fn(), setTransform: vi.fn() });
});
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });
function mount(orders = fixtureOrders, adapter = createFixtureAdapter({ delayMs: 10 })) {
  const source = createFixturePendingOrdersSource(orders);
  const rendered = render(<OptimizationPage user={user} source={source} adapter={adapter} />);
  return { source, adapter, ...rendered };
}
const click = name => fireEvent.click(screen.getByRole('button', { name, exact: true }));
async function prepare() {
  fireEvent.click(screen.getByLabelText('Seleccionar todos'));
  await act(async () => click('Revisar vidrios y piezas'));
}
async function complete() { click('Calcular distribución'); await act(async () => vi.advanceTimersByTimeAsync(1000)); }

test('single, multiple, all and deselection; no manual refresh or dropzone', () => {
  mount();
  expect(screen.queryByRole('button', { name: 'Actualizar pedidos' })).not.toBeInTheDocument();
  expect(screen.queryByText('Pedido seleccionado')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Revisar vidrios y piezas' })).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox', { name: /#21/ })); expect(screen.getByText('1 pedidos seleccionados')).toBeVisible();
  fireEvent.click(screen.getByRole('checkbox', { name: /#22/ })); expect(screen.getByText('2 pedidos seleccionados')).toBeVisible();
  fireEvent.click(screen.getByLabelText('Seleccionar todos')); expect(screen.getByText('0 pedidos seleccionados')).toBeVisible();
  fireEvent.click(screen.getByLabelText('Seleccionar todos')); expect(screen.getByText('2 pedidos seleccionados')).toBeVisible();
});
test('live add, state change, removal, error and reconnection reconcile selection', () => {
  const { source } = mount();
  fireEvent.click(screen.getByLabelText('Seleccionar todos'));
  act(() => source.emit({ type: 'upsert', order: newFixtureOrder }));
  expect(screen.getByRole('checkbox', { name: /#21/ })).toBeChecked();
  expect(screen.getByRole('checkbox', { name: /#24/ })).not.toBeChecked();
  act(() => source.emit({ type: 'upsert', order: { ...fixtureOrders[0], estado: 'EN_OPTIMIZACION' } }));
  expect(screen.queryByRole('checkbox', { name: /#21/ })).not.toBeInTheDocument();
  act(() => source.emit({ type: 'remove', id: 22 })); expect(screen.getByText('0 pedidos seleccionados')).toBeVisible();
  act(() => source.emit({ type: 'error' })); expect(screen.getByRole('alert')).toHaveTextContent('Conexión interrumpida');
  act(() => source.emit({ type: 'reconnect' })); expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
test('groups, progressive placements, arbitrary rotations, metrics and honest confirmation', async () => {
  mount(); await prepare();
  expect(document.querySelector('.first-fit-groups')).toHaveTextContent('Templado · 6 mm'); expect(document.querySelector('.first-fit-groups')).toHaveTextContent('Bronce · 5.5 mm');
  click('Calcular distribución');
  expect(screen.getByText('0 / 4 piezas colocadas')).toBeVisible();
  await act(async () => vi.advanceTimersByTimeAsync(40));
  expect(screen.getByText('1 / 4 piezas colocadas')).toBeVisible();
  expect(document.querySelectorAll('[data-placement]')).toHaveLength(1);
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(screen.getByText('4 / 4 piezas colocadas')).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Resultado del corte' })).toBeVisible();
  expect(screen.getByRole('list', { name: 'Detalle de colocaciones' })).toHaveTextContent('rotación aplicada: 90°');
  expect(document.querySelector('[data-placement="22:104:1"]')).toHaveAttribute('transform', 'translate(2000 150)');
  fireEvent.change(screen.getByLabelText('Vidrio del resultado'), { target: { value: '2:5.5' } });
  expect(screen.getByRole('img', { name: 'Colocaciones en plancha #16' }).querySelector('circle')).toHaveAttribute('r', '240');
  expect(screen.getByText('842 ms')).toBeVisible();
  click('Confirmar corte');
  const dialog = screen.getByRole('alertdialog'); expect(dialog).toHaveTextContent('Se descontarán del inventario las planchas y retazos utilizados');
  expect(within(dialog).getByRole('button', { name: 'Cancelar' })).toHaveFocus();
  fireEvent.keyDown(dialog, { key: 'Escape' }); expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  click('Confirmar corte');
  await act(async () => fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar corte' })));
  expect(screen.getByText(/No se guardó la solución/)).toBeVisible();
});
test('snapshot stays fixed after new pending order and removal during run', async () => {
  const { source } = mount(); await prepare(); click('Calcular distribución');
  act(() => source.emit({ type: 'upsert', order: newFixtureOrder }));
  act(() => source.emit({ type: 'remove', id: 21 }));
  expect(screen.getByText('1 nuevo pedido disponible para la siguiente ejecución.')).toBeVisible();
  expect(screen.getByText(/Pedidos: #21, #22/)).toHaveTextContent('Piezas: 4');
  await act(async () => vi.advanceTimersByTimeAsync(1000)); expect(screen.getByText('4 / 4 piezas colocadas')).toBeVisible();
});
test('rerun clears placements, discard cancels queued events', async () => {
  mount(); await prepare(); await complete(); click('Preparar otro corte');
  expect(screen.getByText('0 / 4 piezas colocadas')).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'Resultado del corte' })).not.toBeInTheDocument();
  click('Descartar'); await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(screen.queryByRole('img', { name: /Colocaciones en/ })).not.toBeInTheDocument();
  expect(screen.getByText('2 pedidos seleccionados')).toBeVisible();
});
test('failed stream can retry', async () => {
  let listener;
  const adapter = { ...createFixtureAdapter(), createEventSource: () => ({ subscribe(fn) { listener = fn; }, dispose: vi.fn() }) };
  mount(fixtureOrders, adapter); await prepare(); click('Calcular distribución');
  act(() => listener({ ...shared.failed_event, sequence: 1, id_optimizacion: 301, data: { ...shared.failed_event.data, message: 'Fallo del proceso' } }));
  expect(screen.getByRole('alert')).toHaveTextContent('Fallo del proceso');
  click('Preparar otro corte'); expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('accepted Location ID remains recoverable after a stream failure without reexecuting First Fit', async () => {
  const adapter = { ...createFixtureAdapter(),
    createEventSource: vi.fn(() => ({ subscribe(event, failed, accepted) {
      accepted(301); failed(new Error('Flujo interrumpido'));
    }, dispose: vi.fn() })),
    loadResult: vi.fn(async () => fixtureRun(prepareFixture([21, 22]))),
  };
  mount(fixtureOrders, adapter); await prepare(); click('Calcular distribución');
  expect(screen.getByText('Trabajo #301')).toBeVisible();
  expect(screen.getByRole('alert')).toHaveTextContent('Flujo interrumpido');
  expect(screen.queryByText('Estado del trabajo: Procesando')).not.toBeInTheDocument();
  expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  expect(screen.getByRole('checkbox', { name: /#21/ })).toBeChecked();
  await act(async () => click('Recuperar resultado'));
  expect(adapter.loadResult).toHaveBeenCalledExactlyOnceWith(301, { resultUrl: null });
  expect(screen.getByText('4 / 4 piezas colocadas')).toBeVisible();
  expect(adapter.createEventSource).toHaveBeenCalledOnce();
});
test('empty and permission prevent execution and reads', () => {
  const view = mount([]); expect(screen.getByText('No hay pedidos pendientes.')).toBeVisible(); view.unmount();
  const source = { load: vi.fn() };
  render(<OptimizationPage user={{ rol: 'Almacenero' }} source={source} />);
  expect(screen.getByRole('alert')).toHaveTextContent('No tienes permiso'); expect(source.load).not.toHaveBeenCalled();
});
test('loading, 401, no mutation and unmount cleanup', () => {
  let listener;
  const source = { load: vi.fn(), subscribe(fn) { listener = fn; return vi.fn(); }, dispose: vi.fn() };
  const expired = vi.fn();
  const view = render(<OptimizationPage user={user} source={source} onSessionExpired={expired} />);
  expect(screen.getByText('Cargando pedidos...')).toBeVisible();
  act(() => listener({ type: 'error', error: { status: 401, message: 'Sesión vencida' } }));
  expect(expired).toHaveBeenCalledOnce(); expect(screen.getByRole('alert')).toHaveTextContent('Sesión vencida');
  view.unmount(); expect(source.dispose).toHaveBeenCalledOnce();
});
test('real adapter prepares persisted pieces without starting a run or inventing stock', async () => {
  const read = vi.spyOn(ordersApi, 'getOrder').mockImplementation(async id => structuredClone(fixtureOrders.find(o => o.id_pedido === id)));
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify([{ id_tipo_vidrio: 1, nombre: 'Templado' }, { id_tipo_vidrio: 2, nombre: 'Bronce' }])));
  const source = createFixturePendingOrdersSource(fixtureOrders);
  render(<OptimizationPage user={user} source={source} />); await prepare();
  expect(read).toHaveBeenCalledTimes(2);
  expect(fetch).toHaveBeenCalledOnce();
  expect(fetch.mock.calls[0][0]).toMatch(/\/inventory\/tipos-vidrio$/);
  expect(fetch.mock.calls[0][1].method).toBe('GET');
  expect(screen.getByRole('button', { name: 'Calcular distribución' })).toBeEnabled();
  expect(document.querySelectorAll('[data-placement]')).toHaveLength(0);
});
test('inventory dimensions override all commercial assumptions', () => {
  expect(sheetToContainer({ id_plancha: 5, ancho_mm: '1234', alto_mm: '5678', espesor_mm: '5.5' }, 'Bronce')).toMatchObject({ material_width_mm: 1234, material_height_mm: 5678 });
  expect(() => sheetToContainer({ ancho_mm: null, alto_mm: 200 }, '')).toThrow();
  expect(prepareFixture([21, 22]).total).toBe(4);
});
test('polling batches pages atomically, retries errors and cancels on dispose', async () => {
  const request = vi.fn().mockResolvedValueOnce({ items: [fixtureOrders[0]], total_pages: 2 })
    .mockResolvedValueOnce({ items: [fixtureOrders[1]], total_pages: 2 })
    .mockRejectedValueOnce(new Error('Red'))
    .mockResolvedValue({ items: [newFixtureOrder], total_pages: 1 });
  const source = createPendingOrdersSource({ request, intervalMs: 50, token: 'local' }); const listener = vi.fn();
  source.subscribe(listener); await source.load();
  expect(listener).toHaveBeenCalledTimes(1); expect(listener.mock.calls[0][0].orders).toHaveLength(2);
  expect(request).toHaveBeenCalledWith({ page: 2, limit: 100, estado: 'PENDIENTE' }, expect.objectContaining({ token: 'local' }));
  await vi.advanceTimersByTimeAsync(50); expect(listener.mock.lastCall[0].type).toBe('error');
  await vi.advanceTimersByTimeAsync(50); expect(listener.mock.lastCall[0].orders[0].id_pedido).toBe(24);
  const signal = request.mock.lastCall[1].signal; source.dispose(); expect(signal.aborted).toBe(true);
  await vi.advanceTimersByTimeAsync(500); expect(request).toHaveBeenCalledTimes(4);
});

test('polling restart ignores late response from disposed StrictMode lifecycle', async () => {
  let resolveOld;
  const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }))
    .mockResolvedValueOnce({ items: [newFixtureOrder], total_pages: 1 });
  const source = createPendingOrdersSource({ request });
  const oldListener = vi.fn(); source.subscribe(oldListener); const first = source.load(); source.dispose();
  const currentListener = vi.fn(); source.subscribe(currentListener); await source.load();
  resolveOld({ items: fixtureOrders, total_pages: 2 }); await first;
  expect(oldListener).not.toHaveBeenCalled(); expect(currentListener).toHaveBeenCalledOnce();
  expect(currentListener.mock.calls[0][0].orders).toEqual([newFixtureOrder]);
  expect(request).toHaveBeenCalledTimes(2); source.dispose();
});

test('public-only stream renders progress, completed stages and confirmation without internal stage events', async () => {
  const adapter = createFixtureAdapter({ delayMs: 10, includeInternalStages: false });
  mount(fixtureOrders, adapter);
  await prepare(); click('Calcular distribución');
  await act(async () => vi.advanceTimersByTimeAsync(40));
  expect(screen.getByText('1 / 4 piezas colocadas')).toBeVisible();
  expect(document.querySelectorAll('[data-placement]')).toHaveLength(1);
  const stages = screen.getByRole('list', { name: 'Etapas de optimización' });
  expect(within(stages).getByText('Calculando distribución').closest('li')).toHaveAttribute('aria-current', 'step');
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(screen.getByText('4 / 4 piezas colocadas')).toBeVisible();
  expect(within(stages).getAllByText('Completado')).toHaveLength(8);
  expect(within(stages).queryByText('Pendiente')).not.toBeInTheDocument();
  expect(screen.getByText('842 ms')).toBeVisible();
  click('Confirmar corte');
  expect(screen.getByRole('alertdialog')).toHaveTextContent('no guardará cambios');
});

test('3D toggles preserve the run, live snapshot and metrics; rerun and discard clear the previous scene', async () => {
  const { source } = mount();
  expect(screen.queryByRole('button', { name: 'Ver en 3D' })).not.toBeInTheDocument();
  await prepare();
  expect(screen.queryByRole('button', { name: 'Ver en 3D' })).not.toBeInTheDocument();
  click('Calcular distribución');
  expect(screen.queryByRole('button', { name: 'Ver en 3D' })).not.toBeInTheDocument();
  await act(async () => vi.advanceTimersByTimeAsync(40));
  click('Ver en 3D');
  act(() => source.emit({ type: 'upsert', order: newFixtureOrder }));
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(screen.getByText('4 / 4 piezas colocadas')).toBeVisible();
  expect(screen.getByText(/Pedidos: #21, #22/)).toHaveTextContent('Piezas: 4');
  expect(screen.getByText('842 ms')).toBeVisible();
  click('Ver en 2D'); click('Ver en 3D');
  expect(screen.getByText('842 ms')).toBeVisible();
  expect(screen.getByRole('checkbox', { name: /#24/ })).not.toBeChecked();
  click('Preparar otro corte');
  expect(screen.queryByRole('slider')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Ver en 3D' })).not.toBeInTheDocument();
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(screen.getByRole('button', { name: 'Ver en 2D' })).toHaveAttribute('aria-pressed', 'true');
  click('Ver en 3D'); click('Descartar');
  expect(screen.queryByRole('button', { name: 'Ver en 3D' })).not.toBeInTheDocument();
  expect(screen.queryByRole('slider')).not.toBeInTheDocument();
});
