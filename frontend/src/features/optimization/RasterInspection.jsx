import { useId, useState } from 'react';
import { InspectionViewport } from './InspectionViewport';
import { RasterComparison } from './RasterComparison';
import { pieceRaster, validInspectionRaster } from './rasterInspectionModel';
import { stockKey, unitKey } from './runContract.js';

export function RasterInspection({ snapshot, group, placements = [], preparation = false }) {
  const id = useId();
  const [chosen, setChosen] = useState('');
  const [grid, setGrid] = useState(true);
  const pieces = snapshot.orders.flatMap(order => order.piezas.filter(piece => group.units.some(u => u.id_pedido === order.id_pedido && u.id_pieza === piece.id_pieza))
    .map(piece => ({ ...piece, orderId: order.id_pedido, key: `${order.id_pedido}:${piece.id_pieza}` })));
  const piece = pieces.find(p => p.key === chosen) ?? pieces[0];
  const raster = piece && pieceRaster(snapshot, piece.orderId, piece.id_pieza);
  const ready = validInspectionRaster(raster);
  return <section className="raster-inspection" aria-label={preparation ? 'Vista previa del vidrio' : 'Detalle de las piezas'}>
    <h3>{group.name} · {group.thickness} mm · {preparation ? 'Vista previa del corte' : 'Detalle de las piezas'}</h3>
    <p>Una vista más detallada puede tardar más en prepararse.</p>
    <p>{snapshot.fixture ? 'Vista ilustrativa con piezas de ejemplo.' : ready ? 'Vista de la pieza disponible.' : 'Este resultado muestra la distribución del corte. Para revisar una pieza con más detalle, abre «Vista previa de piezas».'}</p>
    <label htmlFor={`${id}-piece`}>Pieza para inspeccionar</label>
    <select id={`${id}-piece`} className="ng-control" value={piece?.key ?? ''} onChange={e => setChosen(e.target.value)}>
      {pieces.map(p => <option key={p.key} value={p.key}>Pedido #{p.orderId} · Pieza #{p.id_pieza} · {p.cantidad} unidades</option>)}
    </select>
    {!ready ? <p role="status">Pendiente: vista previa no disponible para esta pieza.</p> : <>
      <p role="status">Preparada · resolución: {raster.resolution_mm} mm por celda · {raster.columns} × {raster.row_count} celdas · {raster.occupied_cells} ocupadas</p>
      <label className="raster-grid-toggle"><input type="checkbox" checked={grid} onChange={e => setGrid(e.target.checked)} />Mostrar celdas</label>
      <InspectionViewport key={piece.key} label="del corte">
        <svg className="raster-cell-view" viewBox={`-0.15 -0.15 ${raster.columns + 0.3} ${raster.row_count + 0.3}`} role="img" aria-label={`Detalle de la pieza #${piece.id_pieza}`} shapeRendering="crispEdges">
          <defs><pattern id={`${id}-grid`} width="1" height="1" patternUnits="userSpaceOnUse"><path d="M 1 0 H 0 V 1" fill="none" stroke="#64748b" strokeWidth="0.025" /></pattern></defs>
          <rect width={raster.columns} height={raster.row_count} fill="white" />
          {raster.spans_by_row.flatMap(({ row, runs }) => runs.map(([start, end], i) => <rect key={`${row}:${i}`} data-raster-run="" x={start} y={row} width={end - start} height="1" fill="#93baf1" />))}
          {grid && <rect data-raster-grid="" width={raster.columns} height={raster.row_count} fill={`url(#${id}-grid)`} stroke="#64748b" strokeWidth="0.025" />}
        </svg>
      </InspectionViewport>
      <p>Azul: superficie de la pieza. Blanco: espacio libre. Esta vista muestra la pieza antes de girarla; consulta la distribución para ver su posición en la plancha.</p>
      {placements.filter(p => p.id_pedido === piece.orderId && p.id_pieza === piece.id_pieza).map(p => <p key={`${stockKey(p)}:${unitKey(p)}`}>Unidad {p.unit_index}: x {p.x_mm} mm · y {p.y_mm} mm · giro recibido {p.rotation_deg}° · {p.material_source === 'PLANCHA' ? 'Plancha' : 'Retazo'} #{p.material_id}, unidad física {p.stock_unit_index}</p>)}
      <details><summary>Comparar forma y detalle del corte · pieza #{piece.id_pieza}</summary>
        <RasterComparison geometry={piece.geometria} piece={piece} raster={{ ...raster, tipo_forma: piece.tipo_forma, cantidad: piece.cantidad }} />
      </details>
    </>}
  </section>;
}
