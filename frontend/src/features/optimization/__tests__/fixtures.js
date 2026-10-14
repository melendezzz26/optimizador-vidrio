export const pieces = [
  { id_pieza: 51, id_pedido: 27, tipo_forma: 'RECTANGULO', cantidad: 5, id_tipo_vidrio: 7, espesor_mm: '6.0', geometria: { type: 'RECTANGULO', width_mm: 10, height_mm: 5 }, dimensiones: { width_mm: 10, height_mm: 5 } },
  { id_pieza: 52, id_pedido: 27, tipo_forma: 'CIRCUNFERENCIA', cantidad: 1, id_tipo_vidrio: 8, espesor_mm: '4.0', geometria: { type: 'CIRCUNFERENCIA', radius_mm: 20 }, dimensiones: { radius_mm: 20 } },
];
export const order = { id_pedido: 27, id_cliente: 41, fecha_registro: '2026-10-14T12:00:00Z', estado: 'PENDIENTE', id_usuario_registro: 4, piezas: pieces };
export const item = { id_pedido: 27, cliente: 'Cliente local', fecha_registro: order.fecha_registro, estado: 'PENDIENTE' };
export const raster = {
  id_pedido: 27, id_pieza: 51, tipo_forma: 'RECTANGULO', cantidad: 5, id_tipo_vidrio: 7, espesor_mm: '6.0',
  geometria: pieces[0].geometria, resolution_mm: 5, row_count: 1, columns: 2, occupied_cells: 2,
  spans_by_row: [{ row: 0, runs: [[0, 2]] }],
};
export const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
};
