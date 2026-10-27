import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { OptimizationPage } from '../OptimizationPage';
import { createBackendRunAdapter } from '../runApi';
import { createFixturePendingOrdersSource } from '../pendingOrdersSource';
import { createFixtureAdapter, fixtureOrders } from '../firstFitFixture';
import { scenarioFixture } from '../runFixtures';
import { withPermissions } from '../../authentication/__tests__/permissionFixtures';

const user = withPermissions({ rol: 'Operario' });
const click = name => fireEvent.click(screen.getByRole('button', { name, exact: true }));

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ fillRect: vi.fn(), setTransform: vi.fn() });
});
afterEach(() => vi.restoreAllMocks());

test('one main flow reviews multiple orders without starting or rasterizing a run', async () => {
  const fetchImpl = vi.fn();
  const readOrder = vi.fn(async id => structuredClone(fixtureOrders.find(order => order.id_pedido === id)));
  const adapter = createBackendRunAdapter({ token: 'test-token', fetchImpl, readOrder });
  render(<OptimizationPage user={user} source={createFixturePendingOrdersSource(fixtureOrders)} adapter={adapter} />);

  expect(screen.queryByRole('navigation', { name: 'Herramientas de corte' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Vista previa de piezas', exact: true })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Distribución de corte', exact: true })).not.toBeInTheDocument();
  expect(screen.getByRole('list', { name: 'Etapas de optimización' })).toBeVisible();
  expect(readOrder).not.toHaveBeenCalled();
  expect(fetchImpl).not.toHaveBeenCalled();

  fireEvent.click(screen.getByLabelText('Seleccionar todos'));
  await act(async () => click('Revisar vidrios y piezas'));
  expect(readOrder.mock.calls.map(([id]) => id)).toEqual([21, 22]);
  expect(fetchImpl).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: 'Calcular distribución', exact: true })).toBeEnabled();
  const inspection = screen.getByRole('region', { name: 'Inspección de piezas' });
  expect(within(inspection).getByRole('status')).toHaveTextContent('Máscara de la ejecución no disponible');
  expect(within(inspection).getByRole('img', { name: 'Geometría original de la pieza #101' })).toBeVisible();
  expect(within(inspection).queryByRole('img', { name: /Detalle de la pieza/ })).not.toBeInTheDocument();
  expect(inspection).not.toHaveTextContent('abre «Vista previa de piezas»');
  expect(within(inspection).getByLabelText('Pieza para inspeccionar').options).toHaveLength(3);
  fireEvent.change(within(inspection).getByLabelText('Vidrio para inspeccionar'), { target: { value: '2:5.5' } });
  expect(within(inspection).getByLabelText('Pieza para inspeccionar').options).toHaveLength(1);
  expect(within(inspection).getByRole('img', { name: 'Geometría original de la pieza #103' })).toBeVisible();
});

test('changing reviewed selection removes the previous inspection and does not start computation', async () => {
  const adapter = createFixtureAdapter();
  const open = vi.spyOn(adapter, 'createEventSource');
  render(<OptimizationPage user={user} source={createFixturePendingOrdersSource(fixtureOrders)} adapter={adapter} />);
  fireEvent.click(screen.getByLabelText('Seleccionar todos'));
  await act(async () => click('Revisar vidrios y piezas'));
  fireEvent.click(screen.getByRole('checkbox', { name: /#22/ }));
  expect(screen.queryByRole('region', { name: 'Inspección de piezas' })).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Pieza para inspeccionar')).not.toBeInTheDocument();
  expect(open).not.toHaveBeenCalled();
});

test.each(['complete', 'incomplete', 'failed'])('%s never certifies preparation or rotations absent from V1', name => {
  render(<OptimizationPage user={user} result={scenarioFixture(name)}
    source={createFixturePendingOrdersSource([])} adapter={{}} />);
  const stages = screen.getByRole('list', { name: 'Etapas de optimización' });
  for (const label of ['B · Preparación geométrica', 'C · Orientaciones']) {
    expect(within(stages).getByText(label).closest('li')).toHaveTextContent('Sin detalle disponible');
    expect(within(stages).getByText(label).closest('li')).not.toHaveAttribute('aria-current');
  }
  if (name === 'incomplete') expect(stages).toHaveTextContent('Resultado parcial');
  if (name === 'failed') expect(stages).toHaveTextContent('Cálculo fallido');
});

test('view-only result inspection remains in the same flow without execution controls', () => {
  render(<OptimizationPage user={{ rol: 'Consulta', permisos: ['optimization.view'] }} result={scenarioFixture('complete')}
    source={createFixturePendingOrdersSource([])} adapter={{}} />);
  expect(screen.getByRole('list', { name: 'Etapas de optimización' })).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Revisar vidrios y piezas' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Calcular distribución', exact: true })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Preparar vista previa' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Confirmar corte', exact: true })).not.toBeInTheDocument();
});
