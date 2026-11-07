import { useState } from 'react';
import { PlacementCanvas } from './PlacementCanvas';
import { resultSnapshot, stockKey, visualPlacement } from './runContract';

const number = value => new Intl.NumberFormat('es-PE', { maximumFractionDigits: 3 }).format(Number(value));
const sourceName = source => `${source.material_source === 'PLANCHA' ? 'Plancha comercial' : 'Retazo de inventario'} #${source.material_id}`;

function SourceDetail({ source, result, pieces, snapshot, requested }) {
  const [open, setOpen] = useState(false);
  const units = result.groups.flatMap(group => group.units);
  const placedArea = pieces.reduce((sum, p) => sum + Number(units.find(u => u.id_pedido === p.id_pedido
    && u.id_pieza === p.id_pieza && u.unit_index === p.unit_index)?.area_mm2 ?? 0), 0);
  const recovered = result.residual_regions.filter(r => stockKey(r) === stockKey(source))
    .reduce((sum, r) => sum + Number(r.area_mm2), 0);
  const material = requested.find(p => p.id_tipo_vidrio === source.id_tipo_vidrio)?.material_nombre
    ?? `Vidrio #${source.id_tipo_vidrio}`;
  const geometry = source.geometria;
  const frame = { ...snapshot, groups: snapshot.groups.map(group => ({ ...group,
    containers: group.containers.filter(s => stockKey(s) === stockKey(source)),
  })).filter(group => group.containers.length) };
  return <details className="comparison-source" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>{sourceName(source)} · unidad {source.stock_unit_index} · {pieces.length} piezas</summary>
    <p>{material} · espesor {source.espesor_mm} mm. La unidad identifica esta fuente dentro de la propuesta.</p>
    <p>{geometry.type === 'RECTANGULO' ? `${geometry.width_mm} × ${geometry.height_mm} mm`
      : geometry.type === 'CIRCUNFERENCIA' ? `Circular · radio ${geometry.radius_mm} mm`
        : `Polígono · vértices (mm): ${geometry.vertices_mm.map(p => `(${p.join(', ')})`).join('; ')}`}</p>
    <dl className="comparison-source-areas">
      <div><dt>Área de la fuente</dt><dd>{number(source.area_mm2)} mm²</dd></div>
      <div><dt>Área de piezas colocadas</dt><dd>{number(placedArea)} mm²</dd></div>
      <div><dt>Área residual total</dt><dd>{number(Number(source.area_mm2) - placedArea)} mm²</dd></div>
      <div><dt>Recuperable potencial</dt><dd>{number(recovered)} mm²</dd></div>
    </dl>
    <ul aria-label={`Piezas en ${sourceName(source)}, unidad ${source.stock_unit_index}`}>
      {pieces.map(p => <li key={`${p.id_pedido}:${p.id_pieza}:${p.unit_index}`}>Pedido #{p.id_pedido} · pieza #{p.id_pieza}
        {' '}· unidad {p.unit_index} · giro {p.rotation_deg}°</li>)}
    </ul>
    {open && <PlacementCanvas snapshot={frame} placements={pieces.map(visualPlacement)} />}
  </details>;
}

export function MaterialTrace({ result, requested = [], compact = false }) {
  if (!result) return <p>El detalle de materiales se mostrará al cargar el resultado guardado.</p>;
  const sources = [...new Map(result.materials_used.map(s => [stockKey(s), s])).values()];
  const sheets = sources.filter(s => s.material_source === 'PLANCHA').length;
  const snapshot = compact ? null : resultSnapshot(result);
  return <section className="comparison-material-trace" aria-label="Materiales propuestos">
    <h3>Materiales propuestos</h3>
    <p>{sheets} planchas comerciales · {sources.length - sheets} retazos de inventario reutilizados</p>
    <p>{result.placed_units} piezas colocadas · {result.unplaced_units.length} pendientes.
      {!result.completo && ' Propuesta parcial: no puede confirmarse.'}</p>
    <p>La simulación no descuenta existencias. Los sobrantes recuperables son potenciales;
      solo se registran como nuevos retazos al confirmar.</p>
    {!sources.length && <p>Este resultado no propone consumir materiales.</p>}
    {compact ? <ul>{sources.map(s => <li key={stockKey(s)}>{sourceName(s)} · unidad {s.stock_unit_index}
      {' '}· vidrio #{s.id_tipo_vidrio} · {s.espesor_mm} mm</li>)}</ul>
      : sources.map(source => <SourceDetail key={stockKey(source)} source={source} result={result}
        snapshot={snapshot} requested={requested} pieces={result.placements.filter(p => stockKey(p) === stockKey(source))} />)}
  </section>;
}

export function InventoryReceipt({ confirmation }) {
  const receipt = confirmation?.receipt;
  if (!receipt) return null;
  return <section className="comparison-inventory-receipt" aria-label="Inventario registrado">
    <h3>Consumo de inventario registrado</h3>
    <ul>{receipt.materials_consumed.map(s => <li key={`${s.source}:${s.material_id}:${s.physical_unit_index}`}>
      {sourceName({ ...s, material_source: s.source })} · unidad {s.physical_unit_index}
    </li>)}</ul>
    <h4>Nuevos retazos registrados</h4>
    {receipt.remnants_created.length ? <ul>{receipt.remnants_created.map(r => <li key={r.remnant_id}>
      Retazo #{r.remnant_id} · {number(r.area_mm2)} mm² · de {sourceName({ ...r.source, material_source: r.source.source })}
      {' '}· unidad {r.source.physical_unit_index}
    </li>)}</ul> : <p>No se registraron nuevos retazos.</p>}
  </section>;
}
