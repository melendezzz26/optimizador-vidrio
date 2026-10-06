import { useId, useState } from "react";
import "./CustomPieceEditor.css";

const DRAWING_WIDTH = 800;
const DRAWING_HEIGHT = 500;

function PolygonCanvas() {
  const instructionsId = useId();
  const [drawing, setDrawing] = useState({ vertices: [], isClosed: false });
  const { vertices, isClosed } = drawing;

  const addVertex = (event) => {
    if (event.button !== 0 || isClosed) return;

    // Map viewport clicks into SVG coordinates, including scrolling and resizing.
    const screenMatrix = event.currentTarget.getScreenCTM();
    if (!screenMatrix) return;

    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(
      screenMatrix.inverse(),
    );

    if (
      point.x < 0 || point.x > DRAWING_WIDTH ||
      point.y < 0 || point.y > DRAWING_HEIGHT
    ) return;

    setDrawing((current) => current.isClosed ? current : {
      ...current,
      vertices: [...current.vertices, { x: point.x, y: point.y }],
    });
  };

  const closePolygon = () => {
    setDrawing((current) => current.vertices.length < 3 || current.isClosed
      ? current
      : { ...current, isClosed: true });
  };

  const undoVertex = () => {
    setDrawing((current) => ({
      vertices: current.vertices.slice(0, -1),
      isClosed: false,
    }));
  };

  const resetDrawing = () => {
    setDrawing({ vertices: [], isClosed: false });
  };

  return (
    <div className="custom-piece-editor__content">
      <div className="custom-piece-editor__status" role="status">
        <strong className="custom-piece-editor__state">
          {isClosed ? "Polígono cerrado" : "Polígono abierto"}
        </strong>
        <span className="custom-piece-editor__count">
          {vertices.length} {vertices.length === 1 ? "vértice" : "vértices"}
        </span>
      </div>

      <p id={instructionsId} className="custom-piece-editor__instructions">
        {isClosed
          ? "Para seguir dibujando, deshaz el último vértice o reinicia el dibujo."
          : "Haz clic dentro del lienzo para agregar vértices. Necesitas al menos 3 para cerrar el polígono."}
      </p>

      {!isClosed && (
  <p className="custom-piece-editor__tip">
    <strong>Consejo de trazado:</strong>{" "}
    coloca los vértices siguiendo el contorno de la pieza. Si el último punto
    no quedó donde esperabas, utiliza Deshacer.
  </p>
)}

      <div className="custom-piece-editor__surface">
        <svg
          className="custom-piece-editor__canvas"
          viewBox={`0 0 ${DRAWING_WIDTH} ${DRAWING_HEIGHT}`}
          role="img"
          aria-label="Lienzo de pieza personalizada"
          aria-describedby={instructionsId}
          data-closed={isClosed}
          onClick={addVertex}
        >
          <title>Editor poligonal por clics</title>
          <g className="custom-piece-editor__drawing" aria-hidden="true">
            {vertices.slice(1).map((vertex, index) => (
              <line
                key={index}
                x1={vertices[index].x}
                y1={vertices[index].y}
                x2={vertex.x}
                y2={vertex.y}
                vectorEffect="non-scaling-stroke"
              />
            ))}
            {isClosed && (
              <line
                x1={vertices[vertices.length - 1].x}
                y1={vertices[vertices.length - 1].y}
                x2={vertices[0].x}
                y2={vertices[0].y}
                vectorEffect="non-scaling-stroke"
              />
            )}
            {vertices.map((vertex, index) => (
              <circle
                key={index}
                cx={vertex.x}
                cy={vertex.y}
                r="7"
                vectorEffect="non-scaling-stroke"
              />
            ))}
          </g>
        </svg>
        {vertices.length === 0 && (
          <span className="custom-piece-editor__empty">Haz clic para comenzar</span>
        )}
      </div>

      <div className="custom-piece-editor__toolbar" role="group" aria-label="Herramientas de dibujo">
        <button
          type="button"
          className="custom-piece-editor__button custom-piece-editor__button--primary"
          disabled={vertices.length < 3 || isClosed}
          onClick={closePolygon}
        >
          Cerrar polígono
        </button>
        <button
          type="button"
          className="custom-piece-editor__button"
          disabled={vertices.length === 0}
          onClick={undoVertex}
          title="Eliminar el último vértice y reabrir el polígono"
        >
          Deshacer último vértice
        </button>
        <button
          type="button"
          className="custom-piece-editor__button"
          disabled={vertices.length === 0}
          onClick={resetDrawing}
        >
          Reiniciar dibujo
        </button>
      </div>
    </div>
  );
}

export default function CustomPieceEditor() {
  const headingId = useId();

  return (
    <section className="custom-piece-editor" aria-labelledby={headingId}>
      <h2 id={headingId}>Pieza personalizada</h2>
      <p className="custom-piece-editor__description">
        Dibuja el contorno uniendo vértices con clics.
      </p>
      <PolygonCanvas />
      <p className="custom-piece-editor__notice">
        <strong>Borrador temporal.</strong>{" "}
        Se pierde al abandonar o recargar la página.
      </p>
    </section>
  );
}
