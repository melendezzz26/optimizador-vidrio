import { buildRunRequest, parseConfirmation, parseRun, readNdjson, RunContractError } from './runContract.js';

// The caller supplies operations once the backend exists. No endpoint or fetch
// is enabled by this interface, and confirmation receives only the run ID.
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
        subscribe(listener, failed) {
          (async () => {
            try {
              for await (const event of readNdjson(await (open ?? pending)(dto, { signal: controller.signal }))) {
                if (!active) break;
                listener(event);
              }
            } catch {
              if (active) failed?.(new RunContractError());
            }
          })();
        },
        dispose() { active = false; controller.abort(); },
      };
    },
  };
}
