// TA-043/B07: explicit comparison-v2 transport. The comparison-v1 API is unchanged.
import { API_URL } from '../../shared/apiUrl';
import { getAccessToken } from '../authentication/authApi';
import { RunContractError, parseConfirmation } from './runContract';
import { parseMaskDescriptor, parseVisualMask } from './visualContract';
import { CATALOG_V2, METHODS_V2, parseComparisonEventV2, parseComparisonV2, parseExecutionV2 } from './comparisonV2Contract';

const check = value => { if (!value) throw new RunContractError(); };
const id = value => Number.isSafeInteger(value) && value > 0;

function maskIdentity(data, comparison, execution) {
  check(data?.profile === 'comparison-v2' && data.schema_version === 2
    && data.comparison_id === comparison.comparison_id && data.execution_id === execution.execution_id
    && data.method === execution.method);
  parseMaskDescriptor(data, comparison.comparison_id);
  return data;
}

export function createComparisonV2Api({ token, fetchImpl = globalThis.fetch } = {}) {
  async function request(path, { method = 'GET', body, key, signal, stream = false, maximum = 16 * 1024 * 1024 } = {}) {
    let response;
    try {
      const access = token ?? getAccessToken();
      response = await fetchImpl(`${API_URL}/api/optimization/comparisons-v2${path}`, { method, signal, cache: 'no-store',
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

  return {
    methods: METHODS_V2,
    catalog: CATALOG_V2,
    history: async (beforeId, signal) => {
      const value = await request(`/history${beforeId ? `?before_id=${beforeId}` : ''}`, { signal });
      check(Array.isArray(value.items) && value.items.length <= 20
        && (value.next_before_id === null || id(value.next_before_id)));
      value.items.forEach(item => check(id(item.comparison_id)
        && ['comparison-v1', 'comparison-v2'].includes(item.profile)
        && typeof item.started_at === 'string' && Number.isFinite(Date.parse(item.started_at))
        && ['EN_EJECUCION', 'COMPLETADA', 'FALLIDA', 'SIN_SOLUCION'].includes(item.status)
        && Array.isArray(item.order_ids) && item.order_ids.every(id)
        && typeof item.confirmed === 'boolean' && typeof item.released === 'boolean'));
      return value;
    },
    start: async (order_ids, key, signal) => parseComparisonV2(await request('', { method: 'POST', body: { order_ids }, key, signal })),
    load: async (comparisonId, signal) => {
      check(id(comparisonId));
      return parseComparisonV2(await request(`/${comparisonId}`, { signal }));
    },
    lookup: async (key, signal) => parseComparisonV2(await request(`/requests/${encodeURIComponent(key)}`, { signal })),
    async choose(current, executionId) {
      check(current.profile === 'comparison-v2' && current.executions.some(e => e.execution_id === executionId));
      const data = parseComparisonV2(await request(`/${current.comparison_id}/selection`, {
        method: 'PUT', body: { execution_id: executionId, expected_version: current.version } }));
      check(data.comparison_id === current.comparison_id && data.selected_execution_id === executionId);
      return data;
    },
    async confirm(current, operation) {
      check(current.profile === 'comparison-v2' && operation.executionId === current.selected_execution_id);
      const data = await request(`/${current.comparison_id}/confirm`, { method: 'POST', key: operation.key,
        body: { execution_id: operation.executionId, expected_version: operation.version } });
      check(data?.profile === 'comparison-v2' && data.schema_version === 2
        && data.comparison_id === current.comparison_id && data.execution_id === operation.executionId
        && id(data.version) && data.version === operation.version + 1);
      parseConfirmation(data.receipt, current.comparison_id);
      return data;
    },
    release: async current => parseComparisonV2(await request(`/${current.comparison_id}/release`, {
      method: 'POST', body: { expected_version: current.version } })),
    async result(comparison, execution, signal) {
      return parseExecutionV2(await request(`/${comparison.comparison_id}/executions/${execution.execution_id}`, { signal }), comparison, execution);
    },
    async manifest(comparison, execution, signal) {
      let offset = 0, value, items = [];
      do {
        value = await request(`/${comparison.comparison_id}/executions/${execution.execution_id}/visual?offset=${offset}`, { signal, maximum: 262144 });
        check(value?.profile === 'comparison-v2' && value.schema_version === 2
          && value.comparison_id === comparison.comparison_id && value.execution_id === execution.execution_id
          && value.method === execution.method && Number.isSafeInteger(value.revision) && value.revision >= 0
          && Number.isSafeInteger(value.execution_sequence) && value.execution_sequence >= 0
          && Number.isSafeInteger(value.processed_units) && Number.isSafeInteger(value.evaluations)
          && Array.isArray(value.items) && value.items.length <= 64
          && (value.next_offset === null || Number.isSafeInteger(value.next_offset)
            && value.next_offset > offset && value.next_offset <= 1024));
        items = [...items, ...value.items.map(item => maskIdentity(item, comparison, execution))];
        check(items.length <= 1024);
        offset = value.next_offset;
      } while (offset !== null);
      return { ...value, items };
    },
    forExecution(comparison, execution) {
      const ownerComparisonId = typeof comparison === 'number' ? comparison : comparison.comparison_id;
      return { async loadVisualMask(runId, descriptor, { signal, ...window } = {}) {
        check(runId === ownerComparisonId);
        const owner = { comparison_id: ownerComparisonId };
        maskIdentity(descriptor, owner, execution);
        const query = new URLSearchParams();
        for (const [key, value] of Object.entries(window)) {
          check(['row_start', 'row_count', 'column_start', 'column_count'].includes(key)
            && Number.isSafeInteger(value) && value >= 0);
          query.set(key, value);
        }
        const value = await request(`/${ownerComparisonId}/executions/${execution.execution_id}/visual/masks/${descriptor.mask_ref}?${query}`,
          { signal, maximum: 262144 });
        maskIdentity(value, owner, execution);
        parseVisualMask({ ...value, schema_version: 2 }, ownerComparisonId, descriptor);
        for (const [key, expected] of Object.entries(window)) check(value.window[key] === expected);
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
              check(encoder.encode(line + '\n').length <= 65536);
              const event = parseComparisonEventV2(JSON.parse(line), comparison);
              if (event.event === 'heartbeat') continue;
              if (event.event !== 'snapshot_required') check(event.sequence === cursor + 1);
              cursor = event.sequence;
              onEvent(event);
            }
            check(encoder.encode(buffer).length <= 65536);
          }
        }
        check((buffer + decoder.decode()).trim() === '');
      } finally { await reader.cancel(); reader.releaseLock(); }
    },
  };
}
