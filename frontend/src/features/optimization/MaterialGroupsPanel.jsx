import { useId, useState } from 'react';
import { RasterInspection } from './RasterInspection';
import { groupRasterReady } from './rasterInspectionModel';

export function MaterialGroupsPanel({ groups, unresolved, snapshot, completedGroups }) {
  const id = useId();
  const [chosen, setChosen] = useState('');
  const group = groups.find(g => g.id === chosen) ?? groups[0];
  return <section className="first-fit-section" aria-labelledby={`${id}-title`}>
    <h2 id={`${id}-title`}>Grupos detectados</h2>
    <p>Compatibilidad visual por material y espesor. {snapshot ? 'Selección preparada; la ejecución conserva este snapshot.' : 'Vista previa automática de la selección; preparación final pendiente.'}</p>
    {!!unresolved.length && <p role="status">Falta detalle de material, espesor o cantidad en pedidos {unresolved.map(n => `#${n}`).join(', ')}. No se presupone compatibilidad.</p>}
    <ul className="first-fit-groups">{groups.map(g => {
      const sheet = g.containers.find(c => c.material_source === 'PLANCHA');
      return <li key={g.id}><strong>{g.name} · {g.thickness} mm</strong>
        <span>{g.units.length} piezas · pedidos {g.orders.map(n => `#${n}`).join(', ')}</span>
        <span>{sheet ? `Plancha base #${sheet.material_id} · ${sheet.material_width_mm} × ${sheet.material_height_mm} mm` : 'El servidor asignará el material durante la ejecución'}</span>
        <span>Estado: {completedGroups.includes(g.id) ? 'Evaluado' : snapshot && sheet && groupRasterReady(snapshot, g) ? 'Listo' : 'Pendiente'}</span>
      </li>;
    })}</ul>
    {snapshot && group && <section aria-labelledby={`${id}-raster`}>
      <h2 id={`${id}-raster`}>Preparación raster · antes de optimizar</h2>
      <div className="first-fit-group-select"><label htmlFor={`${id}-select`}>Grupo para preparar raster</label>
        <select className="ng-control" id={`${id}-select`} value={group.id} onChange={e => setChosen(e.target.value)}>
          {groups.map(g => <option key={g.id} value={g.id}>{g.name} · {g.thickness} mm</option>)}
        </select></div>
      <RasterInspection key={group.id} snapshot={snapshot} group={group} preparation />
    </section>}
  </section>;
}
