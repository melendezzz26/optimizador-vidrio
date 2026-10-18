export const calculationState = state => ({
  EN_EJECUCION: 'Procesando', COMPLETADA: 'Distribución lista',
  SIN_SOLUCION: 'No se encontró una distribución posible', FALLIDA: 'No se pudo calcular el corte',
})[state] ?? 'Estado no disponible';

export const orderWorkState = state => ({
  PENDIENTE: 'Pendiente', EN_OPTIMIZACION: 'En preparación', OPTIMIZADO: 'Distribución calculada',
  CONFIRMADO: 'Confirmado', CANCELADO: 'Cancelado',
})[state] ?? 'Estado no disponible';

export function groupOrdersLabel(ids) {
  const names = ids.map(id => `#${id}`);
  return ids.length === 1 ? `Pedido ${names[0]}` : `Pedidos ${names.length > 2
    ? names.slice(0, -1).join(', ') + ' y ' + names.at(-1) : names.join(' y ')}`;
}
