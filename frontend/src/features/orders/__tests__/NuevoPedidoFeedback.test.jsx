import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import FormularioPedido from '../FormularioPedido';

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }));

const catalog = [{ id_tipo_vidrio: 7, nombre: 'Templado', estado: true, espesores_mm: [6] }];
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });

async function addRectangle() {
  fetch.mockResolvedValueOnce(response([{ id_cliente: 41, nombre_razon_social: 'Cliente prueba', estado: true }]));
  fireEvent.change(screen.getByLabelText('Nombre del cliente'), { target: { value: 'prueba' } });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
  fireEvent.click(await screen.findByRole('button', { name: 'Seleccionar Cliente prueba' }));
  fireEvent.change(screen.getByLabelText('Tipo de vidrio'), { target: { value: '7' } });
  fireEvent.change(screen.getByLabelText('Espesor del vidrio (mm)'), { target: { value: '6' } });
  fireEvent.change(screen.getByLabelText('Ancho (mm)'), { target: { value: '1000' } });
  fireEvent.change(screen.getByLabelText('Alto (mm)'), { target: { value: '500' } });
}

describe('FormularioPedido — feedback compartido (TA-034)', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(catalog)));
  });
  afterEach(() => vi.unstubAllGlobals());

  it('muestra la carga del catálogo y luego el estado vacío', async () => {
    render(<FormularioPedido token="token-de-prueba" standalone />);
    expect(screen.getByText('Cargando materiales…')).toBeInTheDocument();
    expect(await screen.findByText('Falta seleccionar cliente')).toBeInTheDocument();
    expect(screen.queryByText('Cargando materiales…')).not.toBeInTheDocument();
  });

  it('muestra el error del catálogo como alerta', async () => {
    fetch.mockResolvedValueOnce(response({}, 500));
    render(<FormularioPedido token="token-de-prueba" standalone />);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('No se pudo completar la operación');
  });

  it('confirma antes de limpiar el pedido y no borra si se cancela', async () => {
    render(<FormularioPedido token="token-de-prueba" standalone />);
    await screen.findByText('Falta seleccionar cliente');
    await addRectangle();
    fireEvent.click(screen.getByRole('button', { name: /^Cancelar$/ }));
    const dialog = screen.getByRole('alertdialog', { name: '¿Limpiar el pedido?' });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }));
    expect(screen.getByLabelText('Ancho (mm)')).toHaveValue(1000);
    expect(screen.getByLabelText('Cliente seleccionado')).toHaveTextContent('Cliente prueba');

    fireEvent.click(screen.getByRole('button', { name: /^Cancelar$/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Limpiar pedido' }));
    expect(screen.getByText('Falta seleccionar cliente')).toBeInTheDocument();
  });

  it('muestra el éxito sin ventanas del navegador', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    render(<FormularioPedido token="token-de-prueba" standalone />);
    await screen.findByText('Falta seleccionar cliente');
    await addRectangle();
    fetch.mockResolvedValueOnce(response({ id_pedido: 15 }, 201));
    fireEvent.click(screen.getByRole('button', { name: /Guardar pedido/ }));
    expect(await screen.findByText('Pedido registrado correctamente. ID del pedido: 15.')).toBeInTheDocument();
    expect(alertSpy).not.toHaveBeenCalled();
  });

  it('no muestra al usuario el detalle técnico de validación del backend', async () => {
    render(<FormularioPedido token="token-de-prueba" standalone />);
    await screen.findByText('Falta seleccionar cliente');
    await addRectangle();
    fetch.mockResolvedValueOnce(response({ detail: [{ loc: ['body', 'piezas', 0], msg: 'field required' }] }, 422));
    fireEvent.click(screen.getByRole('button', { name: /Guardar pedido/ }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Revisa el cliente, el material, espesor y las medidas de las piezas.');
    expect(alert).not.toHaveTextContent('field required');
  });
});
