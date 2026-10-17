import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import NuevoPedido from '../NuevoPedido';

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }));
const materials = [
  { id_tipo_vidrio: 7, nombre: 'Material de prueba', estado: true, espesores_mm: [5.5, 6] },
  { id_tipo_vidrio: 8, nombre: 'Otro material', estado: true, espesores_mm: [4] },
  { id_tipo_vidrio: 9, nombre: 'Inactivo', estado: false, espesores_mm: [6] },
];
const client = { id_cliente: 41, nombre_razon_social: 'Vidrios Norte', estado: true };
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
const saveButton = () => screen.getByRole('button', { name: 'Guardar pedido' });
const posts = () => fetch.mock.calls.filter(([, options]) => options.method === 'POST');

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => Promise.resolve(response(
    url.includes('/api/clients') ? [client] : materials,
  ))));
});
afterEach(() => vi.unstubAllGlobals());

async function setup(selectClient = true) {
  render(<NuevoPedido token="test-token" />);
  await screen.findByText('Falta seleccionar cliente');
  if (selectClient) {
    fireEvent.change(screen.getByLabelText('Nombre del cliente'), { target: { value: 'Norte' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
    fireEvent.click(await screen.findByRole('button', { name: 'Seleccionar Vidrios Norte' }));
  }
  return userEvent.setup();
}

async function addPiece(shape = 'RECTANGULO', material = '7', thickness = '5.5') {
  // Reuse the initial piece; subsequent pieces share the matching group.
  let group = [...document.querySelectorAll('.orders-material-group')].find(node =>
    within(node).getByLabelText('Tipo de vidrio').value === material &&
    within(node).getByLabelText('Espesor del vidrio (mm)').value === thickness);
  if (group) {
    fireEvent.click(within(group).getByRole('button', { name: 'Agregar pieza', exact: true }));
  } else {
    const groups = [...document.querySelectorAll('.orders-material-group')];
    group = groups.find(node => within(node).getByLabelText('Tipo de vidrio').value === '');
    if (!group) {
      fireEvent.click(screen.getByRole('button', { name: 'Agregar otro material' }));
      group = [...document.querySelectorAll('.orders-material-group')].at(-1);
    }
    fireEvent.change(within(group).getByLabelText('Tipo de vidrio'), { target: { value: material } });
    fireEvent.change(within(group).getByLabelText('Espesor del vidrio (mm)'), { target: { value: thickness } });
  }
  const row = within(group).getAllByText(/^Pieza [0-9]+$/).at(-1).closest('.orders-piece');
  const fields = within(row);
  fireEvent.change(fields.getByLabelText('Forma'), { target: { value: shape } });
  if (shape === 'RECTANGULO') {
    fireEvent.change(fields.getByLabelText('Ancho (mm)'), { target: { value: '1000' } });
    fireEvent.change(fields.getByLabelText('Alto (mm)'), { target: { value: '500' } });
  } else if (shape === 'CIRCUNFERENCIA') {
    fireEvent.change(fields.getByLabelText('Radio (mm)'), { target: { value: '250' } });
  }
  return fields;
}

async function validPolygon(user) {
  const canvas = screen.getByRole('img', { name: /Lienzo del dibujo original/ });
  for (const [x, y] of [[100, 100], [400, 100], [400, 300], [100, 300]]) {
    await user.pointer({ target: canvas, keys: '[MouseLeft]', coords: { clientX: x, clientY: y } });
  }
  await user.click(screen.getByRole('button', { name: 'Cerrar polígono' }));
  expect(screen.getByRole('button', { name: 'Agregar pieza al pedido' })).toBeDisabled();
  for (const [index, value] of [300, 200, 300, 200].entries()) {
    fireEvent.change(screen.getByRole('spinbutton', { name: `Longitud del segmento S${index + 1} en milímetros` }), { target: { value: String(value) } });
  }
  expect(screen.getByText('✓ Geometría validada y lista.')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Agregar pieza al pedido' }));
}

describe('HU-012 T03 con HU-006 multimaterial y HU-007 real', () => {
  test('guarda las tres formas y cantidades con cliente; excluye rawState', async () => {
    const user = await setup();
    const polygon = await addPiece('POLIGONO_CONVEXO');
    fireEvent.change(polygon.getByLabelText('Cantidad'), { target: { value: '3' } });
    await validPolygon(user);
    expect(screen.queryByRole('img', { name: /Lienzo del dibujo original/ })).not.toBeInTheDocument();
    const rectangle = await addPiece('RECTANGULO', '8', '4');
    fireEvent.change(rectangle.getByLabelText('Cantidad'), { target: { value: '2' } });
    await addPiece('CIRCUNFERENCIA', '7', '6');
    expect(posts()).toHaveLength(0);
    fetch.mockResolvedValueOnce(response({ id_pedido: 44, id_cliente: 41, estado: 'PENDIENTE' }, 201));
    await user.click(saveButton());
    await screen.findByText(/ID del pedido: 44/);
    expect(posts()).toHaveLength(1);
    const [url, options] = posts()[0];
    expect(url).toMatch(/\/api\/orders$/);
    expect(options.headers.Authorization).toBe('Bearer test-token');
    expect(JSON.parse(options.body)).toEqual({ id_cliente: 41, piezas: [
      { id_tipo_vidrio: 7, espesor_mm: 5.5, tipo_forma: 'POLIGONO_CONVEXO', cantidad: 3, vertices_mm: expect.any(Array) },
      { id_tipo_vidrio: 8, espesor_mm: 4, tipo_forma: 'RECTANGULO', cantidad: 2, width_mm: 1000, height_mm: 500 },
      { id_tipo_vidrio: 7, espesor_mm: 6, tipo_forma: 'CIRCUNFERENCIA', cantidad: 1, radius_mm: 250 },
    ] });
    expect(screen.queryByText('Pieza 1')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Cliente seleccionado')).not.toBeInTheDocument();
    expect(saveButton()).toBeDisabled();
  }, 15000);

  test.each([['7', '6'], ['8', '4']])('permite la pareja %s/%s en otro grupo sin POST anticipado', async (material, thickness) => {
    await setup();
    await addPiece();
    await addPiece('CIRCUNFERENCIA', material, thickness);
    expect(screen.getByText('Pieza 1')).toBeVisible();
    expect(screen.getByText('Pieza 2')).toBeVisible();
    expect(saveButton()).toBeEnabled();
    expect(posts()).toHaveLength(0);
    fireEvent.click(screen.getAllByRole('button', { name: 'Eliminar material' })[1]);
    expect(saveButton()).toBeEnabled();
  });

  test('bloquea cantidades decimales y medidas no positivas', async () => {
    await setup();
    const fields = await addPiece();
    fireEvent.change(fields.getByLabelText('Cantidad'), { target: { value: '1.5' } });
    expect(saveButton()).toBeDisabled();
    fireEvent.change(fields.getByLabelText('Cantidad'), { target: { value: '1' } });
    for (const value of ['-1', '0']) {
      fireEvent.change(fields.getByLabelText('Ancho (mm)'), { target: { value } });
      expect(saveButton()).toBeDisabled();
    }
    expect(screen.queryByRole('option', { name: 'Triángulo' })).not.toBeInTheDocument();
    expect(posts()).toHaveLength(0);
  });

  test('catálogo activo y geometría válida requeridos; conserva la pieza mínima', async () => {
    const user = await setup();
    await addPiece('POLIGONO_CONVEXO');
    expect(screen.queryByRole('option', { name: 'Inactivo' })).not.toBeInTheDocument();
    expect(saveButton()).toBeDisabled();
    await validPolygon(user);
    expect(saveButton()).toBeEnabled();
    expect(posts()).toHaveLength(0);
    expect(screen.getByRole('button', { name: 'Eliminar pieza' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Eliminar pieza' }));
    expect(screen.getByText('Pieza 1')).toBeVisible();
    expect(saveButton()).toBeEnabled();
  });

  test('bloquea doble envío y edición mientras guarda', async () => {
    await setup();
    await addPiece();
    await addPiece();
    let resolve;
    fetch.mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
    fireEvent.click(saveButton());
    fireEvent.click(screen.getByRole('button', { name: 'Guardando…' }));
    expect(posts()).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Guardando…' })).toBeDisabled();
    expect(screen.getAllByLabelText('Tipo de vidrio')[0]).toBeDisabled();
    expect(screen.getAllByRole('button', { name: 'Eliminar pieza' })[0]).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancelar', exact: true })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cambiar cliente' })).toBeDisabled();
    expect(JSON.parse(posts()[0][1].body).piezas).toHaveLength(2);
    await act(async () => resolve(response({ id_pedido: 42, id_cliente: 41 }, 201)));
    expect(screen.getByText(/ID del pedido: 42/)).toBeVisible();
  });

  test.each([401, 403, 422, 500, 'network'])('fallo %s conserva cliente y piezas; reintento idéntico', async (status) => {
    await setup();
    await addPiece();
    if (status === 'network') fetch.mockRejectedValueOnce(new TypeError('private error'));
    else fetch.mockResolvedValueOnce(response({ detail: 'No se pudo guardar' }, status));
    fireEvent.click(saveButton());
    expect(await screen.findByRole('alert')).toHaveTextContent('Las piezas y el cliente se conservan');
    expect(screen.getByText('Pieza 1')).toBeVisible();
    expect(screen.getByLabelText('Cliente seleccionado')).toHaveTextContent('Vidrios Norte');
    expect(saveButton()).toBeEnabled();
    fetch.mockResolvedValueOnce(response({ id_pedido: 43, id_cliente: 41 }, 201));
    fireEvent.click(saveButton());
    await screen.findByText(/ID del pedido: 43/);
    expect(posts()[0][1].body).toBe(posts()[1][1].body);
  });

  test('error de catálogo permite reintentar sin valores estáticos', async () => {
    fetch.mockRejectedValueOnce(new TypeError('offline'));
    render(<NuevoPedido token="test-token" />);
    await screen.findByRole('alert');
    expect(saveButton()).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar catálogo' }));
    await screen.findByText('Falta seleccionar cliente');
    fireEvent.change(screen.getByLabelText('Nombre del cliente'), { target: { value: 'Norte' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
    fireEvent.click(await screen.findByRole('button', { name: 'Seleccionar Vidrios Norte' }));
    await addPiece();
    expect(screen.getByRole('option', { name: 'Material de prueba' })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  test('no guarda sin cliente, permite cambiarlo conservando las piezas', async () => {
    await setup(false);
    expect(screen.queryByText('Pieza 1')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Agregar otro material' })).not.toBeInTheDocument();
    expect(saveButton()).toBeDisabled();
    fireEvent.click(saveButton());
    expect(posts()).toHaveLength(0);
    fireEvent.change(screen.getByLabelText('Nombre del cliente'), { target: { value: 'Norte' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
    fireEvent.click(await screen.findByRole('button', { name: 'Seleccionar Vidrios Norte' }));
    await addPiece();
    expect(saveButton()).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar cliente' }));
    expect(saveButton()).toBeDisabled();
    expect(screen.getByText('Falta seleccionar cliente')).toBeVisible();
    fetch.mockResolvedValueOnce(response([{ ...client, id_cliente: 42, nombre_razon_social: 'Otro cliente' }]));
    fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
    fireEvent.click(await screen.findByRole('button', { name: 'Seleccionar Otro cliente' }));
    expect(screen.getByLabelText('Ancho (mm)')).toHaveValue(1000);
    expect(screen.getByLabelText('Tipo de vidrio')).toHaveValue('7');
    fetch.mockResolvedValueOnce(response({ id_pedido: 45, id_cliente: 42 }, 201));
    fireEvent.click(saveButton());
    await screen.findByText(/ID del pedido: 45/);
    expect(JSON.parse(posts()[0][1].body).id_cliente).toBe(42);
  });
});
