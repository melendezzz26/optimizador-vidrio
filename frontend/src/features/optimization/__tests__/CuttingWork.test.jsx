import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { OptimizationPage } from '../OptimizationPage';
import { createFixturePendingOrdersSource } from '../pendingOrdersSource';
import shared from '../contractV1Fixture.json';

const operator = { permisos: ['optimization.view', 'optimization.execute'], nombre: 'Operario' };
const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
const glass = { id_tipo_vidrio: 2, nombre: 'Bronce', espesores_mm: [5.5], estado: true };
const order = (id, quantity) => ({ id_pedido: id, cliente: 'Vidriería', estado: 'PENDIENTE', piezas: [{
  id_pieza: id, tipo_forma: 'RECTANGULO', id_tipo_vidrio: 2, espesor_mm: '5.5', cantidad: quantity,
  geometria: { type: 'RECTANGULO', width_mm: 100, height_mm: 50 },
}] });

test('configuration rejection retains reviewed orders, stops progress and allows an explicit retry without order writes', async () => {
  const technical = 'Se requiere una única configuración vigente completa.';
  const log = vi.spyOn(console, 'error').mockImplementation(() => {});
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
    if (String(url).endsWith('/tipos-vidrio')) return json([glass]);
    if (String(url).endsWith('/orders/61')) return json(order(61, 2));
    if (String(url).endsWith('/runs') && options.method === 'POST') return json({ detail: { code: 'CONFIG_CONFLICT', message: technical } }, 409);
    throw new Error(`Unexpected request: ${url}`);
  });
  render(<OptimizationPage user={operator} token="test-token" source={createFixturePendingOrdersSource([order(61, 2)])} />);
  fireEvent.click(screen.getByRole('checkbox', { name: /#61/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Revisar vidrios y piezas' }));
  await screen.findByRole('button', { name: 'Calcular distribución' });
  expect(document.querySelector('.first-fit-groups')).toHaveTextContent('Bronce · 5.5 mm');
  expect(document.querySelector('.first-fit-groups')).toHaveTextContent('2 piezas · Pedido #61');
  expect(screen.getByText('El sistema elegirá una plancha o retazo disponible para realizar el corte.')).toBeVisible();
  for (let attempt = 1; attempt <= 2; attempt++) {
    fireEvent.click(screen.getByRole('button', { name: 'Calcular distribución' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se puede calcular el corte porque faltan los parámetros de trabajo. Solicita al administrador revisar la configuración.');
    expect(screen.getByRole('checkbox', { name: /#61/ })).toBeChecked();
    expect(screen.getByRole('button', { name: 'Calcular distribución' })).toBeEnabled();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    expect(screen.queryByText(/Procesando|EN_EJECUCION|No se pudo calcular el corte/)).not.toBeInTheDocument();
    expect(screen.queryByText(technical)).not.toBeInTheDocument();
    expect(fetch.mock.calls.filter(([, options]) => options.method === 'POST')).toHaveLength(attempt);
  }
  expect(log).toHaveBeenCalledWith('No se pudo iniciar el cálculo de corte', { status: 409, code: 'CONFIG_CONFLICT', detail: technical });
  expect(fetch.mock.calls.filter(([, options]) => ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method)).every(([url]) => String(url).endsWith('/optimization/runs'))).toBe(true);
});

test('multiple orders share one named glass and retain quantities', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(json([glass]));
  render(<OptimizationPage user={operator} source={createFixturePendingOrdersSource([order(61, 2), order(16, 5)])} />);
  fireEvent.click(screen.getByLabelText('Seleccionar todos'));
  await waitFor(() => expect(document.querySelector('.first-fit-groups')).toHaveTextContent('Bronce · 5.5 mm'));
  expect(document.querySelector('.first-fit-groups')).toHaveTextContent('7 piezas · Pedidos #61 y #16');
  expect(document.querySelector('.first-fit-groups')).not.toHaveTextContent('Material #2');
});

test('recovered results resolve catalog names; ID fallback only follows a successful lookup without the ID', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(json([{ id_tipo_vidrio: 7, nombre: 'Bronce' }]));
  render(<OptimizationPage user={{ permisos: ['optimization.view'] }} result={shared.result} source={createFixturePendingOrdersSource([])} />);
  await waitFor(() => expect(document.querySelector('.first-fit-groups')).toHaveTextContent('Bronce · 6.00 mm'));
  expect(screen.getByLabelText('Vidrio del resultado')).toHaveTextContent('Bronce');
});

test.each([[], null])('catalog absence or failure does not invent a glass name (%j)', async catalog => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(catalog ? json(catalog) : json({}, 403));
  render(<OptimizationPage user={operator} source={createFixturePendingOrdersSource([order(61, 2)])} />);
  fireEvent.click(screen.getByRole('checkbox', { name: /#61/ }));
  await waitFor(() => expect(document.querySelector('.first-fit-groups')).toHaveTextContent(catalog ? 'Material #2' : 'Vidrio sin identificar'));
  if (!catalog) expect(document.querySelector('.first-fit-groups')).not.toHaveTextContent('Material #2');
});
