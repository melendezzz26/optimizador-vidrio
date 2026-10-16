import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, Plus, MousePointer2, RotateCcw, Undo2 } from "lucide-react";
import "./CustomPieceEditor.css";
import { interiorAngles } from "./polygonMeasurements";
import { fitVerticesToPreview } from "./geometryScaling";
import { createSegments, isPositiveLength } from "./segmentGeometry";
import { validateConvexPolygon } from "./convexityValidation";
import { buildConstrainedGeometry } from "./constrainedGeometry";

const DRAWING_WIDTH = 800;
const DRAWING_HEIGHT = 500;
const VERTEX_HIT_RADIUS = 24;
const formatLength = (value) => new Intl.NumberFormat("es", { maximumSignificantDigits: 8 }).format(value);

function useCanvasSize() {
  const ref = useRef(null);
  const [size, setSize] = useState({ width: 560, height: 300 });
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        setSize((current) => current.width === width && current.height === height ? current : { width, height });
      }
    });
    observer.observe(ref.current);
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
        aria-label={`Seleccionar segmento ${segment.id}`}
        onClick={() => { onSelect(); localRef.current?.focus(); }}>
        {segment.id}
      </button>
      <div className="custom-piece-editor__field">
        <label className="custom-piece-editor__sr-only" htmlFor={id}>Longitud del segmento {segment.id} en milímetros</label>
        <div className="custom-piece-editor__input-wrapper">
          <input ref={(node) => { localRef.current = node; if (inputRef) inputRef.current = node; }} id={id}
            className="custom-piece-editor__input" type="number" inputMode="decimal" step="any" required
            value={segment.lengthMm} onChange={updateValue} onBlur={() => setTouched(true)}
            aria-invalid={Boolean(invalid)} aria-describedby={invalid ? `${id}-error` : undefined} placeholder="Longitud" />
          <span className="custom-piece-editor__input-unit" aria-hidden="true">mm</span>
        </div>
        {invalid && <p id={`${id}-error`} className="custom-piece-editor__field-error" role="alert">
          {segment.lengthMm === "" && !segment.badInput ? "Completa esta medida." : "Usa un número finito mayor que 0."}
        </p>}
      </div>
    </li>
  );
}

// Labels use CSS-pixel sizing in both SVG coordinate systems. On dense contours,
// keep the active label first and omit colliding labels; all sides remain in the list.
function SegmentOverlay({
  points,
  activeSegmentIndex,
  selectedVertexIndex = null,
  fixedVertices = [],
  onSelectVertex = null,
  measured,
  width,
  height,
  unitScale = 1,
}) {
  const occupied = [];
  const interactiveVertices = Boolean(onSelectVertex) && points.length > 3;
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
  }).sort((a, b) => Number(b.index === activeSegmentIndex) - Number(a.index === activeSegmentIndex));
  return (
    <g className="custom-piece-editor__segments" aria-hidden="true">
      {points.map((start, index) => {
        const end = points[(index + 1) % points.length];
        return <line key={index} x1={start.x} y1={start.y} x2={end.x} y2={end.y}
          data-active={index === activeSegmentIndex} data-provisional={measured ? !measured[index] : false}
          vectorEffect="non-scaling-stroke" />;
      })}
      {labels.map(({ index, x, y }) => {
        if (occupied.some((label) => Math.abs(label.x - x) * unitScale < 44 && Math.abs(label.y - y) * unitScale < 26)) return null;
        occupied.push({ x, y });
        return <text key={index} x={x} y={y} textAnchor="middle" dominantBaseline="central"
          style={{ fontSize: 13 / unitScale, strokeWidth: 5 / unitScale }} data-active={index === activeSegmentIndex}>S{index + 1}</text>;
      })}
      {points.map((point, index) => (
        <text
          key={`vertex-${index}`}
          x={point.x}
          y={Math.max(14 / unitScale, point.y - 12 / unitScale)}
          className="custom-piece-editor__vertex-label"
          data-vertex={index + 1}
          data-interactive={interactiveVertices ? "true" : undefined}
          data-highlight={index === activeSegmentIndex || index === selectedVertexIndex}
          data-selected={index === selectedVertexIndex ? "true" : undefined}
          data-fixed={fixedVertices.includes(index) ? "true" : undefined}
          style={{ fontSize: 12 / unitScale, strokeWidth: 4 / unitScale }}
          textAnchor="middle"
          onClick={interactiveVertices ? (event) => {
            event.stopPropagation();
            onSelectVertex(index);
          } : undefined}
        >
          V{index + 1}
        </text>
      ))}
    </g>
  );
}

function DimensionalPreview({ vertices, result, activeSegmentIndex, selectedVertexIndex, fixedVertices, onSelectVertex }) {
  const [canvasRef, size] = useCanvasSize();
  const points = result.vertices_mm ? result.vertices_mm.map(([x, y]) => ({ x, y })) : vertices;
  const geometry = fitVerticesToPreview(points, size.width, size.height, 38);
  return (
    <svg ref={canvasRef} className="custom-piece-editor__preview-canvas" viewBox={`0 0 ${size.width} ${size.height}`}
      role="img" aria-label={`${result.status === "complete" ? "Vista dimensional completa" : "Vista dimensional provisional"}. Segmento S${activeSegmentIndex + 1} seleccionado.`}>
      {geometry && <>
        <polygon className="custom-piece-editor__preview-shape" points={geometry.points.map(({ x, y }) => `${x},${y}`).join(" ")}
          vectorEffect="non-scaling-stroke" aria-hidden="true" />
        <SegmentOverlay
          points={geometry.points}
          activeSegmentIndex={activeSegmentIndex}
          selectedVertexIndex={selectedVertexIndex}
          fixedVertices={fixedVertices}
          onSelectVertex={onSelectVertex}
          measured={result.measured}
          width={size.width}
          height={size.height}
        />
      </>}
    </svg>
  );
}

function dimensionalError(result) {
  switch (result.error) {
    case "inequality": return "No se puede cerrar un polígono: el lado mayor debe ser menor que la suma de los demás lados.";
    case "angle": return "El ángulo fijado debe ser un número finito mayor que 0 y menor que 180 grados.";
    case "angle-configuration": return "No se encontró un polígono convexo cerrado con las medidas y ángulos ingresados. Revisa o libera una restricción, o cambia el boceto; las longitudes se conservan.";
    case "constraint-limit": return "Puedes fijar como máximo n − 3 ángulos, en vértices diferentes.";
    case "configuration": return "Selecciona una configuración geométrica disponible.";
    case "shape-mismatch": return "Las medidas no corresponden al contorno. Cambia una longitud para escalar toda la figura conservando sus ángulos.";
    case "drawing": return "Hay vértices consecutivos en el mismo punto. Deshaz o reinicia el dibujo para separar esos vértices.";
    case "length": return "Revisa las medidas marcadas: cada longitud debe ser un número finito mayor que 0.";
    case "numeric-range": return "No se pueden representar estas medidas con precisión numérica. Revisa la magnitud de los valores.";
    default: return "No se logró cerrar la vista con este boceto y estas medidas. Revisa las longitudes o corrige el dibujo. Esto no determina su validez para corte.";
  }
}

function PolygonCanvas({ onGuardarVertices, headerReady, disabled, initialState, addLabel, helpText, onGeometryChange }) {
  const instructionsId = useId();
  const drawingHeadingId = useId();
  const dimensionsHeadingId = useId();
  const previewHeadingId = useId();
  const correctionId = useId();
  const validationId = useId();
  const validationHelpId = useId();
  const validationMessageId = useId();
  const firstInputRef = useRef(null);
  const drawingHeadingRef = useRef(null);
  const dimensionsRef = useRef(null);
  const angleInputRefs = useRef({});
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
      constraints: previous?.constraints || (previous?.mode === 'angle' ? [{ vertex: 1, angle: previous.angle }] : []),
    };
  });

  const { vertices, isClosed } = drawing;
  const sketchValidation = useMemo(() => validateConvexPolygon(vertices.map(({ x, y }) => [x, y])), [vertices]);
  const result = useMemo(() => !isClosed ? null : buildConstrainedGeometry(segments, {
    ...construction, mode: construction.constraints.length ? 'angles' : construction.mode === 'angle' ? 'guided' : construction.mode,
    drawing: vertices.map(({ x, y }) => [x, y]),
  }),
  [vertices, isClosed, segments, construction]);
  const validation = useMemo(() => isClosed && !sketchValidation.isValid ? sketchValidation :
    validateConvexPolygon(result?.status === "complete" ? result.vertices_mm : null), [result, isClosed, sketchValidation]);
  const validationRejected = !validation.isValid && validation.reason !== "INCOMPLETE";
  const measuredCount = segments.filter((segment) => !segment.badInput && isPositiveLength(segment.lengthMm)).length;
  const dimensionsReady = result?.status === "complete";
  const canAdd = isClosed && dimensionsReady && validation.reason === "VALID" &&
    Boolean(result?.vertices_mm) && headerReady && Boolean(onGuardarVertices) && !disabled;
  const hasMeasurements = segments.some(({ lengthMm, badInput }) => lengthMm !== "" || badInput);
  const activeSegment = segments[activeSegmentIndex];
  const activeLength = activeSegment && isPositiveLength(activeSegment.lengthMm) && !activeSegment.badInput
    ? `${formatLength(Number(activeSegment.lengthMm))} mm · Medida ingresada`
    : result?.lengths ? `≈ ${formatLength(result.lengths[activeSegmentIndex])} mm · Estimación provisional` : "Sin medida real";
  const angles = useMemo(() => {
    try { return result?.vertices_mm ? interiorAngles(result.vertices_mm) : []; } catch { return []; }
  }, [result]);
  const fixedVertices = useMemo(() => construction.constraints.map((item) => item.vertex), [construction.constraints]);
  const drawingPoints = vertices.map(({ x, y }) => `${x},${y}`).join(" ");

  useEffect(() => {
    if (!isClosed) return;
    if (closedWithKeyboard.current) firstInputRef.current?.focus();
    else dimensionsRef.current?.scrollIntoView({ block: "nearest", behavior: "instant" });
  }, [isClosed]);

  useEffect(() => {
    if (selectedVertexIndex === null) return;
    const input = angleInputRefs.current[selectedVertexIndex];
    if (input) input.focus();
  }, [selectedVertexIndex, construction.constraints.length]);

  useEffect(() => {
    if (onGeometryChange) onGeometryChange(dimensionsReady && validation.isValid ? result.vertices_mm : null);
  }, [onGeometryChange, dimensionsReady, validation.isValid, result]);

  // T03: Selección directa de un vértice para ingresar/fijar su ángulo
  function selectVertex(vertexIndex) {
    if (disabled || !isClosed || vertices.length <= 3) return;
    setSelectedVertexIndex(vertexIndex);
    setActiveSegmentIndex(vertexIndex);
    const defaultAngle = String(
      angles[vertexIndex] !== undefined ? Number(angles[vertexIndex].toFixed(2)) : 90
    );
    setConstruction((current) => {
      if (current.constraints.some((item) => item.vertex === vertexIndex)) {
        return current;
      }
      const maxConstraints = vertices.length - 3;
      if (current.constraints.length < maxConstraints) {
        return {
          ...current,
          constraints: [...current.constraints, { vertex: vertexIndex, angle: defaultAngle }],
        };
      }
      if (maxConstraints === 1) {
        return {
          ...current,
          constraints: [{ vertex: vertexIndex, angle: defaultAngle }],
        };
      }
      return current;
    });
  }

  function addVertex(event) {
    if (disabled || event.button !== 0) return;
    const screenMatrix = event.currentTarget.getScreenCTM();
    if (!screenMatrix) return;
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(screenMatrix.inverse());
    if (point.x < 0 || point.x > DRAWING_WIDTH || point.y < 0 || point.y > DRAWING_HEIGHT) return;

    if (isClosed) {
      if (vertices.length > 3) {
        const hitIndex = vertices.findIndex(
          (v) => Math.hypot(point.x - v.x, point.y - v.y) <= VERTEX_HIT_RADIUS
        );
        if (hitIndex !== -1) selectVertex(hitIndex);
      }
      return;
    }

    setDrawing((current) => current.isClosed ? current : {
      ...current, vertices: [...current.vertices, { x: point.x, y: point.y }],
    });
  }

  function closePolygon(event) {
    if (vertices.length < 3 || isClosed) return;
    closedWithKeyboard.current = event.detail === 0;
    setSegments(createSegments(vertices));
    setActiveSegmentIndex(0);
    setSelectedVertexIndex(null);
    setDrawing((current) => ({ ...current, isClosed: true }));
  }

  function undoVertex() {
    setConstruction({ mode: 'cyclic', angle: '90', constraints: [] });
    setSegments([]);
    setActiveSegmentIndex(null);
    setSelectedVertexIndex(null);
    setDrawing((current) => ({ vertices: current.vertices.slice(0, -1), isClosed: false }));
    if (vertices.length === 1) drawingHeadingRef.current?.focus({ preventScroll: true });
  }

  function resetDrawing() {
    setConstruction({ mode: 'cyclic', angle: '90', constraints: [] });
    setSegments([]);
    setActiveSegmentIndex(null);
    setSelectedVertexIndex(null);
    setDrawing({ vertices: [], isClosed: false });
    drawingHeadingRef.current?.focus({ preventScroll: true });
  }

  function updateSegment(index, lengthMm, badInput) {
    setSegments((current) => current.map((segment) => segment.index === index ? { ...segment, lengthMm, badInput } : segment));
  }

  function toggleAngle(vertex) {
    setActiveSegmentIndex(vertex);
    setSelectedVertexIndex(vertex);
    setConstruction(current => ({
      ...current,
      constraints: current.constraints.some(item => item.vertex === vertex)
        ? current.constraints.filter(item => item.vertex !== vertex)
        : current.constraints.length < vertices.length - 3
          ? [...current.constraints, { vertex, angle: String(angles[vertex] !== undefined ? Number(angles[vertex].toFixed(2)) : 90) }]
          : current.constraints,
    }));
  }

  function updateAngle(vertex, angle) {
    setSelectedVertexIndex(vertex);
    setConstruction(current => ({
      ...current,
      angle: vertex === 1 ? angle : current.angle,
      constraints: current.constraints.map(item => item.vertex === vertex ? { vertex, angle } : item),
    }));
  }

  function addPiece() {
    if (!canAdd) return;

    if (onGuardarVertices) {
      onGuardarVertices({
        // Vértices físicos para la base de datos
        vertices: result.vertices_mm.map((point) => [...point]),
        // Memoria gráfica para poder volver a editar
        rawState: {
          drawing: { vertices: drawing.vertices, isClosed: drawing.isClosed },
          segments: segments,
          construction: { ...construction, constraints: construction.constraints.map(item => ({ ...item })) },
        }
      });
    }
    resetDrawing();
  }

  return (
    <div className="custom-piece-editor__content" data-closed={isClosed}>
      <section className="custom-piece-editor__workspace" aria-labelledby={drawingHeadingId}>
        <div className="custom-piece-editor__workspace-header">
          <h3 id={drawingHeadingId} ref={drawingHeadingRef} tabIndex={-1}>
            <span className="custom-piece-editor__step" aria-hidden="true">1</span>Dibujo original
          </h3>
          <div className="custom-piece-editor__status" role="status" aria-atomic="true">
            <strong data-closed={isClosed}>{isClosed ? "Polígono cerrado" : "Polígono abierto"}</strong>
            <span>{vertices.length} {vertices.length === 1 ? "vértice" : "vértices"}</span>
          </div>
        </div>
        <div className="custom-piece-editor__surface">
          <span className="custom-piece-editor__canvas-label">Boceto · Sin escala física</span>
          {/* Inherited T01 limitation: full keyboard drawing remains outside T02. */}
          <svg ref={canvasRef} className="custom-piece-editor__canvas" viewBox={`0 0 ${DRAWING_WIDTH} ${DRAWING_HEIGHT}`}
            role="img" aria-label="Lienzo del dibujo original, sin escala física"
            aria-describedby={isClosed ? correctionId : instructionsId} data-closed={isClosed} onClick={addVertex}>
            <g className="custom-piece-editor__drawing" aria-hidden="true">
              {isClosed ? <polygon points={drawingPoints} /> : <polyline points={drawingPoints} />}
              {vertices.map((vertex, index) => (
                <circle
                  key={index}
                  cx={vertex.x}
                  cy={vertex.y}
                  r={isClosed && vertices.length > 3 ? (selectedVertexIndex === index ? 7 : 5) : 4}
                  className="custom-piece-editor__vertex-point"
                  data-vertex={index + 1}
                  data-selected={isClosed && selectedVertexIndex === index ? "true" : undefined}
                  data-fixed={isClosed && fixedVertices.includes(index) ? "true" : undefined}
                  onClick={isClosed && vertices.length > 3 ? (event) => {
                    event.stopPropagation();
                    selectVertex(index);
                  } : undefined}
                />
              ))}
            </g>
            {isClosed && (
              <SegmentOverlay
                points={vertices}
                activeSegmentIndex={activeSegmentIndex}
                selectedVertexIndex={selectedVertexIndex}
                fixedVertices={fixedVertices}
                onSelectVertex={vertices.length > 3 ? selectVertex : null}
                width={DRAWING_WIDTH}
                height={DRAWING_HEIGHT}
                unitScale={canvasSize.width / DRAWING_WIDTH}
              />
            )}
          </svg>
          {!vertices.length && <div className="custom-piece-editor__empty" aria-hidden="true">
            <MousePointer2 size={24} strokeWidth={1.5} /><strong>Haz clic para comenzar</strong>
            <span>Marca los vértices siguiendo el contorno de la pieza.</span>
          </div>}
        </div>
        <div className="custom-piece-editor__toolbar" role="group" aria-label="Herramientas de dibujo">
          <button type="button" className="custom-piece-editor__button" disabled={!vertices.length} onClick={undoVertex}
            aria-label="Deshacer último vértice" title="Deshacer último vértice" aria-describedby={isClosed ? correctionId : undefined}>
            <Undo2 size={16} aria-hidden="true" /> Deshacer
          </button>
          <button type="button" className="custom-piece-editor__button custom-piece-editor__button--quiet" disabled={!vertices.length}
            onClick={resetDrawing} aria-label="Reiniciar dibujo" aria-describedby={isClosed ? correctionId : undefined}>
            <RotateCcw size={16} aria-hidden="true" /> Reiniciar
          </button>
          {!isClosed ? <button type="button" className="custom-piece-editor__button custom-piece-editor__button--primary"
            disabled={vertices.length < 3} onClick={closePolygon} aria-describedby={instructionsId}>
            <Check size={16} aria-hidden="true" /> Cerrar polígono
          </button> : <span className="custom-piece-editor__closed-feedback"><Check size={16} aria-hidden="true" /> Contorno cerrado</span>}
        </div>
        {!isClosed ? <p id={instructionsId} className="custom-piece-editor__instructions">
          {vertices.length < 3
            ? `Falta${vertices.length === 2 ? "" : "n"} ${3 - vertices.length} ${vertices.length === 2 ? "vértice" : "vértices"} para cerrar. Deshacer elimina el último punto.`
            : "Puedes seguir dibujando o cerrar el polígono para medir cada lado."}
        </p> : <p id={correctionId} className="custom-piece-editor__correction-note">
          Deshacer reabre y elimina el último vértice. Reiniciar borra el dibujo.
          {hasMeasurements && " Ambas acciones borran las medidas ingresadas."}
          {vertices.length > 3 && " Haz clic directamente sobre un vértice (V1, V2…) para fijar su ángulo."}
        </p>}
      </section>
      <section ref={dimensionsRef} className="custom-piece-editor__dimensions" aria-labelledby={dimensionsHeadingId}>
        <h3 id={dimensionsHeadingId}><span className="custom-piece-editor__step" aria-hidden="true">2</span>Dimensiones por segmento</h3>
        {!isClosed ? <p className="custom-piece-editor__section-help">Cierra el polígono para identificar sus lados e ingresar sus longitudes en milímetros.</p> : <>
          <label className="custom-piece-editor__configuration">Configuración geométrica
            <select value={construction.mode} disabled={construction.constraints.length > 0} onChange={event => setConstruction(current => ({
              ...current,
              mode: event.target.value,
            }))}>
              <option value="cyclic">{vertices.length === 3 ? 'Triángulo por tres lados' : 'Lados independientes · polígono cíclico'}</option>
              <option value="guided">Usar boceto como punto de partida</option>
            </select>
          </label>
          {construction.constraints.length > 0 && <p className="custom-piece-editor__section-help">Libera los ángulos fijados para cambiar la configuración de partida.</p>}
          <p className="custom-piece-editor__section-help">{construction.constraints.length
            ? 'Las longitudes y los ángulos fijados en los vértices seleccionados definen la forma final.'
            : construction.mode === 'guided' ? 'Todos los lados son independientes. El boceto orienta la búsqueda de una forma convexa; puedes hacer clic en un vértice para fijar su ángulo.'
            : vertices.length === 3 ? 'Ingresa los tres lados. Los ángulos se calculan a partir del triángulo resultante.'
            : 'Las longitudes no definen una única forma. Esta configuración coloca todos los vértices sobre una circunferencia o permite hacer clic directamente sobre un vértice para fijar su ángulo.'}</p>
          <p className="custom-piece-editor__progress" role="status" aria-atomic="true">{measuredCount} de {segments.length} medidas ingresadas</p>
          <ol className="custom-piece-editor__segment-list">
            {segments.map((segment) => <SegmentField key={segment.id} segment={segment} active={activeSegmentIndex === segment.index}
              inputRef={segment.index === 0 ? firstInputRef : undefined} onSelect={() => setActiveSegmentIndex(segment.index)}
              onChange={(value, badInput) => updateSegment(segment.index, value, badInput)} />)}
          </ol>
          <p className="custom-piece-editor__section-help">El lado seleccionado se resalta en ambos dibujos. Cada longitud se edita de forma independiente.</p>
        </>}
      </section>
      {isClosed && <section className="custom-piece-editor__preview" aria-labelledby={previewHeadingId}>
        <div className="custom-piece-editor__preview-header">
          <h3 id={previewHeadingId}><span className="custom-piece-editor__step" aria-hidden="true">3</span>Vista dimensional</h3>
          <p className="custom-piece-editor__preview-status" data-ready={dimensionsReady} role="status" aria-atomic="true">
            {dimensionsReady ? "Vista dimensional completa" : "Vista dimensional provisional"}
            {result.status === "error" && " · Cierre pendiente"}
          </p>
        </div>
        <p className="custom-piece-editor__section-help">
          {`${measuredCount} de ${segments.length} lados medidos. ${dimensionsReady ? 'Geometría final según la configuración elegida.' : 'Completa todos los lados y revisa las restricciones para construir la geometría final.'}`}
        </p>
        <div className="custom-piece-editor__preview-surface">
          {result.status === "error" ? <div className="custom-piece-editor__preview-placeholder">
            <p className="custom-piece-editor__geometry-error" role="alert">{dimensionalError(result)}</p>
          </div> : (
            <DimensionalPreview
              vertices={vertices}
              result={result}
              activeSegmentIndex={activeSegmentIndex}
              selectedVertexIndex={selectedVertexIndex}
              fixedVertices={fixedVertices}
              onSelectVertex={vertices.length > 3 ? selectVertex : null}
            />
          )}
        </div>
        <div className="custom-piece-editor__preview-caption">
          <p className="custom-piece-editor__active-length"><strong>{activeSegment?.id}</strong><span>{activeLength}</span></p>
          <p className="custom-piece-editor__preview-note">{!dimensionsReady && "Trazo discontinuo: sin medida real. "}Cuadrícula de referencia, sin escala en mm.</p>
        </div>
        <p className="custom-piece-editor__section-help">Los vértices finales definen la forma guardada. Los ángulos se calculan desde esos vértices.</p>
      </section>}
      {isClosed && (angles.length > 0 || construction.constraints.length > 0 || selectedVertexIndex !== null || (vertices.length > 3 && measuredCount === vertices.length)) && <section className="custom-piece-editor__angles" aria-label="Ángulos interiores">
        <h3>Ángulos interiores</h3>
        <p>Haz clic directamente sobre un vértice en el dibujo o usa la lista para fijar hasta {vertices.length - 3} ángulos.</p>
        {selectedVertexIndex !== null && (
          <p role="status">Vértice V{selectedVertexIndex + 1} seleccionado</p>
        )}
        <p role="status">Restricciones de forma: {construction.constraints.length} de {vertices.length - 3} utilizadas</p>
        <ol>{vertices.map((_, index) => {
          const fixed = construction.constraints.find(item => item.vertex === index);
          const isSelected = selectedVertexIndex === index;
          return <li key={index} data-active={activeSegmentIndex === index} data-selected={isSelected ? "true" : undefined}>
            {fixed ? <label>Ángulo interior fijado en V{index + 1} (grados)
              <input
                ref={(node) => { angleInputRefs.current[index] = node; }}
                type="number"
                step="any"
                required
                value={fixed.angle}
                aria-invalid={!isPositiveLength(fixed.angle) || Number(fixed.angle) >= 180}
                onFocus={() => {
                  setActiveSegmentIndex(index);
                  setSelectedVertexIndex(index);
                }}
                onChange={event => updateAngle(index, event.target.value)}
              /> Fijado
            </label> : <span>V{index + 1}: {angles[index] === undefined ? '—' : `${formatLength(angles[index])}°`} Calculado</span>}
            {vertices.length > 3 && <button type="button" onClick={() => toggleAngle(index)}
              disabled={!fixed && construction.constraints.length >= vertices.length - 3}
              aria-label={`${fixed ? 'Liberar' : 'Fijar'} ángulo V${index + 1}`}>
              {fixed ? 'Liberar ángulo' : 'Fijar ángulo'}
            </button>}
          </li>;
        })}</ol>
      </section>}
      <section className="custom-piece-editor__next-step" aria-labelledby={validationId}>
        <div>
          <h3 id={validationId}><span className="custom-piece-editor__step" aria-hidden="true">4</span>Validación geométrica</h3>
          <div
            role={validationRejected ? "alert" : "status"}
            aria-label="Resultado de validación geométrica"
            aria-atomic="true"
          >
            <p
              id={validationMessageId}
              className="custom-piece-editor__validation-message"
              data-valid={validation.isValid}
              data-rejected={validationRejected}
            >
              {validation.message}
            </p>
          </div>
          {validationRejected && <p>Revisa las medidas o deshaz el dibujo para corregir el contorno.</p>}
          <p id={validationHelpId}>{headerReady
            ? helpText
            : "Selecciona el tipo de vidrio y el espesor en Nuevo pedido para agregar piezas."}</p>
        </div>
        {!onGeometryChange && <button type="button" className="custom-piece-editor__button custom-piece-editor__button--add" disabled={!canAdd} onClick={addPiece} aria-describedby={`${validationMessageId} ${validationHelpId}`}>
          <Plus size={16} aria-hidden="true" /> {addLabel}
        </button>}
      </section>
    </div>
  );
}

export default function CustomPieceEditor({ onGuardarVertices, initialState, headerReady = true, disabled = false,
  title = "Pieza personalizada", addLabel = "Agregar pieza al pedido",
  helpText = "Agrega la pieza y guarda el pedido para registrarla.", onGeometryChange,
}) {
  const headingId = useId();
  return <section className="custom-piece-editor" aria-labelledby={headingId}>
    <header className="custom-piece-editor__header"><h2 id={headingId}>{title}</h2>
      <p>Traza los lados, ingresa sus medidas y elige la configuración de la forma final.</p></header>
    <fieldset className="custom-piece-editor__fieldset" disabled={disabled}>
      <PolygonCanvas onGuardarVertices={onGuardarVertices} initialState={initialState} headerReady={headerReady} disabled={disabled} addLabel={addLabel} helpText={helpText} onGeometryChange={onGeometryChange} />
    </fieldset>
    {!onGeometryChange && <p className="custom-piece-editor__notice">Las piezas agregadas se registran al guardar el pedido.</p>}
  </section>;
}