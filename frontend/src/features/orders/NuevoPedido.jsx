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
import fondoVidrio from "../../assets/fondo-vidrio.png";
import CustomPieceEditor from "./CustomPieceEditor";
import { createOrder, listOrderMaterials } from "./ordersApi";
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
  const [forma, setForma] = useState("POLIGONO_CONVEXO");
  const [cantidad, setCantidad] = useState("1");
  const [medidas, setMedidas] = useState({ width_mm: "", height_mm: "", radius_mm: "" });
  const cantidadValida = Number.isInteger(Number(cantidad)) && Number(cantidad) > 0 && Number(cantidad) <= 2147483647;
  const material = tiposVidrio.find((tipo) => tipo.id_tipo_vidrio === Number(tipoVidrio));
  const headerReady = Boolean(material && material.espesores_mm.some((value) => Number(value) === Number(espesor)));
  // Puente temporal hacia la API monomaterial: comprobar TODAS las piezas.
  // Eliminar este puente cuando se implemente el contrato por pieza y su migración.
  const combinaciones = new Map(piezas.map(({ id_tipo_vidrio, espesor_mm }) =>
    [`${id_tipo_vidrio}:${espesor_mm}`, { id_tipo_vidrio, espesor_mm }]));
  const materialComun = combinaciones.size === 1 ? combinaciones.values().next().value : null;
  const camposMedidas = forma === "RECTANGULO"
    ? [["width_mm", "Ancho (mm)"], ["height_mm", "Alto (mm)"]]
    : [["radius_mm", "Radio (mm)"]];
  const medidasValidas = camposMedidas.every(([campo]) => Number.isFinite(Number(medidas[campo])) && Number(medidas[campo]) > 0);

  const [listaAnimada] = useAutoAnimate();

  const cambiarTipoVidrio = (e) => {
    setTipoVidrio(e.target.value);
    setEspesor("");
  };

  const agregarPieza = (piece) => {
    if (submitting.current || !headerReady || !cantidadValida) return;
    const nuevaPieza = {
      ...piece,
      id_tipo_vidrio: Number(tipoVidrio),
      espesor_mm: Number(espesor),
      cantidad: Number(cantidad),
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
    if (submitting.current || !materialComun || !piezas.length) return;
    submitting.current = true;
    setIsSubmitting(true);
    setError("");
    try {
      const response = await createOrder({
        ...materialComun,
        piezas: piezas.map((pieza) => {
          const base = { tipo_forma: pieza.tipo_forma, cantidad: pieza.cantidad };
          if (pieza.tipo_forma === "RECTANGULO") return { ...base, width_mm: pieza.width_mm, height_mm: pieza.height_mm };
          if (pieza.tipo_forma === "CIRCUNFERENCIA") return { ...base, radius_mm: pieza.radius_mm };
          return { ...base, vertices_mm: pieza.vertices_mm };
        }),
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
            Selecciona el material, espesor y cantidad de cada pieza antes de agregarla.
          </p>
        </div>

        <section className="seccion">
          <h2>Datos de la pieza a agregar</h2>
          <p>Estos datos se asignan a la nueva pieza. Cambiarlos no modifica las piezas ya agregadas.</p>
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
          <div className="campos">
            <div className="campo">
              <label htmlFor="cantidadPieza">Cantidad</label>
              <input id="cantidadPieza" type="number" min="1" max="2147483647" step="1"
                value={cantidad} onChange={(event) => setCantidad(event.target.value)} disabled={isSubmitting}
                aria-invalid={!cantidadValida} aria-describedby={!cantidadValida ? "cantidad-error" : undefined} />
              {!cantidadValida && <p id="cantidad-error" className="pedido-mensaje--error">Ingresa una cantidad entera entre 1 y 2147483647.</p>}
            </div>
            <div className="campo">
              <label htmlFor="formaPieza">Forma</label>
              <select id="formaPieza" value={forma} disabled={isSubmitting} onChange={(event) => setForma(event.target.value)}>
                <option value="RECTANGULO">Rectángulo / Cuadrado</option>
                <option value="CIRCUNFERENCIA">Circunferencia</option>
                <option value="POLIGONO_CONVEXO">Polígono convexo personalizado</option>
              </select>
            </div>
          </div>
          {forma !== "POLIGONO_CONVEXO" && <>
            <div className="campos">
              {camposMedidas.map(([campo, etiqueta]) => {
                const invalida = medidas[campo] !== "" && !(Number.isFinite(Number(medidas[campo])) && Number(medidas[campo]) > 0);
                return <div className="campo" key={campo}>
                  <label htmlFor={campo}>{etiqueta}</label>
                  <input id={campo} type="number" step="any" value={medidas[campo]} disabled={isSubmitting}
                    onChange={(event) => setMedidas((current) => ({ ...current, [campo]: event.target.value }))}
                    aria-invalid={invalida} aria-describedby={invalida ? `${campo}-error` : undefined} />
                  {invalida && <p id={`${campo}-error`} className="pedido-mensaje--error">La medida debe ser un número finito mayor que cero.</p>}
                </div>;
              })}
            </div>
            {(!headerReady || !cantidadValida || !medidasValidas) && <p>Completa material, espesor, cantidad entera y medidas positivas para agregar la pieza estándar.</p>}
            <button type="button" className="boton-agregar" disabled={isSubmitting || !headerReady || !cantidadValida || !medidasValidas}
              onClick={() => {
                if (!medidasValidas) return;
                agregarPieza({ tipo_forma: forma, ...Object.fromEntries(camposMedidas.map(([campo]) => [campo, Number(medidas[campo])])) });
                setMedidas({ width_mm: "", height_mm: "", radius_mm: "" });
              }}>Agregar pieza estándar</button>
          </>}
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
                      <span>{tiposVidrio.find((tipo) => tipo.id_tipo_vidrio === pieza.id_tipo_vidrio)?.nombre} · {pieza.espesor_mm} mm · Cantidad: {pieza.cantidad}</span>
                      <span>{pieza.tipo_forma === "RECTANGULO" ? `Rectángulo · ${pieza.width_mm} × ${pieza.height_mm} mm`
                        : pieza.tipo_forma === "CIRCUNFERENCIA" ? `Circunferencia · Radio: ${pieza.radius_mm} mm`
                        : `Polígono convexo · ${pieza.vertices_mm.length} vértices`}</span>
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

        <div hidden={forma !== "POLIGONO_CONVEXO"}>
          <CustomPieceEditor key={editorKey} onAddPiece={agregarPieza} headerReady={headerReady && cantidadValida} disabled={isSubmitting} />
        </div>

        {combinaciones.size > 1 && <p className="pedido-mensaje" role="status">
          Por ahora solo se pueden guardar juntas piezas del mismo material y espesor. Las piezas con combinaciones distintas permanecen en este borrador; su guardado estará disponible en una próxima actualización.
        </p>}

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
            disabled={!materialComun || piezas.length === 0 || isSubmitting}
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
