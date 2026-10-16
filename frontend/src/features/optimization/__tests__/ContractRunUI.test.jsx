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
  mount(); expect(screen.getByRole('heading', { name: 'Optimización' })).toBeVisible();
  expect(screen.getByText('Estado del cálculo: COMPLETADA')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Ejecutar nuevamente' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Confirmar solución' })).not.toBeInTheDocument();
});
test('execute and confirm are separate capabilities, independent of role names', () => {
  const rendered = mount('complete', [...view, 'optimization.execute']);
  expect(screen.getByRole('button', { name: 'Ejecutar nuevamente' })).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Confirmar solución' })).not.toBeInTheDocument(); rendered.unmount();
  mount('complete', [...view, 'optimization.confirm']);
  expect(screen.getByRole('button', { name: 'Confirmar solución' })).toBeEnabled();
});
test('SIN_SOLUCION preserves diagnostic placements, nullable metrics and disables confirmation', () => {
  mount('incomplete', [...view, 'optimization.confirm']);
  expect(screen.getByText(/SIN_SOLUCION: colocaciones de diagnóstico/)).toBeVisible();
  expect(screen.getByText('3 / 4 piezas colocadas')).toBeVisible();
  expect(screen.getByText('Métricas no disponibles.')).toBeVisible();
  expect(document.querySelectorAll('[data-placement]')).toHaveLength(1);
  expect(screen.queryByRole('button', { name: 'Confirmar solución' })).not.toBeInTheDocument();
});
test.each(['running', 'not-confirmable', 'confirmed', 'failed'])('%s result never offers confirmation', name => {
  mount(name, [...view, 'optimization.confirm']);
  expect(screen.queryByRole('button', { name: 'Confirmar solución' })).not.toBeInTheDocument();
  if (name === 'confirmed') expect(screen.getByText('Solución ya confirmada.')).toBeVisible();
  if (name === 'failed') expect(screen.getByText('Optimización fallida')).toBeVisible();
  if (name === 'running') expect(screen.getByText('Estado del cálculo: EN_EJECUCION')).toBeVisible();
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
  fireEvent.change(screen.getByLabelText('Grupo del resultado'), { target: { value: '8:4' } });
  expect(screen.getByLabelText('Plancha o retazo')).toHaveValue('RETAZO:8:1');
  expect(document.querySelectorAll('[data-piece-3d]')).toHaveLength(1);
});
test('merma is shown in square millimeters using T1 metric names', () => {
  render(<OptimizationPage user={user(view)} result={shared.result} source={createFixturePendingOrdersSource([])} adapter={{}} />);
  expect(screen.getByText('4950 mm²')).toBeVisible();
  expect(screen.getByText('1 %')).toBeVisible(); expect(screen.getByText('3 ms')).toBeVisible();
});
test('confirmation interface gets only the run ID and can represent HTTP 409 without stock writes', async () => {
  const confirm = vi.fn().mockRejectedValue(Object.assign(new Error('conflict'), { status: 409 }));
  mount('complete', [...view, 'optimization.confirm'], { confirm });
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar solución' }));
  await act(async () => fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar solución' })));
  expect(confirm).toHaveBeenCalledExactlyOnceWith(101);
  expect(screen.getByText(/El inventario cambió \(409\)/)).toBeVisible();
});

test('selection crosses adapter boundary exclusively as order_ids', async () => {
  const adapter = createFixtureAdapter();
  const prepare = vi.spyOn(adapter, 'prepare');
  const open = vi.spyOn(adapter, 'createEventSource').mockReturnValue({ subscribe: vi.fn(), dispose: vi.fn() });
  render(<OptimizationPage user={user([...view, 'optimization.execute'])}
    source={createFixturePendingOrdersSource(fixtureOrders)} adapter={adapter} />);
  fireEvent.click(screen.getByLabelText('Seleccionar todos'));
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Preparar optimización' })));
  expect(prepare).toHaveBeenCalledExactlyOnceWith({ order_ids: [21, 22] });
  fireEvent.click(screen.getByRole('button', { name: 'Ejecutar First Fit', exact: true }));
  expect(open.mock.calls[0][0]).toEqual({ order_ids: [21, 22] });
});

test('discard prevents a late canonical recovery from restoring a previous run', async () => {
  let resolve;
  const loadResult = vi.fn(() => new Promise(done => { resolve = done; }));
  mount('complete', view, { loadResult });
  fireEvent.click(screen.getByRole('button', { name: 'Recuperar resultado' }));
  fireEvent.click(screen.getByRole('button', { name: 'Descartar' }));
  await act(async () => resolve(scenarioFixture()));
  expect(screen.queryByRole('region', { name: 'Colocaciones First Fit' })).not.toBeInTheDocument();
});

test('view-only user can query a durable run and retry a failed GET without execution', async () => {
  const loadResult = vi.fn().mockRejectedValueOnce(new Error('Corrida inexistente'))
    .mockResolvedValueOnce(scenarioFixture('confirmed'));
  render(<OptimizationPage user={user(view)} source={createFixturePendingOrdersSource([])} adapter={{ loadResult }} />);
  fireEvent.change(screen.getByLabelText('ID de optimización'), { target: { value: '101' } });
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Consultar resultado' })));
  expect(screen.getByRole('alert')).toHaveTextContent('Corrida inexistente');
  expect(screen.getByRole('button', { name: 'Consultar resultado' })).toBeEnabled();
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Consultar resultado' })));
  expect(loadResult).toHaveBeenNthCalledWith(2, 101);
  expect(screen.getByText('Solución ya confirmada.')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Preparar optimización' })).not.toBeInTheDocument();
});

test('successful confirmation refreshes canonical flags and inventory-dependent metrics through GET', async () => {
  const confirm = vi.fn().mockResolvedValue(shared.confirmation);
  const loadResult = vi.fn().mockResolvedValue(scenarioFixture('confirmed'));
  mount('complete', [...view, 'optimization.confirm'], { confirm, loadResult });
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar solución' }));
  await act(async () => fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar solución' })));
  expect(confirm).toHaveBeenCalledExactlyOnceWith(101);
  expect(loadResult).toHaveBeenCalledExactlyOnceWith(101, { resultUrl: null });
  expect(screen.getByText('Solución ya confirmada.')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Confirmar solución' })).not.toBeInTheDocument();
});

test('a 409 disables repeat confirmation and never restarts the algorithm', async () => {
  const confirm = vi.fn().mockRejectedValue(Object.assign(new Error('Stock cambió'), { status: 409, code: 'STOCK_CONFLICT' }));
  const createEventSource = vi.fn();
  mount('complete', [...view, 'optimization.confirm'], { confirm, createEventSource });
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar solución' }));
  await act(async () => fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Confirmar solución' })));
  expect(screen.getByRole('button', { name: 'Confirmar solución' })).toBeDisabled();
  expect(createEventSource).not.toHaveBeenCalled(); expect(confirm).toHaveBeenCalledOnce();
});
