// TA-040: un verde del job e2e significa que los E2E críticos se ejecutaron y pasaron.
// Playwright no falla por pruebas omitidas; este reporter sí, salvo omisiones aprobadas.
import path from 'node:path';
import process from 'node:process';
import { execFileSync } from 'node:child_process';
import { CRITICAL_E2E_SPECS } from './criticalSpecs.js';
import { createPlan, E2E_PROJECTS, phaseFor, phaseSettings, readEvidence, validateContext, validatePhase, validatePlan, writeEvidence } from './e2ePhases.js';

// Una omisión solo se aprueba con test.info().annotations.push({ type: 'approved-skip',
// description: 'TA-123: motivo' }) o la anotación equivalente en la declaración.
const APPROVAL_ID = /^(TA|HU|EN|ADR)-\d+\b/;

export function gateEnabled(env = process.env) {
  return env.CI === 'true' || env.NEWGLASS_E2E_GATE === '1';
}

export function evaluateE2EGate({ tests, projects, criticalSpecs = CRITICAL_E2E_SPECS }) {
  const problems = [];
  const approved = [];
  for (const project of E2E_PROJECTS) {
    if (!projects.includes(project)) problems.push(`proyecto obligatorio ausente: ${project}`);
  }
  for (const test of tests) {
    const label = `[${test.project}] ${test.file} › ${test.title}`;
    if (!['expected', 'skipped'].includes(test.outcome)) problems.push(`resultado fallido o inestable: ${label} (${test.outcome})`);
    if (test.expectedStatus && !['passed', 'skipped'].includes(test.expectedStatus)) problems.push(`fallo esperado no certifica éxito: ${label}`);
    if (test.statuses && (!test.statuses.length || test.statuses.some(status => status !== (test.outcome === 'skipped' ? 'skipped' : 'passed')))) {
      problems.push(`resultado fallido o incompleto: ${label}`);
    }
    if (test.outcome !== 'skipped') continue;
    const approval = test.annotations.find(annotation => annotation.type === 'approved-skip'
      && APPROVAL_ID.test(annotation.description ?? ''));
    if (approval) approved.push(`${label} (${approval.description})`);
    else problems.push(`omitida sin aprobación: ${label}`);
  }
  for (const spec of criticalSpecs) {
    for (const project of projects) {
      const passed = tests.some(test => test.file === spec && test.project === project && test.outcome === 'expected');
      if (!passed) problems.push(`spec crítico sin ejecución exitosa: [${project}] ${spec}`);
    }
  }
  return { ok: problems.length === 0, problems, approved };
}

function toPlanRecord(test) {
  return {
    id: test.id,
    project: test.parent.project()?.name ?? '',
    file: path.basename(test.location.file),
    title: test.title,
    expectedStatus: test.expectedStatus,
    phase: phaseFor({ file: path.basename(test.location.file), title: test.title }),
  };
}

function toGateRecord(test) {
  return {
    ...toPlanRecord(test),
    outcome: test.outcome(),
    statuses: test.results.map(result => result.status),
    annotations: [...test.annotations, ...test.results.flatMap(result => result.annotations ?? [])],
  };
}

export default class E2EGateReporter {
  constructor() {
    this.errors = [];
    this.startedAt = new Date().toISOString();
  }

  onBegin(config, suite) {
    this.config = config;
    this.projects = config.projects.map(project => project.name);
    this.suite = suite;
  }

  onError(error) { this.errors.push(error.message ?? String(error)); }

  onEnd(result) {
    const settings = phaseSettings();
    if (!gateEnabled() && !settings) return undefined;
    const tests = this.suite?.allTests().map(toGateRecord) ?? [];
    let gate;
    try {
      if (settings) {
        const context = validateContext(readEvidence(path.join(settings.directory, 'context.json')));
        const sha = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: this.config?.rootDir, encoding: 'utf8', windowsHide: true }).trim();
        if (sha !== context.sha) throw new Error('el SHA del checkout cambió durante la ejecución');
        if (settings.phase === 'plan') {
          if (result.status !== 'passed' || this.errors.length) throw new Error('descubrimiento incompleto o con errores');
          const plan = createPlan(context, this.projects, this.suite.allTests().map(toPlanRecord));
          writeEvidence(path.join(settings.directory, 'plan.json'), plan);
          return undefined;
        }
        const plan = validatePlan(readEvidence(path.join(settings.directory, 'plan.json')), context);
        const report = { ...context, phase: settings.phase, planDigest: plan.digest, projects: this.projects,
          startedAt: this.startedAt, finishedAt: new Date().toISOString(), status: result.status, errors: this.errors, tests };
        writeEvidence(path.join(settings.directory, `${settings.phase}.json`), report);
        validatePhase(report, plan, settings.phase);
      }
      gate = evaluateE2EGate({ tests, projects: this.projects ?? [], ...(settings && { criticalSpecs: [] }) });
      if (result.status !== 'passed' || this.errors.length) gate.problems.push(`ejecución ${result.status}; ${this.errors.length} errores globales`);
    } catch (error) { gate = { problems: [error.message], approved: [] }; }
    const { problems, approved } = gate;
    const ok = problems.length === 0;
    for (const line of approved) console.log(`Gate E2E (TA-040): omisión aprobada ${line}`);
    if (ok) {
      console.log(`\nGate E2E (TA-040): ${tests.length} pruebas, sin omisiones no aprobadas; `
        + (settings ? `fase ${settings.phase} completa; cobertura global pendiente del gate conjunto.`
          : `${CRITICAL_E2E_SPECS.length} specs críticos ejecutados en ${this.projects.length} proyectos.`));
      return undefined;
    }
    console.error(`\nGate E2E (TA-040) fallido:\n- ${problems.join('\n- ')}`);
    return { status: 'failed' };
  }
}
