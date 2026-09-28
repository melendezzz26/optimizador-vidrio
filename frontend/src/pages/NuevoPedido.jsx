import { useState } from "react";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import {
  Plus,
  Trash2,
  Save,
  X,
  Layers3,
  Ruler,
  PackagePlus,
} from "lucide-react";
import fondoVidrio from "../assets/fondo-vidrio.png";
import "./NuevoPedido.css";

function NuevoPedido() {
  const tiposVidrio = {
    Incoloro: [3, 4, 5.5, 6, 8, 10, 12],
    Bronce: [4, 5.5, 6, 8, 10],
    Gris: [4, 5.5, 6, 8, 10],
    Catedral: [3, 3.5, 5],
    Reflejante: [4, 5.5, 6, 8],
    Espejo: [2, 3, 4, 6],
  };

  const [tipoVidrio, setTipoVidrio] = useState("");
  const [espesor, setEspesor] = useState("");
  const [piezas, setPiezas] = useState([]);

  const [listaAnimada] = useAutoAnimate();

  const cambiarTipoVidrio = (e) => {
    setTipoVidrio(e.target.value);
    setEspesor("");
  };

  const agregarPieza = () => {
    const nuevaPieza = {
      id: Date.now(),
      nombre: `Pieza ${piezas.length + 1}`,
    };

    setPiezas([...piezas, nuevaPieza]);
  };

  const eliminarPieza = (id) => {
    setPiezas(piezas.filter((pieza) => pieza.id !== id));
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
              >
                <option value="">Seleccionar tipo</option>

                {Object.keys(tiposVidrio).map((tipo) => (
                  <option key={tipo} value={tipo}>
                    {tipo}
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
                disabled={!tipoVidrio}
              >
                <option value="">Seleccionar espesor</option>

                {tipoVidrio &&
                  tiposVidrio[tipoVidrio].map((valor) => (
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

            <button
              type="button"
              className="boton-agregar"
              onClick={agregarPieza}
              disabled={!tipoVidrio || !espesor}
            >
              <Plus size={18} />
              Agregar pieza
            </button>
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
                      <strong>{pieza.nombre}</strong>
                      <span>Pendiente de configurar</span>
                    </div>

                    <span className="estado-pieza">
                      Pendiente
                    </span>

                    <button
                      type="button"
                      className="boton-eliminar"
                      onClick={() => eliminarPieza(pieza.id)}
                      title="Eliminar pieza"
                    >
                      <Trash2 size={18} />
                    </button>

                  </div>
                ))}

              </div>
            )}

          </div>
        </section>

        <div className="acciones">

          <button
            type="button"
            className="boton-cancelar"
          >
            <X size={18} />
            Cancelar
          </button>

          <button
            type="button"
            className="boton-guardar"
            disabled={!tipoVidrio || !espesor || piezas.length === 0}
          >
            <Save size={18} />
            Guardar pedid
          </button>

        </div>

      </div>
    </div>
  );
}

export default NuevoPedido;