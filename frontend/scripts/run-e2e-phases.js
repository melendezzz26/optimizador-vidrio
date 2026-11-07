// Cada invocación descubre todos los escenarios y usa directorios nuevos por fase.
import { spawnSync, execFileSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { mkdirSync, mkdtempSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { evaluateE2EGate } from '../tests/e2e/e2eGateReporter.js';
import { E2E_PHASES, phaseArguments, readCombinedEvidence, readEvidence, validatePlan, writeEvidence } from '../tests/e2e/e2ePhases.js';

const frontend = fileURLToPath(new URL('../', import.meta.url));
const cli = createRequire(import.meta.url).resolve('@playwright/test/cli');
const sha = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: frontend, encoding: 'utf8', windowsHide: true }).trim();
if (process.env.GITHUB_SHA && process.env.GITHUB_SHA !== sha) throw new Error('GITHUB_SHA no coincide con el checkout');
if (process.argv.slice(2).some(arg => arg !== '--plan-only')) throw new Error('Solo se admite --plan-only');
const parent = path.join(frontend, 'test-results', 'e2e-phases');
mkdirSync(parent, { recursive: true });
const directory = mkdtempSync(path.join(parent, 'run-'));
const context = { schemaVersion: 1, runId: randomUUID(), sha, startedAt: new Date().toISOString() };
writeEvidence(path.join(directory, 'context.json'), context);
console.log(`E2E actual: SHA ${sha}, run ${context.runId}, evidencia ${directory}`);
const problems = [];
function execute(phase, args) {
  const result = spawnSync(process.execPath, [cli, ...args], {
    cwd: frontend, stdio: 'inherit', windowsHide: true,
    env: { ...process.env, NEWGLASS_E2E_GATE: '1', NEWGLASS_E2E_PHASE: phase, NEWGLASS_E2E_RUN_DIR: directory },
  });
  if (result.status !== 0 || result.error || result.signal) {
    problems.push(`${phase}: proceso fallido (${result.status ?? result.signal ?? result.error?.message})`);
    return false;
  }
  return true;
}

let plan;
try {
  if (!execute('plan', ['test', '--list', '--reporter=./tests/e2e/e2eGateReporter.js'])) throw new Error('no se completó el descubrimiento');
  plan = validatePlan(readEvidence(path.join(directory, 'plan.json')), context);
  console.log(`Inventario actual: ${plan.tests.length} escenarios; ${E2E_PHASES.map(phase => `${phase}=${plan.tests.filter(test => test.phase === phase).length}`).join(', ')}.`);
  if (!process.argv.includes('--plan-only')) {
    // Fail-fast: un fallo real en B02 impide iniciar la segunda fase. La validación
    // final sigue siendo obligatoria y reporta la fase ausente como incompleta.
    for (const phase of E2E_PHASES) if (!execute(phase, phaseArguments(phase))) break;
  }
} catch (error) { problems.push(error.message); }

if (process.argv.includes('--plan-only')) {
  console.log('Solo inventario: no se ejecutaron escenarios ni se certificó cobertura E2E.');
  process.exitCode = problems.length ? 1 : 0;
} else {
  let tests = [];
  let approved = [];
  try {
    const evidence = readCombinedEvidence(directory, context);
    tests = evidence.tests;
    const gate = evaluateE2EGate({ tests, projects: evidence.plan.projects });
    problems.push(...gate.problems);
    approved = gate.approved;
  } catch (error) { problems.push(error.message); }
  const summary = { ...context, ok: problems.length === 0, planned: plan?.tests.length ?? 0,
    validated: tests.length, approved, problems };
  writeEvidence(path.join(directory, 'validation.json'), summary);
  console.log(`Gate conjunto TA-040: ${summary.ok ? 'PASS' : 'FAIL'}, ${summary.validated}/${summary.planned} escenarios validados.`);
  for (const problem of problems) console.error(problem);
  process.exitCode = summary.ok ? 0 : 1;
}
