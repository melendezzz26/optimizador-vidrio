// Only retain the public admission fields; never render arbitrary server data.
export function admissionDiagnostic(detail) {
  const limit = detail?.limit;
  if (detail?.code !== 'OPTIMIZER_BUSY' || !['active_runs', 'active_runs_per_user'].includes(limit?.name)
      || !Number.isSafeInteger(limit.actual) || limit.actual < 0
      || !Number.isSafeInteger(limit.maximum) || limit.maximum < 0) return null;
  return { code: 'OPTIMIZER_BUSY', name: limit.name, actual: limit.actual, maximum: limit.maximum };
}
