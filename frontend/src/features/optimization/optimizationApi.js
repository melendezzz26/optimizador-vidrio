import { createApiRequest } from '../../shared/apiRequest';

export class OptimizationApiError extends Error {
  constructor(message, status, options = {}) {
    super(message, options);
    this.name = 'OptimizationApiError';
    this.status = status;
  }
}

const request = createApiRequest(OptimizationApiError, {
  401: 'Tu sesión venció. Inicia sesión otra vez.',
  403: 'No tienes permiso para ejecutar la optimización.',
  404: 'El pedido o la pieza solicitada ya no está disponible.',
  409: 'El estado del pedido cambió. Actualiza sus datos para continuar.',
  500: 'El servidor no pudo completar la operación. Inténtalo otra vez.',
});
const unexpected = () => new OptimizationApiError('El servidor devolvió una respuesta inesperada. Actualiza los datos.', 200);
const positive = value => typeof value === 'number' && Number.isFinite(value) && value > 0;
const positiveInteger = value => Number.isSafeInteger(value) && value > 0;

export async function startOptimization(idPedido, options = {}) {
  const data = await request('/api/optimization/start', {
    timeoutMs: 30000, ...options, method: 'POST', body: { id_pedido: idPedido },
    validationFallback: 'No se pudo iniciar. Revisa los datos del pedido y sus piezas.',
  });
  if (data.id_pedido !== idPedido || data.estado !== 'EN_OPTIMIZACION') throw unexpected();
  return data;
}

// Validar rangos recorre los runs recibidos, nunca expande una matriz de celdas.
function validRaster(data, { idPedido, idPieza, resolutionMm }) {
  if (data.id_pedido !== idPedido || data.id_pieza !== idPieza || data.resolution_mm !== resolutionMm
    || !positive(data.resolution_mm) || !positiveInteger(data.cantidad) || !positiveInteger(data.id_tipo_vidrio)
    || !positive(Number(data.espesor_mm)) || !positiveInteger(data.row_count) || !positiveInteger(data.columns)
    || !positiveInteger(data.occupied_cells) || !Array.isArray(data.spans_by_row)
    || data.spans_by_row.length !== data.row_count) return false;
  const geometry = data.geometria;
  if (!geometry || geometry.type !== data.tipo_forma) return false;
  if (geometry.type === 'RECTANGULO') {
    if (!positive(geometry.width_mm) || !positive(geometry.height_mm)) return false;
  } else if (geometry.type === 'CIRCUNFERENCIA') {
    if (!positive(geometry.radius_mm)) return false;
  } else if (geometry.type === 'POLIGONO_CONVEXO') {
    if (!Array.isArray(geometry.vertices_mm) || geometry.vertices_mm.length < 3
      || !geometry.vertices_mm.every(pair => Array.isArray(pair) && pair.length === 2 && pair.every(Number.isFinite))) return false;
  } else return false;
  let previousRow = -1;
  let occupied = 0;
  for (const [index, entry] of data.spans_by_row.entries()) {
    if (!entry || !Number.isInteger(entry.row) || entry.row !== index || entry.row <= previousRow || entry.row >= data.row_count
      || !Array.isArray(entry.runs)) return false;
    previousRow = entry.row;
    let previousEnd = -1;
    for (const run of entry.runs) {
      if (!Array.isArray(run) || run.length !== 2) return false;
      const [start, end] = run;
      if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || start < previousEnd
        || end <= start || end > data.columns) return false;
      previousEnd = end;
      occupied += end - start;
    }
  }
  return occupied === data.occupied_cells;
}

export async function rasterizePiece({ idPedido, idPieza, resolutionMm }, options = {}) {
  const data = await request('/api/optimization/rasterize', {
    timeoutMs: 30000, ...options, method: 'POST',
    body: { id_pedido: idPedido, id_pieza: idPieza, resolution_mm: resolutionMm },
    validationFallback: 'Revisa el pedido, la pieza y la resolución positiva en mm/celda.',
  });
  if (!validRaster(data, { idPedido, idPieza, resolutionMm })) throw unexpected();
  return data;
}
