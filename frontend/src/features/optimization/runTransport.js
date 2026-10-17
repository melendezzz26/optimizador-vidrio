import { buildRunRequest, parseConfirmation, parseRun, readNdjson, RunContractError } from './runContract.js';

// Parsing and lifecycle are shared by the real HTTP adapter and test adapters.
export function createRunTransport({ prepare, open, load, confirm } = {}) {
  const pending = () => { throw new Error('Esta operación está pendiente de integración backend.'); };
  return {
    prepare: request => (prepare ?? pending)(buildRunRequest(request.order_ids)),
    loadResult: async (id, options) => parseRun(await (load ?? pending)(id, options)),
    confirm: async id => parseConfirmation(await (confirm ?? pending)(id), id),
    createEventSource(request) {
      const dto = buildRunRequest(request.order_ids);
      let active = true;
      const controller = new AbortController();
      return {
        subscribe(listener, failed, accepted) {
          (async () => {
            try {
              const chunks = await (open ?? pending)(dto, { signal: controller.signal });
              if (active && chunks.optimizationId) accepted?.(chunks.optimizationId);
              for await (const event of readNdjson(chunks)) {
                if (!active) break;
                listener(event);
              }
            } catch (error) {
              if (active) failed?.(Number.isInteger(error.status) ? error : new RunContractError());
            }
          })();
        },
        dispose() { active = false; controller.abort(); },
      };
    },
  };
}
