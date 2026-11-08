// Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
import { API_URL } from '../../shared/apiUrl';
import { getAccessToken } from '../authentication/authApi';
import { parseRun, parseConfirmation, RunContractError } from './runContract';
import { parseMaskDescriptor, parseVisualMask, parseVisualEvent } from './visualContract';

export const METHODS = ['FF', 'BF', 'WF'];
export const METHOD_NAMES = { FF: 'First Fit', BF: 'Best Fit', WF: 'Worst Fit' };
const id = value => Number.isSafeInteger(value) && value > 0;
const check = value => { if (!value) throw new RunContractError(); };
const profile = data => check(data?.profile === 'comparison-v1' && data.schema_version === 1);
export function parseComparison(data) {
  profile(data);
  check(id(data.comparison_id) && id(data.version) && Array.isArray(data.executions) && data.executions.length === 3
    && new Set(data.executions.map(e => e.execution_id)).size === 3 && METHODS.every(m => data.executions.some(e => e.method === m))
    && Array.isArray(data.requested_pieces) && Array.isArray(data.order_ids) && data.order_ids.every(id)
    && ['EN_EJECUCION', 'COMPLETADA', 'SIN_SOLUCION', 'FALLIDA'].includes(data.status));
  for (const e of data.executions) check(id(e.execution_id) && METHODS.includes(e.method)
    && ['EN_EJECUCION', 'COMPLETADA', 'FALLIDA'].includes(e.status) && typeof e.eligible === 'boolean');
  check(data.selected_execution_id === null || data.executions.some(e => e.execution_id === data.selected_execution_id));
  check(!data.confirmable || data.terminal && !data.released && !data.confirmed && data.selected_execution_id !== null);
  return data;
}

export function parseExecution(data, comparison, execution) {
  profile(data);
  check(data.comparison_id === comparison.comparison_id && data.execution.execution_id === execution.execution_id
    && data.execution.method === execution.method);
  if (data.result) {
    check(data.result.metodo === execution.method && data.result.id_optimizacion === comparison.comparison_id);
    data = { ...data, result: parseRun({ ...data.result, confirmed: false,
      confirmable: data.result.estado === 'COMPLETADA' && data.result.completo }, { methods: METHODS }) };
  }
  return data;
}

function maskIdentity(data, comparisonId, execution) {
  check(data.comparison_id === comparisonId && data.execution_id === execution.execution_id && data.method === execution.method);
  parseMaskDescriptor(data, comparisonId);
  return data;
}

export function parseComparisonEvent(data, comparison) {
  profile(data);
  check(data.comparison_id === comparison.comparison_id && id(data.sequence) && data.data && typeof data.event === 'string');
  const globals = ['comparison_accepted', 'comparison_finished', 'heartbeat', 'snapshot_required'];
  const facts = ['group_started', 'piece_started', 'piece_placed', 'group_completed', 'preparation_started',
    'piece_rasterizing', 'piece_ready', 'preparation_completed', 'orientation_testing', 'source_selected', 'piece_unplaced'];
  check([...globals, ...facts, 'engine_ready', 'engine_started', 'ordering_ready', 'result_persisted', 'execution_failed'].includes(data.event)
    && typeof data.timestamp === 'string' && /(Z|\+00:00)$/.test(data.timestamp) && Number.isFinite(Date.parse(data.timestamp)));
  if (globals.includes(data.event)) check(data.method === null && data.execution_id === null && data.execution_sequence === null);
  else {
    const execution = comparison.executions.find(e => e.execution_id === data.execution_id && e.method === data.method);
    check(execution && id(data.execution_sequence));
    for (const mask of [data.data.mask, data.data.material_mask]) if (mask) maskIdentity(mask, comparison.comparison_id, execution);
    if (data.event === 'preparation_started') check(data.data.metodo === data.method);
    if (facts.includes(data.event)) parseVisualEvent({ schema_version: 2, id_optimizacion: data.comparison_id,
      sequence: data.sequence, occurred_at: data.timestamp, event: data.event, data: data.data }, { methods: METHODS });
    if (data.event === 'result_persisted') check(data.data.execution_id === execution.execution_id && data.data.method === execution.method);
    if (data.event === 'ordering_ready') check(data.data.criterion === 'area_desc_max_side_desc_order_piece_unit_asc'
      && Array.isArray(data.data.units) && data.data.units.length <= 800 && data.data.units.every(u => id(u.id_pedido) && id(u.id_pieza) && id(u.unit_index)));
  }
  return data;
}

export function createComparisonApi({ token, fetchImpl = globalThis.fetch } = {}) {
  async function request(path, { method = 'GET', body, key, signal, stream = false, maximum = 16 * 1024 * 1024 } = {}) {
    let response;
    try {
      const access = token ?? getAccessToken();
      response = await fetchImpl(`${API_URL}/api/optimization/comparisons${path}`, { method, signal, cache: 'no-store',
        headers: { ...(access ? { Authorization: `Bearer ${access}` } : {}), ...(key ? { 'Idempotency-Key': key } : {}),
          ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), Accept: stream ? 'application/x-ndjson' : 'application/json' },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw Object.assign(new Error('No se pudo conectar. Recupera el trabajo antes de iniciar otro.'), { code: 'NETWORK_ERROR', status: 0 });
    }
    async function json() {
      if (!response.body?.getReader) return response.json();
      const reader = response.body.getReader(), decoder = new TextDecoder('utf-8', { fatal: true });
      let size = 0, text = '';
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          size += value.byteLength;
          check(size <= maximum);
          text += decoder.decode(value, { stream: true });
        }
        return JSON.parse(text + decoder.decode());
      } finally { await reader.cancel(); reader.releaseLock(); }
    }
    if (!response.ok) {
      const detail = (await json().catch(() => null))?.detail;
      throw Object.assign(new Error(detail?.message ?? (response.status === 401 ? 'Tu sesión venció.' : 'No se pudo completar la operación.')),
        { status: response.status, code: detail?.code, latestSequence: detail?.latest_sequence });
    }
    return stream ? response : json();
  }
  const api = {
    start: async (order_ids, key, signal) => parseComparison(await request('', { method: 'POST', body: { order_ids }, key, signal })),
    load: async (comparisonId, signal) => { check(id(comparisonId)); return parseComparison(await request(`/${comparisonId}`, { signal })); },
    lookup: async (key, signal) => parseComparison(await request(`/requests/${encodeURIComponent(key)}`, { signal })),
    choose: async (current, executionId) => parseComparison(await request(`/${current.comparison_id}/selection`, {
      method: 'PUT', body: { execution_id: executionId, expected_version: current.version } })),
    release: async current => parseComparison(await request(`/${current.comparison_id}/release`, { method: 'POST', body: { expected_version: current.version } })),
    async confirm(current, operation) {
      const data = await request(`/${current.comparison_id}/confirm`, { method: 'POST', key: operation.key,
        body: { execution_id: operation.executionId, expected_version: operation.version } });
      profile(data); check(data.comparison_id === current.comparison_id && data.execution_id === operation.executionId);
      parseConfirmation(data.receipt, current.comparison_id);
      return data;
    },
    async result(comparison, execution, signal) {
      return parseExecution(await request(`/${comparison.comparison_id}/executions/${execution.execution_id}`, { signal }), comparison, execution);
    },
    async manifest(comparison, execution, signal) {
      let offset = 0, value, items = [];
      do {
        value = await request(`/${comparison.comparison_id}/executions/${execution.execution_id}/visual?offset=${offset}`, { signal, maximum: 262144 });
        profile(value);
        check(value.comparison_id === comparison.comparison_id && value.execution_id === execution.execution_id && value.method === execution.method
          && Array.isArray(value.items) && (value.next_offset === null || id(value.next_offset) && value.next_offset > offset && value.next_offset <= 1024));
        items = [...items, ...value.items.map(m => maskIdentity(m, comparison.comparison_id, execution))];
        check(items.length <= 1024);
        offset = value.next_offset;
      } while (offset !== null);
      return { ...value, items };
    },
    forExecution(comparisonId, execution) {
      return { async loadVisualMask(runId, descriptor, { signal, ...window } = {}) {
        check(runId === comparisonId);
        maskIdentity(descriptor, comparisonId, execution);
        const query = new URLSearchParams();
        for (const [k, v] of Object.entries(window)) {
          check(['row_start', 'row_count', 'column_start', 'column_count'].includes(k) && Number.isSafeInteger(v) && v >= 0);
          query.set(k, v);
        }
        const value = await request(`/${comparisonId}/executions/${execution.execution_id}/visual/masks/${descriptor.mask_ref}?${query}`, { signal, maximum: 262144 });
        profile(value); maskIdentity(value, comparisonId, execution);
        parseVisualMask({ ...value, schema_version: 2 }, comparisonId, descriptor);
        for (const [k, v] of Object.entries(window)) check(value.window[k] === v);
        return value;
      } };
    },
    async observe(comparison, cursor, onEvent, signal) {
      const response = await request(`/${comparison.comparison_id}/events?after_sequence=${cursor}`, { signal, stream: true });
      check(response.headers.get('content-type')?.startsWith('application/x-ndjson') && response.body);
      const reader = response.body.getReader(), decoder = new TextDecoder('utf-8', { fatal: true }), encoder = new TextEncoder();
      let buffer = '';
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          for (let offset = 0; offset < value.length; offset += 4096) {
            buffer += decoder.decode(value.subarray(offset, offset + 4096), { stream: true });
            let newline;
            while ((newline = buffer.indexOf('\n')) >= 0) {
              const line = buffer.slice(0, newline); buffer = buffer.slice(newline + 1);
              check(encoder.encode(line + '\n').length <= 131072);
              const event = parseComparisonEvent(JSON.parse(line), comparison);
              if (event.event === 'heartbeat') continue;
              if (event.event !== 'snapshot_required') check(event.sequence === cursor + 1);
              cursor = event.sequence;
              onEvent(event);
            }
            check(encoder.encode(buffer).length <= 131072);
          }
        }
        check((buffer + decoder.decode()).trim() === '');
      } finally { await reader.cancel(); reader.releaseLock(); }
    },
  };
  return api;
}
