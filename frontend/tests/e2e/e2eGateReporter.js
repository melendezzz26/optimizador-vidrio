// TA-040: un verde del job e2e significa que los E2E críticos se ejecutaron y pasaron.
// Playwright no falla por pruebas omitidas; este reporter sí, salvo omisiones aprobadas.
import path from 'node:path';
import process from 'node:process';
import { CRITICAL_E2E_SPECS } from './criticalSpecs.js';

// Una omisión solo se aprueba con test.info().annotations.push({ type: 'approved-skip',
// description: 'TA-123: motivo' }) o la anotación equivalente en la declaración.
const APPROVAL_ID = /^(TA|HU|EN|ADR)-\d+\b/;

export function gateEnabled(env = process.env) {
  return env.CI === 'true' || env.NEWGLASS_E2E_GATE === '1';
}

export function evaluateE2EGate({ tests, projects, criticalSpecs = CRITICAL_E2E_SPECS }) {
  const problems = [];
  const approved = [];
  for (const test of tests) {
    if (test.outcome !== 'skipped') continue;
    const label = `[${test.project}] ${test.file} › ${test.title}`;
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

function toGateRecord(test) {
  return {
    project: test.parent.project()?.name ?? '',
    file: path.basename(test.location.file),
    title: test.title,
    outcome: test.outcome(),
    annotations: [...test.annotations, ...test.results.flatMap(result => result.annotations ?? [])],
  };
}

export default class E2EGateReporter {
  onBegin(config, suite) {
    this.projects = config.projects.map(project => project.name);
    this.suite = suite;
  }

  onEnd() {
    if (!gateEnabled()) return undefined;
    const tests = this.suite.allTests().map(toGateRecord);
    const { ok, problems, approved } = evaluateE2EGate({ tests, projects: this.projects });
    for (const line of approved) console.log(`Gate E2E (TA-040): omisión aprobada ${line}`);
    if (ok) {
      console.log(`\nGate E2E (TA-040): ${tests.length} pruebas, sin omisiones no aprobadas; `
        + `${CRITICAL_E2E_SPECS.length} specs críticos ejecutados en ${this.projects.length} proyectos.`);
      return undefined;
    }
    console.error(`\nGate E2E (TA-040) fallido:\n- ${problems.join('\n- ')}`);
    return { status: 'failed' };
  }
}