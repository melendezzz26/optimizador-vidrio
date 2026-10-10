import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import NuevoPedido from '../NuevoPedido';

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }));

const catalog = [{ id_tipo_vidrio: 7, nombre: 'Templado', estado: true, espesores_mm: [6] }];
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });

async function addRectangle() {
  fireEvent.click(screen.getByRole('button', { name: /Agregar pieza/ }));
  const [material, espesor] = screen.getAllByRole('combobox');
  fireEvent.change(material, { target: { value: '7' } });
  fireEvent.change(espesor, { target: { value: '6' } });
  const [, ancho, alto] = screen.getAllByRole('spinbutton');
  fireEvent.change(ancho, { target: { value: '1000' } });
  fireEvent.change(alto, { target: { value: '500' } });
}

describe('NuevoPedido — feedback compartido (TA-034)', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(catalog)));
  });
  afterEach(() => vi.unstubAllGlobals());

  it('muestra la carga del catálogo y luego el estado vacío', async () => {
    render(<NuevoPedido token="token-de-prueba" />);
    expect(screen.getByText('Cargando materiales…')).toBeInTheDocument();
    expect(await screen.findByText('No hay piezas agregadas')).toBeInTheDocument();
    expect(screen.queryByText('Cargando materiales…')).not.toBeInTheDocument();
  });

  it('muestra el error del catálogo como alerta', async () => {
    fetch.mockResolvedValueOnce(response({}, 500));
    render(<NuevoPedido token="token-de-prueba" />);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('No se pudo completar la operación');
  });

  it('confirma antes de limpiar el pedido y no borra si se cancela', async () => {
    render(<NuevoPedido token="token-de-prueba" />);
    await screen.findByText('No hay piezas agregadas');
    fireEvent.click(screen.getByRole('button', { name: /Agregar pieza/ }));
    fireEvent.click(screen.getByRole('button', { name: /^Cancelar$/ }));
    const dialog = screen.getByRole('alertdialog', { name: '¿Limpiar el pedido?' });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }));
    expect(screen.queryByText('No hay piezas agregadas')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /^Cancelar$/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Limpiar piezas' }));
    expect(screen.getByText('No hay piezas agregadas')).toBeInTheDocument();
  });

  it('muestra el éxito sin ventanas del navegador', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    render(<NuevoPedido token="token-de-prueba" />);
    await screen.findByText('No hay piezas agregadas');
    await addRectangle();
    fetch.mockResolvedValueOnce(response({ id_pedido: 15 }, 201));
    fireEvent.click(screen.getByRole('button', { name: /Guardar pedido/ }));
    expect(await screen.findByText('Pedido registrado correctamente.')).toBeInTheDocument();
    expect(alertSpy).not.toHaveBeenCalled();
  });

  it('no muestra al usuario el detalle técnico de validación del backend', async () => {
    render(<NuevoPedido token="token-de-prueba" />);
    await screen.findByText('No hay piezas agregadas');
    await addRectangle();
    fetch.mockResolvedValueOnce(response({ detail: [{ loc: ['body', 'piezas', 0], msg: 'field required' }] }, 422));
    fireEvent.click(screen.getByRole('button', { name: /Guardar pedido/ }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('No se pudo registrar el pedido. Revisa las piezas e inténtalo de nuevo.');
    expect(alert).not.toHaveTextContent('field required');
  });
});