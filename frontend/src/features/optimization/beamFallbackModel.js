// S2-M6: lectura pura del diagnóstico de M6 cuando un límite detuvo la búsqueda
// y las unidades restantes se decidieron con First Fit (contadores fallback_*).
const units = count => `${count} ${count === 1 ? 'unidad' : 'unidades'}`;

export function beamFallbackSummary(diagnostic) {
  const statistics = diagnostic?.statistics;
  if (statistics?.fallback_used !== 1) return null;
  const beam = statistics.fallback_beam_units ?? 0;
  const fallback = statistics.fallback_units ?? 0;
  return `Búsqueda continuada con respaldo First Fit: M6 decidió ${units(beam)} y el respaldo ${units(fallback)}.`;
}
