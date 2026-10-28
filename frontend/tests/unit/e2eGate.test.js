// TA-040: el gate E2E falla ante omisiones no aprobadas y specs críticos sin ejecutar.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';

const e2eDir = new URL('../e2e/', import.meta.url);
const gate = () => import('../e2e/e2eGateReporter.js');
const PROJECTS = ['chromium-desktop', 'chromium-mobile'];

// Corrida simulada: una prueba aprobada por spec crítico y proyecto, más los casos extra.
function run(critical, extra = []) {
  const tests = critical.flatMap(file => PROJECTS.map(project => ({
    project, file, title: 'flujo principal', outcome: 'expected', annotations: [],
  })));
  return [...tests, ...extra];
}

const skipped = (annotations = []) => ({
  project: 'chromium-mobile', file: 'hu015-rasterization.spec.js',
  title: 'HU-015: CIRCUNFERENCIA', outcome: 'skipped', annotations,
});

test('CA-06: el gate solo actúa en CI o con NEWGLASS_E2E_GATE=1', async () => {
  const { gateEnabled } = await gate();
  assert.equal(gateEnabled({}), false);
  assert.equal(gateEnabled({ CI: 'true' }), true);
  assert.equal(gateEnabled({ NEWGLASS_E2E_GATE: '1' }), true);
  assert.equal(gateEnabled({ CI: 'false', NEWGLASS_E2E_GATE: '0' }), false);
});

test('una corrida completa sin omisiones pasa el gate', async () => {
  const { evaluateE2EGate } = await gate();
  const critical = ['a.spec.js', 'b.spec.js'];
  const result = evaluateE2EGate({ tests: run(critical), projects: PROJECTS, criticalSpecs: critical });
  assert.deepEqual(result, { ok: true, problems: [], approved: [] });
});

test('CA-02: una prueba omitida sin aprobación hace fallar el gate y se identifica', async () => {
  const { evaluateE2EGate } = await gate();
  const critical = ['hu015-rasterization.spec.js'];
  const result = evaluateE2EGate({ tests: run(critical, [skipped([{ type: 'skip', description: 'faltan credenciales' }])]),
    projects: PROJECTS, criticalSpecs: critical });
  assert.equal(result.ok, false);
  assert.deepEqual(result.problems,
    ['omitida sin aprobación: [chromium-mobile] hu015-rasterization.spec.js › HU-015: CIRCUNFERENCIA']);
});

test('CA-03: una omisión aprobada con ID válido pasa y se lista; sin ID válido, falla', async () => {
  const { evaluateE2EGate } = await gate();
  const critical = ['hu015-rasterization.spec.js'];
  const approved = evaluateE2EGate({ tests: run(critical, [skipped([{ type: 'approved-skip', description: 'TA-099: navegador sin soporte' }])]),
    projects: PROJECTS, criticalSpecs: critical });
  assert.equal(approved.ok, true);
  assert.deepEqual(approved.approved,
    ['[chromium-mobile] hu015-rasterization.spec.js › HU-015: CIRCUNFERENCIA (TA-099: navegador sin soporte)']);
  for (const description of ['', 'pendiente', 'ta-099 en minúsculas']) {
    const rejected = evaluateE2EGate({ tests: run(critical, [skipped([{ type: 'approved-skip', description }])]),
      projects: PROJECTS, criticalSpecs: critical });
    assert.equal(rejected.ok, false, description);
  }
});

test('CA-04: un spec crítico sin prueba aprobada en algún proyecto hace fallar el gate', async () => {
  const { evaluateE2EGate } = await gate();
  const critical = ['a.spec.js', 'b.spec.js'];
  const onlyDesktopB = run(['a.spec.js']).concat({ project: 'chromium-desktop', file: 'b.spec.js',
    title: 'flujo', outcome: 'expected', annotations: [] });
  assert.deepEqual(evaluateE2EGate({ tests: onlyDesktopB, projects: PROJECTS, criticalSpecs: critical }).problems,
    ['spec crítico sin ejecución exitosa: [chromium-mobile] b.spec.js']);
  const failing = run(critical).map(t => (t.file === 'a.spec.js' ? { ...t, outcome: 'unexpected' } : t));
  assert.equal(evaluateE2EGate({ tests: failing, projects: PROJECTS, criticalSpecs: critical }).ok, false);
  assert.equal(evaluateE2EGate({ tests: [], projects: PROJECTS, criticalSpecs: critical }).problems.length, 4);
});

test('la lista de specs críticos coincide con los specs E2E del repositorio', async () => {
  const { CRITICAL_E2E_SPECS } = await import('../e2e/criticalSpecs.js');
  const onDisk = readdirSync(e2eDir).filter(name => name.endsWith('.spec.js')).sort();
  assert.deepEqual([...CRITICAL_E2E_SPECS].sort(), onDisk);
});

test('playwright.config.js registra el reporter del gate sin quitar los existentes', async () => {
  const { default: config } = await import('../../playwright.config.js');
  const names = config.reporter.map(([name]) => name);
  assert.deepEqual(names, ['list', 'html', './tests/e2e/e2eGateReporter.js']);
});

test('CA-01: HU-015 no depende de variables de entorno ni se omite', () => {
  const source = readFileSync(new URL('hu015-rasterization.spec.js', e2eDir), 'utf8');
  assert.doesNotMatch(source, /HU015_E2E_/);
  assert.doesNotMatch(source, /test\.(skip|fixme)\(/);
});