import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, Plus, MousePointer2, RotateCcw, Undo2, MousePointerClick } from "lucide-react";
import "./CustomPieceEditor.css";
import { interiorAngles } from "./polygonMeasurements";
import { fitVerticesToPreview } from "./geometryScaling";
import { createSegments, isPositiveLength } from "./segmentGeometry";
import { validateConvexPolygon } from "./convexityValidation";
import { buildConstrainedGeometry } from "./constrainedGeometry";

const DRAWING_WIDTH = 800;
const DRAWING_HEIGHT = 500;
const VERTEX_HIT_RADIUS = 30;
const formatLength = (value) => new Intl.NumberFormat("es", { maximumSignificantDigits: 8 }).format(value);

// Hook para adaptar el lienzo al tamaño de la columna izquierda
function useCanvasSize() {
  const ref = useRef(null);
  const [size, setSize] = useState({ width: 800, height: 480 });
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        setSize((current) => current.width === width && current.height === height ? current : { width, height });
      }
    });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return [ref, size];
}

function SegmentField({ segment, active, onSelect, onChange, inputRef }) {
  const id = useId();
  const localRef = useRef(null);
  const [touched, setTouched] = useState(false);
  const invalid = segment.badInput || ((touched || segment.lengthMm !== "") && !isPositiveLength(segment.lengthMm));
  function updateValue(event) {
    const input = event.currentTarget;
    input.setCustomValidity(input.value !== "" && !isPositiveLength(input.value) ? "Ingresa un número mayor que 0." : "");
    onChange(input.value, input.validity.badInput);
  }
  return (
    <li className="custom-piece-editor__segment-row" data-active={active} onFocus={onSelect}>
      <button type="button" className="custom-piece-editor__segment-selector" aria-pressed={active}
        onClick={() => { onSelect(); localRef.current?.focus(); }}>
        {segment.id}
      </button>
      <div className="custom-piece-editor__field">
        <label className="custom-piece-editor__sr-only" htmlFor={id}>{segment.id}</label>
        <div className="custom-piece-editor__input-wrapper">
          <input ref={(node) => { localRef.current = node; if (inputRef) inputRef.current = node; }} id={id}
            className="custom-piece-editor__input" type="number" inputMode="decimal" step="any" required
            value={segment.lengthMm} onChange={updateValue} onBlur={() => setTouched(true)}
            aria-invalid={Boolean(invalid)} placeholder="Longitud" />
          <span className="custom-piece-editor__input-unit">mm</span>
        </div>
        {invalid && <p className="custom-piece-editor__field-error">{segment.lengthMm === "" && !segment.badInput ? "Completa esta medida." : "Número > 0"}</p>}
      </div>
    </li>
  );
}

// Overlay único para pintar segmentos, etiquetas in-situ y ángulos
function SegmentOverlay({
  points, angles, activeSegmentIndex, selectedVertexIndex, fixedVertices, onSelectVertex, width, height, unitScale = 1
}) {
  const occupied = [];
  const interactive = Boolean(onSelectVertex) && points.length > 3;

  const labels = points.map((start, index) => {
    const end = points[(index + 1) % points.length];
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const length = Math.hypot(dx, dy) || 1;
    return {
      index,
      x: Math.max(24 / unitScale, Math.min(width - 24 / unitScale, (start.x + end.x) / 2 + dy / length * 17 / unitScale)),
      y: Math.max(18 / unitScale, Math.min(height - 18 / unitScale, (start.y + end.y) / 2 - dx / length * 17 / unitScale)),
    };
  });

  return (
    <g className="custom-piece-editor__segments" aria-hidden="true">
      {points.map((start, index) => {
        const end = points[(index + 1) % points.length];
        return <line key={index} x1={start.x} y1={start.y} x2={end.x} y2={end.y}
          data-active={index === activeSegmentIndex} vectorEffect="non-scaling-stroke" />;
      })}

      {labels.map(({ index, x, y }) => {
        if (occupied.some((label) => Math.abs(label.x - x) * unitScale < 44 && Math.abs(label.y - y) * unitScale < 26)) return null;
        occupied.push({ x, y });
        return <text key={index} x={x} y={y} textAnchor="middle" dominantBaseline="central"
          style={{ fontSize: 14 / unitScale, strokeWidth: 5 / unitScale }} data-active={index === activeSegmentIndex}>S{index + 1}</text>;
      })}

      {points.map((point, index) => {
        const angleVal = angles[index] !== undefined && !Number.isNaN(angles[index]) ? `${Math.round(angles[index])}°` : '';
        const labelText = angleVal ? `V${index + 1} (${angleVal})` : `V${index + 1}`;
        const isSelected = index === selectedVertexIndex;
        const isFixed = fixedVertices.includes(index);

        return (
          <g key={`vertex-group-${index}`}
             onClick={interactive ? (e) => { e.stopPropagation(); onSelectVertex(index); } : undefined}
             style={{ cursor: interactive ? 'pointer' : 'default', pointerEvents: 'auto' }}>
            <circle
              cx={point.x} cy={point.y}
              r={(isSelected ? 8 : isFixed ? 6 : 5) / unitScale}
              className="custom-piece-editor__vertex-point"
              data-selected={isSelected ? "true" : undefined}
              data-fixed={isFixed ? "true" : undefined}
            />
            <text
              x={point.x} y={point.y - (14 / unitScale)}
              className="custom-piece-editor__vertex-label"
              data-selected={isSelected ? "true" : undefined}
              data-fixed={isFixed ? "true" : undefined}
              style={{ fontSize: (isSelected ? 14 : 12) / unitScale, strokeWidth: 4 / unitScale }}
              textAnchor="middle">
              {labelText}
            </text>
          </g>
        );
      })}
    </g>
  );
}

// Textos de error amigables
function dimensionalError(result) {
  if (!result || !result.error) return "";
  const msgs = {
    "inequality": "Las medidas no cuadran: un lado es demasiado largo y la figura no alcanza a cerrarse.",
    "angle": "El ángulo que ingresaste debe ser mayor a 0 y menor a 180 grados.",
    "angle-configuration": "Las medidas y ángulos que fijaste chocan entre sí. Prueba cambiando una medida o liberando un ángulo.",
    "constraint-limit": "Ya fijaste la cantidad máxima de ángulos permitidos para esta figura.",
    "shape-mismatch": "Las medidas ingresadas deforman demasiado la figura original. Revisa si hay algún error de tipeo.",
    "length": "Por favor, verifica que todas las medidas sean mayores a cero."
  };
  return msgs[result.error] || "No se pudo formar la figura con estas medidas. Revisa los valores ingresados.";
}

export default function CustomPieceEditor({ onGuardarVertices, initialState, headerReady = true, disabled = false, title="Pieza personalizada", addLabel="Agregar pieza al pedido", helpText="Agrega la pieza y guarda el pedido para registrarla.", onGeometryChange }) {
  const headingId = useId();
  const validationId = useId();
  const firstInputRef = useRef(null);
  const angleInputRef = useRef(null);
  const closedWithKeyboard = useRef(false);

  const [canvasRef, canvasSize] = useCanvasSize();
  const [drawing, setDrawing] = useState(initialState?.drawing || { vertices: [], isClosed: false });
  const [segments, setSegments] = useState(initialState?.segments || []);
  const [activeSegmentIndex, setActiveSegmentIndex] = useState(initialState?.segments ? 0 : null);

  const [selectedVertexIndex, setSelectedVertexIndex] = useState(() => {
    const initialConstraints = initialState?.construction?.constraints;
    return Array.isArray(initialConstraints) && initialConstraints.length > 0 ? initialConstraints[0].vertex : null;
  });

  const [construction, setConstruction] = useState(() => {
    const previous = initialState?.construction;
    return {
      mode: previous?.mode === 'sketch' || previous?.mode === 'angle' ? 'guided' : previous?.mode || (initialState?.drawing?.isClosed ? 'guided' : 'cyclic'),
      angle: previous?.angle || '90',
      constraints: previous?.constraints || [],
    };
  });

  const { vertices, isClosed } = drawing;

  const sketchValidation = useMemo(() => validateConvexPolygon(vertices.map(({ x, y }) => [x, y])), [vertices]);
  const result = useMemo(() => !isClosed ? null : buildConstrainedGeometry(segments, {
    ...construction, mode: construction.constraints.length ? 'angles' : construction.mode,
    drawing: vertices.map(({ x, y }) => [x, y]),
  }), [vertices, isClosed, segments, construction]);

  const validation = useMemo(() => isClosed && !sketchValidation.isValid ? sketchValidation :
    validateConvexPolygon(result?.status === "complete" ? result.vertices_mm : null), [result, isClosed, sketchValidation]);

  const validationRejected = !validation.isValid && validation.reason !== "INCOMPLETE";
  const measuredCount = segments.filter((segment) => !segment.badInput && isPositiveLength(segment.lengthMm)).length;
  const dimensionsReady = result?.status === "complete";
  const canAdd = isClosed && dimensionsReady && validation.reason === "VALID" && Boolean(result?.vertices_mm) && headerReady && !disabled;

  const angles = useMemo(() => { try { return result?.vertices_mm ? interiorAngles(result.vertices_mm) : []; } catch { return []; } }, [result]);
  const fixedVertices = useMemo(() => construction.constraints.map((item) => item.vertex), [construction.constraints]);
  const maxConstraints = Math.max(0, vertices.length - 3);
  const isLimitReached = construction.constraints.length >= maxConstraints;

  useEffect(() => {
    if (!isClosed) return;
    if (closedWithKeyboard.current) firstInputRef.current?.focus();
  }, [isClosed]);

  useEffect(() => {
    if (selectedVertexIndex !== null && angleInputRef.current) angleInputRef.current.focus();
  }, [selectedVertexIndex, construction.constraints.length]);

  // --- LÓGICA DEL LIENZO ÚNICO ---
  let displayPoints = vertices;
  let unitScale = canvasSize.width / DRAWING_WIDTH;
  let isProvisional = false;

  if (isClosed) {
    const sourcePoints = result?.vertices_mm ? result.vertices_mm.map(([x,y]) => ({x, y})) : vertices;
    const geometry = fitVerticesToPreview(sourcePoints, canvasSize.width, canvasSize.height, 40);
    if (geometry) {
      displayPoints = geometry.points;
      unitScale = 1;
    }
    isProvisional = !dimensionsReady;
  }

  const drawingPointsString = displayPoints.map(({ x, y }) => `${x},${y}`).join(" ");

  function selectVertex(vertexIndex) {
    if (disabled || !isClosed || vertices.length <= 3) return;
    setSelectedVertexIndex(vertexIndex);
    setActiveSegmentIndex(vertexIndex);
  }

  function addVertex(event) {
    if (disabled || event.button !== 0 || isClosed) return;
    const screenMatrix = event.currentTarget.getScreenCTM();
    if (!screenMatrix) return;
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(screenMatrix.inverse());
    setDrawing((current) => ({ ...current, vertices: [...current.vertices, { x: point.x, y: point.y }] }));
  }

  function closePolygon(event) {
    if (vertices.length < 3 || isClosed) return;
    closedWithKeyboard.current = event.detail === 0;
    setSegments(createSegments(vertices));
    setActiveSegmentIndex(0);
    setSelectedVertexIndex(null);
    setDrawing((current) => ({ ...current, isClosed: true }));
  }

  function resetDrawing() {
    setConstruction({ mode: 'cyclic', angle: '90', constraints: [] });
    setSegments([]); setActiveSegmentIndex(null); setSelectedVertexIndex(null);
    setDrawing({ vertices: [], isClosed: false });
  }

  function updateSegment(index, lengthMm, badInput) {
    setSegments((current) => current.map((s) => s.index === index ? { ...s, lengthMm, badInput } : s));
  }

  function handleAngleFix(vertex, angleValue) {
    setConstruction(current => {
      const isFixed = current.constraints.some(c => c.vertex === vertex);
      let newConstraints = [...current.constraints];

      if (isFixed) {
        newConstraints = newConstraints.map(c => c.vertex === vertex ? { vertex, angle: angleValue } : c);
      } else {
        if (newConstraints.length >= maxConstraints) return current;
        newConstraints.push({ vertex, angle: angleValue });
      }
      return { ...current, constraints: newConstraints };
    });
  }

  function unfixAngle(vertex) {
    setConstruction(current => ({
      ...current, constraints: current.constraints.filter(c => c.vertex !== vertex)
    }));
  }

  return (
    <section className="custom-piece-editor" aria-labelledby={headingId}>
      <div className="custom-piece-editor__header">
        <h2 id={headingId}>{title}</h2>
      </div>

      <fieldset className="custom-piece-editor__fieldset" disabled={disabled}>

        <div className="custom-piece-editor__split-layout">

          {/* --- COLUMNA IZQUIERDA: LIENZO Y VALIDACIÓN --- */}
          <div className="custom-piece-editor__canvas-pane">
            <div className="custom-piece-editor__toolbar">
              {!isClosed ? (
                <button type="button" className="custom-piece-editor__button custom-piece-editor__button--primary" disabled={vertices.length < 3} onClick={closePolygon}>
                  <Check size={16} /> Cerrar polígono
                </button>
              ) : (
                <span style={{ color: 'var(--editor-success)', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Check size={16} /> Geometría calculada
                </span>
              )}
              <button type="button" className="custom-piece-editor__button" disabled={!vertices.length} onClick={() => setDrawing(c => ({...c, vertices: c.vertices.slice(0, -1)}))} style={{ marginLeft: 'auto', display: isClosed ? 'none' : 'flex' }}>
                <Undo2 size={16} /> Deshacer
              </button>
              <button type="button" className="custom-piece-editor__button" disabled={!vertices.length} onClick={resetDrawing}>
                <RotateCcw size={16} /> Reiniciar
              </button>
            </div>

            <div className="custom-piece-editor__surface" ref={canvasRef}>
              <span className="custom-piece-editor__canvas-label">
                {!isClosed ? "Boceto libre" : isProvisional ? "Vista Dimensional (Calculando...)" : "Vista Dimensional Exacta"}
              </span>
              <svg className="custom-piece-editor__canvas" viewBox={`0 0 ${isClosed ? canvasSize.width : DRAWING_WIDTH} ${isClosed ? canvasSize.height : DRAWING_HEIGHT}`}
                data-closed={isClosed} onClick={addVertex}>
                <g className="custom-piece-editor__drawing" aria-hidden="true">
                  {isClosed ? (
                    <polygon points={drawingPointsString} data-provisional={isProvisional} />
                  ) : (
                    <>
                      <polyline points={drawingPointsString} />
                      {vertices.map((vertex, index) => <circle key={index} cx={vertex.x} cy={vertex.y} r="5" className="custom-piece-editor__vertex-point" />)}
                    </>
                  )}
                </g>
                {/* Dibuja las etiquetas y hace la magia del in-situ */}
                {isClosed && (
                  <SegmentOverlay
                    points={displayPoints} angles={angles} activeSegmentIndex={activeSegmentIndex}
                    selectedVertexIndex={selectedVertexIndex} fixedVertices={fixedVertices}
                    onSelectVertex={vertices.length > 3 ? selectVertex : null}
                    width={canvasSize.width} height={canvasSize.height} unitScale={unitScale}
                  />
                )}
              </svg>
              {!vertices.length && (
                <div className="custom-piece-editor__empty" aria-hidden="true">
                  <MousePointer2 size={24} strokeWidth={1.5} /><strong>Haz clic para comenzar</strong>
                  <span>Imagina la forma de tu vidrio y marca cada esquina.</span>
                </div>
              )}
            </div>

            {/* NUEVO LUGAR PARA LA VALIDACIÓN GEOMÉTRICA */}
            {isClosed && (
              <div className="custom-piece-editor__validation-box">
                <h3 id={validationId}>Validación geométrica</h3>
                <div role={validationRejected ? "alert" : "status"} aria-atomic="true">
                  {result?.status === "error" ? (
                    <p className="custom-piece-editor__geometry-error">{dimensionalError(result)}</p>
                  ) : validationRejected ? (
                    <p className="custom-piece-editor__geometry-error">{validation.message || "La figura dibujada tiene cruces o ángulos inválidos."}</p>
                  ) : validation.isValid && isClosed && dimensionsReady ? (
                    <p className="custom-piece-editor__validation-message" data-valid="true">
                      ✓ Geometría validada y lista.
                    </p>
                  ) : (
                    <p className="custom-piece-editor__validation-message" style={{ color: 'var(--editor-muted)' }}>
                      Pendiente de completar dimensiones.
                    </p>
                  )}
                </div>
                {!dimensionsReady && !validationRejected && result?.status !== "error" && (
                  <p className="custom-piece-editor__validation-hint">{headerReady ? helpText : "Selecciona el tipo de vidrio y el espesor en Nuevo pedido para agregar piezas."}</p>
                )}
              </div>
            )}
          </div>

          {/* --- COLUMNA DERECHA: CONTROLES --- */}
          <div className="custom-piece-editor__controls-pane">
            {!isClosed ? (
              <div className="custom-piece-editor__instruction-panel">
                <h3>Paso 1: Dibujar contorno</h3>
                <p style={{ color: 'var(--editor-muted)', fontSize: '14px', lineHeight: '1.5' }}>
                  Haz clic en el lienzo vacío para marcar las esquinas de tu pieza.
                  Sigue el borde en orden hasta formar la figura completa. No te preocupes por el tamaño, las medidas se ingresan en el siguiente paso.
                </p>
                <p style={{ marginTop: '12px' }}><strong>Faltan {Math.max(0, 3 - vertices.length)} vértices</strong> para poder cerrar la figura.</p>
              </div>
            ) : (
              <>
                <div className="custom-piece-editor__measurements-panel">
                  <h3>Paso 2: Medidas y Ángulos</h3>

                  {vertices.length === 3 ? (
                    <p style={{ color: 'var(--editor-muted)', fontSize: '13px', lineHeight: '1.5', marginBottom: '8px' }}>
                      Ingresa la medida de los 3 lados. Al ser un triángulo, la figura tomará su forma correcta automáticamente sin necesidad de fijar ángulos.
                    </p>
                  ) : (
                    <p style={{ color: 'var(--editor-muted)', fontSize: '13px', lineHeight: '1.5', marginBottom: '8px' }}>
                      Ingresa las medidas de cada lado. Para que esta figura de {vertices.length} lados tome su forma exacta, <strong>puedes fijar hasta {maxConstraints} {maxConstraints === 1 ? 'ángulo' : 'ángulos'}</strong> haciendo clic en las esquinas del dibujo.
                    </p>
                  )}

                  <div className="custom-piece-editor__configuration">
                    <label style={{ fontSize: '13px', fontWeight: '600', color: 'var(--editor-navy)' }}>Comportamiento de la figura</label>
                    <select value={construction.mode} disabled={construction.constraints.length > 0} onChange={e => setConstruction(c => ({...c, mode: e.target.value}))}>
                      <option value="cyclic">{vertices.length === 3 ? 'Triángulo (Automático)' : 'Polígono Cíclico (Automático)'}</option>
                      <option value="guided">Guiado por mi boceto inicial</option>
                    </select>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                    <span style={{ fontSize: '13px', color: 'var(--editor-navy)', fontWeight: '650' }}>Lados de la pieza</span>
                    <span style={{ fontSize: '12px', color: 'var(--editor-muted)' }}>{measuredCount} / {segments.length} completados</span>
                  </div>

                  <ol className="custom-piece-editor__segment-list">
                    {segments.map((segment) => <SegmentField key={segment.id} segment={segment} active={activeSegmentIndex === segment.index}
                      inputRef={segment.index === 0 ? firstInputRef : undefined} onSelect={() => setActiveSegmentIndex(segment.index)}
                      onChange={(value, badInput) => updateSegment(segment.index, value, badInput)} />)}
                  </ol>

                  {/* LISTA DINÁMICA DE MÚLTIPLES ÁNGULOS */}
                  {vertices.length > 3 && (
                    <div className="custom-piece-editor__angles-panel">
                      <h4>
                        <span>Ángulos interiores <MousePointerClick size={14} style={{ display: 'inline', verticalAlign: 'middle', marginLeft: '4px' }}/></span>
                        <span style={{ fontSize: '12px', color: 'var(--editor-muted)', fontWeight: 'normal' }}>{construction.constraints.length} / {maxConstraints} fijados</span>
                      </h4>

                      {construction.constraints.length === 0 && selectedVertexIndex === null ? (
                        <p style={{ fontSize: '12px', color: 'var(--editor-muted)', margin: 0, lineHeight: '1.5' }}>
                          Haz clic en las esquinas del dibujo (V1, V2...) para fijar un ángulo exacto si la pieza lo requiere.
                        </p>
                      ) : (
                        <ul className="custom-piece-editor__angle-list">
                          {vertices.map((_, index) => {
                            const fixed = construction.constraints.find(c => c.vertex === index);
                            const isSelected = selectedVertexIndex === index;

                            if (!fixed && !isSelected) return null;

                            const displayAngleValue = fixed
                              ? fixed.angle
                              : (angles[index] !== undefined && !Number.isNaN(angles[index])
                                  ? Number(angles[index].toFixed(2))
                                  : "");

                            return (
                              <li key={index} className="custom-piece-editor__vertex-input-group" data-active={isSelected ? "true" : undefined}>
                                <span>V{index + 1}</span>
                                <input
                                  ref={isSelected ? angleInputRef : null}
                                  type="number" step="any" placeholder="Ángulo"
                                  value={displayAngleValue}
                                  onChange={(e) => handleAngleFix(index, e.target.value)}
                                  onFocus={() => { setActiveSegmentIndex(index); setSelectedVertexIndex(index); }}
                                  disabled={!fixed && isLimitReached}
                                />
                                {fixed ? (
                                  <button type="button" data-active="true" onClick={() => unfixAngle(index)}>Liberar</button>
                                ) : (
                                  <button
                                    type="button"
                                    disabled={isLimitReached}
                                    onClick={() => handleAngleFix(index, String(angles[index] !== undefined && !Number.isNaN(angles[index]) ? Number(angles[index].toFixed(2)) : 90))}
                                  >
                                    Fijar
                                  </button>
                                )}
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  )}
                </div>

                {/* BOTÓN AL FINAL DE LA COLUMNA DE CONTROLES */}
                {!onGeometryChange && (
                  <div style={{ marginTop: 'auto', paddingTop: '16px' }}>
                    <button type="button" className="custom-piece-editor__button--add" disabled={!canAdd} onClick={() => {
                      if (onGuardarVertices) onGuardarVertices({
                        vertices: result.vertices_mm.map((point) => [...point]),
                        rawState: { drawing: { vertices: drawing.vertices, isClosed: drawing.isClosed }, segments, construction }
                      });
                    }}>
                      <Plus size={18} /> {addLabel}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </fieldset>
    </section>
  );
}