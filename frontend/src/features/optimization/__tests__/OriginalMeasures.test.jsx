// TA-046 T02: las medidas originales se ven junto al resultado de cada motor y en la comparación.
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import fixture from '../../../../../docs/contracts/optimization/comparison-v1.json';
import { OptimizationPage } from '../OptimizationPage';
import { OriginalMeasuresTable } from '../OriginalMeasuresTable';
import { createFixturePendingOrdersSource } from '../pendingOrdersSource';
import { withPermissions } from '../../authentication/__tests__/permissionFixtures';

beforeEach(() => {
  localStorage.clear();
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ fillRect: vi.fn(), setTransform: vi.fn() });
});

const rows = table => within(table).getAllByRole('row').slice(1).map(row => [...row.querySelectorAll('th, td')].map(cell => cell.textContent));

test('la tabla conserva decimales originales de rectángulos y círculos', () => {
  render(<OriginalMeasuresTable pieces={[
    { id_pedido: 4, id_pieza: 10, tipo_forma: 'RECTANGULO', cantidad: 1, id_tipo_vidrio: 7, espesor_mm: '6.00', geometria: { width_mm: '125.36', height_mm: '80.04' } },
    { id_pedido: 4, id_pieza: 11, tipo_forma: 'CIRCUNFERENCIA', cantidad: 1, id_tipo_vidrio: 7, espesor_mm: '6.00', geometria: { radius_mm: '3.04' } },
  ]} />);
  expect(screen.getByText('125.36 × 80.04 mm')).toBeVisible();
  expect(screen.getByText('Radio 3.04 mm')).toBeVisible();
});

test('la tabla describe forma, cantidad, vidrio y medidas en mm, incluidos los lados del polígono', () => {
  render(<OriginalMeasuresTable pieces={[
    { id_pedido: 4, id_pieza: 10, tipo_forma: 'RECTANGULO', cantidad: 3, material_nombre: 'Templado', espesor_mm: '6.00', geometria: { type: 'RECTANGULO', width_mm: 800, height_mm: 600 } },
    { id_pedido: 4, id_pieza: 11, tipo_forma: 'POLIGONO_CONVEXO', cantidad: 1, material_nombre: 'Templado', espesor_mm: '6.00', geometria: { type: 'POLIGONO_CONVEXO', vertices_mm: [[0, 0], [300, 0], [300, 400]] } },
  ]} />);
  const table = screen.getByRole('table', { name: 'Medidas originales del pedido' });
  expect(rows(table)).toEqual([
    ['#4', '#10', 'Rectángulo', '3', 'Templado · 6 mm', '800 × 600 mm'],
    ['#4', '#11', 'Polígono convexo', '1', 'Templado · 6 mm', '3 lados: 300 · 400 · 500 mm'],
  ]);
  expect(screen.getByText(/pueden aparecer giradas/)).toBeVisible();
});

test('CA-06: el resultado de cada motor y la comparación muestran las medidas sin desplegar nada', async () => {
  const current = structuredClone(fixture.completed);
  const api = {
    start: vi.fn(async () => structuredClone(fixture.accepted)),
    lookup: vi.fn(async () => structuredClone(current)),
    load: vi.fn(async () => structuredClone(current)),
    result: vi.fn(async (_, e) => structuredClone(fixture.results[e.execution_id])),
    manifest: vi.fn(async (_, e) => structuredClone(fixture.manifests[e.execution_id])),
    observe: vi.fn(async (_, cursor, callback) => { for (const e of fixture.events) if (e.sequence > cursor) callback(structuredClone(e)); }),
    forExecution: vi.fn(() => ({ loadVisualMask: vi.fn(async (_, descriptor) => structuredClone(fixture.masks[descriptor.mask_ref])) })),
    choose: vi.fn(), confirm: vi.fn(), release: vi.fn(),
  };
  const source = createFixturePendingOrdersSource([{ id_pedido: 1, cliente: 'Cliente de prueba', piezas: fixture.accepted.requested_pieces }]);
  render(<OptimizationPage user={withPermissions({ id_usuario: 1, usuario: 'Operario', rol: 'Operario' })} source={source} comparisonAdapter={api} />);
  fireEvent.click(await screen.findByRole('checkbox', { name: /Pedido #1/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Comparar con los tres motores' }));
  await waitFor(() => expect(screen.getByText('Comparación finalizada')).toBeVisible());

  const first = screen.getByRole('tabpanel', { name: /First Fit/ });
  await within(first).findByRole('heading', { name: 'Resultado de First Fit' }, { timeout: 3000 });
  expect(rows(within(first).getByRole('table', { name: 'Medidas originales del pedido' })))
    .toEqual([['#1', '#1', 'Rectángulo', '3', 'Material sintético · 6 mm', '2 × 2 mm']]);

  fireEvent.click(screen.getByRole('tab', { name: 'Comparación' }));
  const comparison = screen.getByRole('tabpanel', { name: 'Comparación' });
  expect(within(comparison).getByRole('table', { name: 'Medidas originales del pedido' })).toBeVisible();
  expect(within(comparison).getByRole('table', { name: 'Métricas de los tres motores' })).toBeVisible();
});
