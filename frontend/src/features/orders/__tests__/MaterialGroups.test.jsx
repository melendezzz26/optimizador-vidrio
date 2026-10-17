import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';
import FormularioPedido from '../FormularioPedido';

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }));

const catalog = [
  { id_tipo_vidrio: 7, nombre: 'Templado', estado: true, espesores_mm: [5.5, 6] },
  { id_tipo_vidrio: 8, nombre: 'Laminado', estado: true, espesores_mm: [4] },
];
const response = data => ({ ok: true, status: 200, json: async () => data });
const groups = () => [...document.querySelectorAll('.orders-material-group')];
const change = (input, value) => fireEvent.change(input, { target: { value: String(value) } });
const save = () => screen.getByRole('button', { name: 'Guardar pedido' });
const post = () => fetch.mock.calls.find(([, options]) => options.method === 'POST');

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    if (options.method === 'POST') return response({ id_pedido: 91 });
    if (String(url).includes('/api/clients')) return response([{ id_cliente: 41, nombre_razon_social: 'Cliente grupos', estado: true }]);
    return response(catalog);
  }));
});

async function selectClient() {
  change(screen.getByLabelText('Nombre del cliente'), 'grupos');
  fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
  fireEvent.click(await screen.findByRole('button', { name: 'Seleccionar Cliente grupos' }));
}

async function setup() {
  const view = render(<FormularioPedido token="groups-token" standalone />);
  await screen.findByText('Falta seleccionar cliente');
  await selectClient();
  return view;
}

function material(group, id = 7, thickness = 5.5) {
  change(within(group).getByLabelText('Tipo de vidrio'), id);
  change(within(group).getByLabelText('Espesor del vidrio (mm)'), thickness);
}

function rectangle(row, width = 100, height = 50, quantity = 1) {
  change(within(row).getByLabelText('Ancho (mm)'), width);
  change(within(row).getByLabelText('Alto (mm)'), height);
  change(within(row).getByLabelText('Cantidad'), quantity);
}

test('la pieza inicial permanece bloqueada hasta completar material y espesor', async () => {
  await setup();
  expect(groups()).toHaveLength(1);
  expect(screen.getAllByText(/^Pieza \d+$/)).toHaveLength(1);
  for (const label of ['Forma', 'Cantidad', 'Ancho (mm)', 'Alto (mm)']) expect(screen.getByLabelText(label)).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Agregar pieza' })).toBeDisabled();
  change(screen.getByLabelText('Tipo de vidrio'), 7);
  expect(screen.getByLabelText('Espesor del vidrio (mm)')).toBeEnabled();
  expect(screen.getByLabelText('Cantidad')).toBeDisabled();
  change(screen.getByLabelText('Espesor del vidrio (mm)'), 5.5);
  expect(screen.getByLabelText('Cantidad')).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Agregar pieza' })).toBeEnabled();
  expect(save()).toBeDisabled();
});

test('distintas formas y cantidades comparten material; un segundo grupo persiste otra combinación', async () => {
  await setup();
  material(groups()[0]);
  rectangle(groups()[0].querySelector('.orders-piece'), 100, 50, 2);
  fireEvent.click(screen.getByRole('button', { name: 'Agregar pieza' }));
  const circle = groups()[0].querySelectorAll('.orders-piece')[1];
  change(within(circle).getByLabelText('Forma'), 'CIRCUNFERENCIA');
  change(within(circle).getByLabelText('Radio (mm)'), 25);
  change(within(circle).getByLabelText('Cantidad'), 3);
  expect(screen.getAllByLabelText('Tipo de vidrio')).toHaveLength(1);
  fireEvent.click(screen.getByRole('button', { name: 'Agregar otro vidrio' }));
  const previous = within(groups()[0]).getByRole('button', { name: /Templado · 5.5 mm.*5 piezas.*Completo/ });
  expect(previous).toHaveAttribute('aria-expanded', 'false');
  expect(within(groups()[0]).getByLabelText('Radio (mm)')).not.toBeVisible();
  fireEvent.click(previous);
  expect(previous).toHaveAttribute('aria-expanded', 'true');
  expect(within(groups()[0]).getByLabelText('Radio (mm)')).toHaveValue(25);
  fireEvent.click(previous);
  expect(within(groups()[1]).getByLabelText('Cantidad')).toBeDisabled();
  expect(save()).toBeDisabled();
  material(groups()[1], 8, 4);
  rectangle(groups()[1], 200, 80, 4);
  fireEvent.click(save());
  await screen.findByText(/ID del pedido: 91/);
  expect(JSON.parse(post()[1].body)).toEqual({ id_cliente: 41, piezas: [
    { tipo_forma: 'RECTANGULO', id_tipo_vidrio: 7, espesor_mm: 5.5, cantidad: 2, width_mm: 100, height_mm: 50 },
    { tipo_forma: 'CIRCUNFERENCIA', id_tipo_vidrio: 7, espesor_mm: 5.5, cantidad: 3, radius_mm: 25 },
    { tipo_forma: 'RECTANGULO', id_tipo_vidrio: 8, espesor_mm: 4, cantidad: 4, width_mm: 200, height_mm: 80 },
  ] });
  await selectClient();
  expect(groups()).toHaveLength(1);
  expect(screen.getByLabelText('Tipo de vidrio')).toHaveValue('');
  expect(screen.getByLabelText('Ancho (mm)')).toHaveValue(null);
});

test('cambiar material limpia espesor y bloquea todas las piezas sin perder sus medidas', async () => {
  await setup();
  material(groups()[0]);
  rectangle(groups()[0]);
  fireEvent.click(screen.getByRole('button', { name: 'Agregar pieza' }));
  rectangle(groups()[0].querySelectorAll('.orders-piece')[1], 200, 80, 2);
  change(screen.getByLabelText('Tipo de vidrio'), 8);
  expect(screen.getByLabelText('Espesor del vidrio (mm)')).toHaveValue('');
  screen.getAllByLabelText('Cantidad').forEach(input => expect(input).toBeDisabled());
  expect(save()).toBeDisabled();
  change(screen.getByLabelText('Espesor del vidrio (mm)'), 4);
  expect(screen.getAllByLabelText('Ancho (mm)').map(input => Number(input.value))).toEqual([100, 200]);
  fireEvent.click(save());
  await screen.findByText(/ID del pedido: 91/);
  expect(JSON.parse(post()[1].body).piezas.map(piece => [piece.id_tipo_vidrio, piece.espesor_mm])).toEqual([[8, 4], [8, 4]]);
});

test('impide repetir una combinación y libera su espesor al eliminar el grupo', async () => {
  await setup();
  material(groups()[0]);
  fireEvent.click(screen.getByRole('button', { name: 'Agregar otro vidrio' }));
  change(within(groups()[1]).getByLabelText('Tipo de vidrio'), 7);
  const thickness = within(groups()[1]).getByLabelText('Espesor del vidrio (mm)');
  expect(within(thickness).getByRole('option', { name: '5.5 mm (En uso)' })).toBeDisabled();
  change(thickness, 6);
  fireEvent.click(screen.getByRole('button', { name: 'Agregar otro vidrio' }));
  expect(within(groups()[2]).getByRole('option', { name: 'Templado (En uso)' })).toBeDisabled();
  fireEvent.click(within(groups()[0]).getByRole('button', { name: 'Eliminar vidrio' }));
  expect(within(groups()[1]).getByRole('option', { name: 'Templado' })).toBeEnabled();
  change(within(groups()[1]).getByLabelText('Tipo de vidrio'), 7);
  expect(within(groups()[1]).getByRole('option', { name: '5.5 mm' })).toBeEnabled();
});

test('rerender y cambio de cliente conservan el borrador sin recargar el catálogo', async () => {
  const view = await setup();
  material(groups()[0]);
  rectangle(groups()[0], 123, 45, 2);
  view.rerender(<FormularioPedido token="groups-token" standalone toolbar={<p>Barra actualizada</p>} onSuccess={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Cambiar cliente' }));
  expect(save()).toBeDisabled();
  await selectClient();
  expect(screen.getByLabelText('Ancho (mm)')).toHaveValue(123);
  expect(screen.getByLabelText('Cantidad')).toHaveValue(2);
  expect(fetch.mock.calls.filter(([url]) => String(url).includes('/tipos-vidrio'))).toHaveLength(1);
});

test('un catálogo fallido se recupera conservando cliente y creando la pieza inicial bloqueada', async () => {
  fetch.mockRejectedValueOnce(new TypeError('offline'));
  render(<FormularioPedido token="groups-token" standalone />);
  await screen.findByRole('alert');
  await selectClient();
  expect(save()).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Reintentar catálogo' }));
  await screen.findByText('Pieza 1');
  expect(screen.getByLabelText('Cliente seleccionado')).toHaveTextContent('Cliente grupos');
  expect(screen.getByLabelText('Cantidad')).toBeDisabled();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('un pedido optimizado permite inspeccionar el polígono sin editarlo', async () => {
  fetch.mockImplementation(async url => response(String(url).includes('/tipos-vidrio') ? catalog : {
    estado: 'OPTIMIZADO', piezas: [{ id_tipo_vidrio: 7, espesor_mm: 5.5, cantidad: 1,
      tipo_forma: 'POLIGONO_CONVEXO', geometria: { vertices_mm: [[0, 0], [100, 0], [100, 50], [0, 50]] } }],
  }));
  const user = userEvent.setup();
  render(<FormularioPedido token="groups-token" idPedido={91} mode="view" />);
  await user.click(await screen.findByRole('button', { name: /Templado · 5.5 mm.*1 pieza.*Completo/ }));
  await user.click(screen.getByRole('button', { name: 'Ver figura' }));
  const dialog = screen.getByRole('dialog', { name: 'Dibujar Polígono Convexo' });
  expect(within(dialog).getByLabelText('Longitud del segmento S1 en milímetros')).toBeDisabled();
  expect(within(dialog).getByRole('button', { name: 'Agregar pieza al pedido' })).toBeDisabled();
  await user.keyboard('{Escape}');
  expect(screen.getByRole('button', { name: 'Ver figura' })).toHaveFocus();
  expect(fetch.mock.calls.every(([, options]) => options.method !== 'PUT')).toBe(true);
});
