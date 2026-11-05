// TA-046 T01: regresión de teclado y foco en el registro de pedidos (SPEC-TA-046 §3, K-01 a K-06).
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';
import CustomPieceEditor from '../CustomPieceEditor';
import FormularioPedido from '../FormularioPedido';

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }));

const catalog = [{ id_tipo_vidrio: 7, nombre: 'Templado', estado: true, espesores_mm: [5.5, 6] }];
const observed = { fila: 4, texto: 'C,0,150', estado: 'OBSERVADO', tipo_forma: 'CIRCUNFERENCIA', cantidad: null, medidas: null, causas: ['Cantidad debe ser un entero mayor a 0'] };
const json = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = String(url);
    if (path.endsWith('/api/orders') && options.method === 'POST') return json({ id_pedido: 91 }, 201);
    if (path.includes('/api/orders/import/preview')) return json({ archivo: 'a.csv', resumen: { total: 1, validas: 0, observadas: 1 }, filas: [observed] });
    if (path.includes('/api/orders/import/validate')) return json({ archivo: 'a.csv', resumen: { total: 1, validas: 1, observadas: 0 }, filas: [{ ...observed, estado: 'VALIDO', cantidad: 2, medidas: { radius_mm: 150 }, causas: [] }] });
    if (path.includes('/api/clients')) return json([{ id_cliente: 41, nombre_razon_social: 'Cliente teclado', estado: true }]);
    return json(catalog);
  }));
});

const orderPosts = () => fetch.mock.calls.filter(([url, options]) => String(url).endsWith('/api/orders') && options?.method === 'POST');
const groups = () => [...document.querySelectorAll('.orders-material-group')];

async function setup() {
  const user = userEvent.setup();
  render(<FormularioPedido token="keyboard-token" standalone />);
  await user.type(await screen.findByLabelText('Nombre del cliente'), 'teclado{Enter}');
  await user.click(await screen.findByRole('button', { name: 'Seleccionar Cliente teclado' }));
  await user.selectOptions(screen.getByLabelText('Tipo de vidrio'), '7');
  await user.selectOptions(screen.getByLabelText('Espesor del vidrio (mm)'), '6');
  return user;
}

test('K-01: Enter en un campo guarda el pedido válido una sola vez y no envía uno inválido', async () => {
  const user = await setup();
  await user.type(screen.getByLabelText('Ancho (mm)'), '100');
  await user.type(screen.getByLabelText('Alto (mm)'), '{Enter}');
  expect(orderPosts()).toHaveLength(0);
  await user.type(screen.getByLabelText('Alto (mm)'), '200{Enter}{Enter}');
  await waitFor(() => expect(screen.getByText(/Pedido registrado correctamente/)).toBeInTheDocument());
  expect(orderPosts()).toHaveLength(1);
});

test('K-02 y K-03: al agregar una pieza o un vidrio, el foco va a su primer campo', async () => {
  const user = await setup();
  await user.click(screen.getByRole('button', { name: 'Agregar pieza' }));
  const forms = within(groups()[0]).getAllByLabelText('Forma');
  expect(forms).toHaveLength(2);
  expect(forms[1]).toHaveFocus();
  await user.click(screen.getByRole('button', { name: 'Agregar otro vidrio' }));
  expect(within(groups()[1]).getByLabelText('Tipo de vidrio')).toHaveFocus();
});

test('K-04: al eliminar una pieza o un vidrio, el foco queda en el formulario y no se pierde', async () => {
  const user = await setup();
  await user.click(screen.getByRole('button', { name: 'Agregar pieza' }));
  await user.click(within(groups()[0]).getAllByRole('button', { name: 'Eliminar pieza' })[1]);
  expect(within(groups()[0]).getByLabelText('Forma')).toHaveFocus();

  await user.click(screen.getByRole('button', { name: 'Agregar otro vidrio' }));
  await user.click(within(groups()[1]).getByRole('button', { name: 'Eliminar vidrio' }));
  expect(groups()).toHaveLength(1);
  expect(document.activeElement).not.toBe(document.body);
  expect(groups()[0].contains(document.activeElement)).toBe(true);
});

test('K-05: Enter en una fila corregida de la importación revalida', async () => {
  const user = await setup();
  await user.click(screen.getByRole('button', { name: 'Importar CSV/XLSX' }));
  await user.upload(screen.getByLabelText('Archivo CSV o XLSX'), new File(['C,0,150'], 'a.csv', { type: 'text/csv' }));
  const input = await screen.findByLabelText('Fila 4');
  await user.clear(input);
  await user.type(input, 'C,2,150{Enter}');
  expect(await screen.findByText(/1 fila · 1 válidas · 0 observadas/)).toBeInTheDocument();
  expect(orderPosts()).toHaveLength(0);
});

test('K-06: un polígono se crea y se mide solo con teclado', async () => {
  const user = userEvent.setup();
  const onGuardarVertices = vi.fn();
  render(<CustomPieceEditor onGuardarVertices={onGuardarVertices} />);
  const sides = screen.getByLabelText(/Número de lados/);
  await user.clear(sides);
  await user.type(sides, '3{Enter}');
  const lengths = screen.getAllByLabelText(/Longitud del segmento S\d en milímetros/);
  expect(lengths).toHaveLength(3);
  expect(lengths[0]).toHaveFocus();
  for (const [input, value] of [[lengths[0], '300'], [lengths[1], '400'], [lengths[2], '500']]) await user.type(input, value);
  const add = screen.getByRole('button', { name: /Agregar pieza al pedido/ });
  await waitFor(() => expect(add).toBeEnabled());
  await user.click(add);
  expect(onGuardarVertices).toHaveBeenCalledTimes(1);
  expect(onGuardarVertices.mock.calls[0][0].vertices).toHaveLength(3);
});