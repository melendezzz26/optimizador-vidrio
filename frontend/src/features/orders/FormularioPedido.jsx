import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { useAutoAnimate } from '@formkit/auto-animate/react';
import { Loader2, PackagePlus, Plus, Save, Trash2, X } from 'lucide-react';
import { AppShell } from '../../shared/components/AppShell';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';
import { ConfirmDialog, EmptyState, FeedbackMessage, FieldError, LoadingState } from '../../shared/components/feedback';
import CustomPieceEditor from './CustomPieceEditor';
import { createSegments, getDrawingSegmentLength } from './segmentGeometry';
import { createOrder, getOrder, listOrderMaterials, updateOrder } from './ordersApi';
import './NuevoPedido.css';

function restoredPolygonState(verticesMm) {
  if (!Array.isArray(verticesMm) || verticesMm.length < 3) return null;
  const xs = verticesMm.map(([x]) => Number(x));
  const ys = verticesMm.map(([, y]) => Number(y));
  if (![...xs, ...ys].every(Number.isFinite)) return null;
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const span = Math.max(Math.max(...xs) - minX, Math.max(...ys) - minY);
  if (!Number.isFinite(span) || span <= 0) return null;
  const scale = 420 / span;
  const drawingVertices = verticesMm.map(([x, y]) => ({
    x: 190 + (Number(x) - minX) * scale,
    y: 40 + (Number(y) - minY) * scale,
  }));
  const segments = createSegments(drawingVertices).map((segment, index) => ({
    ...segment,
    lengthMm: getDrawingSegmentLength(
      { x: Number(verticesMm[index][0]), y: Number(verticesMm[index][1]) },
      { x: Number(verticesMm[(index + 1) % verticesMm.length][0]), y: Number(verticesMm[(index + 1) % verticesMm.length][1]) },
    ),
  }));
  return { drawing: { vertices: drawingVertices, isClosed: true }, segments };
}

function pieceFromResponse(piece, index, localId) {
  const vertices = piece.tipo_forma === 'POLIGONO_CONVEXO'
    ? piece.geometria?.vertices_mm ?? piece.dimensiones?.vertices ?? []
    : [];
  return {
    id: localId,
    nombre: `Pieza ${index + 1}`,
    tipo_vidrio_id: String(piece.id_tipo_vidrio),
    espesor: String(piece.espesor_mm),
    tipo_forma: piece.tipo_forma,
    cantidad: piece.cantidad,
    dimensiones: piece.tipo_forma === 'POLIGONO_CONVEXO'
      ? { vertices, rawState: restoredPolygonState(vertices) }
      : { ...(piece.dimensiones ?? piece.geometria ?? {}) },
  };
}

function positiveNumber(value) {
  return value !== '' && Number.isFinite(Number(value)) && Number(value) > 0;
}

function validationMessage(piece, field) {
  if (field === 'material' && !piece.tipo_vidrio_id) return 'Selecciona un material.';
  if (field === 'espesor' && !positiveNumber(piece.espesor)) return 'Selecciona un espesor válido.';
  if (field === 'cantidad' && (!Number.isInteger(Number(piece.cantidad)) || Number(piece.cantidad) <= 0)) {
    return 'Ingresa una cantidad entera mayor que 0.';
  }
  if (field === 'width_mm' && !positiveNumber(piece.dimensiones.width_mm)) return 'Ingresa un ancho mayor que 0.';
  if (field === 'height_mm' && !positiveNumber(piece.dimensiones.height_mm)) return 'Ingresa un alto mayor que 0.';
  if (field === 'radius_mm' && !positiveNumber(piece.dimensiones.radius_mm)) return 'Ingresa un radio mayor que 0.';
  return '';
}

function buildPayload(pieces) {
  return {
    piezas: pieces.map((piece) => {
      const base = {
        tipo_forma: piece.tipo_forma,
        id_tipo_vidrio: Number(piece.tipo_vidrio_id),
        espesor_mm: Number(piece.espesor),
        cantidad: Number(piece.cantidad),
      };
      if (piece.tipo_forma === 'RECTANGULO') {
        return { ...base, width_mm: Number(piece.dimensiones.width_mm), height_mm: Number(piece.dimensiones.height_mm) };
      }
      if (piece.tipo_forma === 'CIRCUNFERENCIA') {
        return { ...base, radius_mm: Number(piece.dimensiones.radius_mm) };
      }
      return { ...base, vertices_mm: piece.dimensiones.vertices ?? [] };
    }),
  };
}

export default function FormularioPedido({
  token,
  idPedido = null,
  onCerrar = null,
  onSuccess,
  onSubmittingChange,
  mode = 'create',
  standalone = false,
  user,
  toolbar,
}) {
  const [tiposDisponibles, setTiposDisponibles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorGlobal, setErrorGlobal] = useState('');
  const [loadError, setLoadError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [estadoPedido, setEstadoPedido] = useState('PENDIENTE');
  const [piezas, setPiezas] = useState([]);
  const [touched, setTouched] = useState({});
  const [piezaEnEdicion, setPiezaEnEdicion] = useState(null);
  const [isCancelDialogOpen, setIsCancelDialogOpen] = useState(false);
  const [listaAnimada] = useAutoAnimate();
  const nextPieceIdRef = useRef(0);
  const submittingRef = useRef(false);
  const formId = useId();
  const titleId = useId();
  const editorTitleId = useId();
  const editorDialogRef = useRef(null);
  const editorCloseRef = useRef(null);
  const editorTriggerRef = useRef(null);
  const editing = idPedido !== null && idPedido !== undefined;
  const creating = !editing && mode === 'create';
  const readOnly = editing && estadoPedido !== 'PENDIENTE';

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setIsLoading(true);
      setErrorGlobal('');
      setLoadError('');
      try {
        const [materials, order] = await Promise.all([
          listOrderMaterials({ signal: controller.signal, token }),
          editing ? getOrder(idPedido, { signal: controller.signal, token }) : Promise.resolve(null),
        ]);
        if (controller.signal.aborted) return;
        setTiposDisponibles(materials);
        if (order) {
          setEstadoPedido(order.estado);
          nextPieceIdRef.current = 0;
          setPiezas(order.piezas.map((piece, index) => pieceFromResponse(piece, index, nextPieceIdRef.current++)));
        }
      } catch (error) {
        if (error.name === 'AbortError' || controller.signal.aborted) return;
        setErrorGlobal(error.message);
        setLoadError(error.message);
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [editing, idPedido, token]);

  useEffect(() => {
    if (piezaEnEdicion === null) return undefined;
    const trigger = editorTriggerRef.current;
    editorCloseRef.current?.focus();
    return () => trigger?.focus?.();
  }, [piezaEnEdicion]);

  const actualizarPieza = useCallback((id, field, value) => {
    setPiezas((current) => current.map((piece) => {
      if (piece.id !== id) return piece;
      if (field === 'tipo_vidrio_id') return { ...piece, tipo_vidrio_id: value, espesor: '' };
      if (field === 'espesor') return { ...piece, espesor: value };
      if (field === 'cantidad') return { ...piece, cantidad: value === '' ? '' : Number(value) };
      if (field === 'tipo_forma') {
        const dimensiones = value === 'RECTANGULO' ? { width_mm: '', height_mm: '' }
          : value === 'CIRCUNFERENCIA' ? { radius_mm: '' } : { vertices: [] };
        return { ...piece, tipo_forma: value, dimensiones };
      }
      if (field === 'dimensiones') return { ...piece, dimensiones: value };
      return { ...piece, dimensiones: { ...piece.dimensiones, [field]: value } };
    }));
  }, []);

  function addPiece() {
    const id = nextPieceIdRef.current++;
    setPiezas((current) => [...current, {
      id,
      nombre: `Pieza ${current.length + 1}`,
      tipo_vidrio_id: '',
      espesor: '',
      cantidad: 1,
      tipo_forma: 'RECTANGULO',
      dimensiones: { width_mm: '', height_mm: '' },
    }]);
  }

  function removePiece(id) {
    setPiezas((current) => current.filter((piece) => piece.id !== id)
      .map((piece, index) => ({ ...piece, nombre: `Pieza ${index + 1}` })));
  }

  function openEditor(id) {
    editorTriggerRef.current = document.activeElement;
    setPiezaEnEdicion(id);
  }

  function handleEditorKeyDown(event) {
    if (event.key === 'Escape') {
      event.stopPropagation();
      setPiezaEnEdicion(null);
      return;
    }
    if (event.key !== 'Tab') return;
    const dialog = editorDialogRef.current;
    const controls = [...dialog.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')];
    if (!controls.length) {
      event.preventDefault();
      return;
    }
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (!dialog.contains(document.activeElement)) {
      event.preventDefault();
      first.focus();
    } else if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function fieldProps(piece, field) {
    const id = `${formId}-piece-${piece.id}-${field}`;
    const errorId = `${id}-error`;
    const error = touched[`${piece.id}:${field}`] ? validationMessage(piece, field) : '';
    return {
      id,
      'aria-invalid': error ? 'true' : undefined,
      'aria-describedby': error ? errorId : undefined,
      onBlur: () => setTouched((current) => ({ ...current, [`${piece.id}:${field}`]: true })),
      error: error ? <FieldError id={errorId}>{error}</FieldError> : null,
    };
  }

  function isValid() {
    if (!piezas.length) return false;
    return piezas.every((piece) => {
      if (!piece.tipo_vidrio_id || !positiveNumber(piece.espesor)
        || !Number.isInteger(Number(piece.cantidad)) || Number(piece.cantidad) <= 0) return false;
      if (piece.tipo_forma === 'RECTANGULO') {
        return positiveNumber(piece.dimensiones.width_mm) && positiveNumber(piece.dimensiones.height_mm);
      }
      if (piece.tipo_forma === 'CIRCUNFERENCIA') return positiveNumber(piece.dimensiones.radius_mm);
      return Array.isArray(piece.dimensiones.vertices) && piece.dimensiones.vertices.length >= 3;
    });
  }

  async function saveOrder() {
    if (submittingRef.current || !isValid() || readOnly) return;
    submittingRef.current = true;
    setIsSubmitting(true);
    onSubmittingChange?.(true);
    setErrorGlobal('');
    setSuccessMessage('');
    try {
      const payload = buildPayload(piezas);
      if (editing) await updateOrder(idPedido, payload, { token });
      else await createOrder(payload, { token });
      setSuccessMessage(editing ? 'Pedido actualizado correctamente.' : 'Pedido registrado correctamente.');
      onSuccess?.(editing ? 'update' : 'create');
      if (onCerrar) onCerrar();
      else if (!editing) setPiezas([]);
    } catch (error) {
      setErrorGlobal(error.message);
    } finally {
      submittingRef.current = false;
      setIsSubmitting(false);
      onSubmittingChange?.(false);
    }
  }

  const getThicknesses = (materialId) => tiposDisponibles.find(
    (type) => String(type.id_tipo_vidrio) === String(materialId),
  )?.espesores_mm ?? [];

  const content = (
    <>
      {standalone && <PageHeader
        context={editing ? 'Gestión de pedidos' : 'Registro de pedido'}
        title={editing ? `Pedido #${idPedido}` : 'Nuevo pedido'}
        description={editing ? 'Revisa o actualiza las piezas del pedido.' : 'Configura el material, espesor y medidas de cada pieza requerida.'}
        titleId={titleId}
        icon={PackagePlus}
      />}
      <PageCard as="section" aria-labelledby={standalone ? titleId : undefined}>
        {isLoading && <LoadingState>{editing ? 'Cargando pedido…' : 'Cargando materiales…'}</LoadingState>}
        {errorGlobal && <FeedbackMessage variant="error" title="No se pudo completar la operación">{errorGlobal}</FeedbackMessage>}
        {successMessage && <FeedbackMessage variant="success">{successMessage}</FeedbackMessage>}
        {readOnly && <FeedbackMessage variant="warning" title="Pedido en modo lectura">El estado {estadoPedido} no permite modificar sus piezas.</FeedbackMessage>}

        {!isLoading && (!loadError || creating) && <>
          <section className="orders-section">
            <div className="orders-section__header">
              <div>
                <h2>Piezas del pedido</h2>
                <p className="orders-section__description">{readOnly ? 'Detalle de las piezas solicitadas.' : 'Agrega y configura todas las piezas del pedido.'}</p>
              </div>
              {!readOnly && <button type="button" className="ng-button ng-button--primary" onClick={addPiece} disabled={isSubmitting}>
                <Plus size={18} /> Agregar pieza
              </button>}
            </div>

            <div ref={listaAnimada}>
              {!piezas.length ? <EmptyState title="No hay piezas agregadas" description={readOnly ? 'Este pedido no contiene piezas.' : 'Haz clic en «Agregar pieza» para comenzar.'} /> : (
                <div className="orders-pieces">
                  {piezas.map((piece, index) => {
                    const ids = Object.fromEntries(['material', 'espesor', 'forma', 'cantidad', 'ancho', 'alto', 'radio']
                      .map((field) => [field, `${formId}-piece-${piece.id}-${field}`]));
                    const materialField = fieldProps(piece, 'material');
                    const thicknessField = fieldProps(piece, 'espesor');
                    const quantityField = fieldProps(piece, 'cantidad');
                    return <div className="orders-piece" key={piece.id}>
                      <div className="orders-piece__header">
                        <div className="orders-piece__identity">
                          <div className="orders-piece__index">{index + 1}</div>
                          <div className="orders-piece__details"><strong>{piece.nombre}</strong><span>Material y geometría propios</span></div>
                        </div>
                        {!readOnly && <button type="button" className="orders-remove-button" onClick={() => removePiece(piece.id)} aria-label={`Eliminar ${piece.nombre}`} disabled={isSubmitting}>
                          <Trash2 size={18} />
                        </button>}
                      </div>
                      <div className="orders-fields-row orders-fields-row--configuration">
                        <div className="orders-field">
                          <label htmlFor={ids.material}>Material</label>
                          <select {...materialField} value={piece.tipo_vidrio_id} onChange={(event) => actualizarPieza(piece.id, 'tipo_vidrio_id', event.target.value)} disabled={readOnly || isSubmitting} className="ng-control orders-control orders-control--material">
                            <option value="">Seleccionar…</option>
                            {tiposDisponibles.map((type) => <option key={type.id_tipo_vidrio} value={type.id_tipo_vidrio}>{type.nombre}</option>)}
                          </select>{materialField.error}
                        </div>
                        <div className="orders-field">
                          <label htmlFor={ids.espesor}>Espesor</label>
                          <select {...thicknessField} value={piece.espesor} onChange={(event) => actualizarPieza(piece.id, 'espesor', event.target.value)} disabled={readOnly || isSubmitting || !piece.tipo_vidrio_id} className="ng-control orders-control orders-control--thickness">
                            <option value="">Espesor…</option>
                            {getThicknesses(piece.tipo_vidrio_id).map((thickness) => <option key={thickness} value={thickness}>{thickness} mm</option>)}
                          </select>{thicknessField.error}
                        </div>
                        <div className="orders-field">
                          <label htmlFor={ids.forma}>Forma</label>
                          <select id={ids.forma} value={piece.tipo_forma} onChange={(event) => {
                            actualizarPieza(piece.id, 'tipo_forma', event.target.value);
                            if (event.target.value === 'POLIGONO_CONVEXO') openEditor(piece.id);
                          }} disabled={readOnly || isSubmitting} className="ng-control orders-control orders-control--shape">
                            <option value="RECTANGULO">Rectángulo / Cuadrado</option>
                            <option value="CIRCUNFERENCIA">Círculo</option>
                            <option value="POLIGONO_CONVEXO">Polígono convexo</option>
                          </select>
                        </div>
                        <div className="orders-field">
                          <label htmlFor={ids.cantidad}>Cant.</label>
                          <input {...quantityField} id={ids.cantidad} type="number" min="1" step="1" value={piece.cantidad} onChange={(event) => actualizarPieza(piece.id, 'cantidad', event.target.value)} disabled={readOnly || isSubmitting} className="ng-control orders-control orders-control--quantity" />{quantityField.error}
                        </div>
                      </div>
                      <div className="orders-fields-row orders-fields-row--measurements">
                        {piece.tipo_forma === 'RECTANGULO' && ['width_mm', 'height_mm'].map((field) => {
                          const label = field === 'width_mm' ? 'Ancho (mm)' : 'Alto (mm)';
                          const fieldId = ids[field === 'width_mm' ? 'ancho' : 'alto'];
                          const props = fieldProps(piece, field);
                          return <div className="orders-field" key={field}>
                            <label htmlFor={fieldId}>{label}</label>
                            <input {...props} id={fieldId} type="number" min="0" step="any" value={piece.dimensiones[field]} onChange={(event) => actualizarPieza(piece.id, field, event.target.value)} disabled={readOnly || isSubmitting} className="ng-control orders-control orders-control--dimension" />{props.error}
                          </div>;
                        })}
                        {piece.tipo_forma === 'CIRCUNFERENCIA' && (() => {
                          const props = fieldProps(piece, 'radius_mm');
                          return <div className="orders-field"><label htmlFor={ids.radio}>Radio (mm)</label>
                            <input {...props} id={ids.radio} type="number" min="0" step="any" value={piece.dimensiones.radius_mm} onChange={(event) => actualizarPieza(piece.id, 'radius_mm', event.target.value)} disabled={readOnly || isSubmitting} className="ng-control orders-control orders-control--dimension" />{props.error}
                          </div>;
                        })()}
                        {piece.tipo_forma === 'POLIGONO_CONVEXO' && <div className="orders-polygon-status">
                          {piece.dimensiones.vertices?.length ? <span className="orders-polygon-status__complete">✓ Geometría cargada</span> : <span className="orders-polygon-status__pending">Falta dibujar</span>}
                          <button type="button" className="ng-button orders-editor-open" onClick={() => openEditor(piece.id)} disabled={isSubmitting}>{readOnly ? 'Ver dibujo' : 'Editar dibujo'}</button>
                        </div>}
                      </div>
                    </div>;
                  })}
                </div>
              )}
            </div>
          </section>

          <ActionBar>
            {onCerrar && <button type="button" className="ng-button" onClick={onCerrar} disabled={isSubmitting}><X size={18} /> Cerrar</button>}
            {standalone && creating && <button type="button" className="ng-button" onClick={() => setIsCancelDialogOpen(true)} disabled={isSubmitting}><X size={18} /> Cancelar</button>}
            {!readOnly && <button type="button" className="ng-button ng-button--primary" onClick={saveOrder} disabled={!isValid() || isSubmitting}>
              {isSubmitting ? <Loader2 size={18} className="ng-loading-icon" /> : <Save size={18} />}
              {isSubmitting ? 'Guardando…' : editing ? 'Guardar cambios' : 'Guardar pedido'}
            </button>}
          </ActionBar>
        </>}
      </PageCard>

      <ConfirmDialog open={isCancelDialogOpen} title="¿Limpiar el pedido?" confirmLabel="Limpiar piezas"
        onConfirm={() => { setPiezas([]); setErrorGlobal(''); setSuccessMessage(''); setIsCancelDialogOpen(false); }}
        onCancel={() => setIsCancelDialogOpen(false)}>
        <p>Se quitarán todas las piezas agregadas. Esta acción no se puede deshacer.</p>
      </ConfirmDialog>

      {piezaEnEdicion !== null && <div className="orders-editor-backdrop">
        <div ref={editorDialogRef} className="orders-editor-dialog" role="dialog" aria-modal="true" aria-labelledby={editorTitleId} tabIndex={-1} onKeyDown={handleEditorKeyDown}>
          <div className="orders-editor-dialog__header">
            <h3 id={editorTitleId}>Dibujar Polígono Convexo</h3>
            <button ref={editorCloseRef} type="button" className="orders-editor-dialog__close" aria-label="Cerrar editor de polígono" onClick={() => setPiezaEnEdicion(null)}><X size={24} aria-hidden="true" /></button>
          </div>
          <div className="orders-editor-dialog__content">
            <CustomPieceEditor
              initialState={piezas.find((piece) => piece.id === piezaEnEdicion)?.dimensiones?.rawState}
              disabled={readOnly}
              onGuardarVertices={(dimensions) => {
                if (!readOnly) actualizarPieza(piezaEnEdicion, 'dimensiones', dimensions);
                setPiezaEnEdicion(null);
              }}
            />
          </div>
        </div>
      </div>}
    </>
  );

  return standalone
    ? <AppShell activeItem="orders" user={user}>{toolbar}{content}</AppShell>
    : content;
}
