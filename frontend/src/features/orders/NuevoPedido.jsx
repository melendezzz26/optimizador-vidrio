import { useState, useEffect, useCallbackseCallback } from "react";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import { 
  Plus, Trash2, Save, X, PackagePlus, Loader2,
  Home, ShoppingCart, Archive, BarChart2, Users, Settings
} from "lucide-react";
import fondoVidrio from "../../assets/fondo-vidrio.png";
import "./NuevoPedido.css";
import CustomPieceEditor from './CustomPieceEditor';

export default function NuevoPedido({ token }) {
  const [tiposDisponibles, setTiposDisponibles] = useState([]);
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorGlobal, setErrorGlobal] = useState("");

  const [piezas, setPiezas] = useState([]);
  const [listaAnimada] = useAutoAnimate();
  const [piezaEnEdicion, setPiezaEnEdicion] = useState(null);

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
  }, [baseUrl, token]);

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

const actualizarPieza = useCallback((id, campo, valor) => {
    // Usamos prevPiezas para evitar problemas de dependencias en React
    setPiezas(prevPiezas => prevPiezas.map(pieza => {
      if (pieza.id === id) {
        if (campo === 'cantidad') {
          return { ...pieza, cantidad: parseInt(valor) || '' };
        }
        if (campo === 'tipo_vidrio_id') {
          return { ...pieza, tipo_vidrio_id: valor, espesor: "" };
        }
        if (campo === 'espesor') {
          return { ...pieza, espesor: valor };
        }
        if (campo === 'tipo_forma') {
          let nuevasDimensiones = {};
          if (valor === 'RECTANGULO') nuevasDimensiones = { width_mm: '', height_mm: '' };
          if (valor === 'CIRCUNFERENCIA') nuevasDimensiones = { radius_mm: '' };
          if (valor === 'POLIGONO_CONVEXO') nuevasDimensiones = { vertices: [] };
          return { ...pieza, tipo_forma: valor, dimensiones: nuevasDimensiones };
        }
        
        if (campo === 'dimensiones') {
          return { ...pieza, dimensiones: valor };
        }

        return { 
          ...pieza, 
          dimensiones: { ...pieza.dimensiones, [campo]: parseFloat(valor) || '' } 
        };
      }
      return pieza;
    }));
  }, []);
  
  const esPedidoValido = () => {
    if (piezas.length === 0) return false;
    
    return piezas.every(p => {
      // 1. Validar que tenga material, espesor y cantidad
      if (!p.tipo_vidrio_id || !p.espesor || !p.cantidad) return false;
      
      // 2. Validar las medidas según la forma que eligió el operario
      if (p.tipo_forma === 'RECTANGULO' && (!p.dimensiones.width_mm || !p.dimensiones.height_mm)) return false;
      if (p.tipo_forma === 'CIRCUNFERENCIA' && !p.dimensiones.radius_mm) return false;
      
      // 3. Validar que el polígono tenga al menos 3 vértices dibujados
      if (p.tipo_forma === 'POLIGONO_CONVEXO' && (!p.dimensiones.vertices || p.dimensiones.vertices.length < 3)) return false;
      
      return true;
    });
  };

  const cancelarPedido = () => {
      if (window.confirm("¿Estás seguro de que deseas limpiar todas las piezas del pedido?")) {
        setPiezas([]);
        setErrorGlobal("");
      }
    };

useEffect(() => {
  const recibirDatosDelEditor = (evento) => {
      if (evento.key === 'verticesPoligono_completados') {
        const index = localStorage.getItem('piezaEnEdicion_index');
        
        if (index !== null) {
          const vertices = JSON.parse(evento.newValue);
          actualizarPieza(parseInt(index), 'dimensiones', { vertices });
          
          localStorage.removeItem('verticesPoligono_completados');
          localStorage.removeItem('piezaEnEdicion_index');
        }
      }
    };

    window.addEventListener('storage', recibirDatosDelEditor);
    return () => window.removeEventListener('storage', recibirDatosDelEditor);
  }, [actualizarPieza]);

  const abrirEditor = (id) => {
    setPiezaEnEdicion(id);
  };

  const guardarPedido = async () => {
    setIsSubmitting(true);
    setErrorGlobal("");
    
    const payload = {
      // Ya no enviamos id_tipo_vidrio ni espesor_mm aquí afuera
      piezas: piezas.map(p => {
        // 1. Extraemos rawState y vertices originales para no enviarlos tal cual
        // eslint-disable-next-line no-unused-vars
        const { rawState, vertices, ...medidasLimpias } = p.dimensiones;

        // 2. Armamos la pieza metiendo el material y espesor ADENTRO, como exige FastAPI
        const piezaFormateada = {
          tipo_forma: p.tipo_forma, 
          id_tipo_vidrio: parseInt(p.tipo_vidrio_id), // Movido adentro de la pieza
          espesor_mm: parseFloat(p.espesor),         // Movido adentro de la pieza
          cantidad: parseInt(p.cantidad),
          ...medidasLimpias // Inyecta width_mm, height_mm, o radius_mm
        };

        // 3. Si es polígono, le cambiamos el nombre de "vertices" a "vertices_mm"
        if (p.tipo_forma === 'POLIGONO_CONVEXO') {
          piezaFormateada.vertices_mm = vertices;
        }

        return piezaFormateada;
      })
    };

    try {
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
        // 2. Extraemos el mensaje real de FastAPI para que no diga [object Object]
        const mensajeReal = errorData.detail 
            ? JSON.stringify(errorData.detail) 
            : "Error del servidor al guardar.";
        throw new Error(mensajeReal);
      }

      alert("¡Pedido registrado con éxito!"); 
      setPiezas([]); 
      
    } catch (error) {
      console.error(error);
      // Ahora verás el reclamo exacto de FastAPI en la caja roja
      setErrorGlobal(error.message); 
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
                          onChange={(e) => {
                            const nuevaForma = e.target.value;
                            actualizarPieza(pieza.id, 'tipo_forma', nuevaForma);
                            // Abre el editor de inmediato si es polígono convexo
                            if (nuevaForma === 'POLIGONO_CONVEXO') {
                              abrirEditor(pieza.id);
                            }
                          }}
                          style={{ padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)', fontSize: '13px', width: '190px' }} 
                        >
                          <option value="RECTANGULO">Rectángulo / Cuadrado</option>
                          <option value="CIRCUNFERENCIA">Círculo</option>
                          <option value="POLIGONO_CONVEXO">Polígono Convexo</option>
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

                      {pieza.tipo_forma === 'POLIGONO_CONVEXO' && (
                        <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          {pieza.dimensiones?.vertices?.length > 0 ? (
                            <span style={{ color: 'green', fontSize: '13px', fontWeight: 'bold' }}>✓ Vértices cargados</span>
                          ) : (
                            <span style={{ color: '#d97706', fontSize: '13px', fontWeight: 'bold' }}>⚠️ Falta dibujar</span>
                          )}
                          <button
                            type="button"
                            onClick={() => abrirEditor(pieza.id)}
                            style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-strong)', backgroundColor: 'white', cursor: 'pointer', fontSize: '13px' }}
                          >
                            Editar dibujo
                          </button>
                        </div>
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

      {piezaEnEdicion !== null && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0, 0, 0, 0.6)', zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ backgroundColor: '#fff', borderRadius: '12px', width: '90%', maxWidth: '1000px', height: '85vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)' }}>
            
            <div style={{ padding: '16px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, color: 'var(--text-900)' }}>Dibujar Polígono Convexo</h3>
              <button onClick={() => setPiezaEnEdicion(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}>
                <X size={24} />
              </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '24px', backgroundColor: '#f9fafb' }}>
              <CustomPieceEditor 
                // Buscamos la pieza que estamos editando y le pasamos su rawState
                initialState={piezas.find(p => p.id === piezaEnEdicion)?.dimensiones?.rawState}
                onGuardarVertices={(datos) => {
                  // datos ahora trae { vertices, rawState }
                  actualizarPieza(piezaEnEdicion, 'dimensiones', datos);
                  setPiezaEnEdicion(null); 
                }}
              />
            </div>
            
          </div>
        </div>
      )}
    </div>
  );
}