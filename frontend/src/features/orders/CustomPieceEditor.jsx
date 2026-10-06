import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, LockKeyhole, MousePointer2, RotateCcw, Undo2 } from "lucide-react";
import "./CustomPieceEditor.css";
import { fitVerticesToPreview } from "./geometryScaling";
import { buildDimensionalGeometry, createSegments, isPositiveLength } from "./segmentGeometry";

const DRAWING_WIDTH = 800;
const DRAWING_HEIGHT = 500;
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
function SegmentOverlay({ points, activeSegmentIndex, measured, width, height, unitScale = 1 }) {
  const occupied = [];
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
    </g>
  );
}

function DimensionalPreview({ vertices, result, activeSegmentIndex }) {
  const [canvasRef, size] = useCanvasSize();
  const points = result.vertices_mm ? result.vertices_mm.map(([x, y]) => ({ x, y })) : vertices;
  const geometry = fitVerticesToPreview(points, size.width, size.height, 38);
  return (
    <svg ref={canvasRef} className="custom-piece-editor__preview-canvas" viewBox={`0 0 ${size.width} ${size.height}`}
      role="img" aria-label={`${result.status === "complete" ? "Vista dimensional completa" : "Vista dimensional provisional"}. Segmento S${activeSegmentIndex + 1} seleccionado.`}>
      {geometry && <>
        <polygon className="custom-piece-editor__preview-shape" points={geometry.points.map(({ x, y }) => `${x},${y}`).join(" ")}
          vectorEffect="non-scaling-stroke" aria-hidden="true" />
        <SegmentOverlay points={geometry.points} activeSegmentIndex={activeSegmentIndex} measured={result.measured}
          width={size.width} height={size.height} />
      </>}
    </svg>
  );
}

function dimensionalError(result, total) {
  switch (result.error) {
    case "drawing": return "Hay vértices consecutivos en el mismo punto. Deshaz o reinicia el dibujo para separar esos vértices.";
    case "length": return "Revisa las medidas marcadas: cada longitud debe ser un número finito mayor que 0.";
    case "inequality": return result.measuredCount < total
      ? "Las medidas actuales y los lados estimados todavía no permiten cerrar la figura. Completa las medidas pendientes o corrige las ingresadas."
      : "Las longitudes ingresadas no permiten formar un polígono cerrado. Revisa las medidas de los segmentos.";
    case "numeric-range": return "No se pueden representar estas medidas con precisión numérica. Revisa la magnitud de los valores.";
    default: return "No se logró cerrar la vista con este boceto y estas medidas. Revisa las longitudes o corrige el dibujo. Esto no determina su validez para corte.";
  }
}

function PolygonCanvas() {
  const instructionsId = useId();
  const drawingHeadingId = useId();
  const dimensionsHeadingId = useId();
  const previewHeadingId = useId();
  const correctionId = useId();
  const validationId = useId();
  const validationHelpId = useId();
  const firstInputRef = useRef(null);
  const drawingHeadingRef = useRef(null);
  const dimensionsRef = useRef(null);
  const closedWithKeyboard = useRef(false);
  const [canvasRef, canvasSize] = useCanvasSize();
  const [drawing, setDrawing] = useState({ vertices: [], isClosed: false });
  const [segments, setSegments] = useState([]);
  const [activeSegmentIndex, setActiveSegmentIndex] = useState(null);
  const { vertices, isClosed } = drawing;
  const result = useMemo(() => isClosed ? buildDimensionalGeometry(vertices, segments) : null, [vertices, isClosed, segments]);
  const measuredCount = segments.filter((segment) => !segment.badInput && isPositiveLength(segment.lengthMm)).length;
  const dimensionsReady = result?.status === "complete";
  const hasMeasurements = segments.some(({ lengthMm, badInput }) => lengthMm !== "" || badInput);
  const activeSegment = segments[activeSegmentIndex];
  const activeLength = activeSegment && isPositiveLength(activeSegment.lengthMm) && !activeSegment.badInput
    ? `${formatLength(Number(activeSegment.lengthMm))} mm · Medida ingresada`
    : result?.lengths ? `≈ ${formatLength(result.lengths[activeSegmentIndex])} mm · Estimación provisional` : "Sin medida real";
  const drawingPoints = vertices.map(({ x, y }) => `${x},${y}`).join(" ");

  useEffect(() => {
    if (!isClosed) return;
    if (closedWithKeyboard.current) firstInputRef.current?.focus();
    else dimensionsRef.current?.scrollIntoView({ block: "nearest", behavior: "instant" });
  }, [isClosed]);

  function addVertex(event) {
    if (event.button !== 0 || isClosed) return;
    const screenMatrix = event.currentTarget.getScreenCTM();
    if (!screenMatrix) return;
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(screenMatrix.inverse());
    if (point.x < 0 || point.x > DRAWING_WIDTH || point.y < 0 || point.y > DRAWING_HEIGHT) return;
    setDrawing((current) => current.isClosed ? current : {
      ...current, vertices: [...current.vertices, { x: point.x, y: point.y }],
    });
  }

  function closePolygon(event) {
    if (vertices.length < 3 || isClosed) return;
    closedWithKeyboard.current = event.detail === 0;
    setSegments(createSegments(vertices));
    setActiveSegmentIndex(0);
    setDrawing((current) => ({ ...current, isClosed: true }));
  }

  function undoVertex() {
    setSegments([]);
    setActiveSegmentIndex(null);
    setDrawing((current) => ({ vertices: current.vertices.slice(0, -1), isClosed: false }));
    if (vertices.length === 1) drawingHeadingRef.current?.focus({ preventScroll: true });
  }

  function resetDrawing() {
    setSegments([]);
    setActiveSegmentIndex(null);
    setDrawing({ vertices: [], isClosed: false });
    drawingHeadingRef.current?.focus({ preventScroll: true });
  }

  function updateSegment(index, lengthMm, badInput) {
    setSegments((current) => current.map((segment) => segment.index === index ? { ...segment, lengthMm, badInput } : segment));
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
              {vertices.map((vertex, index) => <circle key={index} cx={vertex.x} cy={vertex.y} r="4" />)}
            </g>
            {isClosed && <SegmentOverlay points={vertices} activeSegmentIndex={activeSegmentIndex}
              width={DRAWING_WIDTH} height={DRAWING_HEIGHT} unitScale={canvasSize.width / DRAWING_WIDTH} />}
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
        </p>}
      </section>
      <section ref={dimensionsRef} className="custom-piece-editor__dimensions" aria-labelledby={dimensionsHeadingId}>
        <h3 id={dimensionsHeadingId}><span className="custom-piece-editor__step" aria-hidden="true">2</span>Dimensiones por segmento</h3>
        {!isClosed ? <p className="custom-piece-editor__section-help">Cierra el polígono para identificar sus lados e ingresar sus longitudes en milímetros.</p> : <>
          <p className="custom-piece-editor__section-help">Selecciona un lado e ingresa su longitud. Puedes corregir cualquier medida.</p>
          <p className="custom-piece-editor__progress" role="status" aria-atomic="true">{measuredCount} de {segments.length} medidas ingresadas</p>
          <ol className="custom-piece-editor__segment-list">
            {segments.map((segment) => <SegmentField key={segment.id} segment={segment} active={activeSegmentIndex === segment.index}
              inputRef={segment.index === 0 ? firstInputRef : undefined} onSelect={() => setActiveSegmentIndex(segment.index)}
              onChange={(value, badInput) => updateSegment(segment.index, value, badInput)} />)}
          </ol>
          <p className="custom-piece-editor__section-help">El lado seleccionado se resalta en ambos dibujos. Los campos vacíos siguen pendientes.</p>
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
          {result.status === "unscaled" ? "Sin escala física. Ingresa una primera medida para dimensionar el boceto."
            : `${measuredCount} de ${segments.length} segmentos medidos. ${dimensionsReady ? "Reconstrucción cerrada con tus longitudes." : "Los lados sin medida usan estimaciones del boceto."}`}
        </p>
        <div className="custom-piece-editor__preview-surface">
          {result.status === "error" ? <div className="custom-piece-editor__preview-placeholder">
            <p className="custom-piece-editor__geometry-error" role="alert">{dimensionalError(result, segments.length)}</p>
          </div> : <DimensionalPreview vertices={vertices} result={result} activeSegmentIndex={activeSegmentIndex} />}
        </div>
        <div className="custom-piece-editor__preview-caption">
          <p className="custom-piece-editor__active-length"><strong>{activeSegment?.id}</strong><span>{activeLength}</span></p>
          <p className="custom-piece-editor__preview-note">{!dimensionsReady && "Trazo discontinuo: sin medida real. "}Cuadrícula de referencia, sin escala en mm.</p>
        </div>
        <p className="custom-piece-editor__section-help">El boceto orienta la reconstrucción; las longitudes pueden cambiar sus ángulos. Esta vista no es otro editor.</p>
      </section>}
      {isClosed && <section className="custom-piece-editor__next-step" aria-labelledby={validationId}>
        <div>
          <h3 id={validationId}><span className="custom-piece-editor__step" aria-hidden="true">4</span>Validación pendiente</h3>
          <p id={validationHelpId}>{dimensionsReady ? "Las dimensiones están completas. Falta validar la geometría en T03."
            : "Completa las longitudes y el cierre dimensional. Agregar la pieza requiere después la validación de T03."}</p>
        </div>
        <button type="button" className="custom-piece-editor__button custom-piece-editor__button--add" disabled aria-describedby={validationHelpId}>
          <LockKeyhole size={16} aria-hidden="true" /> Agregar pieza al pedido
        </button>
      </section>}
    </div>
  );
}

export default function CustomPieceEditor() {
  const headingId = useId();
  return <section className="custom-piece-editor" aria-labelledby={headingId}>
    <header className="custom-piece-editor__header"><h2 id={headingId}>Pieza personalizada</h2>
      <p>Traza el contorno y define la longitud real de cada lado.</p></header>
    <PolygonCanvas />
    <p className="custom-piece-editor__notice"><strong>Borrador temporal.</strong> Se pierde al salir o recargar la página.</p>
  </section>;
}
