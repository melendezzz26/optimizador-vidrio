import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import { watchDashboardResponses } from '../e2e/dashboardResponses.js';

const apiOrigin = 'http://127.0.0.1:8017';
const dashboardQueries = [
  '/api/inventory/planchas', '/api/inventory/retazos', '/api/clients',
  '/api/orders?estado=PENDIENTE&page=1&limit=1',
  '/api/orders?estado=EN_OPTIMIZACION&page=1&limit=1',
  '/api/orders?page=1&limit=5',
];

function request(path, method = 'GET', origin = apiOrigin) {
  return { url: () => new URL(path, origin).href, method: () => method };
}

function response(started, status = 200) {
  return { url: started.url, request: () => started, status: () => status };
}

function currentDashboard(page) {
  const requests = dashboardQueries.map(path => request(path));
  for (const started of requests) page.emit('request', started);
  for (const started of requests.toReversed()) page.emit('response', response(started));
  return requests;
}

test('collects all six current sources with their actual response, query and status', () => {
  const page = new EventEmitter();
  const { responses } = watchDashboardResponses(page, apiOrigin);
  const started = currentDashboard(page);
  assert.equal(responses.length, 6);
  assert.ok(responses.every(item => item.status === 200));
  const pending = responses.find(item => item.query.get('estado') === 'PENDIENTE');
  assert.equal(pending.query.get('limit'), '1');
  assert.equal(pending.response.request(), started[3]);
});

test('a late response started before returning to Inicio cannot become its seventh source', () => {
  const page = new EventEmitter();
  const { responses, beginCycle } = watchDashboardResponses(page, apiOrigin);
  const previousVisit = request(dashboardQueries[3]);
  page.emit('request', previousVisit);
  beginCycle();
  currentDashboard(page);
  page.emit('response', response(previousVisit));
  assert.equal(responses.length, 6);
  assert.ok(responses.every(item => item.response.request() !== previousVisit));
});

test('multiple navigation cycles isolate old requests even when URLs and permissions match', () => {
  const page = new EventEmitter();
  const { responses, beginCycle } = watchDashboardResponses(page, apiOrigin);
  const first = request('/api/inventory/planchas');
  page.emit('request', first);
  beginCycle();
  const second = request('/api/inventory/retazos');
  page.emit('request', second);
  beginCycle();
  const current = ['/api/inventory/planchas', '/api/inventory/retazos'].map(path => request(path));
  for (const started of current) page.emit('request', started);
  for (const started of [first, current[0], second, current[1]]) page.emit('response', response(started));
  assert.equal(responses.length, 2);
  assert.deepEqual(responses.map(item => item.response.request()), current);
});

test('ignores other origins, authentication, modules and non-GET requests', () => {
  const page = new EventEmitter();
  const { responses } = watchDashboardResponses(page, apiOrigin);
  for (const started of [request('/api/users'), request('/api/auth/me'),
    request('/api/orders', 'POST'), request('/api/orders', 'GET', 'http://127.0.0.1:5173')]) {
    page.emit('request', started);
    page.emit('response', response(started));
  }
  assert.equal(responses.length, 0);
});

test('retains current authorization and server failures for the existing assertions', () => {
  const page = new EventEmitter();
  const { responses } = watchDashboardResponses(page, apiOrigin);
  for (const status of [403, 503]) {
    const started = request('/api/inventory/planchas');
    page.emit('request', started);
    page.emit('response', response(started, status));
  }
  assert.deepEqual(responses.map(item => item.status), [403, 503]);
});

test('a response whose request was never observed in this cycle is excluded', () => {
  const page = new EventEmitter();
  const { responses } = watchDashboardResponses(page, apiOrigin);
  page.emit('response', response(request('/api/orders')));
  assert.equal(responses.length, 0);
});
