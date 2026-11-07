// HU-018 T03 y T04: corregir filas observadas, bloquear la confirmación y pasar las piezas al pedido.
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';
import FormularioPedido from '../FormularioPedido';

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }));

const catalog = [
  { id_tipo_vidrio: 7, nombre: 'Templado', estado: true, espesores_mm: [5.5, 6] },
  { id_tipo_vidrio: 8, nombre: 'Laminado', estado: true, espesores_mm: [4] },
];
const rectangle = { fila: 2, texto: 'R,3,800,600', estado: 'VALIDO', tipo_forma: 'RECTANGULO', cantidad: 3, medidas: { width_mm: 800, height_mm: 600 }, causas: [] };
const triangle = { fila: 3, texto: 'P,1,{{300,},{400,},{500,}}', estado: 'VALIDO', tipo_forma: 'POLIGONO_CONVEXO', cantidad: 1, medidas: { vertices_mm: [[0, 0], [300, 0], [300, 400]] }, causas: [] };
const observed = { fila: 4, texto: 'C,0,150', estado: 'OBSERVADO', tipo_forma: 'CIRCUNFERENCIA', cantidad: null, medidas: null, causas: ['Cantidad debe ser un entero mayor a 0'] };
const corrected = { ...observed, texto: 'C,2,150', estado: 'VALIDO', cantidad: 2, medidas: { radius_mm: 150 }, causas: [] };
const preview = filas => ({
  archivo: 'piezas.csv', filas,
  resumen: { total: filas.length, validas: filas.filter(row => row.estado === 'VALIDO').length, observadas: filas.filter(row => row.estado !== 'VALIDO').length },
});
const json = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
let previewData;

beforeEach(() => {
  previewData = preview([rectangle, triangle, observed]);
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = String(url);
    if (path.includes('/api/orders/import/preview')) return json(previewData);
    if (path.includes('/api/orders/import/validate')) return json(preview([rectangle, triangle, corrected]));
    if (path.endsWith('/api/orders') && options.method === 'POST') return json({ id_pedido: 91 }, 201);
    if (path.includes('/api/clients')) return json([{ id_cliente: 41, nombre_razon_social: 'Cliente importación', estado: true }]);
    return json(catalog);
  }));
});

const calls = fragment => fetch.mock.calls.filter(([url, options]) => String(url).includes(fragment) && options?.method === 'POST');
const orderPosts = () => fetch.mock.calls.filter(([url, options]) => String(url).endsWith('/api/orders') && options?.method === 'POST');
const csv = () => new File(['R,3,800,600'], 'piezas.csv', { type: 'text/csv' });

async function setup() {
  const user = userEvent.setup();
  render(<FormularioPedido token="import-token" standalone />);
  await user.type(await screen.findByLabelText('Nombre del cliente'), 'importación');
  await user.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
  await user.click(await screen.findByRole('button', { name: 'Seleccionar Cliente importación' }));
  await user.click(screen.getByRole('button', { name: 'Importar CSV/XLSX' }));
  await user.upload(screen.getByLabelText('Archivo CSV o XLSX'), csv());
  await screen.findByRole('table', { name: 'Vista previa del archivo' });
  return user;
}

async function chooseMaterial(user) {
  await user.selectOptions(screen.getByLabelText('Tipo de vidrio para estas piezas'), '7');
  await user.selectOptions(screen.getByLabelText('Espesor (mm)'), '6');
}

const addButton = () => screen.getByRole('button', { name: 'Agregar al pedido' });

test('CA-07: con una fila observada no se puede agregar, aunque haya material, y se dice cuántas faltan', async () => {
  const user = await setup();
  expect(addButton()).toBeDisabled();
  expect(addButton()).toHaveAccessibleDescription('Corrige 1 fila observada para continuar.');
  await chooseMaterial(user);
  expect(addButton()).toBeDisabled();
  expect(screen.getAllByText(/^Pieza \d+$/)).toHaveLength(1);
});

test('CA-11: la fila corregida se revalida sin volver a subir el archivo y sin perder las demás', async () => {
  const user = await setup();
  const input = screen.getByLabelText('Fila 4');
  expect(input).toHaveValue('C,0,150');
  expect(input).toHaveAccessibleDescription('Cantidad debe ser un entero mayor a 0');
  await user.clear(input);
  await user.type(input, 'C,2,150');
  await user.click(screen.getByRole('button', { name: 'Revalidar' }));

  expect(await screen.findByText(/3 filas · 3 válidas · 0 observadas/)).toBeInTheDocument();
  expect(screen.queryByRole('group', { name: 'Corrige las filas observadas' })).not.toBeInTheDocument();
  expect(calls('/api/orders/import/preview')).toHaveLength(1);
  const [[, options]] = calls('/api/orders/import/validate');
  expect(JSON.parse(options.body)).toEqual({
    archivo: 'piezas.csv',
    filas: [{ fila: 2, texto: 'R,3,800,600' }, { fila: 3, texto: 'P,1,{{300,},{400,},{500,}}' }, { fila: 4, texto: 'C,2,150' }],
  });
  expect(addButton()).toBeDisabled();
  expect(addButton()).toHaveAccessibleDescription('Elige el tipo de vidrio y el espesor.');
  await chooseMaterial(user);
  expect(addButton()).toBeEnabled();
});

test('CA-12: las piezas pasan al grupo del material y el pedido se registra una sola vez con un doble clic', async () => {
  previewData = preview([rectangle, triangle, corrected]);
  const user = await setup();
  expect(screen.queryByText('Falta seleccionar cliente')).not.toBeInTheDocument();
  await chooseMaterial(user);
  await user.click(addButton());

  expect(screen.queryByRole('region', { name: 'Importar piezas desde archivo' })).not.toBeInTheDocument();
  expect(screen.getByText('Se agregaron 3 piezas del archivo al pedido.')).toBeInTheDocument();
  const groups = [...document.querySelectorAll('.orders-material-group')];
  expect(groups).toHaveLength(1);
  expect(within(groups[0]).getByRole('button', { name: /Templado · 6 mm/ })).toHaveTextContent('6 piezas');
  expect(within(groups[0]).getByText('✓ Figura configurada')).toBeInTheDocument();
  expect(orderPosts()).toHaveLength(0);

  const save = screen.getByRole('button', { name: 'Guardar pedido' });
  expect(save).toBeEnabled();
  fireEvent.click(save);
  fireEvent.click(save);
  await waitFor(() => expect(screen.getByText(/Pedido registrado correctamente/)).toBeInTheDocument());

  const orders = orderPosts();
  expect(orders).toHaveLength(1);
  expect(JSON.parse(orders[0][1].body)).toEqual({
    id_cliente: 41,
    piezas: [
      { tipo_forma: 'RECTANGULO', id_tipo_vidrio: 7, espesor_mm: 6, cantidad: 3, width_mm: 800, height_mm: 600 },
      { tipo_forma: 'POLIGONO_CONVEXO', id_tipo_vidrio: 7, espesor_mm: 6, cantidad: 1, vertices_mm: [[0, 0], [300, 0], [300, 400]] },
      { tipo_forma: 'CIRCUNFERENCIA', id_tipo_vidrio: 7, espesor_mm: 6, cantidad: 2, radius_mm: 150 },
    ],
  });
});

test('el polígono importado se abre en el editor de figuras', async () => {
  previewData = preview([triangle]);
  const user = await setup();
  await chooseMaterial(user);
  await user.click(addButton());
  await user.click(screen.getByRole('button', { name: 'Editar figura' }));
  expect(screen.getByRole('dialog', { name: 'Dibujar Polígono Convexo' })).toBeInTheDocument();
});

async function setupValidOrderWithImport() {
  const user = userEvent.setup();
  render(<FormularioPedido token="import-token" standalone />);
  await user.type(await screen.findByLabelText('Nombre del cliente'), 'importación');
  await user.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
  await user.click(await screen.findByRole('button', { name: 'Seleccionar Cliente importación' }));
  const row = screen.getByText('Pieza 1', { selector: 'strong' }).closest('.orders-piece');
  const group = row.closest('.orders-material-group');
  await user.selectOptions(within(group).getByLabelText('Tipo de vidrio'), '7');
  await user.selectOptions(within(group).getByLabelText('Espesor del vidrio (mm)'), '6');
  await user.type(within(row).getByLabelText('Ancho (mm)'), '800');
  await user.type(within(row).getByLabelText('Alto (mm)'), '600');
  expect(screen.getByRole('button', { name: 'Guardar pedido' })).toBeEnabled();
  await user.click(screen.getByRole('button', { name: 'Importar CSV/XLSX' }));
  return user;
}

test('una importación observada bloquea guardar un pedido válido hasta revalidar', async () => {
  const user = await setupValidOrderWithImport();
  previewData = preview([observed]);
  await user.upload(screen.getByLabelText('Archivo CSV o XLSX'), csv());
  await screen.findByLabelText('Fila 4');
  const save = screen.getByRole('button', { name: 'Guardar pedido' });
  expect(save).toBeDisabled();
  expect(save).toHaveAccessibleDescription('Corrige las filas observadas antes de confirmar el pedido.');
  fireEvent.click(save);
  expect(orderPosts()).toHaveLength(0);
  await user.clear(screen.getByLabelText('Fila 4'));
  await user.type(screen.getByLabelText('Fila 4'), 'C,2,150');
  await user.click(screen.getByRole('button', { name: 'Revalidar' }));
  await waitFor(() => expect(save).toBeEnabled());
});

test('cerrar una importación observada descarta el bloqueo del pedido', async () => {
  const user = await setupValidOrderWithImport();
  previewData = preview([observed]);
  await user.upload(screen.getByLabelText('Archivo CSV o XLSX'), csv());
  await screen.findByLabelText('Fila 4');
  expect(screen.getByRole('button', { name: 'Guardar pedido' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Cerrar importación' }));
  expect(screen.getByRole('button', { name: 'Guardar pedido' })).toBeEnabled();
});

test('una importación válida abierta no bloquea guardar un pedido válido', async () => {
  const user = await setupValidOrderWithImport();
  previewData = preview([rectangle]);
  await user.upload(screen.getByLabelText('Archivo CSV o XLSX'), csv());
  await screen.findByRole('table', { name: 'Vista previa del archivo' });
  expect(screen.getByRole('button', { name: 'Guardar pedido' })).toBeEnabled();
});
