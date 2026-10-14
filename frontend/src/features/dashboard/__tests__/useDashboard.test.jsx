import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { loadDashboardSource } from '../dashboardApi';
import { useDashboard } from '../useDashboard';
import { dashboardUser, deferred, emptyResponse, sourceResponse } from './fixtures';

vi.mock('../dashboardApi', () => ({ loadDashboardSource: vi.fn() }));
const props = { user: dashboardUser(), token: 'synthetic', onSessionExpired: vi.fn() };
beforeEach(() => { props.onSessionExpired.mockClear(); loadDashboardSource.mockReset().mockImplementation(async source => sourceResponse(source)); });

test('carga por fuente sin valores falsos; una fuente lenta no oculta las que ya llegaron', async () => {
  const pending = deferred();
  loadDashboardSource.mockImplementation(source => source === 'planchas' ? pending.promise : Promise.resolve(sourceResponse(source)));
  const { result } = renderHook(() => useDashboard(props));
  expect(Object.values(result.current.blocks).every(block => block.data === null)).toBe(true);
  await waitFor(() => expect(result.current.blocks.retazos.status).toBe('success'));
  expect(result.current.blocks.planchas).toEqual({ status: 'loading', data: null, error: '' });
  await act(async () => pending.resolve(sourceResponse('planchas')));
  expect(result.current.status).toBe('success');
});
test('Almacenero consulta solo inventario; roles desconocidos no disparan requests', async () => {
  const { result, rerender } = renderHook(value => useDashboard(value), { initialProps: { ...props, user: dashboardUser('Almacenero') } });
  await waitFor(() => expect(result.current.status).toBe('success'));
  expect(loadDashboardSource.mock.calls.map(([source]) => source)).toEqual(['planchas', 'retazos']);
  rerender({ ...props, user: dashboardUser('Unknown') });
  expect(result.current.blocks).toEqual({});
  expect(loadDashboardSource).toHaveBeenCalledTimes(2);
});
test('fallo parcial no fabrica cero ni borra datos válidos y permite retry explícito', async () => {
  loadDashboardSource.mockImplementation(async source => { if (source === 'planchas') throw new Error('SQL internal'); return sourceResponse(source); });
  const { result } = renderHook(() => useDashboard(props));
  await waitFor(() => expect(result.current.status).toBe('partial-error'));
  expect(result.current.blocks.planchas).toMatchObject({ status: 'error', data: null });
  expect(result.current.blocks.planchas.error).not.toContain('SQL');
  expect(result.current.blocks.retazos.data.activeRecords).toBe(1);
  loadDashboardSource.mockImplementation(async source => sourceResponse(source));
  act(() => result.current.refresh());
  expect(result.current.blocks.retazos.data).toBeNull();
  await waitFor(() => expect(result.current.status).toBe('success'));
  expect(loadDashboardSource).toHaveBeenCalledTimes(12);
});
test.each(['empty', 'error'])('%s global se distingue de éxito y de valores simulados', async kind => {
  loadDashboardSource.mockImplementation(async source => { if (kind === 'error') throw new Error('network'); return emptyResponse(source); });
  const { result } = renderHook(() => useDashboard(props));
  await waitFor(() => expect(result.current.status).toBe(kind));
  if (kind === 'error') expect(Object.values(result.current.blocks).every(block => block.data === null)).toBe(true);
  else expect(result.current.blocks.pendingOrders.data.total).toBe(0);
});
test('401 limpia datos válidos, aborta pendientes y notifica expiración una sola vez', async () => {
  const expired = deferred();
  loadDashboardSource.mockImplementation(source => source === 'clients' ? expired.promise : Promise.resolve(sourceResponse(source)));
  const { result } = renderHook(() => useDashboard(props));
  await waitFor(() => expect(result.current.blocks.planchas.data?.activeUnits).toBe(5));
  await act(async () => expired.reject(Object.assign(new Error('expired'), { status: 401 })));
  expect(props.onSessionExpired).toHaveBeenCalledOnce();
  expect(Object.values(result.current.blocks).every(block => block.data === null)).toBe(true);
  expect(loadDashboardSource.mock.calls[0][1].signal.aborted).toBe(true);
});
test('403 de una fuente no concede datos ni elimina inventario autorizado', async () => {
  loadDashboardSource.mockImplementation(async source => { if (source === 'clients') throw Object.assign(new Error('private'), { status: 403 }); return sourceResponse(source); });
  const { result } = renderHook(() => useDashboard(props));
  await waitFor(() => expect(result.current.status).toBe('partial-error'));
  expect(result.current.blocks.clients).toMatchObject({ status: 'error', data: null, error: 'No tienes permiso para consultar esta información.' });
  expect(result.current.blocks.planchas.status).toBe('success');
  expect(props.onSessionExpired).not.toHaveBeenCalled();
});
test('respuesta vieja de otro usuario/rol/token no vuelve a aparecer aunque ignore abort', async () => {
  const old = deferred();
  loadDashboardSource.mockImplementation(() => old.promise);
  const { result, rerender } = renderHook(value => useDashboard(value), { initialProps: props });
  const oldSignal = loadDashboardSource.mock.calls[0][1].signal;
  loadDashboardSource.mockImplementation(async source => sourceResponse(source));
  rerender({ ...props, user: { ...dashboardUser('Almacenero'), id_usuario: 12 }, token: 'synthetic-other' });
  expect(Object.keys(result.current.blocks)).toEqual(['planchas', 'retazos']);
  expect(result.current.blocks.planchas.data).toBeNull();
  await waitFor(() => expect(result.current.status).toBe('success'));
  await act(async () => old.resolve([{ id_plancha: 99, estado: true, cantidad: 999 }]));
  expect(oldSignal.aborted).toBe(true);
  expect(result.current.blocks.planchas.data.activeUnits).toBe(5);
  expect(result.current.blocks.clients).toBeUndefined();
});
test('unmount aborta y un 401 tardío no afecta una sesión posterior', async () => {
  const late = deferred();
  loadDashboardSource.mockImplementation(() => late.promise);
  const { unmount } = renderHook(() => useDashboard(props));
  const signal = loadDashboardSource.mock.calls[0][1].signal;
  unmount();
  await act(async () => late.reject(Object.assign(new Error('late'), { status: 401 })));
  expect(signal.aborted).toBe(true);
  expect(props.onSessionExpired).not.toHaveBeenCalled();
});
