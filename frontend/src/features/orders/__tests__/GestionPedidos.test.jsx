import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import GestionPedidos from '../GestionPedidos';
import { cancelOrder, listOrders } from '../ordersApi';

vi.mock('../ordersApi', () => ({
  cancelOrder: vi.fn(),
  listOrders: vi.fn(),
}));

vi.mock('../FormularioPedido', () => ({
  default: ({ idPedido, mode, onCerrar, onSuccess, onSubmittingChange }) => (
    <div role="group" aria-label="Formulario canónico de pedidos">
      <p>{idPedido ? `Pedido ${idPedido}` : 'Pedido nuevo'} ({mode})</p>
      <button type="button" onClick={() => onSubmittingChange(true)}>Iniciar guardado</button>
      <button type="button" onClick={() => { onSuccess(mode); onCerrar(); }}>Guardar formulario</button>
      <button type="button" onClick={onCerrar}>Cerrar formulario</button>
    </div>
  ),
}));

const user = { id_usuario: 4, username: 'O40000001', nombre: 'Operaria Prueba', rol: 'Operario' };
const orders = [
  { id_pedido: 27, fecha_registro: '2026-10-08T12:00:00Z', cliente: 'Vidrios Andinos', estado: 'PENDIENTE' },
  { id_pedido: 28, fecha_registro: '2026-10-07T12:00:00Z', cliente: 'Constructora Lima', estado: 'OPTIMIZADO' },
];
const page = (items = orders, total = items.length, totalPages = total ? 1 : 0) => ({
  items, total, page: 1, limit: 10, total_pages: totalPages,
});
const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
};

beforeEach(() => {
  listOrders.mockResolvedValue(page());
  cancelOrder.mockResolvedValue({ message: 'Pedido cancelado exitosamente' });
});

afterEach(() => vi.clearAllMocks());

function renderOrders() {
  const onSessionExpired = vi.fn();
  render(<GestionPedidos token="orders-token" user={user} toolbar={<div>Barra global</div>}
    onSessionExpired={onSessionExpired} />);
  return { onSessionExpired };
}

async function loadedOrders() {
  renderOrders();
  await screen.findByRole('row', { name: /27.*Vidrios Andinos/i });
}

describe('GestionPedidos — listado y filtros', () => {
  test('carga el listado inicial con los parámetros predeterminados', async () => {
    await loadedOrders();
    expect(listOrders).toHaveBeenCalledWith(
      { page: 1, limit: 10, estado: '', cliente: '', fecha: '' },
      expect.objectContaining({ token: 'orders-token', signal: expect.any(AbortSignal) }),
    );
  });

  test('muestra el estado de carga mientras espera la respuesta', () => {
    listOrders.mockReturnValueOnce(new Promise(() => {}));
    renderOrders();
    expect(screen.getByText('Cargando pedidos...')).toBeVisible();
  });

  test('muestra errores de carga con feedback accesible y maneja 401', async () => {
    listOrders.mockRejectedValueOnce(Object.assign(new Error('Servicio no disponible'), { status: 401 }));
    const { onSessionExpired } = renderOrders();
    expect(await screen.findByRole('alert')).toHaveTextContent('Servicio no disponible');
    expect(onSessionExpired).toHaveBeenCalledOnce();
  });

  test('muestra EmptyState cuando no hay pedidos', async () => {
    listOrders.mockResolvedValueOnce(page([], 0, 0));
    renderOrders();
    expect(await screen.findByText('Todavía no hay pedidos registrados.')).toBeVisible();
  });

  test('renderiza pedidos, fecha, cliente y estado', async () => {
    await loadedOrders();
    expect(screen.getByRole('row', { name: /28.*Constructora Lima.*Optimizado/i })).toBeVisible();
    expect(screen.getByText('08/10/2026')).toBeVisible();
  });

  test('aplica el filtro por cliente al enviar el formulario y no al teclear', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    listOrders.mockClear();
    await userEventInstance.type(screen.getByRole('searchbox', { name: 'Buscar por cliente' }), 'Lima');
    expect(listOrders).not.toHaveBeenCalled();
    await userEventInstance.click(screen.getByRole('button', { name: 'Aplicar filtros' }));
    await screen.findByRole('row', { name: /27.*Vidrios Andinos/i });
    expect(listOrders).toHaveBeenCalledWith(expect.objectContaining({ cliente: 'Lima', page: 1 }), expect.any(Object));
  });

  test('aplica el filtro por estado', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    await userEventInstance.selectOptions(screen.getByLabelText('Estado'), 'PENDIENTE');
    await userEventInstance.click(screen.getByRole('button', { name: 'Aplicar filtros' }));
    await screen.findByRole('row', { name: /27.*Vidrios Andinos/i });
    expect(listOrders).toHaveBeenLastCalledWith(expect.objectContaining({ estado: 'PENDIENTE' }), expect.any(Object));
  });

  test('aplica el filtro por fecha', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    fireEvent.change(screen.getByLabelText('Fecha de registro'), { target: { value: '2026-10-08' } });
    await userEventInstance.click(screen.getByRole('button', { name: 'Aplicar filtros' }));
    await screen.findByRole('row', { name: /27.*Vidrios Andinos/i });
    expect(listOrders).toHaveBeenLastCalledWith(expect.objectContaining({ fecha: '2026-10-08' }), expect.any(Object));
  });

  test('reinicia a la primera página al aplicar los filtros', async () => {
    const userEventInstance = userEvent.setup();
    listOrders.mockResolvedValue(page(orders, 25, 3));
    await loadedOrders();
    await userEventInstance.click(screen.getByRole('button', { name: 'Página siguiente' }));
    await screen.findByText('Página 2 de 3 (25 pedidos)');
    await userEventInstance.type(screen.getByRole('searchbox', { name: 'Buscar por cliente' }), 'Norte');
    await userEventInstance.click(screen.getByRole('button', { name: 'Aplicar filtros' }));
    await screen.findByText('Página 1 de 3 (25 pedidos)');
    expect(listOrders).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, cliente: 'Norte' }), expect.any(Object));
  });

  test('pagina atrás y adelante y deshabilita los extremos', async () => {
    const userEventInstance = userEvent.setup();
    listOrders.mockResolvedValue(page(orders.slice(0, 1), 12, 2));
    await loadedOrders();
    const previous = screen.getByRole('button', { name: 'Página anterior' });
    const next = screen.getByRole('button', { name: 'Página siguiente' });
    expect(previous).toBeDisabled();
    await userEventInstance.click(next);
    await screen.findByText('Página 2 de 2 (12 pedidos)');
    expect(next).toBeDisabled();
    await userEventInstance.click(previous);
    await screen.findByText('Página 1 de 2 (12 pedidos)');
  });

  test('representa total_pages cero sin mostrar Página 1 de 0 y deshabilita ambos botones', async () => {
    listOrders.mockResolvedValueOnce(page([], 0, 0));
    renderOrders();
    await screen.findByText('0 pedidos para mostrar');
    expect(screen.queryByText(/Página 1 de 0/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Página anterior' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Página siguiente' })).toBeDisabled();
  });

  test('una respuesta anterior no reemplaza los resultados de una búsqueda más reciente', async () => {
    const first = deferred();
    const second = deferred();
    listOrders.mockReset().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const userEventInstance = userEvent.setup();
    renderOrders();
    await userEventInstance.type(screen.getByRole('searchbox', { name: 'Buscar por cliente' }), 'nueva');
    await userEventInstance.click(screen.getByRole('button', { name: 'Aplicar filtros' }));
    expect(listOrders).toHaveBeenCalledTimes(2);
    expect(listOrders.mock.calls[0][1].signal.aborted).toBe(true);
    await act(async () => second.resolve(page([{ ...orders[0], id_pedido: 99, cliente: 'Resultado nuevo' }], 1, 1)));
    expect(await screen.findByRole('row', { name: /99.*Resultado nuevo/i })).toBeVisible();
    await act(async () => first.resolve(page([{ ...orders[0], id_pedido: 11, cliente: 'Resultado obsoleto' }], 1, 1)));
    expect(screen.getByRole('row', { name: /99.*Resultado nuevo/i })).toBeVisible();
    expect(screen.queryByText('Resultado obsoleto')).not.toBeInTheDocument();
  });
});

describe('GestionPedidos — acciones y modal', () => {
  test('abre el modal de creación con nombre accesible y foco inicial', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    const trigger = screen.getByRole('button', { name: 'Nuevo pedido' });
    await userEventInstance.click(trigger);
    const dialog = screen.getByRole('dialog', { name: 'Crear pedido' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(within(dialog).getByLabelText('Formulario canónico de pedidos')).toBeVisible();
    expect(within(dialog).getByRole('button', { name: 'Cerrar formulario de pedido' })).toHaveFocus();
  });

  test('abre edición de un pendiente y detalle de un pedido no pendiente', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    await userEventInstance.click(screen.getByRole('button', { name: 'Editar pedido 27' }));
    expect(screen.getByRole('dialog', { name: 'Pedido #27 · Editar' })).toBeVisible();
    await userEventInstance.click(screen.getByRole('button', { name: 'Cerrar formulario de pedido' }));
    await userEventInstance.click(screen.getByRole('button', { name: 'Ver pedido 28' }));
    expect(screen.getByRole('dialog', { name: 'Pedido #28 · Detalle' })).toBeVisible();
  });

  test('Escape cierra el modal y devuelve el foco al botón que lo abrió', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    const trigger = screen.getByRole('button', { name: 'Nuevo pedido' });
    await userEventInstance.click(trigger);
    await userEventInstance.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  test('atrapa Tab y Shift+Tab dentro del modal', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    await userEventInstance.click(screen.getByRole('button', { name: 'Nuevo pedido' }));
    const dialog = screen.getByRole('dialog', { name: 'Crear pedido' });
    const close = within(dialog).getByRole('button', { name: 'Cerrar formulario de pedido' });
    const last = within(dialog).getByRole('button', { name: 'Cerrar formulario' });
    await userEventInstance.tab({ shift: true });
    expect(last).toHaveFocus();
    await userEventInstance.tab();
    expect(close).toHaveFocus();
  });

  test('no permite cerrar el modal durante el guardado', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    await userEventInstance.click(screen.getByRole('button', { name: 'Nuevo pedido' }));
    const dialog = screen.getByRole('dialog', { name: 'Crear pedido' });
    await userEventInstance.click(within(dialog).getByRole('button', { name: 'Iniciar guardado' }));
    await userEventInstance.keyboard('{Escape}');
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Cerrar formulario de pedido' })).toBeDisabled();
  });

  test('abre la confirmación para cancelar un pedido pendiente', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    await userEventInstance.click(screen.getByRole('button', { name: 'Cancelar pedido 27' }));
    expect(screen.getByRole('alertdialog', { name: '¿Cancelar el pedido #27?' })).toBeVisible();
  });

  test('Cancelar en ConfirmDialog cierra sin llamar la API', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    await userEventInstance.click(screen.getByRole('button', { name: 'Cancelar pedido 27' }));
    const dialog = screen.getByRole('alertdialog', { name: '¿Cancelar el pedido #27?' });
    await userEventInstance.click(within(dialog).getByRole('button', { name: 'Cancelar', exact: true }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(cancelOrder).not.toHaveBeenCalled();
  });

  test('confirma cancelación, informa éxito y refresca el listado', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    await userEventInstance.click(screen.getByRole('button', { name: 'Cancelar pedido 27' }));
    const dialog = screen.getByRole('alertdialog', { name: '¿Cancelar el pedido #27?' });
    await userEventInstance.click(within(dialog).getByRole('button', { name: 'Sí, cancelar pedido' }));
    expect(cancelOrder).toHaveBeenCalledWith(27, { token: 'orders-token' });
    expect(await screen.findByText('Pedido #27 cancelado correctamente.')).toBeVisible();
    await screen.findByRole('row', { name: /27.*Vidrios Andinos/i });
    expect(listOrders).toHaveBeenCalledTimes(2);
  });

  test('muestra error si falla la cancelación', async () => {
    const userEventInstance = userEvent.setup();
    cancelOrder.mockRejectedValueOnce(new Error('No se pudo cancelar'));
    await loadedOrders();
    await userEventInstance.click(screen.getByRole('button', { name: 'Cancelar pedido 27' }));
    const dialog = screen.getByRole('alertdialog');
    await userEventInstance.click(within(dialog).getByRole('button', { name: 'Sí, cancelar pedido' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cancelar');
    expect(listOrders).toHaveBeenCalledTimes(1);
  });

  test('bloquea cancelaciones duplicadas mientras la solicitud está pendiente', async () => {
    const userEventInstance = userEvent.setup();
    const pending = deferred();
    cancelOrder.mockReturnValueOnce(pending.promise);
    await loadedOrders();
    await userEventInstance.click(screen.getByRole('button', { name: 'Cancelar pedido 27' }));
    const confirm = within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Sí, cancelar pedido' });
    await userEventInstance.click(confirm);
    expect(confirm).toBeDisabled();
    fireEvent.click(confirm);
    expect(cancelOrder).toHaveBeenCalledOnce();
    await act(async () => pending.resolve({ message: 'OK' }));
  });

  test('al guardar el formulario activo cierra, muestra éxito y refresca', async () => {
    const userEventInstance = userEvent.setup();
    await loadedOrders();
    await userEventInstance.click(screen.getByRole('button', { name: 'Nuevo pedido' }));
    const dialog = screen.getByRole('dialog', { name: 'Crear pedido' });
    await userEventInstance.click(within(dialog).getByRole('button', { name: 'Guardar formulario' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(await screen.findByText('Pedido creado correctamente.')).toBeVisible();
    await screen.findByRole('row', { name: /27.*Vidrios Andinos/i });
    expect(listOrders).toHaveBeenCalledTimes(2);
  });
});
