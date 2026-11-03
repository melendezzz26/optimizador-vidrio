// HU-018 T02: cargar el archivo, ver la vista previa y elegir el material sin registrar el pedido.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';
import FormularioPedido from '../FormularioPedido';

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }));

const catalog = [
  { id_tipo_vidrio: 7, nombre: 'Templado', estado: true, espesores_mm: [5.5, 6] },
  { id_tipo_vidrio: 8, nombre: 'Laminado', estado: true, espesores_mm: [4] },
];
const PREVIEW = {
  archivo: 'piezas.csv',
  resumen: { total: 3, validas: 2, observadas: 1 },
  filas: [
    { fila: 2, texto: 'R,3,800,600', estado: 'VALIDO', tipo_forma: 'RECTANGULO', cantidad: 3, medidas: { width_mm: 800, height_mm: 600 }, causas: [] },
    { fila: 3, texto: 'P,1,{{300,},{400,},{500,}}', estado: 'VALIDO', tipo_forma: 'POLIGONO_CONVEXO', cantidad: 1, medidas: { vertices_mm: [[0, 0], [300, 0], [300, 400]] }, causas: [] },
    { fila: 4, texto: 'C,0,150', estado: 'OBSERVADO', tipo_forma: 'CIRCUNFERENCIA', cantidad: null, medidas: null, causas: ['Cantidad debe ser un entero mayor a 0'] },
  ],
};
const json = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
let previewResponse;

beforeEach(() => {
  previewResponse = json(PREVIEW);
  vi.stubGlobal('fetch', vi.fn(async url => (String(url).includes('/api/orders/import/preview') ? previewResponse : json(catalog))));
});

const csv = () => new File(['R,3,800,600\nC,0,150'], 'piezas.csv', { type: 'text/csv' });
const importCalls = () => fetch.mock.calls.filter(([url]) => String(url).includes('/api/orders/import'));

async function openImport() {
  const user = userEvent.setup();
  render(<FormularioPedido token="import-token" standalone />);
  await user.click(await screen.findByRole('button', { name: 'Importar CSV/XLSX' }));
  return user;
}

test('CA-05: el archivo se previsualiza con su resumen y sus filas, y después se elige el material', async () => {
  const user = await openImport();
  const panel = screen.getByRole('region', { name: 'Importar piezas desde archivo' });
  expect(within(panel).queryByLabelText('Tipo de vidrio para estas piezas')).not.toBeInTheDocument();

  await user.upload(within(panel).getByLabelText('Archivo CSV o XLSX'), csv());

  const table = await within(panel).findByRole('table', { name: 'Vista previa del archivo' });
  expect(within(panel).getByText(/3 filas · 2 válidas · 1 observadas/)).toBeInTheDocument();
  const rows = within(table).getAllByRole('row').slice(1).map(row => [...row.querySelectorAll('th, td')].map(cell => cell.textContent));
  expect(rows).toEqual([
    ['2', 'Rectángulo', '3', '800 × 600 mm', 'Válido', '—'],
    ['3', 'Polígono convexo', '1', '3 lados', 'Válido', '—'],
    ['4', 'Círculo', '—', '—', 'Observado', 'Cantidad debe ser un entero mayor a 0'],
  ]);

  const [[url, options]] = importCalls();
  expect(url).toMatch(/\/api\/orders\/import\/preview$/);
  expect(options.method).toBe('POST');
  expect(options.body).toBeInstanceOf(FormData);
  expect(options.body.get('archivo').name).toBe('piezas.csv');
  expect(options.headers).toEqual({ Authorization: 'Bearer import-token' });

  await user.selectOptions(within(panel).getByLabelText('Tipo de vidrio para estas piezas'), '7');
  const thickness = within(panel).getByLabelText('Espesor (mm)');
  expect(within(thickness).getAllByRole('option').map(option => option.textContent)).toEqual(['Espesor…', '5.5 mm', '6 mm']);
  await user.selectOptions(thickness, '6');
  expect(thickness).toHaveValue('6');

  expect(fetch.mock.calls.some(([url, options]) => String(url).endsWith('/api/orders') && options?.method === 'POST')).toBe(false);
});

test('un error del archivo completo se muestra con el mensaje del servidor y sin tabla', async () => {
  previewResponse = json({ detail: 'Selecciona un archivo .csv o .xlsx.' }, 422);
  const user = await openImport();
  await user.upload(screen.getByLabelText('Archivo CSV o XLSX'), csv());
  const alert = await screen.findByRole('alert');
  expect(alert).toHaveTextContent('No se pudo importar el archivo');
  expect(alert).toHaveTextContent('Selecciona un archivo .csv o .xlsx.');
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});

test('un archivo de más de 1 MB muestra el límite', async () => {
  previewResponse = json({ detail: 'El archivo supera el tamaño máximo de 1 MB.' }, 413);
  const user = await openImport();
  await user.upload(screen.getByLabelText('Archivo CSV o XLSX'), csv());
  expect(await screen.findByRole('alert')).toHaveTextContent('El archivo supera el tamaño máximo de 1 MB.');
});

test('cerrar la importación descarta la vista previa y devuelve el foco al botón', async () => {
  const user = await openImport();
  await user.upload(screen.getByLabelText('Archivo CSV o XLSX'), csv());
  await screen.findByRole('table');
  await user.click(screen.getByRole('button', { name: 'Cerrar importación' }));
  expect(screen.queryByRole('region', { name: 'Importar piezas desde archivo' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Importar CSV/XLSX' })).toHaveFocus();
  await user.click(screen.getByRole('button', { name: 'Importar CSV/XLSX' }));
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});