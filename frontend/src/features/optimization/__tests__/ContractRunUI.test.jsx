import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { OptimizationPage } from '../OptimizationPage';
import { scenarioFixture } from '../runFixtures';
import { createFixturePendingOrdersSource } from '../pendingOrdersSource';
import shared from '../contractV1Fixture.json';
import { Sidebar } from '../../../shared/components/Sidebar';
import { createFixtureAdapter, fixtureOrders } from '../firstFitFixture';

const user = permissions => ({ rol: 'Rol sin reglas locales', nombre: 'Prueba', permisos: permissions });
const view = ['optimization.view'];
function mount(name = 'complete', permissions = view, adapter = {}) {
  return render(<OptimizationPage user={user(permissions)} result={scenarioFixture(name)}
    source={createFixturePendingOrdersSource([])} adapter={adapter} />);
}
beforeEach(() => vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ fillRect: vi.fn(), setTransform: vi.fn() }));

test('without view denies module and never loads a source, even if execute is present', () => {
  const source = { load: vi.fn() };
  render(<OptimizationPage user={user(['optimization.execute'])} source={source} />);
  expect(screen.getByRole('alert')).toHaveTextContent('No tienes permiso para consultar');
  expect(source.load).not.toHaveBeenCalled();
});
test('view-only capability grants navigation and result consultation without execution', () => {
  const rendered = render(<Sidebar user={user(view)} />);
  expect(screen.getByRole('button', { name: 'Optimización' })).toBeVisible(); rendered.unmount();
  mount(); expect(screen.getByRole('heading', { name: 'Optimización de corte' })).toBeVisible();
  expect(screen.getByText('Estado del trabajo: Distribución lista')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Preparar otro corte' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Confirmar corte' })).not.toBeInTheDocument();
});
test('execute and confirm are separate capabilities, independent of role names', () => {
  const rendered = mount('complete', [...view, 'optimization.execute']);
  expect(screen.getByRole('button', { name: 'Preparar otro corte' })).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Confirmar corte' })).not.toBeInTheDocument(); rendered.unmount();
  mount('complete', [...view, 'optimization.confirm']);
  expect(screen.getByRole('button', { name: 'Confirmar corte' })).toBeEnabled();
});
test('SIN_SOLUCION preserves diagnostic placements, nullable metrics and disables confirmation', () => {
  mount('incomplete', [...view, 'optimization.confirm']);
  expect(screen.getByText(/No se encontró una distribución posible. Revisa las piezas/)).toBeVisible();
  expect(screen.getByText('3 / 4 piezas colocadas')).toBeVisible();
  expect(screen.getByText('El resumen del corte no está disponible.')).toBeVisible();
  expect(document.querySelectorAll('[data-placement]')).toHaveLength(1);
  expect(screen.queryByRole('button', { name: 'Confirmar corte' })).not.toBeInTheDocument();
});
test.each(['running', 'not-confirmable', 'confirmed', 'failed'])('%s result never offers confirmation', name => {
  mount(name, [...view, 'optimization.confirm']);
  expect(screen.queryByRole('button', { name: 'Confirmar corte' })).not.toBeInTheDocument();
  if (name === 'confirmed') expect(screen.getByText('Corte ya confirmado.')).toBeVisible();
  if (name === 'failed') expect(screen.getByText('No se pudo calcular el corte')).toBeVisible();
  if (name === 'running') expect(screen.getByText('Estado del trabajo: Procesando')).toBeVisible();
});
test('physical sheet units isolate 2D/3D placements; oriented 90-degree geometry is never rotated twice', () => {
  mount();
  expect(screen.getByLabelText('Plancha o retazo')).toHaveValue('PLANCHA:5:1');
  expect(screen.getByRole('option', { name: /Plancha #5 · unidad 1/ })).toBeInTheDocument();
  expect(screen.getByRole('option', { name: /Plancha #5 · unidad 2/ })).toBeInTheDocument();
  expect(document.querySelectorAll('[data-placement]')).toHaveLength(1);
  fireEvent.change(screen.getByLabelText('Plancha o retazo'), { target: { value: 'PLANCHA:5:2' } });
  expect(document.querySelectorAll('[data-placement]')).toHaveLength(2);
  const placed = document.querySelector('[data-placement="10:27:2"]');
  expect(placed).toHaveAttribute('transform', 'translate(0 0)');
  expect(placed.querySelector('rect')).toHaveAttribute('width', '5');
  expect(placed.querySelector('rect')).toHaveAttribute('height', '10');
  expect(placed.outerHTML).not.toContain('rotate(');
  fireEvent.click(screen.getByRole('button', { name: 'Ver en 3D' }));
  expect(document.querySelectorAll('[data-piece-3d]')).toHaveLength(2);
  fireEvent.change(screen.getByLabelText('Vidrio del resultado'), { target: { value: '8:4' } });
  expect(screen.getByLabelText('Plancha o retazo')).toHaveValue('RETAZO:8:1');
  expect(document.querySelectorAll('[data-piece-3d]')).toHaveLength(1);
});
test('merma is shown in square millimeters using T1 metric names', () => {
  render(<OptimizationPage user={user(view)} result={shared.result} source={createFixturePendingOrdersSource([])} adapter={{}} />);
  expect(screen.getByText('4950 mm² · 99.000 %')).toBeVisible();
  expect(screen.getByText('50.00 mm² · 1 %')).toBeVisible(); expect(screen.getByText('3 ms')).toBeVisible();
});
test('confirmation interface gets only the run ID and can represent HTTP 409 without stock writes', async () => {
  const confirm = vi.fn().mockRejectedValue(Object.assign(new Error('conflict'), { status: 409 }));
  mount('complete', [...view, 'optimization.confirm'], { confirm });
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar corte' }));
  await act(async () => fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar corte' })));
  expect(confirm).toHaveBeenCalledExactlyOnceWith(101);
  expect(screen.getByText(/El inventario cambió/)).toBeVisible();
});

test('selection crosses adapter boundary exclusively as order_ids', async () => {
  const adapter = createFixtureAdapter();
  const prepare = vi.spyOn(adapter, 'prepare');
  const open = vi.spyOn(adapter, 'createEventSource').mockReturnValue({ subscribe: vi.fn(), dispose: vi.fn() });
  render(<OptimizationPage user={user([...view, 'optimization.execute'])}
    source={createFixturePendingOrdersSource(fixtureOrders)} adapter={adapter} />);
  fireEvent.click(screen.getByLabelText('Seleccionar todos'));
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Revisar vidrios y piezas' })));
  expect(prepare).toHaveBeenCalledExactlyOnceWith({ order_ids: [21, 22] });
  fireEvent.click(screen.getByRole('button', { name: 'Calcular distribución', exact: true }));
  expect(open.mock.calls[0][0]).toEqual({ order_ids: [21, 22] });
});

test('discard prevents a late canonical recovery from restoring a previous run', async () => {
  let resolve;
  const loadResult = vi.fn(() => new Promise(done => { resolve = done; }));
  mount('complete', view, { loadResult });
  fireEvent.click(screen.getByRole('button', { name: 'Recuperar resultado' }));
  fireEvent.click(screen.getByRole('button', { name: 'Descartar' }));
  await act(async () => resolve(scenarioFixture()));
  expect(screen.queryByRole('region', { name: 'Distribución de piezas' })).not.toBeInTheDocument();
});

test('view-only user can query a durable run and retry a failed GET without execution', async () => {
  const loadResult = vi.fn().mockRejectedValueOnce(new Error('Corrida inexistente'))
    .mockResolvedValueOnce(scenarioFixture('confirmed'));
  render(<OptimizationPage user={user(view)} source={createFixturePendingOrdersSource([])} adapter={{ loadResult }} />);
  fireEvent.change(screen.getByLabelText('Número de trabajo'), { target: { value: '101' } });
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Consultar resultado' })));
  expect(screen.getByRole('alert')).toHaveTextContent('Corrida inexistente');
  expect(screen.getByRole('button', { name: 'Consultar resultado' })).toBeEnabled();
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Consultar resultado' })));
  expect(loadResult).toHaveBeenNthCalledWith(2, 101);
  expect(screen.getByText('Corte ya confirmado.')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Revisar vidrios y piezas' })).not.toBeInTheDocument();
});

test('successful confirmation refreshes canonical flags and inventory-dependent metrics through GET', async () => {
  const confirm = vi.fn().mockResolvedValue(shared.confirmation);
  const loadResult = vi.fn().mockResolvedValue(scenarioFixture('confirmed'));
  mount('complete', [...view, 'optimization.confirm'], { confirm, loadResult });
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar corte' }));
  await act(async () => fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar corte' })));
  expect(confirm).toHaveBeenCalledExactlyOnceWith(101);
  expect(loadResult).toHaveBeenCalledExactlyOnceWith(101, { resultUrl: null });
  expect(screen.getByText('Corte ya confirmado.')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Confirmar corte' })).not.toBeInTheDocument();
});

test('a 409 disables repeat confirmation and never restarts the algorithm', async () => {
  const confirm = vi.fn().mockRejectedValue(Object.assign(new Error('Stock cambió'), { status: 409, code: 'STOCK_CONFLICT' }));
  const createEventSource = vi.fn();
  mount('complete', [...view, 'optimization.confirm'], { confirm, createEventSource });
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar corte' }));
  await act(async () => fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar corte' })));
  expect(screen.getByRole('button', { name: 'Confirmar corte' })).toBeDisabled();
  expect(createEventSource).not.toHaveBeenCalled(); expect(confirm).toHaveBeenCalledOnce();
});

test('STATE_CONFLICT distinguishes a changed run/order state from a stock conflict', async () => {
  const confirm = vi.fn().mockRejectedValue(Object.assign(new Error('Estado cambió'), { status: 409, code: 'STATE_CONFLICT' }));
  mount('complete', [...view, 'optimization.confirm'], { confirm });
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar corte' }));
  await act(async () => fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar corte' })));
  expect(screen.getByText(/El trabajo o sus pedidos cambiaron/)).toBeVisible();
  expect(screen.queryByText(/El inventario cambió/)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Confirmar corte' })).toBeDisabled();
});
