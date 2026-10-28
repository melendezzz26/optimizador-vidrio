import { useId, useState } from 'react';
import { RasterInspection } from './RasterInspection';
import { groupRasterReady } from './rasterInspectionModel';
import { groupOrdersLabel } from './workLabels';

export function MaterialGroupsPanel({ groups, unresolved, snapshot, completedGroups, showInspection = true }) {
  const id = useId();
  const [chosen, setChosen] = useState('');
  const group = groups.find(g => g.id === chosen) ?? groups[0];
  return <section className="first-fit-section" aria-labelledby={`${id}-title`}>
    <h2 id={`${id}-title`}>Vidrios del pedido</h2>
    <p>{snapshot ? 'Vidrios y piezas revisados. Ya puedes calcular la distribución.' : 'Revisa los pedidos para consultar sus vidrios, espesores y cantidades.'}</p>
    {!!unresolved.length && <p role="status">Falta consultar el vidrio, espesor o cantidad de los pedidos {unresolved.map(n => `#${n}`).join(', ')}.</p>}
    <ul className="first-fit-groups">{groups.map(g => {
      const sheet = g.containers.find(c => c.material_source === 'PLANCHA');
      return <li key={g.id}><strong>{g.name} · {g.thickness} mm</strong>
        <span>{g.units.length} {g.units.length === 1 ? 'pieza' : 'piezas'} · {groupOrdersLabel(g.orders)}</span>
        <span>{sheet ? `Plancha #${sheet.material_id} · ${sheet.material_width_mm} × ${sheet.material_height_mm} mm` : 'El sistema elegirá una plancha o retazo disponible para realizar el corte.'}</span>
        <span>{completedGroups.includes(g.id) ? 'Distribución calculada' : snapshot && (!snapshot.fixture || sheet && groupRasterReady(snapshot, g)) ? 'Listo para calcular' : 'Por revisar'}</span>
      </li>;
    })}</ul>
    {showInspection && snapshot && group && <section aria-labelledby={`${id}-raster`}>
      <h2 id={`${id}-raster`}>Inspección de piezas</h2>
      <div className="first-fit-group-select"><label htmlFor={`${id}-select`}>Vidrio para inspeccionar</label>
        <select className="ng-control" id={`${id}-select`} value={group.id} onChange={e => setChosen(e.target.value)}>
          {groups.map(g => <option key={g.id} value={g.id}>{g.name} · {g.thickness} mm</option>)}
        </select></div>
      <RasterInspection key={group.id} snapshot={snapshot} group={group} preparation />
    </section>}
  </section>;
}
