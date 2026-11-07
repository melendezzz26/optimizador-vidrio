// TA-040: protocolo de evidencia de una única ejecución, sin reutilizar reportes.
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { CRITICAL_E2E_SPECS } from './criticalSpecs.js';

export const E2E_PROJECTS = Object.freeze(['chromium-desktop', 'chromium-mobile']);
export const E2E_PHASES = Object.freeze(['b02', 'remaining']);
export const B02_TITLE = 'TA-043 B02 smoke: historia v1 y FF intacta después del upgrade PostgreSQL';
const check = (condition, message) => { if (!condition) throw new Error(message); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const text = value => typeof value === 'string' && value.length > 0;
const time = value => typeof value === 'string' ? Date.parse(value) : NaN;

export const phaseFor = test => test.file === 'optimization-comparison.spec.js' && test.title === B02_TITLE ? 'b02' : 'remaining';
export const phaseArguments = phase => {
  check(E2E_PHASES.includes(phase), `fase desconocida: ${phase}`);
  return ['test', phase === 'b02' ? '--grep' : '--grep-invert', B02_TITLE];
};

export function phaseSettings(env = process.env) {
  if (!env.NEWGLASS_E2E_PHASE && !env.NEWGLASS_E2E_RUN_DIR) return null;
  check(['plan', ...E2E_PHASES].includes(env.NEWGLASS_E2E_PHASE), 'fase E2E inválida');
  check(text(env.NEWGLASS_E2E_RUN_DIR) && path.isAbsolute(env.NEWGLASS_E2E_RUN_DIR), 'falta el directorio absoluto de esta ejecución');
  return { phase: env.NEWGLASS_E2E_PHASE, directory: env.NEWGLASS_E2E_RUN_DIR };
}

export function readEvidence(file) {
  try { return JSON.parse(readFileSync(file, 'utf8')); }
  catch (error) { throw new Error(`evidencia ausente o JSON corrupto: ${file}: ${error.message}`, { cause: error }); }
}

export function writeEvidence(file, value) {
  // Un segundo proceso no puede sobrescribir una fase ni reemplazar evidencia.
  writeFileSync(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
}

export function validateContext(context) {
  check(context?.schemaVersion === 1 && text(context.runId) && /^[a-f0-9]{40}$/.test(context.sha)
    && Number.isFinite(time(context.startedAt)), 'identidad de ejecución inválida');
  return context;
}

function identity(test) {
  return [test.id, test.project, test.file, test.title, test.expectedStatus, test.phase];
}

function validateTests(tests) {
  check(Array.isArray(tests) && tests.length > 0, 'inventario de escenarios vacío o inválido');
  const ids = new Set();
  for (const test of tests) {
    check(test && [test.id, test.project, test.file, test.title].every(text)
      && E2E_PROJECTS.includes(test.project) && CRITICAL_E2E_SPECS.includes(test.file)
      && ['passed', 'skipped'].includes(test.expectedStatus) && test.phase === phaseFor(test), 'escenario inválido');
    check(!ids.has(test.id), `escenario duplicado: ${test.id}`);
    ids.add(test.id);
  }
}

function digest(plan) {
  const { digest: unused, ...body } = plan;
  void unused;
  return createHash('sha256').update(JSON.stringify(body)).digest('hex');
}

export function createPlan(context, projects, tests) {
  const plan = { ...context, projects, tests };
  plan.digest = digest(plan);
  return validatePlan(plan, context);
}

export function validatePlan(plan, context) {
  validateContext(context);
  check(plan?.schemaVersion === 1 && plan.runId === context.runId && plan.sha === context.sha
    && plan.startedAt === context.startedAt, 'inventario de otra ejecución o SHA');
  check(plan.digest === digest(plan), 'inventario corrupto: digest no coincide');
  check(same(plan.projects, E2E_PROJECTS), 'faltan proyectos o cambió el inventario de proyectos');
  validateTests(plan.tests);
  for (const project of E2E_PROJECTS) {
    check(plan.tests.filter(test => test.project === project && test.phase === 'b02').length === 1,
      `B02 debe contener exactamente un escenario en ${project}`);
    check(plan.tests.some(test => test.project === project && test.phase === 'remaining'), `fase restante vacía en ${project}`);
    for (const file of CRITICAL_E2E_SPECS) {
      check(plan.tests.some(test => test.project === project && test.file === file), `spec crítico ausente del inventario: [${project}] ${file}`);
    }
  }
  return plan;
}

export function validatePhase(report, plan, phase) {
  check(report?.schemaVersion === 1 && report.phase === phase && E2E_PHASES.includes(phase), `reporte de fase inválido: ${phase}`);
  check(report.runId === plan.runId && report.sha === plan.sha && report.planDigest === plan.digest,
    `reporte de otra ejecución, SHA o inventario: ${phase}`);
  check(same(report.projects, E2E_PROJECTS), `proyectos incompletos en ${phase}`);
  check(Number.isFinite(time(report.startedAt)) && Number.isFinite(time(report.finishedAt))
    && time(report.startedAt) >= time(plan.startedAt) && time(report.finishedAt) >= time(report.startedAt), `fechas inválidas en ${phase}`);
  check(report.status === 'passed', `ejecución incompleta o fallida: ${phase} (${report.status})`);
  check(Array.isArray(report.errors) && report.errors.length === 0, `errores globales en ${phase}`);
  validateTests(report.tests);
  const expected = plan.tests.filter(test => test.phase === phase);
  const actual = new Map(report.tests.map(test => [test.id, test]));
  check(actual.size === expected.length, `cantidad de escenarios incompleta o inesperada en ${phase}`);
  for (const test of expected) {
    const result = actual.get(test.id);
    check(result && same(identity(result), identity(test)), `escenario ausente o distinto en ${phase}: ${test.id}`);
    check(['expected', 'unexpected', 'flaky', 'skipped'].includes(result.outcome)
      && Array.isArray(result.annotations) && Array.isArray(result.statuses) && result.statuses.length > 0,
    `resultado incompleto o corrupto: ${test.id}`);
    check(result.annotations.every(annotation => annotation && typeof annotation.type === 'string'
      && (annotation.description === undefined || typeof annotation.description === 'string')), `anotaciones corruptas: ${test.id}`);
  }
  return report.tests;
}

export function readCombinedEvidence(directory, context) {
  const plan = validatePlan(readEvidence(path.join(directory, 'plan.json')), context);
  const reports = E2E_PHASES.map(phase => readEvidence(path.join(directory, `${phase}.json`)));
  const tests = reports.flatMap((report, index) => validatePhase(report, plan, E2E_PHASES[index]));
  validateTests(tests);
  check(tests.length === plan.tests.length, 'la unión de fases no cubre el inventario completo');
  return { plan, tests, reports };
}
