import { ActionBar, PageCard } from '../../shared/components/PageLayout';
import { EmptyState, FeedbackMessage, FieldError, LoadingState } from '../../shared/components/feedback';
import { useOptimization } from './useOptimization';
import { RasterComparison } from './RasterComparison';
import { orderWorkState } from './workLabels';
import './OptimizationPage.css';

const SHAPES = { RECTANGULO: 'Rectángulo', CIRCUNFERENCIA: 'Circunferencia', POLIGONO_CONVEXO: 'Polígono convexo' };
const stateLabel = orderWorkState;
const dateLabel = value => new Date(value).toLocaleDateString('es-PE');
const materialLabel = (id, flow) => flow.materials.find(material => String(material.id_tipo_vidrio) === String(id))?.nombre
  ?? (flow.materialStatus === 'ready' ? `Material #${id}` : flow.materialStatus === 'error' ? 'Vidrio sin identificar' : 'Consultando vidrio?');

function geometryLabel(piece) {
  const geometry = piece.geometria;
  if (!geometry) return 'Geometría no disponible';
  if (piece.tipo_forma === 'RECTANGULO') return `${geometry.width_mm} × ${geometry.height_mm} mm`;
  if (piece.tipo_forma === 'CIRCUNFERENCIA') return `Radio: ${geometry.radius_mm} mm`;
  const vertices = geometry.vertices_mm;
  if (!Array.isArray(vertices)) return 'Vértices no disponibles';
  return `${vertices.length} vértices (mm): ${vertices.slice(0, 4).map(pair => `(${pair.join(', ')})`).join('; ')}${vertices.length > 4 ? '; …' : ''}`;
}

export function Hu015Rasterization(props) {
  const flow = useOptimization(props);
  const order = flow.selection?.order;
  const selectedPiece = order?.piezas.find(piece => String(piece.id_pieza) === flow.pieceId);
  const rasterIsCurrent = Boolean(flow.raster && flow.raster.id_pedido === order?.id_pedido
    && flow.raster.id_pieza === selectedPiece?.id_pieza);
  const currentRaster = rasterIsCurrent ? flow.raster : null;
  const previewGeometry = currentRaster?.geometria ?? selectedPiece?.geometria;
  const recovery = flow.scope === 'EN_OPTIMIZACION';
  return <PageCard className="optimization-page">
    <header className="optimization-section-heading"><h2>Vista previa de piezas</h2>
      <p>Prepara un pedido y revisa la forma y las medidas de sus piezas antes del corte.</p></header>
    {flow.materialWarning && <FeedbackMessage variant="warning">{flow.materialWarning}</FeedbackMessage>}
    <div className="optimization-columns">
      <section aria-labelledby="optimization-orders-title">
        <h2 id="optimization-orders-title">{recovery ? 'Procesos iniciados' : 'Pedidos pendientes'}</h2>
        <div className="optimization-actions">
          <button type="button" className="ng-button" disabled={flow.list.loading || flow.starting} onClick={flow.refresh}>Actualizar pedidos</button>
          <button type="button" className="ng-button" disabled={flow.starting}
            onClick={() => flow.changeScope(recovery ? 'PENDIENTE' : 'EN_OPTIMIZACION')}>
            {recovery ? 'Ver pedidos pendientes' : 'Recuperar proceso iniciado'}
          </button>
        </div>
        {recovery && <p>Selecciona un pedido en curso para continuar sin volver a iniciarlo.</p>}
        {flow.list.loading ? <LoadingState>Cargando pedidos...</LoadingState>
          : flow.list.error ? <FeedbackMessage variant="error">{flow.list.error}</FeedbackMessage>
            : !flow.list.items.length ? <EmptyState title={recovery ? 'No hay procesos iniciados disponibles.' : 'No hay pedidos pendientes disponibles para iniciar optimización.'} />
              : <ul className="optimization-orders" aria-label={recovery ? 'Pedidos en optimización' : 'Pedidos pendientes'}>
                {flow.list.items.map(item => <li key={item.id_pedido}>
                  <button type="button" className="ng-button optimization-order" aria-pressed={flow.selection?.item.id_pedido === item.id_pedido}
                    disabled={flow.starting} onClick={() => flow.selectOrder(item)}>
                    <strong>Pedido #{item.id_pedido}</strong><span>{item.cliente}</span>
                    <small>{dateLabel(item.fecha_registro)} · {stateLabel(item.estado)}</small>
                  </button>
                </li>)}
              </ul>}
        {flow.list.totalPages > 1 && <nav className="optimization-actions" aria-label="Páginas de pedidos">
          <button type="button" className="ng-button" disabled={flow.page <= 1 || flow.list.loading || flow.starting} onClick={() => flow.goToPage(flow.page - 1)}>Anterior</button>
          <span>Página {flow.page} de {flow.list.totalPages}</span>
          <button type="button" className="ng-button" disabled={flow.page >= flow.list.totalPages || flow.list.loading || flow.starting} onClick={() => flow.goToPage(flow.page + 1)}>Siguiente</button>
        </nav>}
      </section>
      <section aria-labelledby="optimization-order-title">
        <h2 id="optimization-order-title">Pedido seleccionado{flow.selection ? ` #${flow.selection.item.id_pedido}` : ''}</h2>
        {!flow.selection && <EmptyState title="Selecciona un pedido para consultar sus piezas." />}
        {flow.selection?.loading && <LoadingState>Consultando detalle del pedido...</LoadingState>}
        {flow.selection?.error && <FeedbackMessage variant="error">{flow.selection.error}</FeedbackMessage>}
        {order && <>
          <dl className="optimization-facts">
            <div><dt>Cliente</dt><dd>{flow.selection.item.cliente ?? (order.id_cliente ? `Cliente #${order.id_cliente}` : 'Sin cliente asociado')}</dd></div>
            <div><dt>Fecha</dt><dd>{dateLabel(order.fecha_registro)}</dd></div>
            <div><dt>Estado</dt><dd>{stateLabel(order.estado)}</dd></div>
            <div><dt>Piezas del pedido</dt><dd>{order.piezas.length}</dd></div>
          </dl>
          {!order.piezas.length ? <FeedbackMessage variant="warning">El pedido no contiene piezas disponibles. No se puede iniciar la optimización.</FeedbackMessage>
            : <div className="optimization-table-scroll"><table className="optimization-pieces">
              <caption>Piezas del pedido #{order.id_pedido}</caption>
              <thead><tr><th scope="col">Pieza</th><th scope="col">Forma y medidas</th><th scope="col">Cantidad</th><th scope="col">Vidrio y espesor</th></tr></thead>
              <tbody>{order.piezas.map(piece => <tr key={piece.id_pieza}>
                <th scope="row">#{piece.id_pieza}</th>
                <td>{SHAPES[piece.tipo_forma] ?? piece.tipo_forma}<small>{geometryLabel(piece)}</small></td>
                <td>{piece.cantidad}</td>
                <td>{materialLabel(piece.id_tipo_vidrio, flow)}<small>{piece.espesor_mm} mm</small></td>
              </tr>)}</tbody>
            </table></div>}
          {!['PENDIENTE', 'EN_OPTIMIZACION'].includes(order.estado) && <FeedbackMessage variant="warning">El estado actual del pedido no permite preparar la vista previa.</FeedbackMessage>}
        </>}
        {flow.feedback && <FeedbackMessage variant={flow.feedback.variant}>{flow.feedback.message}</FeedbackMessage>}
        {flow.selection?.blocked && !flow.selection.loading && <button type="button" className="ng-button" disabled={flow.starting} onClick={flow.reloadSelection}>Actualizar detalle del pedido</button>}
        <ActionBar><button type="button" className="ng-button ng-button--primary" disabled={!flow.canStart} aria-busy={flow.starting} onClick={flow.start}>
          {flow.starting ? 'Preparando pedido...' : 'Preparar vista previa'}
        </button></ActionBar>
      </section>
    </div>
    <section className="optimization-raster" aria-labelledby="optimization-raster-title">
      <h2 id="optimization-raster-title">Vista de la pieza</h2>
      {!flow.canChoosePiece && <p>Prepara un pedido para consultar la vista previa de sus piezas.</p>}
      <form onSubmit={flow.rasterize} noValidate>
        <div className="ng-field-grid">
          <div className="ng-field"><label htmlFor="optimization-piece">Pieza del pedido</label>
            <select id="optimization-piece" className="ng-control" value={flow.pieceId} disabled={!flow.canChoosePiece} onChange={event => flow.changePiece(event.target.value)}>
              <option value="">Selecciona una pieza</option>
              {order?.piezas.map(piece => <option key={piece.id_pieza} value={piece.id_pieza}>Pieza #{piece.id_pieza} · {SHAPES[piece.tipo_forma]} · Cantidad: {piece.cantidad}</option>)}
            </select>
          </div>
          <div className="ng-field"><label htmlFor="optimization-resolution">Detalle de la vista (mm)</label>
            <input id="optimization-resolution" className="ng-control" type="number" min="0" step="any" required
              value={flow.resolution} disabled={!flow.canChoosePiece} onChange={event => flow.changeResolution(event.target.value)}
              aria-invalid={!flow.validResolution} aria-describedby={!flow.validResolution ? 'optimization-resolution-error' : 'optimization-resolution-help'} />
            <p id="optimization-resolution-help">Usa una medida mayor que 0 mm. Una medida menor muestra más detalle y puede tardar más.</p>
            <FieldError id="optimization-resolution-error">{!flow.validResolution && 'El detalle de la vista debe ser una medida mayor que 0.'}</FieldError>
          </div>
        </div>
        <ActionBar><button type="submit" className="ng-button ng-button--primary" disabled={!flow.canRasterize} aria-busy={flow.rasterizing}>
          {flow.rasterizing ? 'Preparando vista previa...' : 'Ver pieza'}
        </button></ActionBar>
      </form>
      {flow.rasterizing && <LoadingState>Preparando vista de la pieza #{flow.pieceId} con detalle de {flow.resolution} mm/celda...</LoadingState>}
      {flow.rasterError && <FeedbackMessage variant="error">{flow.rasterError}</FeedbackMessage>}
      {flow.raster && <section className="optimization-result" aria-label="Detalle de la pieza">
        <FeedbackMessage variant="success" title="Vista previa lista">La forma de la pieza está lista para revisar.</FeedbackMessage>
        <dl className="optimization-facts">
          <div><dt>Pedido / pieza</dt><dd>#{flow.raster.id_pedido} / #{flow.raster.id_pieza}</dd></div>
          <div><dt>Tipo de forma</dt><dd>{SHAPES[flow.raster.tipo_forma]}</dd></div>
          <div><dt>Cantidad</dt><dd>{flow.raster.cantidad}</dd></div>
          <div><dt>Resolución</dt><dd>{flow.raster.resolution_mm} mm/celda</dd></div>
          <div><dt>Filas</dt><dd>{flow.raster.row_count}</dd></div>
          <div><dt>Columnas</dt><dd>{flow.raster.columns}</dd></div>
          <div><dt>Celdas ocupadas</dt><dd>{flow.raster.occupied_cells}</dd></div>
          <div><dt>Vidrio</dt><dd>{materialLabel(flow.raster.id_tipo_vidrio, flow)}</dd></div>
          <div><dt>Espesor</dt><dd>{flow.raster.espesor_mm} mm</dd></div>
        </dl>
        <p>La vista muestra una pieza del pedido. La cantidad indica cuántas unidades se necesitan.</p>
      </section>}
      {flow.canChoosePiece && selectedPiece && <RasterComparison
        geometry={previewGeometry}
        raster={currentRaster}
        piece={selectedPiece}
        rasterizing={flow.rasterizing}
      />}
    </section>
  </PageCard>;
}
