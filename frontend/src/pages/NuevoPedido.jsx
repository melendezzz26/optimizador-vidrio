import { useEffect, useRef, useState } from "react";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import {
  Trash2,
  Save,
  X,
  Layers3,
  Ruler,
  PackagePlus,
} from "lucide-react";
import fondoVidrio from "../assets/fondo-vidrio.png";
import CustomPieceEditor from "../features/orders/CustomPieceEditor";
import { createOrder, listOrderMaterials } from "../features/orders/ordersApi";
import "./NuevoPedido.css";

function NuevoPedido() {
  const [tiposVidrio, setTiposVidrio] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState("");
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submitting = useRef(false);
  const nextPieceId = useRef(1);
  const [error, setError] = useState("");
  const [savedOrderId, setSavedOrderId] = useState(null);
  const [editorKey, setEditorKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    listOrderMaterials(controller.signal).then((materials) => {
      setTiposVidrio(materials.filter((material) => material.estado && material.espesores_mm.length));
    }).catch((err) => {
      if (!controller.signal.aborted) setCatalogError(err.message);
    }).finally(() => {
      if (!controller.signal.aborted) setCatalogLoading(false);
    });
    return () => controller.abort();
  }, [catalogAttempt]);

  const [tipoVidrio, setTipoVidrio] = useState("");
  const [espesor, setEspesor] = useState("");
  const [piezas, setPiezas] = useState([]);
  const material = tiposVidrio.find((tipo) => tipo.id_tipo_vidrio === Number(tipoVidrio));
  const headerReady = Boolean(material && material.espesores_mm.some((value) => Number(value) === Number(espesor)));

  const [listaAnimada] = useAutoAnimate();

  const cambiarTipoVidrio = (e) => {
    setTipoVidrio(e.target.value);
    setEspesor("");
  };

  const agregarPieza = (piece) => {
    if (submitting.current || !headerReady) return;
    const nuevaPieza = {
      ...piece,
      id: nextPieceId.current++,
    };
    setPiezas((current) => [...current, nuevaPieza]);
    setSavedOrderId(null);
    setError("");
  };

  const eliminarPieza = (id) => {
    if (submitting.current) return;
    setPiezas((current) => current.filter((pieza) => pieza.id !== id));
  };

  const guardarPedido = async () => {
    if (submitting.current || !headerReady || !piezas.length) return;
    submitting.current = true;
    setIsSubmitting(true);
    setError("");
    try {
      const response = await createOrder({
        id_tipo_vidrio: Number(tipoVidrio), espesor_mm: Number(espesor),
        piezas: piezas.map(({ tipo_forma, cantidad, vertices_mm }) => ({ tipo_forma, cantidad, vertices_mm })),
      });
      setSavedOrderId(response.id_pedido);
      setPiezas([]);
      setEditorKey((current) => current + 1);
    } catch (err) {
      setError(err.message);
    } finally {
      submitting.current = false;
      setIsSubmitting(false);
    }
  };

  return (
        <div
            className="pagina-pedido"
                style={{ "--bg-image": `url(${fondoVidrio})` }}
        >
      <div className="contenedor-pedido">

        <div className="encabezado">
          <span className="etiqueta-pagina">
            <PackagePlus size={16} />
            Registro de pedido
          </span>

          <h1>Nuevo pedido</h1>

          <p>
            Selecciona el material y agrega las piezas requeridas por el cliente.
          </p>
        </div>

        <section className="seccion">
          <h2>Datos del pedido</h2>
          {catalogLoading && <p role="status">Cargando materiales…</p>}
          {catalogError && <div role="alert"><p>{catalogError}</p>
            <button type="button" className="boton-cancelar" onClick={() => {
              setCatalogError(""); setCatalogLoading(true); setCatalogAttempt((current) => current + 1);
            }}>Reintentar catálogo</button></div>}
          {!catalogLoading && !catalogError && !tiposVidrio.length && <p role="status">No hay materiales activos con espesores disponibles.</p>}

          <div className="campos">

            <div className="campo">
              <label htmlFor="tipoVidrio">
                <Layers3 size={17} />
                Tipo de vidrio
              </label>

              <select
                id="tipoVidrio"
                value={tipoVidrio}
                onChange={cambiarTipoVidrio}
                disabled={isSubmitting || catalogLoading}
              >
                <option value="">Seleccionar tipo</option>

                {tiposVidrio.map((tipo) => (
                  <option key={tipo.id_tipo_vidrio} value={tipo.id_tipo_vidrio}>
                    {tipo.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div className="campo">
              <label htmlFor="espesor">
                <Ruler size={17} />
                Espesor
              </label>

              <select
                id="espesor"
                value={espesor}
                onChange={(e) => setEspesor(e.target.value)}
                disabled={!tipoVidrio || isSubmitting}
              >
                <option value="">Seleccionar espesor</option>

                {material &&
                  material.espesores_mm.map((valor) => (
                    <option key={valor} value={valor}>
                      {valor} mm
                    </option>
                  ))}
              </select>
            </div>

          </div>
        </section>

        <section className="seccion">

          <div className="encabezado-piezas">
            <div>
              <h2>Piezas del pedido</h2>

              <p className="texto-secundario">
                Agrega todas las piezas que forman parte del pedido.
              </p>
            </div>

          </div>

          <div ref={listaAnimada}>

            {piezas.length === 0 ? (
              <div className="sin-piezas">
                <PackagePlus size={32} />

                <strong>No hay piezas agregadas</strong>

                <span>
                  Selecciona el tipo y espesor del vidrio para comenzar.
                </span>
              </div>
            ) : (
              <div className="lista-piezas">

                {piezas.map((pieza, index) => (
                  <div className="pieza" key={pieza.id}>

                    <div className="numero-pieza">
                      {index + 1}
                    </div>

                    <div className="datos-pieza">
                      <strong>Pieza {index + 1}</strong>
                      <span>Polígono convexo · {pieza.vertices_mm.length} vértices · Cantidad: {pieza.cantidad}</span>
                    </div>

                    <span className="estado-pieza">
                      Sin guardar
                    </span>

                    <button
                      type="button"
                      className="boton-eliminar"
                      onClick={() => eliminarPieza(pieza.id)}
                      title="Eliminar pieza"
                      aria-label={`Eliminar pieza ${index + 1}`}
                      disabled={isSubmitting}
                    >
                      <Trash2 size={18} />
                    </button>

                  </div>
                ))}

              </div>
            )}

          </div>
        </section>

        <CustomPieceEditor key={editorKey} onAddPiece={agregarPieza} headerReady={headerReady} disabled={isSubmitting} />

        {error && <p className="pedido-mensaje pedido-mensaje--error" role="alert">{error} Las piezas se conservan; puedes corregir o reintentar.</p>}
        {savedOrderId !== null && <p className="pedido-mensaje" role="status">Pedido guardado correctamente. ID del pedido: {savedOrderId}.</p>}

        <div className="acciones">

          <button
            type="button"
            className="boton-cancelar"
            disabled={isSubmitting}
            onClick={() => { setPiezas([]); setError(""); setSavedOrderId(null); setEditorKey((current) => current + 1); }}
          >
            <X size={18} />
            Cancelar
          </button>

          <button
            type="button"
            className="boton-guardar"
            disabled={!headerReady || piezas.length === 0 || isSubmitting}
            onClick={guardarPedido}
            aria-busy={isSubmitting}
          >
            <Save size={18} />
            {isSubmitting ? "Guardando pedido…" : "Guardar pedido"}
          </button>

        </div>

      </div>
    </div>
  );
}

export default NuevoPedido;
