import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import FormularioPedido from '../FormularioPedido';
import NuevoPedido from '../NuevoPedido';

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }));

const catalog = [{ id_tipo_vidrio: 7, nombre: 'Templado', estado: true, espesores_mm: [5.5, 6] }];
const polygonOrder = {
  id_pedido: 73,
  estado: 'PENDIENTE',
  fecha_registro: '2026-10-10T10:00:00Z',
  id_usuario_registro: 1,
  piezas: [{
    id_pieza: 31,
    id_pedido: 73,
    id_tipo_vidrio: 7,
    espesor_mm: '5.5',
    tipo_forma: 'POLIGONO_CONVEXO',
    cantidad: 2,
    dimensiones: null,
    geometria: { type: 'POLIGONO_CONVEXO', vertices_mm: [[0, 0], [300, 0], [300, 200], [0, 200]] },
    area_mm2: '60000',
  }],
};
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });

beforeEach(() => vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(catalog))));
afterEach(() => vi.unstubAllGlobals());

describe('FormularioPedido canónico', () => {
  test('NuevoPedido queda como wrapper del modo crear', async () => {
    render(<NuevoPedido token="wrapper-token" />);
    expect(await screen.findByRole('heading', { name: 'Nuevo pedido' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Agregar pieza' })).toBeEnabled();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  test('acepta medidas decimales positivas y anuncia errores de campo asociados', async () => {
    const user = userEvent.setup();
    render(<FormularioPedido token="decimal-token" standalone />);
    await screen.findByText('No hay piezas agregadas');
    await user.click(screen.getByRole('button', { name: 'Agregar pieza' }));
    const row = screen.getByText('Pieza 1', { selector: 'strong' }).closest('.orders-piece');
    await user.selectOptions(within(row).getByLabelText('Material'), '7');
    await user.selectOptions(within(row).getByLabelText('Espesor'), '5.5');
    fireEvent.change(within(row).getByLabelText('Ancho (mm)'), { target: { value: '10.5' } });
    fireEvent.change(within(row).getByLabelText('Alto (mm)'), { target: { value: '5.25' } });
    expect(screen.getByRole('button', { name: 'Guardar pedido' })).toBeEnabled();

    const quantity = within(row).getByLabelText('Cant.');
    fireEvent.change(quantity, { target: { value: '1.5' } });
    fireEvent.blur(quantity);
    const fieldError = await screen.findByText('Ingresa una cantidad entera mayor que 0.');
    expect(quantity).toHaveAttribute('aria-invalid', 'true');
    expect(quantity).toHaveAttribute('aria-describedby', fieldError.closest('p').id);
    expect(screen.getByRole('button', { name: 'Guardar pedido' })).toBeDisabled();
  });

  test('edita un polígono existente y conserva geometría válida en el PUT', async () => {
    const user = userEvent.setup();
    fetch.mockImplementation(async (url, options = {}) => {
      if (String(url).includes('/api/inventory/tipos-vidrio')) return response(catalog);
      if (String(url).endsWith('/api/orders/73') && options.method === 'PUT') {
        return response({ message: 'Pedido actualizado exitosamente', id_pedido: 73 });
      }
      if (String(url).endsWith('/api/orders/73')) return response(polygonOrder);
      throw new Error(`Solicitud inesperada: ${url}`);
    });

    render(<FormularioPedido token="edit-token" idPedido={73} mode="edit" />);
    expect(await screen.findByText('✓ Geometría cargada')).toBeVisible();
    const row = screen.getByText('Pieza 1', { selector: 'strong' }).closest('.orders-piece');
    expect(within(row).getByLabelText('Material')).toHaveValue('7');
    expect(within(row).getByLabelText('Espesor')).toHaveValue('5.5');

    await user.click(within(row).getByRole('button', { name: 'Editar dibujo' }));
    const dialog = screen.getByRole('dialog', { name: 'Dibujar Polígono Convexo' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('button', { name: 'Cerrar editor de polígono' })).toHaveFocus();
    expect(screen.getByText('Geometría convexa validada.')).toBeVisible();
    const firstSide = screen.getByRole('spinbutton', { name: 'Longitud del segmento S1 en milímetros' });
    expect(firstSide).toHaveValue(300);
    fireEvent.change(firstSide, { target: { value: '320' } });
    expect(screen.getByText('Geometría convexa validada.')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Agregar pieza al pedido' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(within(row).getByRole('button', { name: 'Editar dibujo' })).toHaveFocus();

    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByText('Pedido actualizado correctamente.')).toBeVisible();
    const putCall = fetch.mock.calls.find(([, options]) => options.method === 'PUT');
    expect(putCall).toBeDefined();
    expect(putCall[1].headers.Authorization).toBe('Bearer edit-token');
    const payload = JSON.parse(putCall[1].body);
    expect(payload).not.toHaveProperty('id_tipo_vidrio');
    expect(payload).not.toHaveProperty('espesor_mm');
    expect(payload.piezas).toHaveLength(1);
    expect(payload.piezas[0]).toMatchObject({
      tipo_forma: 'POLIGONO_CONVEXO',
      id_tipo_vidrio: 7,
      espesor_mm: 5.5,
      cantidad: 2,
    });
    expect(payload.piezas[0].vertices_mm).toHaveLength(4);
    expect(payload.piezas[0].vertices_mm.flat().every(Number.isFinite)).toBe(true);
  });
});
