// V1 exposes accepted runs and placements, not a preparation barrier or tested
// orientations. Keep those stages unknown until the visual contract supplies them.
export function OptimizationStages({ state }) {
  const calculating = state.status === 'running';
  const finished = ['completed', 'no_solution'].includes(state.status);
  const failed = state.status === 'failed';
  const hasRun = Boolean(state.optimizationId || state.runId);
  const searchObserved = Boolean(state.activeGroup || state.placements.length || state.completedGroups.length);
  const steps = [
    ['A · Selección de pedidos', state.snapshot ? 'Selección revisada' : state.status === 'preparing' ? 'Revisando selección' : 'Selecciona pedidos', !state.snapshot && !hasRun],
    ['B · Preparación geométrica', hasRun ? 'Sin detalle disponible' : 'Al iniciar el cálculo', false],
    ['C · Orientaciones', hasRun ? 'Sin detalle disponible' : 'Durante el cálculo', false],
    ['D · Colocación de piezas', finished ? 'Cálculo terminado' : failed ? 'Cálculo interrumpido'
      : calculating ? searchObserved ? 'En curso' : 'Esperando avance' : 'Pendiente', calculating && searchObserved],
    ['E · Resultado', state.status === 'completed' ? 'Resultado completo' : state.status === 'no_solution' ? 'Resultado parcial'
      : failed ? 'Cálculo fallido' : 'Pendiente', finished],
  ];
  return <ol className="first-fit-stages" aria-label="Etapas de optimización">
    {steps.map(([label, detail, active]) => <li key={label} aria-current={active ? 'step' : undefined}>
      <span>{label}</span><small>{detail}</small>
    </li>)}
  </ol>;
}
