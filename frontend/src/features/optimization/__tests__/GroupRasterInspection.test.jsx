import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { OptimizationPage } from '../OptimizationPage';
import { withPermissions } from '../../authentication/__tests__/permissionFixtures';
import { createFixturePendingOrdersSource } from '../pendingOrdersSource';
import { createFixtureAdapter, fixtureOrders, fixturePlacements, prepareFixture } from '../firstFitFixture';
import { PlacementCanvas } from '../PlacementCanvas';
import { RasterInspection } from '../RasterInspection';

beforeEach(() => { vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ fillRect: vi.fn(), setTransform: vi.fn() }); });
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });
const click = (name, scope = screen) => fireEvent.click(scope.getByRole('button', { name, exact: true }));
test('selection previews groups immediately and preparation exposes all masks before any result', async () => {
  const source = createFixturePendingOrdersSource(fixtureOrders);
  render(<OptimizationPage user={withPermissions({ rol: 'Operario' })} source={source} adapter={createFixtureAdapter()} />);
  fireEvent.click(screen.getByLabelText('Seleccionar todos'));
  const groups = screen.getByRole('region', { name: 'Grupos detectados' });
  expect(groups).toHaveTextContent('Plancha base #15'); expect(groups).toHaveTextContent('Plancha base #16');
  expect(groups).toHaveTextContent('3 piezas · pedidos #21, #22');
  expect(screen.queryByRole('img', { name: /Celdas raster/ })).not.toBeInTheDocument();
  await act(async () => click('Preparar optimización'));
  expect(screen.getByRole('heading', { name: 'Preparación raster · antes de optimizar' })).toBeVisible();
  expect(screen.getByRole('img', { name: 'Celdas raster de pieza #101' })).toBeVisible();
  expect(screen.getByText(/Preparada · resolución: 100 mm por celda/)).toBeVisible();
  expect(screen.queryByRole('group', { name: 'Vista del resultado' })).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Grupo para preparar raster'), { target: { value: '2:5.5' } });
  expect(screen.getByLabelText('Pieza para inspeccionar').options).toHaveLength(1);
  expect(screen.getByRole('img', { name: 'Celdas raster de pieza #103' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Ejecutar First Fit', exact: true })).toBeEnabled();
});

test('result modes isolate groups, keep snapshot and allow zoom/grid inspection and empty remnant', () => {
  const snapshot = prepareFixture([21, 22]); const before = JSON.stringify(snapshot);
  const placements = fixturePlacements(snapshot);
  render(<PlacementCanvas snapshot={snapshot} placements={placements} />);
  expect(document.querySelectorAll('[data-placement]')).toHaveLength(3);
  expect(screen.getByLabelText('Plancha o retazo').options).toHaveLength(1);
  click('Acercar 2D'); expect(screen.getByLabelText('Ampliación 2D')).toHaveTextContent('150 %');
  expect(document.querySelector('.inspection-content')).toHaveStyle({ width: '150%' });
  click('Ajustar 2D'); expect(screen.getByLabelText('Ampliación 2D')).toHaveTextContent('100 %');
  click('Ver en 3D'); click('Acercar 3D');
  expect(screen.getByLabelText('Ampliación 3D')).toHaveTextContent('150 %');
  fireEvent.change(screen.getByLabelText('Grupo del resultado'), { target: { value: '2:5.5' } });
  expect(document.querySelectorAll('[data-piece-3d]')).toHaveLength(1);
  expect(screen.getByRole('list', { name: 'Piezas en la vista 3D' })).not.toHaveTextContent('Pedido #22');
  click('Ver máscara raster');
  expect(screen.getByLabelText('Grupo del resultado')).toHaveValue('2:5.5');
  expect(screen.getByRole('img', { name: 'Celdas raster de pieza #103' })).toBeVisible();
  click('Acercar raster'); expect(screen.getByLabelText('Ampliación raster')).toHaveTextContent('150 %');
  fireEvent.click(screen.getByLabelText('Mostrar celdas')); expect(document.querySelector('[data-raster-grid]')).toBeNull();
  fireEvent.click(screen.getByLabelText('Mostrar celdas')); expect(document.querySelector('[data-raster-grid]')).not.toBeNull();
  for (let i = 0; i < 10; i++) click('Acercar raster');
  expect(screen.getByLabelText('Ampliación raster')).toHaveTextContent('400 %'); expect(screen.getByRole('button', { name: 'Acercar raster' })).toBeDisabled();
  click('Ver en 3D'); expect(screen.getByLabelText('Ampliación 3D')).toHaveTextContent('150 %');
  click('Restablecer vista'); expect(screen.getByLabelText('Ampliación 3D')).toHaveTextContent('100 %');
  click('Ver en 2D'); fireEvent.change(screen.getByLabelText('Plancha o retazo'), { target: { value: 'RETAZO:8:1' } });
  expect(document.querySelectorAll('[data-placement]')).toHaveLength(0);
  expect(screen.getByText('Las piezas aparecerán al recibir sus colocaciones.')).toBeVisible();
  expect(JSON.stringify(snapshot)).toBe(before);
});

test('rendering rejects incompatible imported placements and hides result modes for unplaced group', () => {
  const snapshot = prepareFixture([21, 22]); const placements = fixturePlacements(snapshot);
  render(<PlacementCanvas snapshot={snapshot} placements={[placements[0], { ...placements[3], group_id: '1:6', material_id: 15 }]} />);
  expect(document.querySelectorAll('[data-placement]')).toHaveLength(1);
  fireEvent.change(screen.getByLabelText('Grupo del resultado'), { target: { value: '2:5.5' } });
  expect(screen.queryByRole('group', { name: 'Vista del resultado' })).not.toBeInTheDocument();
  expect(document.querySelectorAll('[data-placement]')).toHaveLength(0);
});

test('missing raster is explicit, never fabricated from geometry', () => {
  const snapshot = prepareFixture([21]); snapshot.rasters = {};
  render(<RasterInspection snapshot={snapshot} group={snapshot.groups[0]} />);
  expect(screen.getByRole('status')).toHaveTextContent('no se recibió máscara');
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
});

test('execution waits for complete raster preparation instead of silently running with missing masks', async () => {
  const snapshot = prepareFixture([21, 22]); delete snapshot.rasters[103];
  const source = createFixturePendingOrdersSource(fixtureOrders);
  const adapter = { ...createFixtureAdapter(), prepare: async () => snapshot };
  render(<OptimizationPage user={withPermissions({ rol: 'Operario' })} source={source} adapter={adapter} />);
  fireEvent.click(screen.getByLabelText('Seleccionar todos'));
  await act(async () => click('Preparar optimización'));
  expect(screen.getByRole('button', { name: 'Ejecutar First Fit', exact: true })).toBeDisabled();
  expect(screen.getByText(/faltan máscaras válidas/)).toBeVisible();
  expect(document.querySelector('.first-fit-groups')).toHaveTextContent('Estado: Pendiente');
});

test('prepared masks and groups stay fixed when live order details change during execution', async () => {
  vi.useFakeTimers();
  const source = createFixturePendingOrdersSource(fixtureOrders);
  render(<OptimizationPage user={withPermissions({ rol: 'Operario' })} source={source} adapter={createFixtureAdapter({ delayMs: 10 })} />);
  fireEvent.click(screen.getByLabelText('Seleccionar todos'));
  await act(async () => click('Preparar optimización')); click('Ejecutar First Fit');
  const changed = structuredClone(fixtureOrders[0]); changed.piezas[0].espesor_mm = 10;
  act(() => source.emit({ type: 'upsert', order: changed }));
  const groups = within(screen.getByRole('region', { name: 'Grupos detectados' }));
  expect(groups.getByText('Templado · 6 mm', { selector: 'strong' })).toBeVisible();
  expect(groups.queryByText(/10 mm/)).not.toBeInTheDocument();
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(screen.getByText('4 / 4 piezas colocadas')).toBeVisible();
});
