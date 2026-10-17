import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { OptimizationPage } from '../OptimizationPage';
import { getOrder, listOrderMaterials, listOrders } from '../../orders/ordersApi';
import { rasterizePiece, startOptimization } from '../optimizationApi';
import { deferred, item, order, raster } from './fixtures';
import { withPermissions } from '../../authentication/__tests__/permissionFixtures'

vi.mock('../../orders/ordersApi', () => ({ getOrder: vi.fn(), listOrders: vi.fn(), listOrderMaterials: vi.fn() }));
vi.mock('../optimizationApi', () => ({ rasterizePiece: vi.fn(), startOptimization: vi.fn() }));
const user = { rol: 'Operario', nombre: 'Operario local' };
const error = (status, message = 'Error recuperable') => Object.assign(new Error(message), { status });
const pageData = items => ({ items, total: items.length, total_pages: items.length ? 1 : 0, page: 1, limit: 10 });
let persisted;

beforeEach(() => {
  vi.resetAllMocks();
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
    fillRect: vi.fn(), setTransform: vi.fn(),
  });
  persisted = structuredClone(order);
  listOrders.mockImplementation(async ({ estado }) => pageData(persisted.estado === estado ? [{ ...item, estado }] : []));
  getOrder.mockImplementation(async () => structuredClone(persisted));
  listOrderMaterials.mockResolvedValue([{ id_tipo_vidrio: 7, nombre: 'Vidrio claro' }, { id_tipo_vidrio: 8, nombre: 'Vidrio gris' }]);
  startOptimization.mockImplementation(async () => {
    persisted.estado = 'EN_OPTIMIZACION';
    return { id_pedido: 27, estado: 'EN_OPTIMIZACION' };
  });
  rasterizePiece.mockResolvedValue(raster);
});

function renderPage(role = 'Operario') {
  const onSessionExpired = vi.fn();
  const rendered = render(<OptimizationPage initialMode="hu015" user={withPermissions({ ...user, rol: role })} token="test-token" onSessionExpired={onSessionExpired} />);
  return { ...rendered, onSessionExpired };
}
async function select() {
  fireEvent.click(await screen.findByRole('button', { name: /Pedido #27/ }));
  await screen.findByRole('table', { name: 'Piezas del pedido #27' });
}
async function started() {
  renderPage(); await select();
  fireEvent.click(screen.getByRole('button', { name: 'Preparar vista previa' }));
  await waitFor(() => expect(screen.getByLabelText('Pieza del pedido')).toBeEnabled());
}
function choose() { fireEvent.change(screen.getByLabelText('Pieza del pedido'), { target: { value: '51' } }); }
function calculate() { fireEvent.click(screen.getByRole('button', { name: 'Ver pieza' })); }
async function completed() { await started(); choose(); calculate(); await screen.findByText('Vista previa lista'); }

test('loading inicial, filtro backend PENDIENTE y start bloqueado sin selección', async () => {
  const pending = deferred(); listOrders.mockReturnValue(pending.promise);
  renderPage();
  expect(screen.getByText('Cargando pedidos...')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Preparar vista previa' })).toBeDisabled();
  expect(listOrders).toHaveBeenCalledWith({ estado: 'PENDIENTE', page: 1, limit: 10 }, expect.objectContaining({ token: 'test-token', signal: expect.any(AbortSignal) }));
  await act(async () => pending.resolve(pageData([])));
});

test('estado vacío y actualización explícita recupera nuevos pendientes', async () => {
  listOrders.mockResolvedValueOnce(pageData([]));
  renderPage();
  await screen.findByText('No hay pedidos pendientes disponibles para iniciar optimización.');
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar pedidos' }));
  expect(await screen.findByRole('button', { name: /Pedido #27.*Cliente local/ })).toBeVisible();
});

test('selecciona pedido, consulta detalle y muestra una fila por pieza persistida y materiales por pieza', async () => {
  renderPage(); await select();
  expect(getOrder).toHaveBeenCalledWith(27, expect.objectContaining({ token: 'test-token' }));
  const table = screen.getByRole('table');
  expect(within(table).getAllByRole('row')).toHaveLength(3);
  expect(within(table).getByRole('row', { name: /#51.*Rectángulo.*10 × 5 mm.*5.*Vidrio claro.*6.0 mm/ })).toBeVisible();
  expect(within(table).getByText('Vidrio gris')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Preparar vista previa' })).toBeEnabled();
  expect(screen.getByLabelText('Pieza del pedido')).toBeDisabled();
  expect(screen.getByLabelText('Detalle de la vista (mm)')).toHaveValue(5);
  expect(screen.getByRole('button', { name: 'Ver pieza' })).toBeDisabled();
});

test('start loading impide doble envío y no anticipa En preparación', async () => {
  const pending = deferred(); startOptimization.mockReturnValue(pending.promise);
  renderPage(); await select();
  fireEvent.doubleClick(screen.getByRole('button', { name: 'Preparar vista previa' }));
  fireEvent.click(screen.getByRole('button', { name: 'Preparar vista previa' }));
  const button = screen.getByRole('button', { name: 'Preparando pedido...' });
  fireEvent.click(button);
  expect(button).toBeDisabled(); expect(startOptimization).toHaveBeenCalledOnce();
  expect(screen.getByText('Pendiente', { selector: 'dd' })).toBeVisible();
  expect(screen.getByLabelText('Pieza del pedido')).toBeDisabled();
  persisted.estado = 'EN_OPTIMIZACION';
  await act(async () => pending.resolve({ id_pedido: 27, estado: 'EN_OPTIMIZACION' }));
});

test('200 conserva selección, actualiza estado, relee piezas y no rasteriza automáticamente', async () => {
  await started();
  expect(screen.getByRole('heading', { name: 'Pedido seleccionado #27' })).toBeVisible();
  expect(screen.getByText('En preparación', { selector: 'dd' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Preparar vista previa' })).toBeDisabled();
  expect(await screen.findByText('No hay pedidos pendientes disponibles para iniciar optimización.')).toBeVisible();
  expect(getOrder).toHaveBeenCalledTimes(2);
  expect(rasterizePiece).not.toHaveBeenCalled();
});

test('409 informa conflicto, refresca pendientes y no concede un inicio local', async () => {
  startOptimization.mockImplementation(async () => { persisted.estado = 'EN_OPTIMIZACION'; throw error(409); });
  renderPage(); await select();
  fireEvent.click(screen.getByRole('button', { name: 'Preparar vista previa' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('El pedido ya no está disponible');
  await screen.findByText('No hay pedidos pendientes disponibles para iniciar optimización.');
  expect(screen.getByText('Pendiente', { selector: 'dd' })).toBeVisible();
  expect(screen.getByLabelText('Pieza del pedido')).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Preparar vista previa' })).toBeDisabled();
  expect(getOrder).toHaveBeenCalledTimes(1);
});

test.each(['', '0', '-1', 'Infinity', 'NaN'])('resolución inválida %s impide submit', async value => {
  await started(); choose();
  fireEvent.change(screen.getByLabelText('Detalle de la vista (mm)'), { target: { value } });
  expect(screen.getByLabelText('Detalle de la vista (mm)')).toHaveAttribute('aria-invalid', 'true');
  expect(screen.getByRole('button', { name: 'Ver pieza' })).toBeDisabled();
  fireEvent.submit(screen.getByRole('button', { name: 'Ver pieza' }).closest('form'));
  expect(rasterizePiece).not.toHaveBeenCalled();
});

test('raster loading evita doble envío y success muestra resumen técnico con cantidad 5', async () => {
  const pending = deferred(); rasterizePiece.mockReturnValue(pending.promise);
  await started(); choose(); calculate();
  expect(screen.getByRole('button', { name: 'Preparando vista previa...' })).toBeDisabled();
  fireEvent.submit(screen.getByRole('button', { name: 'Preparando vista previa...' }).closest('form'));
  expect(rasterizePiece).toHaveBeenCalledOnce();
  expect(rasterizePiece).toHaveBeenCalledWith({ idPedido: 27, idPieza: 51, resolutionMm: 5 }, expect.objectContaining({ token: 'test-token', signal: expect.any(AbortSignal) }));
  await act(async () => pending.resolve(raster));
  const result = screen.getByRole('region', { name: 'Detalle de la pieza' });
  expect(within(result).getByText('Vista previa lista')).toBeVisible();
  for (const label of ['Tipo de forma', 'Cantidad', 'Resolución', 'Filas', 'Columnas', 'Celdas ocupadas', 'Vidrio', 'Espesor']) expect(within(result).getByText(label)).toBeVisible();
  expect(within(result).getByText('Cantidad').nextElementSibling).toHaveTextContent('5');
  expect(screen.getAllByRole('row')).toHaveLength(3);
  expect(screen.getByRole('img', { name: 'Geometría original de la pieza #51' }).querySelector('rect')).toHaveAttribute('width', '10');
  expect(screen.getByRole('img', { name: 'Detalle del corte de la pieza #51' })).toBeVisible();
  expect(document.querySelectorAll('canvas')).toHaveLength(1);
  expect(screen.getAllByRole('img', { name: /Geometría original de la pieza/ })).toHaveLength(1);
});

test('422 recursos permite cambiar resolución y reintentar sin repetir start', async () => {
  rasterizePiece.mockRejectedValueOnce(error(422, 'Resolución demasiado fina para el límite de recursos.'));
  await started(); choose();
  expect(screen.getByRole('img', { name: 'Geometría original de la pieza #51' })).toBeVisible();
  expect(screen.getByText('Selecciona «Ver pieza» para preparar la vista previa.')).toBeVisible();
  calculate();
  expect(await screen.findByRole('alert')).toHaveTextContent('Resolución demasiado fina');
  expect(screen.getByRole('img', { name: 'Geometría original de la pieza #51' })).toBeVisible();
  expect(screen.getByText('Selecciona «Ver pieza» para preparar la vista previa.')).toBeVisible();
  expect(document.querySelectorAll('canvas')).toHaveLength(0);
  fireEvent.change(screen.getByLabelText('Detalle de la vista (mm)'), { target: { value: '7.5' } });
  rasterizePiece.mockResolvedValueOnce({ ...raster, resolution_mm: 7.5 });
  calculate(); await screen.findByText('Vista previa lista');
  expect(rasterizePiece.mock.calls[1][0].resolutionMm).toBe(7.5);
  expect(screen.getByRole('img', { name: 'Detalle del corte de la pieza #51' })).toBeVisible();
  expect(startOptimization).toHaveBeenCalledOnce();
});

test.each(['piece', 'resolution', 'order'])('cambiar %s limpia resultado previo', async change => {
  await completed();
  if (change === 'piece') fireEvent.change(screen.getByLabelText('Pieza del pedido'), { target: { value: '52' } });
  if (change === 'resolution') fireEvent.change(screen.getByLabelText('Detalle de la vista (mm)'), { target: { value: '10' } });
  if (change === 'order') fireEvent.click(screen.getByRole('button', { name: 'Recuperar proceso iniciado' }));
  expect(screen.queryByText('Vista previa lista')).not.toBeInTheDocument();
  expect(document.querySelectorAll('canvas')).toHaveLength(0);
  if (change === 'piece') expect(screen.getByRole('img', { name: 'Geometría original de la pieza #52' }).querySelector('circle')).toHaveAttribute('r', '20');
});

test('una respuesta raster tardía no reaparece después de cambiar pieza', async () => {
  const pending = deferred(); rasterizePiece.mockReturnValue(pending.promise);
  await started(); choose(); calculate();
  const signal = rasterizePiece.mock.calls[0][1].signal;
  fireEvent.change(screen.getByLabelText('Pieza del pedido'), { target: { value: '52' } });
  expect(signal.aborted).toBe(true);
  await act(async () => pending.resolve(raster));
  expect(screen.queryByText('Vista previa lista')).not.toBeInTheDocument();
});

test('ignora detalle tardío al seleccionar otro pedido', async () => {
  const pending = deferred();
  listOrders.mockResolvedValue(pageData([item, { ...item, id_pedido: 28 }]));
  getOrder.mockReturnValueOnce(pending.promise).mockResolvedValueOnce({ ...order, id_pedido: 28, piezas: [] });
  renderPage(); fireEvent.click(await screen.findByRole('button', { name: /Pedido #27/ }));
  fireEvent.click(screen.getByRole('button', { name: /Pedido #28/ }));
  await screen.findByText('El pedido no contiene piezas disponibles. No se puede iniciar la optimización.');
  await act(async () => pending.resolve(order));
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Pedido seleccionado #28' })).toBeVisible();
});

test('recupera explícitamente EN_OPTIMIZACION por filtro y detalle sin POST start', async () => {
  persisted.estado = 'EN_OPTIMIZACION'; renderPage();
  fireEvent.click(screen.getByRole('button', { name: 'Recuperar proceso iniciado' }));
  await select();
  expect(listOrders).toHaveBeenLastCalledWith(expect.objectContaining({ estado: 'EN_OPTIMIZACION' }), expect.any(Object));
  expect(screen.getByLabelText('Pieza del pedido')).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Preparar vista previa' })).toBeDisabled();
  expect(startOptimization).not.toHaveBeenCalled();
});

test.each(['EN_OPTIMIZACION', 'PENDIENTE', 'CANCELADO'])('inicio incierto consulta GET y reconcilia %s sin repetir POST', async state => {
  startOptimization.mockImplementation(async () => { persisted.estado = state; throw error(0, 'Timeout'); });
  renderPage(); await select();
  fireEvent.click(screen.getByRole('button', { name: 'Preparar vista previa' }));
  await waitFor(() => expect(getOrder).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(screen.queryByText('Preparando pedido...')).not.toBeInTheDocument());
  expect(startOptimization).toHaveBeenCalledOnce();
  expect(screen.getByRole('button', { name: 'Preparar vista previa' }).disabled).toBe(state !== 'PENDIENTE');
  expect(screen.getByLabelText('Pieza del pedido').disabled).toBe(state !== 'EN_OPTIMIZACION');
});

test('si POST incierto y GET falla, oculta estado obsoleto, no afirma éxito y permite reconciliar explícitamente', async () => {
  startOptimization.mockRejectedValue(error(0, 'Timeout del inicio.'));
  getOrder.mockResolvedValueOnce(order).mockRejectedValueOnce(error(0, 'No se pudo consultar el pedido.'));
  renderPage(); await select();
  fireEvent.click(screen.getByRole('button', { name: 'Preparar vista previa' }));
  expect(await screen.findByText('El inicio sigue sin confirmar y no se pudo consultar el pedido. Actualiza el detalle antes de continuar.')).toBeVisible();
  expect(screen.getByRole('alert')).toHaveTextContent('No se pudo consultar el pedido.');
  expect(screen.queryByText('Pendiente', { selector: 'dd' })).not.toBeInTheDocument();
  expect(screen.getByLabelText('Pieza del pedido')).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Preparar vista previa' })).toBeDisabled();
  expect(startOptimization).toHaveBeenCalledOnce();

  getOrder.mockResolvedValueOnce({ ...order, estado: 'EN_OPTIMIZACION' });
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar detalle del pedido' }));
  await waitFor(() => expect(screen.getByLabelText('Pieza del pedido')).toBeEnabled());
  expect(startOptimization).toHaveBeenCalledOnce();
});

test('si falla detalle después de start confirmado reintenta GET, nunca POST', async () => {
  getOrder.mockResolvedValueOnce(order).mockRejectedValueOnce(error(500, 'No se pudo consultar el detalle.'));
  renderPage(); await select();
  fireEvent.click(screen.getByRole('button', { name: 'Preparar vista previa' }));
  await screen.findByText('No se pudo consultar el detalle.');
  expect(screen.getByLabelText('Pieza del pedido')).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar detalle del pedido' }));
  await waitFor(() => expect(screen.getByLabelText('Pieza del pedido')).toBeEnabled());
  expect(startOptimization).toHaveBeenCalledOnce();
});

test('fallo de catálogo conserva IDs y no bloquea el inicio', async () => {
  listOrderMaterials.mockRejectedValue(error(500)); renderPage(); await select();
  expect(screen.getByText(/No se pudo consultar el catálogo de vidrios/)).toBeVisible();
  expect(screen.getAllByText('Vidrio sin identificar').length).toBeGreaterThan(0);
  expect(screen.queryByText('Material #7')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Preparar vista previa' })).toBeEnabled();
});

test.each([401, 403, 404, 422])('start maneja %s sin transición falsa y 401 usa cierre global', async status => {
  startOptimization.mockRejectedValue(error(status));
  const { onSessionExpired } = renderPage(); await select();
  fireEvent.click(screen.getByRole('button', { name: 'Preparar vista previa' }));
  await screen.findByRole('alert');
  expect(screen.getByLabelText('Pieza del pedido')).toBeDisabled();
  expect(onSessionExpired).toHaveBeenCalledTimes(status === 401 ? 1 : 0);
});

test.each([401, 403, 404, 409, 500])('raster maneja %s sin resultado obsoleto', async status => {
  rasterizePiece.mockRejectedValue(error(status));
  await started(); choose(); calculate();
  expect(await screen.findByRole('alert')).toHaveTextContent('Error recuperable');
  expect(screen.queryByText('Vista previa lista')).not.toBeInTheDocument();
});

test('paginación consulta page 2 conservando el filtro real', async () => {
  listOrders.mockResolvedValue({ ...pageData([item]), total: 11, total_pages: 2 });
  renderPage(); await screen.findByRole('button', { name: /Pedido #27/ });
  fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }));
  await waitFor(() => expect(listOrders).toHaveBeenLastCalledWith({ estado: 'PENDIENTE', page: 2, limit: 10 }, expect.any(Object)));
});

test('Almacenero no accede ni dispara consultas de Optimization', () => {
  renderPage('Almacenero');
  expect(screen.getByRole('alert')).toHaveTextContent('No tienes permiso');
  expect(listOrders).not.toHaveBeenCalled();
});

test('al desmontar limpia contexto y no publica respuestas tardías', async () => {
  const pending = deferred(); startOptimization.mockReturnValue(pending.promise);
  const { unmount } = renderPage(); await select();
  fireEvent.click(screen.getByRole('button', { name: 'Preparar vista previa' }));
  unmount(); persisted.estado = 'EN_OPTIMIZACION';
  await act(async () => pending.resolve({ id_pedido: 27, estado: 'EN_OPTIMIZACION' }));
  expect(getOrder).toHaveBeenLastCalledWith(27, expect.any(Object));
  renderPage();
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  expect(screen.queryByText('Vista previa lista')).not.toBeInTheDocument();
});
