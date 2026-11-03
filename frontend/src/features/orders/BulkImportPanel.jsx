import { useEffect, useId, useRef, useState } from 'react';
import { ListPlus, RefreshCw, X } from 'lucide-react';
import { FeedbackMessage, LoadingState } from '../../shared/components/feedback';
import {
  SHAPE_LABELS, blockingReason, canAddToOrder, describeMeasures, revalidationBody, rowsToPieces,
} from './bulkImportModel';
import { previewImport, validateImport } from './ordersApi';
import './BulkImportPanel.css';

// HU-018: primero se carga el archivo y después se elige el material (SPEC-HU-018 §6.1).
// Las filas observadas se corrigen aquí y se revalidan en el backend (§6.2).
export default function BulkImportPanel({ token, materials = [], onClose, onAdd }) {
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [material, setMaterial] = useState({ tipo_vidrio_id: '', espesor: '' });
  const [drafts, setDrafts] = useState({});
  const controllerRef = useRef(null);
  const titleId = useId();
  const fileId = useId();
  const materialId = useId();
  const thicknessId = useId();
  const fixId = useId();
  const reasonId = useId();

  useEffect(() => () => controllerRef.current?.abort(), []);

  // Una sola petición a la vez: si llega otra, la anterior se cancela y no pisa el resultado.
  async function load(send, { keepPreview = false } = {}) {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setIsLoading(true);
    setError('');
    if (!keepPreview) setPreview(null);
    try {
      const result = await send(controller.signal);
      if (controller.signal.aborted) return;
      setPreview(result);
      setDrafts({});
    } catch (requestError) {
      if (!controller.signal.aborted) setError(requestError.message);
    } finally {
      if (!controller.signal.aborted) setIsLoading(false);
    }
  }

  function handleFile(event) {
    const file = event.target.files?.[0];
    event.target.value = ''; // permite volver a cargar el mismo archivo corregido
    if (file) load(signal => previewImport(file, { signal, token }));
  }

  function revalidate() {
    const body = revalidationBody(preview, drafts);
    load(signal => validateImport(body, { signal, token }), { keepPreview: true });
  }

  const thicknesses = materials.find(type => String(type.id_tipo_vidrio) === String(material.tipo_vidrio_id))?.espesores_mm ?? [];
  const summary = preview?.resumen;
  const observedRows = preview?.filas.filter(row => row.estado !== 'VALIDO') ?? [];
  const reason = blockingReason(preview, material);

  return (
    <section className="orders-import" aria-labelledby={titleId}>
      <div className="orders-import__header">
        <h3 id={titleId}>Importar piezas desde archivo</h3>
        <button type="button" className="orders-import__close" aria-label="Cerrar importación" onClick={onClose}>
          <X size={20} aria-hidden="true" />
        </button>
      </div>
      <p className="orders-import__help">
        Una pieza por fila: <code>TIPO,CANTIDAD,MEDIDAS</code>. Ejemplos: <code>R,3,800,600</code> · <code>C,2,150</code> ·{' '}
        <code>{'P,1,{{120,60},{160,120},{120,60},{160,120}}'}</code>
      </p>

      <div className="orders-field">
        <label htmlFor={fileId}>Archivo CSV o XLSX</label>
        <input id={fileId} type="file" accept=".csv,.xlsx" onChange={handleFile} disabled={isLoading} className="ng-control" />
      </div>

      {isLoading && <LoadingState>Leyendo archivo…</LoadingState>}
      {error && <FeedbackMessage variant="error" title="No se pudo importar el archivo">{error}</FeedbackMessage>}

      {preview && <>
        <p className="orders-import__summary" role="status">
          <strong>{preview.archivo}</strong>: {summary.total} {summary.total === 1 ? 'fila' : 'filas'} · {summary.validas} válidas · {summary.observadas} observadas
        </p>

        <div className="orders-import__table-scroll">
          <table className="orders-import__table">
            <caption>Vista previa del archivo</caption>
            <thead>
              <tr><th scope="col">Fila</th><th scope="col">Tipo</th><th scope="col">Cantidad</th><th scope="col">Medidas</th><th scope="col">Estado</th><th scope="col">Causas</th></tr>
            </thead>
            <tbody>
              {preview.filas.map(row => (
                <tr key={row.fila} className={row.estado === 'VALIDO' ? undefined : 'orders-import__row--observed'}>
                  <th scope="row">{row.fila}</th>
                  <td>{SHAPE_LABELS[row.tipo_forma] ?? '—'}</td>
                  <td>{row.cantidad ?? '—'}</td>
                  <td>{describeMeasures(row)}</td>
                  <td>{row.estado === 'VALIDO' ? 'Válido' : 'Observado'}</td>
                  <td>{row.causas.length ? row.causas.join('; ') : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="orders-import__material">
          <div className="orders-field">
            <label htmlFor={materialId}>Tipo de vidrio para estas piezas</label>
            <select id={materialId} className="ng-control orders-control" value={material.tipo_vidrio_id}
              onChange={event => setMaterial({ tipo_vidrio_id: event.target.value, espesor: '' })}>
              <option value="">Seleccionar…</option>
              {materials.map(type => <option key={type.id_tipo_vidrio} value={type.id_tipo_vidrio}>{type.nombre}</option>)}
            </select>
          </div>
          <div className="orders-field">
            <label htmlFor={thicknessId}>Espesor (mm)</label>
            <select id={thicknessId} className="ng-control orders-control" value={material.espesor} disabled={!material.tipo_vidrio_id}
              onChange={event => setMaterial(current => ({ ...current, espesor: event.target.value }))}>
              <option value="">Espesor…</option>
              {thicknesses.map(thickness => <option key={thickness} value={thickness}>{thickness} mm</option>)}
            </select>
          </div>
        </div>

        {observedRows.length > 0 && (
          <fieldset className="orders-import__fixes" disabled={isLoading}>
            <legend>Corrige las filas observadas</legend>
            {observedRows.map(row => (
              <div className="orders-field" key={row.fila}>
                <label htmlFor={`${fixId}-${row.fila}`}>Fila {row.fila}</label>
                <input id={`${fixId}-${row.fila}`} className="ng-control" value={drafts[row.fila] ?? row.texto}
                  aria-describedby={`${fixId}-${row.fila}-causes`} spellCheck={false}
                  onChange={event => setDrafts(current => ({ ...current, [row.fila]: event.target.value }))} />
                <span id={`${fixId}-${row.fila}-causes`} className="orders-import__causes">{row.causas.join('; ')}</span>
              </div>
            ))}
            <div>
              <button type="button" className="ng-button" onClick={revalidate}>
                <RefreshCw size={18} aria-hidden="true" /> Revalidar
              </button>
            </div>
          </fieldset>
        )}

        <div className="orders-import__actions">
          {reason && <p id={reasonId} className="orders-import__reason">{reason}</p>}
          <button type="button" className="ng-button ng-button--primary" aria-describedby={reason ? reasonId : undefined}
            disabled={isLoading || !canAddToOrder(preview, material)}
            onClick={() => onAdd(rowsToPieces(preview.filas), material)}>
            <ListPlus size={18} aria-hidden="true" /> Agregar al pedido
          </button>
        </div>
      </>}
    </section>
  );
}