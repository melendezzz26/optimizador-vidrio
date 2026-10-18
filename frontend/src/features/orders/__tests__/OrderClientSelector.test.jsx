import { useState } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import OrderClientSelector from '../OrderClientSelector';

const client = { id_cliente: 41, nombre_razon_social: 'Vidrios Norte', tipo_documento: 'TEST', numero_documento: 'DEMO-003', estado: false };
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
function Harness() {
  const [selected, setSelected] = useState(null);
  return <OrderClientSelector value={selected} onChange={setSelected} token="test-token" />;
}
beforeEach(() => vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response([client]))));
afterEach(() => vi.unstubAllGlobals());

test.each(['query', 'document'])('busca explícitamente por %s y selecciona por teclado', async (mode) => {
  const user = userEvent.setup();
  render(<Harness />);
  expect(screen.getByText(/Buscar por nombre, DNI o RUC/)).toBeVisible();
  expect(screen.getByRole('option', { name: 'DNI o RUC' })).toBeInTheDocument();
  expect(screen.queryByText('Documento exacto')).not.toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: 'Buscar', exact: true })).toBeDisabled();
  await user.selectOptions(screen.getByLabelText('Buscar por'), mode);
  const input = screen.getByLabelText(mode === 'query' ? 'Nombre del cliente' : 'Documento del cliente');
  await user.type(input, mode === 'query' ? 'Norte' : 'DEMO-003');
  expect(fetch).not.toHaveBeenCalled();
  await user.keyboard('{Enter}');
  const select = await screen.findByRole('button', { name: 'Seleccionar Vidrios Norte' });
  expect(fetch.mock.calls[0][0]).toContain(mode === 'query' ? '?query=Norte' : '?document=DEMO-003');
  expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer test-token');
  expect(screen.getByText('TEST — DEMO-003 · Inactivo')).toBeVisible();
  select.focus();
  await user.keyboard('{Enter}');
  expect(screen.getByLabelText('Cliente seleccionado')).toHaveTextContent('Vidrios Norte');
  expect(screen.getByLabelText('Cliente seleccionado')).toHaveFocus();
  await user.click(screen.getByRole('button', { name: 'Cambiar cliente' }));
  expect(await screen.findByLabelText(mode === 'query' ? 'Nombre del cliente' : 'Documento del cliente')).toBeVisible();
});

test('muestra carga, vacío, fallo controlado y permite reintentar', async () => {
  render(<Harness />);
  fireEvent.change(screen.getByLabelText('Nombre del cliente'), { target: { value: 'Norte' } });
  let resolve;
  fetch.mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
  fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
  expect(screen.getByText('Buscando clientes…')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Buscar', exact: true })).toBeDisabled();
  await act(async () => resolve(response([])));
  expect(screen.getByText('No se encontraron clientes')).toBeVisible();
  fetch.mockRejectedValueOnce(new Error('private network failure'));
  fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Revisa la conexión');
  expect(screen.getByRole('alert')).not.toHaveTextContent('private');
  fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
  expect(await screen.findByText('Vidrios Norte')).toBeVisible();
});

test('registra con campos opcionales y selecciona automáticamente; doble envío bloqueado', async () => {
  render(<Harness />);
  fireEvent.click(screen.getByRole('button', { name: 'Registrar nuevo cliente' }));
  expect(screen.getByLabelText('Nombre o razón social')).toHaveFocus();
  expect(screen.getByRole('button', { name: 'Registrar y seleccionar' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Nombre o razón social'), { target: { value: ' Vidrios Norte ' } });
  let resolve;
  fetch.mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
  fireEvent.click(screen.getByRole('button', { name: 'Registrar y seleccionar' }));
  fireEvent.click(screen.getByRole('button', { name: 'Registrando cliente…' }));
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText('Nombre o razón social')).toBeDisabled();
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ nombre_razon_social: 'Vidrios Norte', tipo_documento: null, numero_documento: null, telefono: null });
  await act(async () => resolve(response(client, 201)));
  expect(screen.getByText('Cliente registrado y seleccionado para este pedido.')).toBeVisible();
  expect(screen.getByLabelText('Cliente seleccionado')).toHaveTextContent('Vidrios Norte');
});

test.each([409, 422, 500])('alta %s conserva datos y oculta detalles técnicos', async (status) => {
  render(<Harness />);
  fireEvent.click(screen.getByRole('button', { name: 'Registrar nuevo cliente' }));
  fireEvent.change(screen.getByLabelText('Nombre o razón social'), { target: { value: 'Vidrios Norte' } });
  fireEvent.change(screen.getByLabelText('Tipo de documento (opcional)'), { target: { value: 'TEST' } });
  fireEvent.change(screen.getByLabelText('Número de documento (opcional)'), { target: { value: 'DEMO-003' } });
  fetch.mockResolvedValueOnce(response({ detail: [{ msg: 'private SQL' }] }, status));
  fireEvent.click(screen.getByRole('button', { name: 'Registrar y seleccionar' }));
  const alert = await screen.findByRole('alert');
  expect(alert).not.toHaveTextContent('private SQL');
  expect(alert).toHaveTextContent(status === 409 ? 'Ya existe un cliente' : status === 422 ? 'Revisa los datos' : 'Inténtalo otra vez');
  expect(screen.getByLabelText('Nombre o razón social')).toHaveValue('Vidrios Norte');
  expect(screen.getByRole('button', { name: 'Registrar y seleccionar' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Volver a buscar' }));
  expect(screen.getByLabelText('Nombre del cliente')).toBeVisible();
});

test('aborta la consulta al desmontar el formulario', async () => {
  fetch.mockImplementationOnce(() => new Promise(() => {}));
  const { unmount } = render(<Harness />);
  fireEvent.change(screen.getByLabelText('Nombre del cliente'), { target: { value: 'Norte' } });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
  const { signal } = fetch.mock.calls[0][1];
  unmount();
  expect(signal.aborted).toBe(true);
});
