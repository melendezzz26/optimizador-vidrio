import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { OptimizationApiError, rasterizePiece, startOptimization } from '../optimizationApi';
import { API_URL } from '../../../shared/apiUrl';
import { raster } from './fixtures';

const response = (data, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => data });
beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe('contratos de Optimization', () => {
  test('start envía únicamente el ID, utiliza transporte autenticado y devuelve el estado confirmado', async () => {
    const data = { id_pedido: 27, estado: 'PENDIENTE' };
    fetch.mockResolvedValue(response(data));
    await expect(startOptimization(27, { token: 'test-token' })).resolves.toBe(data);
    expect(fetch).toHaveBeenCalledWith(`${API_URL}/api/optimization/start`, expect.objectContaining({
      method: 'POST', body: JSON.stringify({ id_pedido: 27 }),
      headers: { Authorization: 'Bearer test-token', 'Content-Type': 'application/json' },
    }));
  });

  test('raster envía IDs y resolución, sin geometría ni material; conserva el objeto y spans recibidos', async () => {
    const data = structuredClone(raster);
    const before = JSON.stringify(data);
    Object.freeze(data.spans_by_row[0].runs[0]);
    Object.freeze(data.spans_by_row[0].runs);
    Object.freeze(data.spans_by_row[0]);
    Object.freeze(data.spans_by_row);
    Object.freeze(data);
    fetch.mockResolvedValue(response(data));
    const result = await rasterizePiece({ idPedido: 27, idPieza: 51, resolutionMm: 5, geometry: 'must not be sent', cantidad: 99 });
    expect(fetch).toHaveBeenCalledWith(`${API_URL}/api/optimization/rasterize`, expect.objectContaining({
      method: 'POST', body: JSON.stringify({ id_pedido: 27, id_pieza: 51, resolution_mm: 5 }),
    }));
    expect(result).toBe(data);
    expect(result.spans_by_row).toBe(data.spans_by_row);
    expect(JSON.stringify(data)).toBe(before);
  });

  test('acepta resolución positiva fraccionaria sin lista cerrada', async () => {
    fetch.mockResolvedValue(response({ ...raster, resolution_mm: 2.75 }));
    await rasterizePiece({ idPedido: 27, idPieza: 51, resolutionMm: 2.75 });
    expect(JSON.parse(fetch.mock.calls[0][1].body).resolution_mm).toBe(2.75);
  });

  test('conserva filas sin runs, incluidas por el serializador backend', async () => {
    const data = { ...raster, row_count: 2, spans_by_row: [...raster.spans_by_row, { row: 1, runs: [] }] };
    fetch.mockResolvedValue(response(data));
    await expect(rasterizePiece({ idPedido: 27, idPieza: 51, resolutionMm: 5 })).resolves.toBe(data);
  });

  test.each([401, 403, 404, 409, 500])('start propaga status %s y no filtra detalles internos', async status => {
    fetch.mockResolvedValue(response({ detail: 'INTERNAL SQL stacktrace' }, status));
    await expect(startOptimization(27)).rejects.toMatchObject({ name: 'OptimizationApiError', status });
    await expect(startOptimization(27)).rejects.not.toThrow('INTERNAL');
  });

  test('422 conserva el mensaje funcional seguro del backend', async () => {
    fetch.mockResolvedValue(response({ detail: 'La rejilla excede el límite de recursos.' }, 422));
    await expect(rasterizePiece({ idPedido: 27, idPieza: 51, resolutionMm: 0.01 })).rejects.toMatchObject({ status: 422, message: 'La rejilla excede el límite de recursos.' });
  });

  test('422 estructurado usa mensaje de validación sin volcar el payload', async () => {
    fetch.mockResolvedValue(response({ detail: [{ loc: ['body'], msg: 'internal' }] }, 422));
    await expect(startOptimization(27)).rejects.toThrow('Revisa los datos del pedido');
  });

  test.each([{ id_pedido: 28, estado: 'PENDIENTE' }, { id_pedido: 27, estado: 'EN_OPTIMIZACION' }])('rechaza un start no confirmado: %j', async data => {
    fetch.mockResolvedValue(response(data));
    await expect(startOptimization(27)).rejects.toMatchObject({ status: 200 });
  });

  test.each([
    { spans_by_row: [{ row: 0, runs: [[0, 99]] }] },
    { spans_by_row: [{ row: 0, runs: [[0, 2], [1, 2]] }] },
    { spans_by_row: [{ row: -1, runs: [[0, 2]] }] },
    { spans_by_row: [{ row: 1, runs: [[0, 2]] }] },
    { spans_by_row: [{ row: 0, runs: [[0, 2]] }, { row: 2, runs: [] }] },
    { row_count: 3 },
    { spans_by_row: null }, { occupied_cells: 3 }, { id_pieza: 52 }, { resolution_mm: 10 },
    { geometria: { type: 'CIRCUNFERENCIA', radius_mm: 20 } },
  ])('rechaza respuesta raster inconsistente sin mostrar éxito: %j', async invalid => {
    fetch.mockResolvedValue(response({ ...raster, ...invalid }));
    await expect(rasterizePiece({ idPedido: 27, idPieza: 51, resolutionMm: 5 })).rejects.toBeInstanceOf(OptimizationApiError);
  });

  test('timeout de start produce resultado incierto status 0 sin reintentar POST', async () => {
    vi.useFakeTimers();
    fetch.mockImplementation((url, { signal }) => new Promise((resolve, reject) => {
      signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
    }));
    const result = expect(startOptimization(27, { timeoutMs: 50 })).rejects.toMatchObject({ status: 0 });
    await vi.advanceTimersByTimeAsync(50);
    await result;
    expect(fetch).toHaveBeenCalledOnce();
  });
});
