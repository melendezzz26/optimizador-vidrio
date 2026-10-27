const dashboardPaths = new Set([
  '/api/inventory/planchas', '/api/inventory/retazos', '/api/orders', '/api/clients',
]);

export function watchDashboardResponses(page, apiOrigin) {
  const responses = [];
  page.on('response', response => {
    const url = new URL(response.url());
    if (url.origin === apiOrigin && response.request().method() === 'GET' && dashboardPaths.has(url.pathname)) {
      responses.push({ path: url.pathname, query: url.searchParams, status: response.status(), response });
    }
  });
  return { responses, beginCycle: () => { responses.length = 0; } };
}
