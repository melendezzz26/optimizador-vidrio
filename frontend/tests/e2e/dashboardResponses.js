const dashboardPaths = new Set([
  '/api/inventory/planchas', '/api/inventory/retazos', '/api/orders', '/api/clients',
]);

export function watchDashboardResponses(page, apiOrigin) {
  const responses = [];
  let currentRequests = new WeakSet();
  page.on('request', request => {
    const url = new URL(request.url());
    if (url.origin === apiOrigin && request.method() === 'GET' && dashboardPaths.has(url.pathname)) {
      currentRequests.add(request);
    }
  });
  page.on('response', response => {
    // A response can arrive after its originating module has unmounted. Only
    // requests started in this visit/refresh belong to its source assertions.
    if (!currentRequests.has(response.request())) return;
    const url = new URL(response.url());
    if (url.origin === apiOrigin && response.request().method() === 'GET' && dashboardPaths.has(url.pathname)) {
      responses.push({ path: url.pathname, query: url.searchParams, status: response.status(), response });
    }
  });
  return {
    responses,
    beginCycle() {
      currentRequests = new WeakSet();
      responses.length = 0;
    },
  };
}
