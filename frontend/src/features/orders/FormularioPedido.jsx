import { useCallback, useEffect, useEffectEvent, useId, useRef, useState } from 'react';
import { useAutoAnimate } from '@formkit/auto-animate/react';
import { Loader2, PackagePlus, Plus, Save, Trash2, X } from 'lucide-react';
import { AppShell } from '../../shared/components/AppShell';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';
import { ConfirmDialog, EmptyState, FeedbackMessage, FieldError, LoadingState } from '../../shared/components/feedback';
import CustomPieceEditor from './CustomPieceEditor';
import OrderClientSelector from './OrderClientSelector';
import { validateConvexPolygon } from './convexityValidation';
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

function buildPayload(materialGroups) {
  const piezas = [];
  materialGroups.forEach((group) => {
    group.piezas.forEach((piece) => {
      const base = {
        tipo_forma: piece.tipo_forma,
        id_tipo_vidrio: Number(group.tipo_vidrio_id),
        espesor_mm: Number(group.espesor),
        cantidad: Number(piece.cantidad),
      };
      if (piece.tipo_forma === 'RECTANGULO') {
        piezas.push({ ...base, width_mm: Number(piece.dimensiones.width_mm), height_mm: Number(piece.dimensiones.height_mm) });
      } else if (piece.tipo_forma === 'CIRCUNFERENCIA') {
        piezas.push({ ...base, radius_mm: Number(piece.dimensiones.radius_mm) });
      } else {
        piezas.push({ ...base, vertices_mm: piece.dimensiones.vertices ?? [] });
      }
    });
  });
  return { piezas };
}

export default function FormularioPedido({
  token, idPedido = null, onCerrar = null, onSuccess, onSubmittingChange,
  mode = 'create', standalone = false, user, toolbar,
}) {
  const [tiposDisponibles, setTiposDisponibles] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientFormKey, setClientFormKey] = useState(0);
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorGlobal, setErrorGlobal] = useState('');
  const [loadError, setLoadError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [estadoPedido, setEstadoPedido] = useState('PENDIENTE');

  const [materialGroups, setMaterialGroups] = useState([]);
  const initialSnapshotRef = useRef(null);

  const [touched, setTouched] = useState({});
  const [piezaEnEdicion, setPiezaEnEdicion] = useState(null);
  const [isCancelDialogOpen, setIsCancelDialogOpen] = useState(false);
  const [listaAnimada] = useAutoAnimate();
  const nextGroupIdRef = useRef(0);
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

  const disableEditing = readOnly || isSubmitting;

  const createEmptyPiece = () => ({
    id: nextPieceIdRef.current++,
    nombre: '',
    cantidad: 1,
    tipo_forma: 'RECTANGULO',
    dimensiones: { width_mm: '', height_mm: '' },
  });

  // Read current mode after loading without reloading or discarding the draft
  // when presentation props change.
  const initializeCreateForm = useEffectEvent(() => {
    if (creating) setMaterialGroups([{
      id: `group-${nextGroupIdRef.current++}`,
      tipo_vidrio_id: '', espesor: '',
      piezas: [{ ...createEmptyPiece(), nombre: 'Pieza 1' }],
    }]);
  });

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
        setTiposDisponibles(materials.filter((material) => material.estado !== false));

        if (order) {
          setEstadoPedido(order.estado);
          nextPieceIdRef.current = 0;
          nextGroupIdRef.current = 0;

          const groupsMap = new Map();
          order.piezas.forEach((piece, index) => {
            const key = `${piece.id_tipo_vidrio}-${piece.espesor_mm}`;
            if (!groupsMap.has(key)) {
              groupsMap.set(key, {
                id: `group-${nextGroupIdRef.current++}`,
                tipo_vidrio_id: String(piece.id_tipo_vidrio),
                espesor: String(piece.espesor_mm),
                piezas: []
              });
            }
            groupsMap.get(key).piezas.push(pieceFromResponse(piece, index, nextPieceIdRef.current++));
          });

          const groups = Array.from(groupsMap.values());
          let globalPieceIndex = 1;
          groups.forEach(group => {
            group.piezas.forEach(piece => { piece.nombre = `Pieza ${globalPieceIndex++}`; });
          });

          setMaterialGroups(groups);
          initialSnapshotRef.current = JSON.parse(JSON.stringify(groups));
        } else {
          initializeCreateForm();
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
  }, [editing, idPedido, token, catalogAttempt]);

  useEffect(() => {
    if (!piezaEnEdicion) return undefined;
    const trigger = editorTriggerRef.current;
    editorCloseRef.current?.focus();
    return () => trigger?.focus?.();
  }, [piezaEnEdicion]);

  const recalculatePieceNames = (groups) => {
    let index = 1;
    return groups.map(group => ({
      ...group,
      piezas: group.piezas.map(piece => ({ ...piece, nombre: `Pieza ${index++}` }))
    }));
  };

  const addMaterialGroup = () => {
    setMaterialGroups(curr => recalculatePieceNames([...curr, {
      id: `group-${nextGroupIdRef.current++}`, tipo_vidrio_id: '', espesor: '', piezas: [createEmptyPiece()]
    }]));
  };

  const removeMaterialGroup = (groupId) => setMaterialGroups(curr => recalculatePieceNames(curr.filter(g => g.id !== groupId)));

  const updateMaterialGroup = (groupId, field, value) => {
    setMaterialGroups(curr => curr.map(group => {
      if (group.id !== groupId) return group;
      if (field === 'tipo_vidrio_id') return { ...group, tipo_vidrio_id: value, espesor: '' };
      return { ...group, [field]: value };
    }));
  };

  const addPieceToGroup = (groupId) => {
    setMaterialGroups(curr => recalculatePieceNames(curr.map(group => {
      if (group.id !== groupId) return group;
      return { ...group, piezas: [...group.piezas, createEmptyPiece()] };
    })));
  };

  const removePiece = (groupId, pieceId) => {
    setMaterialGroups(curr => recalculatePieceNames(curr.map(group => {
      if (group.id !== groupId) return group;
      return { ...group, piezas: group.piezas.filter(p => p.id !== pieceId) };
    })));
  };

  const updatePiece = useCallback((groupId, pieceId, field, value) => {
    setMaterialGroups(curr => curr.map(group => {
      if (group.id !== groupId) return group;
      const updatedPiezas = group.piezas.map(piece => {
        if (piece.id !== pieceId) return piece;
        if (field === 'cantidad') return { ...piece, cantidad: value === '' ? '' : Number(value) };
        if (field === 'tipo_forma') {
          const dimensiones = value === 'RECTANGULO' ? { width_mm: '', height_mm: '' }
            : value === 'CIRCUNFERENCIA' ? { radius_mm: '' } : { vertices: [] };
          return { ...piece, tipo_forma: value, dimensiones };
        }
        if (field === 'dimensiones') return { ...piece, dimensiones: value };
        return { ...piece, dimensiones: { ...piece.dimensiones, [field]: value } };
      });
      return { ...group, piezas: updatedPiezas };
    }));
  }, []);

  function openEditor(groupId, pieceId) {
    editorTriggerRef.current = document.activeElement;
    setPiezaEnEdicion({ groupId, pieceId });
  }

  function handleCancelAction() {
    if (editing) {
      setMaterialGroups(JSON.parse(JSON.stringify(initialSnapshotRef.current)));
      setIsCancelDialogOpen(false);
      if (onCerrar) onCerrar();
    } else {
      setMaterialGroups([{ id: `group-${nextGroupIdRef.current++}`, tipo_vidrio_id: '', espesor: '', piezas: [{ ...createEmptyPiece(), nombre: 'Pieza 1' }] }]);
      setSelectedClient(null);
      setClientFormKey((key) => key + 1);
      setErrorGlobal('');
      setSuccessMessage('');
      setIsCancelDialogOpen(false);
    }
  }

  function fieldProps(identifier, field, value) {
    const id = `${formId}-${identifier}-${field}`;
    const errorId = `${id}-error`;
    let error = '';

    if (touched[`${identifier}:${field}`]) {
       if (field === 'material' && !value) error = 'Selecciona un material.';
       else if (field === 'espesor' && !positiveNumber(value)) error = 'Selecciona un espesor válido.';
       else if (field === 'cantidad' && (!Number.isInteger(Number(value)) || Number(value) <= 0)) error = 'Ingresa una cantidad entera mayor que 0.';
       else if (field === 'width_mm' && !positiveNumber(value)) error = 'Ingresa un ancho mayor que 0.';
       else if (field === 'height_mm' && !positiveNumber(value)) error = 'Ingresa un alto mayor que 0.';
       else if (field === 'radius_mm' && !positiveNumber(value)) error = 'Ingresa un radio mayor que 0.';
    }

    return {
      id,
      'aria-invalid': error ? 'true' : undefined,
      'aria-describedby': error ? errorId : undefined,
      onBlur: () => setTouched((current) => ({ ...current, [`${identifier}:${field}`]: true })),
      error: error ? <FieldError id={errorId}>{error}</FieldError> : null,
    };
  }

  const getThicknesses = (materialId) => tiposDisponibles.find(
    (type) => String(type.id_tipo_vidrio) === String(materialId),
  )?.espesores_mm ?? [];

  const getUsedThicknesses = (groupId, materialId) => {
    return materialGroups
      .filter(g => g.id !== groupId && String(g.tipo_vidrio_id) === String(materialId) && g.espesor)
      .map(g => String(g.espesor));
  };

  const isMaterialFullyUsed = (groupId, materialId) => {
    const available = getThicknesses(materialId);
    const used = getUsedThicknesses(groupId, materialId);
    return available.length > 0 && available.every(t => used.includes(String(t)));
  };

  function isValid() {
    if ((creating && !selectedClient) || loadError || !materialGroups.length) return false;

    const uniqueKeys = new Set(materialGroups.filter(g => g.tipo_vidrio_id && g.espesor).map(g => `${g.tipo_vidrio_id}-${g.espesor}`));
    if (uniqueKeys.size !== materialGroups.filter(g => g.tipo_vidrio_id && g.espesor).length) return false;

    return materialGroups.every(group => {
      if (!group.tipo_vidrio_id || !positiveNumber(group.espesor) || !group.piezas.length) return false;
      return group.piezas.every((piece) => {
        if (!Number.isInteger(Number(piece.cantidad)) || Number(piece.cantidad) <= 0) return false;
        if (piece.tipo_forma === 'RECTANGULO') return positiveNumber(piece.dimensiones.width_mm) && positiveNumber(piece.dimensiones.height_mm);
        if (piece.tipo_forma === 'CIRCUNFERENCIA') return positiveNumber(piece.dimensiones.radius_mm);
        return validateConvexPolygon(piece.dimensiones.vertices).isValid;
      });
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
      const payload = buildPayload(materialGroups);
      const result = editing
        ? await updateOrder(idPedido, payload, { token })
        : await createOrder({ ...payload, id_cliente: selectedClient.id_cliente }, { token });
      setSuccessMessage(editing ? 'Pedido actualizado correctamente.' : `Pedido registrado correctamente. ID del pedido: ${result.id_pedido}.`);
      onSuccess?.(editing ? 'update' : 'create', result);
      if (onCerrar) onCerrar();
      else if (!editing) {
        setMaterialGroups([{ id: `group-${nextGroupIdRef.current++}`, tipo_vidrio_id: '', espesor: '', piezas: [{ ...createEmptyPiece(), nombre: 'Pieza 1' }] }]);
        setSelectedClient(null);
        setClientFormKey((key) => key + 1);
      }
    } catch (error) {
      setErrorGlobal(`${error.message} ${creating ? 'Las piezas y el cliente se conservan' : 'Las piezas se conservan'} para reintentar.`);
    } finally {
      submittingRef.current = false;
      setIsSubmitting(false);
      onSubmittingChange?.(false);
    }
  }

  const content = (
    <>
      {standalone && <PageHeader context={editing ? 'Gestión de pedidos' : 'Registro de pedido'} title={editing ? `Pedido #${idPedido}` : 'Nuevo pedido'} description={editing ? 'Revisa o actualiza las piezas del pedido.' : 'Configura el material, espesor y medidas de cada pieza requerida.'} titleId={titleId} icon={PackagePlus} />}
      <PageCard as="section" aria-labelledby={standalone ? titleId : undefined}>
        {isLoading && <LoadingState>{editing ? 'Cargando pedido…' : 'Cargando materiales…'}</LoadingState>}
        {errorGlobal && <FeedbackMessage variant="error" title="No se pudo completar la operación">{errorGlobal}</FeedbackMessage>}
        {loadError && creating && <button type="button" className="ng-button" onClick={() => setCatalogAttempt((attempt) => attempt + 1)}>Reintentar catálogo</button>}
        {successMessage && <FeedbackMessage variant="success">{successMessage}</FeedbackMessage>}
        {readOnly && <FeedbackMessage variant="warning" title="Pedido en modo lectura">El estado {estadoPedido} no permite modificar sus piezas.</FeedbackMessage>}

        {!isLoading && (!loadError || creating) && <>
          {creating && <OrderClientSelector key={clientFormKey} value={selectedClient} onChange={setSelectedClient} disabled={isSubmitting} token={token} />}

          <section className="orders-section">
            <div className="orders-section__header">
              <div>
                <h2>Materiales y piezas</h2>
                <p className="orders-section__description">
                  {readOnly ? 'Detalle de las piezas solicitadas.' : 'Agrupa las piezas por tipo de vidrio y espesor.'}
                </p>
              </div>
            </div>

            <div ref={listaAnimada} className="orders-materials">
              {creating && !selectedClient ? (
                <EmptyState
                  title="Falta seleccionar cliente"
                  description="Busca y selecciona un cliente en la parte superior para habilitar la configuración de piezas."
                />
              ) : !materialGroups.length ? (
                <EmptyState
                  title="No hay materiales agregados"
                  description="Haz clic en «Agregar otro material» para comenzar."
                />
              ) : (
                materialGroups.map((group) => {
                  const materialField = fieldProps(group.id, 'material', group.tipo_vidrio_id);
                  const thicknessField = fieldProps(group.id, 'espesor', group.espesor);

                  // NUEVA REGLA ESTRICTA: ¿Falta seleccionar vidrio o espesor en este grupo?
                  const isMaterialMissing = !group.tipo_vidrio_id || !group.espesor;
                  // Si falta material o el formulario está bloqueado, se deshabilita todo.
                  const disablePieceEditing = disableEditing || isMaterialMissing;

                  return (
                    <div className="orders-material-group" key={group.id}>
                      <div className="orders-material-group__header">
                        <div className="orders-material-group__fields">
                          <div className="orders-field" style={{ width: '180px' }}>
                            <label htmlFor={materialField.id}>Tipo de vidrio</label>
                            <select {...materialField} value={group.tipo_vidrio_id} onChange={(e) => updateMaterialGroup(group.id, 'tipo_vidrio_id', e.target.value)} disabled={disableEditing} className="ng-control orders-control">
                              <option value="">Seleccionar…</option>
                              {tiposDisponibles.map((type) => {
                                const fullyUsed = isMaterialFullyUsed(group.id, type.id_tipo_vidrio);
                                return (
                                  <option key={type.id_tipo_vidrio} value={type.id_tipo_vidrio} disabled={fullyUsed}>
                                    {type.nombre} {fullyUsed ? '(En uso)' : ''}
                                  </option>
                                );
                              })}
                            </select>
                            {materialField.error}
                          </div>
                          <div className="orders-field" style={{ width: '160px' }}>
                            <label htmlFor={thicknessField.id}>Espesor del vidrio (mm)</label>
                            <select {...thicknessField} value={group.espesor} onChange={(e) => updateMaterialGroup(group.id, 'espesor', e.target.value)} disabled={disableEditing || !group.tipo_vidrio_id} className="ng-control orders-control">
                              <option value="">Espesor…</option>
                              {getThicknesses(group.tipo_vidrio_id).map((thickness) => {
                                const isUsed = getUsedThicknesses(group.id, group.tipo_vidrio_id).includes(String(thickness));
                                return (
                                  <option key={thickness} value={thickness} disabled={isUsed}>
                                    {thickness} mm {isUsed ? '(En uso)' : ''}
                                  </option>
                                );
                              })}
                            </select>
                            {thicknessField.error}
                          </div>
                        </div>
                        {!readOnly && materialGroups.length > 1 && (
                          <button type="button" className="ng-button ng-button--danger" onClick={() => removeMaterialGroup(group.id)} disabled={disableEditing}>
                            <Trash2 size={16} /> Eliminar material
                          </button>
                        )}
                      </div>

                      <div className="orders-material-group__body">
                        <div className="orders-pieces-list">
                          {group.piezas.map((piece) => {
                            const quantityField = fieldProps(piece.id, 'cantidad', piece.cantidad);

                            return (
                              <div className="orders-piece" key={piece.id}>
                                <div className="orders-piece__header">
                                  <div className="orders-piece__identity">
                                    <div className="orders-piece__index">{piece.nombre.replace('Pieza ', '')}</div>
                                    <div className="orders-piece__details"><strong>{piece.nombre}</strong><span>Atributos de corte</span></div>
                                  </div>
                                  {!readOnly && (
                                    <button type="button" className="orders-remove-button" onClick={() => removePiece(group.id, piece.id)} aria-label="Eliminar pieza" disabled={disableEditing || (materialGroups.length === 1 && group.piezas.length === 1)}>
                                      <Trash2 size={18} />
                                    </button>
                                  )}
                                </div>

                                <div className="orders-fields-row">
                                  <div className="orders-field">
                                    <label htmlFor={`forma-${piece.id}`}>Forma</label>
                                    <select id={`forma-${piece.id}`} value={piece.tipo_forma} onChange={(e) => {
                                      updatePiece(group.id, piece.id, 'tipo_forma', e.target.value);
                                      if (e.target.value === 'POLIGONO_CONVEXO') openEditor(group.id, piece.id);
                                    }}
                                    disabled={disablePieceEditing} /* BLOQUEADO SI FALTA MATERIAL */
                                    className="ng-control orders-control orders-control--shape">
                                      <option value="RECTANGULO">Rectángulo</option>
                                      <option value="CIRCUNFERENCIA">Círculo</option>
                                      <option value="POLIGONO_CONVEXO">Polígono convexo</option>
                                    </select>
                                  </div>

                                  {piece.tipo_forma === 'RECTANGULO' && ['width_mm', 'height_mm'].map((field) => {
                                    const label = field === 'width_mm' ? 'Ancho (mm)' : 'Alto (mm)';
                                    const props = fieldProps(piece.id, field, piece.dimensiones[field]);
                                    return <div className="orders-field" key={field}>
                                      <label htmlFor={props.id}>{label}</label>
                                      <input {...props} id={props.id} type="number" min="0" step="any" placeholder={label} value={piece.dimensiones[field]} onChange={(e) => updatePiece(group.id, piece.id, field, e.target.value)}
                                      disabled={disablePieceEditing} /* BLOQUEADO SI FALTA MATERIAL */
                                      className="ng-control orders-control orders-control--dimension" />
                                      {props.error}
                                    </div>;
                                  })}

                                  {piece.tipo_forma === 'CIRCUNFERENCIA' && (() => {
                                    const props = fieldProps(piece.id, 'radius_mm', piece.dimensiones.radius_mm);
                                    return <div className="orders-field">
                                      <label htmlFor={props.id}>Radio (mm)</label>
                                      <input {...props} id={props.id} type="number" min="0" step="any" placeholder="Radio (mm)" value={piece.dimensiones.radius_mm} onChange={(e) => updatePiece(group.id, piece.id, 'radius_mm', e.target.value)}
                                      disabled={disablePieceEditing} /* BLOQUEADO SI FALTA MATERIAL */
                                      className="ng-control orders-control orders-control--dimension" />
                                      {props.error}
                                    </div>;
                                  })()}

                                  {piece.tipo_forma === 'POLIGONO_CONVEXO' && (
                                    <div className="orders-polygon-status">
                                      {piece.dimensiones.vertices?.length ? (
                                        <span className="orders-polygon-status__complete">✓ Figura configurada</span>
                                      ) : isMaterialMissing ? (
                                        <span className="orders-polygon-status__pending" style={{ color: 'var(--editor-error)' }}>
                                          Falta material
                                        </span>
                                      ) : (
                                        <span className="orders-polygon-status__pending">Falta configurar</span>
                                      )}
                                      <button
                                        type="button"
                                        className="ng-button orders-editor-open"
                                        onClick={() => openEditor(group.id, piece.id)}
                                        disabled={isSubmitting || isMaterialMissing}
                                      >
                                        {readOnly ? 'Ver figura' : 'Editar figura'}
                                      </button>
                                    </div>
                                  )}

                                  <div className="orders-field">
                                    <label htmlFor={quantityField.id}>Cantidad</label>
                                    <input {...quantityField} id={quantityField.id} type="number" min="1" step="1" placeholder="Cant." value={piece.cantidad} onChange={(e) => updatePiece(group.id, piece.id, 'cantidad', e.target.value)}
                                    disabled={disablePieceEditing} /* BLOQUEADO SI FALTA MATERIAL */
                                    className="ng-control orders-control orders-control--quantity" />
                                    {quantityField.error}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>

                        {!readOnly && (
                          <div style={{ marginTop: '12px' }}>
                            <button type="button" className="ng-button" onClick={() => addPieceToGroup(group.id)}
                            disabled={disableEditing || isMaterialMissing} /* BLOQUEADO SI FALTA MATERIAL */>
                              <Plus size={16} /> Agregar pieza
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {!readOnly && !(creating && !selectedClient) && (
              <div className="orders-add-material-wrap">
                <button type="button" className="ng-button" onClick={addMaterialGroup} disabled={isSubmitting}>
                  <Plus size={18} /> Agregar otro material
                </button>
              </div>
            )}
          </section>

          {creating && !selectedClient && <p id={`${formId}-client-help`}>Selecciona un cliente para guardar el pedido.</p>}
          <ActionBar>
            {onCerrar && <button type="button" className="ng-button" onClick={() => setIsCancelDialogOpen(true)} disabled={isSubmitting}><X size={18} /> Cancelar</button>}
            {standalone && creating && <button type="button" className="ng-button" onClick={() => setIsCancelDialogOpen(true)} disabled={isSubmitting}><X size={18} /> Cancelar</button>}
            {!readOnly && <button type="button" className="ng-button ng-button--primary" onClick={saveOrder} aria-describedby={creating && !selectedClient ? `${formId}-client-help` : undefined} disabled={!isValid() || isSubmitting}>
              {isSubmitting ? <Loader2 size={18} className="ng-loading-icon" /> : <Save size={18} />}
              {isSubmitting ? 'Guardando…' : editing ? 'Guardar cambios' : 'Guardar pedido'}
            </button>}
          </ActionBar>
        </>}
      </PageCard>

      <ConfirmDialog open={isCancelDialogOpen} title={editing ? "¿Cancelar edición?" : "¿Limpiar el pedido?"} confirmLabel={editing ? "Sí, cancelar" : "Limpiar pedido"}
        onConfirm={handleCancelAction}
        onCancel={() => setIsCancelDialogOpen(false)}>
        <p>{editing ? "Se descartarán los cambios no guardados." : "Se quitarán todas las piezas y la selección del cliente. Esta acción no se puede deshacer."}</p>
      </ConfirmDialog>

      {piezaEnEdicion !== null && <div className="orders-editor-backdrop">
        <div ref={editorDialogRef} className="orders-editor-dialog" role="dialog" aria-modal="true" aria-labelledby={editorTitleId} tabIndex={-1}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.stopPropagation();
              setPiezaEnEdicion(null);
            }
            if (event.key === 'Tab') {
              const controls = [...editorDialogRef.current.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]')]
                .filter(element => element.style.display !== 'none');
              const first = controls[0];
              const last = controls.at(-1);
              if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
              else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
            }
          }}>
          <div className="orders-editor-dialog__header">
            <h3 id={editorTitleId}>Dibujar Polígono Convexo</h3>
            <button ref={editorCloseRef} type="button" className="orders-editor-dialog__close" aria-label="Cerrar editor de polígono" onClick={() => setPiezaEnEdicion(null)}><X size={24} aria-hidden="true" /></button>
          </div>
          <div className="orders-editor-dialog__content">
            <CustomPieceEditor
              initialState={materialGroups.find(g => g.id === piezaEnEdicion.groupId)?.piezas.find(p => p.id === piezaEnEdicion.pieceId)?.dimensiones?.rawState}
              disabled={readOnly}
              onGuardarVertices={(dimensions) => {
                if (!readOnly) updatePiece(piezaEnEdicion.groupId, piezaEnEdicion.pieceId, 'dimensiones', dimensions);
                setPiezaEnEdicion(null);
              }}
            />
          </div>
        </div>
      </div>}
    </>
  );

  return standalone ? <AppShell activeItem="orders" user={user}>{toolbar}{content}</AppShell> : content;
}