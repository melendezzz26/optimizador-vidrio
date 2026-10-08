import { useState, useEffect } from "react";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import { 
  Plus, Trash2, Save, X, PackagePlus, Loader2,
  Home, ShoppingCart, Archive, BarChart2, Users, Settings
} from "lucide-react";
import fondoVidrio from "../../assets/fondo-vidrio.png";
import "./NuevoPedido.css";

export default function NuevoPedido({ token }) {
    const [tiposDisponibles, setTiposDisponibles] = useState([]);
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorGlobal, setErrorGlobal] = useState("");

  const [piezas, setPiezas] = useState([]);
  const [listaAnimada] = useAutoAnimate();

  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    const fetchTiposVidrio = async () => {
      try {
        const response = await fetch(`${baseUrl}/api/inventory/tipos-vidrio`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });        
        if (!response.ok) throw new Error("Error en la red");
        
        const data = await response.json();
        setTiposDisponibles(data);
      } catch (err) {
        console.error(err);
        setErrorGlobal("Error al conectar con la base de datos para cargar los vidrios.");
      } finally {
        setIsLoadingConfig(false);
      }
    };
    fetchTiposVidrio();
  }, []);

  // Función para obtener los espesores dinámicos según el vidrio seleccionado en cada pieza
  const obtenerEspesores = (idVidrio) => {
    const tipo = tiposDisponibles.find(t => t.id_tipo_vidrio.toString() === idVidrio?.toString());
    return tipo ? tipo.espesores_mm : [];
  };

  const agregarPieza = () => {
      // Busca el número más alto extrayéndolo del texto "Pieza X"
      const numeroMaximo = piezas.length > 0 
        ? Math.max(...piezas.map(p => parseInt(p.nombre.split(' ')[1]) || 0)) 
        : 0;

      const nuevaPieza = {
        id: Date.now(),
        nombre: `Pieza ${numeroMaximo + 1}`,
        espesor: "",        
        cantidad: 1,
        tipo_forma: "RECTANGULO",
        dimensiones: { width_mm: '', height_mm: '' }
      };
      setPiezas([...piezas, nuevaPieza]);
    };

  const eliminarPieza = (id) => {
      // 1. Filtramos para quitar la pieza eliminada
      // 2. Usamos map() para renumerar las que quedan (index + 1)
      const piezasRenumeradas = piezas
        .filter((pieza) => pieza.id !== id)
        .map((pieza, index) => ({
          ...pieza,
          nombre: `Pieza ${index + 1}`
        }));
        
      setPiezas(piezasRenumeradas);
    };

  const actualizarPieza = (id, campo, valor) => {
    setPiezas(piezas.map(pieza => {
      if (pieza.id === id) {
        if (campo === 'cantidad') {
          return { ...pieza, cantidad: parseInt(valor) || '' };
        }
        if (campo === 'tipo_vidrio_id') {
          // Si cambia el material, reseteamos el espesor porque podría no estar disponible
          return { ...pieza, tipo_vidrio_id: valor, espesor: "" };
        }
        if (campo === 'espesor') {
          return { ...pieza, espesor: valor };
        }
        if (campo === 'tipo_forma') {
          let nuevasDimensiones = {};
          if (valor === 'RECTANGULO') nuevasDimensiones = { width_mm: '', height_mm: '' };
          if (valor === 'CIRCUNFERENCIA') nuevasDimensiones = { radius_mm: '' };
          if (valor === 'TRIANGULO') nuevasDimensiones = { base_mm: '', height_mm: '' };
          return { ...pieza, tipo_forma: valor, dimensiones: nuevasDimensiones };
        }
        
        return { 
          ...pieza, 
          dimensiones: { ...pieza.dimensiones, [campo]: parseFloat(valor) || '' } 
        };
      }
      return pieza;
    }));
  };
  
  const esPedidoValido = () => {
    if (piezas.length === 0) return false;
    return piezas.every(p => {
      if (!p.tipo_vidrio_id || !p.espesor || !p.cantidad) return false;
      if (p.tipo_forma === 'RECTANGULO' && (!p.dimensiones.width_mm || !p.dimensiones.height_mm)) return false;
      if (p.tipo_forma === 'CIRCUNFERENCIA' && !p.dimensiones.radius_mm) return false;
      if (p.tipo_forma === 'TRIANGULO' && (!p.dimensiones.base_mm || !p.dimensiones.height_mm)) return false;
      return true;
    });
  };

  const cancelarPedido = () => {
      if (window.confirm("¿Estás seguro de que deseas limpiar todas las piezas del pedido?")) {
        setPiezas([]);
        setErrorGlobal("");
      }
    };

  const guardarPedido = async () => {
    setIsSubmitting(true);
    setErrorGlobal("");
    
    // Tomamos el material de la primera pieza para el nivel global del pedido,
    // y "esparcimos" las dimensiones para que queden planas como espera el backend.
    const payload = {
      id_tipo_vidrio: parseInt(piezas[0].tipo_vidrio_id),
      espesor_mm: parseFloat(piezas[0].espesor),
      piezas: piezas.map(p => ({
        tipo_forma: p.tipo_forma,
        cantidad: p.cantidad,
        ...p.dimensiones 
      }))
    };

    try {
      // Hacemos la conexión real con el backend inyectando el token
      const response = await fetch(`${baseUrl}/api/orders/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Error del servidor al guardar.");
      }

      console.log("Pedido guardado exitosamente en BD:", payload);
      alert("¡Pedido registrado con éxito!"); // O usa un Toast si tienes uno
      setPiezas([]); // Limpiar después de guardar
      
    } catch (error) {
      console.error(error);
      setErrorGlobal(error.message || "Ocurrió un error al guardar el pedido.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="app-layout">
      {/* SIDEBAR LATERAL */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">N</div>
          <div>
            <h2>NewGlass</h2>
            <p>Especialistas en vidrio</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button className="nav-item"><Home size={20} /> Inicio</button>
          <button className="nav-item active"><ShoppingCart size={20} /> Registro de pedidos</button>
          <button className="nav-item"><Archive size={20} /> Gestión de inventario</button>
          <button className="nav-item"><BarChart2 size={20} /> Consulta de resultados</button>
          <button className="nav-item"><Users size={20} /> Panel de roles</button>
          <button className="nav-item"><Settings size={20} /> Configuración</button>
        </nav>
      </aside>

      {/* ÁREA DE CONTENIDO PRINCIPAL */}
      <main className="pagina-pedido" style={{ backgroundImage: `linear-gradient(rgba(245, 247, 250, 0.85), rgba(245, 247, 250, 0.85)), url(${fondoVidrio})`, backgroundAttachment: 'fixed' }}>
        
        <div className="contenedor-pedido">
          <div className="encabezado">
            <span className="etiqueta-pagina">
              <PackagePlus size={16} /> Registro de pedido
            </span>
            <h1>Nuevo pedido</h1>
            <p>Configura el material, espesor y medidas de cada pieza requerida por el cliente.</p>
          </div>

          {errorGlobal && (
            <div className="alerta-error" role="alert">
              {errorGlobal}
            </div>
          )}

          <section className="seccion">
            <div className="encabezado-piezas">
              <div>
                <h2>Piezas del pedido</h2>
                <p className="texto-secundario">Agrega todas las piezas que forman parte del pedido.</p>
              </div>
              <button type="button" className="boton-agregar" onClick={agregarPieza} disabled={isLoadingConfig || isSubmitting}>
                <Plus size={18} /> Agregar pieza
              </button>
            </div>

            <div ref={listaAnimada}>
              {piezas.length === 0 ? (
                <div className="sin-piezas">
                  <PackagePlus size={32} />
                  <strong>No hay piezas agregadas</strong>
                  <span>Haz clic en "Agregar pieza" para comenzar a armar el pedido.</span>
                </div>
              ) : (

              <div className="lista-piezas">
                {piezas.map((pieza, index) => (
                  <div className="pieza" key={pieza.id} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    
                    {/* Fila 1: Título y Eliminar */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div className="pieza-info">
                        <div className="numero-pieza">{index + 1}</div>
                        <div className="datos-pieza">
                          <strong>{pieza.nombre}</strong>
                          <span>Configura material y medidas</span>
                        </div>
                      </div>
                      <button type="button" className="boton-eliminar" onClick={() => eliminarPieza(pieza.id)} title="Eliminar pieza">
                        <Trash2 size={18} />
                      </button>
                    </div>

                    {/* Fila 2: Material, Espesor, Forma y Cantidad */}
                    <div style={{ display: 'flex', gap: '24px', paddingLeft: '48px', flexWrap: 'wrap', alignItems: 'center' }}>
                      <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label style={{ fontSize: '13px', color: 'var(--text-600)' }}>Material</label>
                        <select 
                          value={pieza.tipo_vidrio_id} 
                          onChange={(e) => actualizarPieza(pieza.id, 'tipo_vidrio_id', e.target.value)}
                          style={{ padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)', fontSize: '13px', width: '140px' }}
                        >
                          <option value="">Seleccionar...</option>
                          {tiposDisponibles.map(t => <option key={t.id_tipo_vidrio} value={t.id_tipo_vidrio}>{t.nombre}</option>)}
                        </select>
                      </div>

                      <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label style={{ fontSize: '13px', color: 'var(--text-600)' }}>Espesor</label>
                        <select 
                          value={pieza.espesor} 
                          onChange={(e) => actualizarPieza(pieza.id, 'espesor', e.target.value)}
                          disabled={!pieza.tipo_vidrio_id}
                          style={{ padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)', fontSize: '13px', width: '100px' }}
                        >
                          <option value="">Espesor...</option>
                          {obtenerEspesores(pieza.tipo_vidrio_id).map(e => <option key={e} value={e}>{e} mm</option>)}
                        </select>
                      </div>

                      <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label style={{ fontSize: '13px', color: 'var(--text-600)' }}>Forma</label>
                        <select 
                          value={pieza.tipo_forma} 
                          onChange={(e) => actualizarPieza(pieza.id, 'tipo_forma', e.target.value)}
                          // Ancho ampliado de 120px a 190px para que el texto encaje perfectamente
                          style={{ padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)', fontSize: '13px', width: '190px' }} 
                        >
                          <option value="RECTANGULO">Rectángulo / Cuadrado</option>
                          <option value="CIRCUNFERENCIA">Círculo</option>
                          <option value="TRIANGULO">Triángulo</option>
                        </select>
                      </div>

                      <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label style={{ fontSize: '13px', color: 'var(--text-600)' }}>Cant.</label>
                        <input 
                          type="number" min="1" 
                          value={pieza.cantidad} 
                          onChange={(e) => actualizarPieza(pieza.id, 'cantidad', e.target.value)}
                          style={{ width: '60px', padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                        />
                      </div>
                    </div>

                    {/* Fila 3: Medidas dinámicas según el tipo de forma */}
                    <div style={{ display: 'flex', gap: '24px', paddingLeft: '48px', alignItems: 'center' }}>
                      {pieza.tipo_forma === 'RECTANGULO' && (
                        <>
                          <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <label style={{ fontSize: '13px', color: 'var(--text-600)' }}>Ancho (mm)</label>
                            <input 
                              type="number" min="1" placeholder="Ej: 1000"
                              value={pieza.dimensiones.width_mm} 
                              onChange={(e) => actualizarPieza(pieza.id, 'width_mm', e.target.value)}
                              style={{ width: '90px', padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                            />
                          </div>
                          <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <label style={{ fontSize: '13px', color: 'var(--text-600)' }}>Alto (mm)</label>
                            <input 
                              type="number" min="1" placeholder="Ej: 500"
                              value={pieza.dimensiones.height_mm} 
                              onChange={(e) => actualizarPieza(pieza.id, 'height_mm', e.target.value)}
                              style={{ width: '90px', padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                            />
                          </div>
                        </>
                      )}

                      {pieza.tipo_forma === 'CIRCUNFERENCIA' && (
                        <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <label style={{ fontSize: '13px', color: 'var(--text-600)' }}>Radio (mm)</label>
                          <input 
                            type="number" min="1" placeholder="Ej: 250"
                            value={pieza.dimensiones.radius_mm} 
                            onChange={(e) => actualizarPieza(pieza.id, 'radius_mm', e.target.value)}
                            style={{ width: '90px', padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                          />
                        </div>
                      )}

                      {pieza.tipo_forma === 'TRIANGULO' && (
                        <>
                          <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <label style={{ fontSize: '13px', color: 'var(--text-600)' }}>Base (mm)</label>
                            <input 
                              type="number" min="1" placeholder="Ej: 800"
                              value={pieza.dimensiones.base_mm} 
                              onChange={(e) => actualizarPieza(pieza.id, 'base_mm', e.target.value)}
                              style={{ width: '90px', padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                            />
                          </div>
                          <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <label style={{ fontSize: '13px', color: 'var(--text-600)' }}>Alto (mm)</label>
                            <input 
                              type="number" min="1" placeholder="Ej: 600"
                              value={pieza.dimensiones.height_mm} 
                              onChange={(e) => actualizarPieza(pieza.id, 'height_mm', e.target.value)}
                              style={{ width: '90px', padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                            />
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>  
              )}
            </div>
          </section>

          <div className="acciones">
            <button type="button" className="boton-cancelar" onClick={cancelarPedido} disabled={isSubmitting}>
              <X size={18} /> Cancelar
            </button>

            <button 
              type="button" 
              className="boton-guardar" 
              onClick={guardarPedido} 
              disabled={!esPedidoValido() || isSubmitting}
            >
              {isSubmitting ? <Loader2 size={18} className="spin" /> : <Save size={18} />}
              {isSubmitting ? "Guardando..." : "Guardar pedido"}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}