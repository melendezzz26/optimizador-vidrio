import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { execFileSync } from 'node:child_process';
import { CRITICAL_E2E_SPECS } from '../e2e/criticalSpecs.js';
import E2EGateReporter, { evaluateE2EGate } from '../e2e/e2eGateReporter.js';
import { B02_TITLE, createPlan, E2E_PHASES, E2E_PROJECTS, phaseArguments, phaseFor, phaseSettings,
  readCombinedEvidence, readEvidence, validatePhase, validatePlan, writeEvidence } from '../e2e/e2ePhases.js';

const context = { schemaVersion: 1, runId: 'current-run', sha: 'a'.repeat(40), startedAt: '2026-11-05T00:00:00.000Z' };
const record = (file, project, title) => ({ id: `${project}/${file}/${title}`, project, file, title,
  expectedStatus: 'passed', phase: phaseFor({ file, title }) });
const inventory = () => [...CRITICAL_E2E_SPECS.flatMap(file => E2E_PROJECTS.map(project => record(file, project, 'flujo principal'))),
  ...E2E_PROJECTS.map(project => record(CRITICAL_E2E_SPECS[0], project, 'flujo alternativo')),
  ...E2E_PROJECTS.map(project => record('optimization-comparison.spec.js', project, B02_TITLE))];
const plan = () => createPlan(context, [...E2E_PROJECTS], inventory());
const report = (phase, manifest = plan()) => ({ ...context, phase, planDigest: manifest.digest, projects: [...E2E_PROJECTS],
  startedAt: '2026-11-05T00:00:01.000Z', finishedAt: '2026-11-05T00:00:02.000Z', status: 'passed', errors: [],
  tests: manifest.tests.filter(test => test.phase === phase).map(test => ({ ...test, outcome: 'expected', statuses: ['passed'], annotations: [] })) });

function evidence(t) {
  const directory = mkdtempSync(path.join(tmpdir(), 'newglass-e2e-gate-'));
  t.after(() => {
    assert.equal(path.dirname(directory), path.resolve(tmpdir()));
    rmSync(directory, { recursive: true });
  });
  const manifest = plan();
  writeEvidence(path.join(directory, 'plan.json'), manifest);
  for (const phase of E2E_PHASES) writeEvidence(path.join(directory, `${phase}.json`), report(phase, manifest));
  return directory;
}

function joint(directory, identity = context) {
  const value = readCombinedEvidence(directory, identity);
  return evaluateE2EGate({ tests: value.tests, projects: value.plan.projects });
}

test('el reporter real aplaza cobertura global de B02 y persiste su evidencia independiente', t => {
  const directory = evidence(t);
  // evidence() ya creó los reportes sintéticos: esta prueba usa otro destino
  // vacío para que la escritura exclusiva del reporter sea parte de la prueba.
  const target = path.join(directory, 'reporter');
  const reporterContext = { ...context, sha: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8', windowsHide: true }).trim() };
  const manifest = createPlan(reporterContext, [...E2E_PROJECTS], inventory());
  mkdirSync(target);
  writeEvidence(path.join(target, 'context.json'), reporterContext);
  writeEvidence(path.join(target, 'plan.json'), manifest);
  const keys = ['NEWGLASS_E2E_PHASE', 'NEWGLASS_E2E_RUN_DIR'];
  const previous = keys.map(key => process.env[key]);
  t.after(() => keys.forEach((key, index) => {
    if (previous[index] === undefined) delete process.env[key];
    else process.env[key] = previous[index];
  }));
  process.env.NEWGLASS_E2E_PHASE = 'b02'; process.env.NEWGLASS_E2E_RUN_DIR = target;
  const tests = manifest.tests.filter(test => test.phase === 'b02').map(test => ({
    ...test, parent: { project: () => ({ name: test.project }) }, location: { file: test.file },
    annotations: [], results: [{ status: 'passed' }], outcome: () => 'expected',
  }));
  const reporter = new E2EGateReporter();
  reporter.onBegin({ projects: E2E_PROJECTS.map(name => ({ name })), rootDir: process.cwd() }, { allTests: () => tests });
  assert.equal(reporter.onEnd({ status: 'passed' }), undefined);
  assert.equal(validatePhase(readEvidence(path.join(target, 'b02.json')), manifest, 'b02').length, 2);
});

test('B02 aislado no exige cobertura global; la unión exige todos los escenarios del inventario', t => {
  const manifest = plan();
  assert.equal(validatePhase(report('b02', manifest), manifest, 'b02').length, 2);
  assert.equal(evaluateE2EGate({ tests: report('b02', manifest).tests, projects: E2E_PROJECTS }).ok, false);
  const directory = evidence(t);
  assert.equal(joint(directory).ok, true);
  assert.equal(readCombinedEvidence(directory, context).tests.length, inventory().length);
});

test('las dos selecciones son complementarias y B02 conserva su título exacto', () => {
  assert.deepEqual(phaseArguments('b02'), ['test', '--grep', B02_TITLE]);
  assert.deepEqual(phaseArguments('remaining'), ['test', '--grep-invert', B02_TITLE]);
  assert.throws(() => phaseArguments('unknown'), /fase desconocida/);
  assert.equal(phaseSettings({}), null);
  assert.throws(() => phaseSettings({ NEWGLASS_E2E_PHASE: 'b02' }), /directorio absoluto/);
  assert.throws(() => phaseSettings({ NEWGLASS_E2E_PHASE: 'unknown' }), /fase E2E inválida/);
});

test('el inventario rechaza proyectos, B02 y specs críticos ausentes, incluso antes de ejecutar', () => {
  assert.throws(() => createPlan(context, ['chromium-desktop'], inventory()), /proyectos/);
  assert.throws(() => createPlan(context, E2E_PROJECTS, inventory().filter(test => test.phase !== 'b02')), /B02/);
  assert.throws(() => createPlan(context, E2E_PROJECTS, inventory().filter(test => test.file !== CRITICAL_E2E_SPECS[0])), /spec crítico ausente/);
  const manifest = plan(); manifest.tests.pop();
  assert.throws(() => validatePlan(manifest, context), /digest/);
});

for (const field of ['runId', 'sha', 'planDigest']) {
  test(`un reporte antiguo o ajeno falla por ${field}`, t => {
    const directory = evidence(t), stale = report('b02');
    stale[field] = 'stale';
    writeFileSync(path.join(directory, 'b02.json'), JSON.stringify(stale));
    assert.throws(() => joint(directory), /otra ejecución, SHA o inventario/);
  });
}

test('un inventario de otra invocación no puede certificar la ejecución actual', t => {
  assert.throws(() => joint(evidence(t), { ...context, runId: 'next-run' }), /otra ejecución/);
});

test('los reportes son de escritura única y no se pueden sobrescribir con otra fase', t => {
  const directory = evidence(t);
  assert.throws(() => writeEvidence(path.join(directory, 'b02.json'), report('b02')), /EEXIST/);
  const swapped = report('remaining');
  assert.throws(() => validatePhase(swapped, plan(), 'b02'), /reporte de fase inválido/);
});

for (const file of ['plan.json', 'b02.json', 'remaining.json']) {
  test(`un archivo ausente o corrupto falla: ${file}`, t => {
    const directory = evidence(t), target = path.join(directory, file);
    writeFileSync(target, '{broken');
    assert.throws(() => joint(directory), /JSON corrupto/);
    rmSync(target);
    assert.throws(() => joint(directory), /evidencia ausente/);
  });
}

for (const mutation of ['missing', 'duplicate', 'wrong-scenario', 'wrong-project', 'no-results', 'bad-annotations']) {
  test(`una fase no puede perder o inventar resultados: ${mutation}`, () => {
    const value = report('remaining');
    if (mutation === 'missing') value.tests.pop();
    if (mutation === 'duplicate') value.tests.push(value.tests[0]);
    if (mutation === 'wrong-scenario') value.tests[0].title = 'otro escenario';
    if (mutation === 'wrong-project') value.projects.pop();
    if (mutation === 'no-results') value.tests[0].statuses = [];
    if (mutation === 'bad-annotations') value.tests[0].annotations = [null];
    assert.throws(() => validatePhase(value, plan(), 'remaining'));
  });
}

for (const status of ['failed', 'timedout', 'interrupted', undefined]) {
  test(`una ejecución no completada falla aunque tenga tests aprobados: ${status}`, () => {
    assert.throws(() => validatePhase({ ...report('b02'), status }, plan(), 'b02'), /incompleta o fallida/);
  });
}

test('errores globales y fechas previas a esta invocación no pasan el gate', () => {
  assert.throws(() => validatePhase({ ...report('b02'), errors: ['global teardown failed'] }, plan(), 'b02'), /errores globales/);
  assert.throws(() => validatePhase({ ...report('b02'), startedAt: '2020-01-01T00:00:00Z' }, plan(), 'b02'), /fechas inválidas/);
});

for (const outcome of ['unexpected', 'flaky', 'skipped']) {
  test(`la unión rechaza ${outcome} aunque otro test del mismo spec haya pasado`, t => {
    const directory = evidence(t), value = report('remaining');
    value.tests[0].outcome = outcome;
    value.tests[0].statuses = [outcome === 'skipped' ? 'skipped' : 'failed'];
    writeFileSync(path.join(directory, 'remaining.json'), JSON.stringify(value));
    assert.equal(joint(directory).ok, false);
  });
}

test('un fallo marcado como esperado no certifica un escenario aprobado', () => {
  const value = report('remaining');
  value.tests[0].statuses = ['failed'];
  assert.equal(evaluateE2EGate({ tests: value.tests, projects: value.projects }).ok, false);
  const tests = inventory(); tests[0].expectedStatus = 'failed';
  assert.throws(() => createPlan(context, E2E_PROJECTS, tests), /escenario inválido/);
});
