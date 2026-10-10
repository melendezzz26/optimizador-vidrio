import { useState, useEffect, useCallback } from "react";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import { Plus, Trash2, Save, X, PackagePlus, Loader2 } from "lucide-react";
import CustomPieceEditor from './CustomPieceEditor';
// No importamos el layout de NuevoPedido.css aquí, solo usará las clases internas.

export default function FormularioPedido({ token, idPedido = null, onCerrar = null }) {
  const [tiposDisponibles, setTiposDisponibles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorGlobal, setErrorGlobal] = useState("");
  
  const [estadoPedido, setEstadoPedido] = useState("PENDIENTE"); // Para saber si bloqueamos la edición
  const [piezas, setPiezas] = useState([]);
  const [listaAnimada] = useAutoAnimate();
  const [piezaEnEdicion, setPiezaEnEdicion] = useState(null);

  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const esModoLectura = estadoPedido !== "PENDIENTE";

  // 1. Cargar tipos de vidrio y (si hay idPedido) los datos del pedido
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        // Cargar Catálogo
        const resVidrios = await fetch(`${baseUrl}/api/inventory/tipos-vidrio`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resVidrios.ok) throw new Error("Error cargando catálogo.");
        setTiposDisponibles(await resVidrios.json());

        // Cargar Pedido Existente (si estamos editando)
        if (idPedido) {
          const resPedido = await fetch(`${baseUrl}/api/orders/${idPedido}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (!resPedido.ok) throw new Error("Error cargando el pedido.");
          const dataPedido = await resPedido.json();
          
          setEstadoPedido(dataPedido.estado);
          
          // Mapear las piezas que vienen de la BD al formato del frontend
          const piezasFormateadas = dataPedido.piezas.map((p, index) => ({
            id: p.id_pieza || Date.now() + index,
            nombre: `Pieza ${index + 1}`,
            tipo_vidrio_id: p.id_tipo_vidrio,
            espesor: p.espesor_mm,
            tipo_forma: p.tipo_forma,
            cantidad: p.cantidad,
            dimensiones: p.dimensiones || (p.tipo_forma === 'POLIGONO_CONVEXO' ? { vertices: p.geometria.vertices_mm } : {})
          }));
          setPiezas(piezasFormateadas);
        }
      } catch (err) {
        console.error(err);
        setErrorGlobal(err.message);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [baseUrl, token, idPedido]);

  const obtenerEspesores = (idVidrio) => {
    const tipo = tiposDisponibles.find(t => t.id_tipo_vidrio?.toString() === idVidrio?.toString());
    return tipo ? tipo.espesores_mm : [];
  };

  const agregarPieza = () => {
    if (esModoLectura) return;
    const numeroMaximo = piezas.length > 0 ? Math.max(...piezas.map(p => parseInt(p.nombre.split(' ')[1]) || 0)) : 0;
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
    if (esModoLectura) return;
    const piezasRenumeradas = piezas.filter((p) => p.id !== id).map((p, i) => ({ ...p, nombre: `Pieza ${i + 1}` }));
    setPiezas(piezasRenumeradas);
  };

  const actualizarPieza = useCallback((id, campo, valor) => {
    if (esModoLectura) return;
    setPiezas(prevPiezas => prevPiezas.map(pieza => {
      if (pieza.id === id) {
        if (campo === 'cantidad') return { ...pieza, cantidad: parseInt(valor) || '' };
        if (campo === 'tipo_vidrio_id') return { ...pieza, tipo_vidrio_id: valor, espesor: "" };
        if (campo === 'espesor') return { ...pieza, espesor: valor };
        if (campo === 'tipo_forma') {
          let nuevasDimensiones = {};
          if (valor === 'RECTANGULO') nuevasDimensiones = { width_mm: '', height_mm: '' };
          if (valor === 'CIRCUNFERENCIA') nuevasDimensiones = { radius_mm: '' };
          if (valor === 'POLIGONO_CONVEXO') nuevasDimensiones = { vertices: [] };
          return { ...pieza, tipo_forma: valor, dimensiones: nuevasDimensiones };
        }
        if (campo === 'dimensiones') return { ...pieza, dimensiones: valor };
        return { ...pieza, dimensiones: { ...pieza.dimensiones, [campo]: parseFloat(valor) || '' } };
      }
      return pieza;
    }));
  }, [esModoLectura]);

  const esPedidoValido = () => {
    if (piezas.length === 0) return false;
    return piezas.every(p => {
      if (!p.tipo_vidrio_id || !p.espesor || !p.cantidad) return false;
      if (p.tipo_forma === 'RECTANGULO' && (!p.dimensiones.width_mm || !p.dimensiones.height_mm)) return false;
      if (p.tipo_forma === 'CIRCUNFERENCIA' && !p.dimensiones.radius_mm) return false;
      if (p.tipo_forma === 'POLIGONO_CONVEXO' && (!p.dimensiones.vertices || p.dimensiones.vertices.length < 3)) return false;
      return true;
    });
  };

  const guardarPedido = async () => {
    setIsSubmitting(true);
    setErrorGlobal("");
    
    const payload = {
      piezas: piezas.map(p => {
        // eslint-disable-next-line no-unused-vars
        const { rawState, vertices, ...medidasLimpias } = p.dimensiones;
        const piezaFormateada = {
          tipo_forma: p.tipo_forma, 
          id_tipo_vidrio: parseInt(p.tipo_vidrio_id),
          espesor_mm: parseFloat(p.espesor),
          cantidad: parseInt(p.cantidad),
          ...medidasLimpias 
        };
        if (p.tipo_forma === 'POLIGONO_CONVEXO') {
          piezaFormateada.vertices_mm = vertices || [];
        }
        return piezaFormateada;
      })
    };

    try {
      // Dinámico: Si hay idPedido, hacemos PUT. Si no, hacemos POST.
      const url = idPedido ? `${baseUrl}/api/orders/${idPedido}` : `${baseUrl}/api/orders/`;
      const method = idPedido ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method: method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : "Error al guardar el pedido.");
      }

      alert(`¡Pedido ${idPedido ? 'actualizado' : 'registrado'} con éxito!`);
      if (onCerrar) onCerrar(); // Si está en el modal, lo cerramos tras guardar
      else setPiezas([]); // Si está en la página de crear, solo limpiamos

    } catch (error) {
      console.error(error);
      setErrorGlobal(error.message); 
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '40px' }}>
        <Loader2 className="spin" size={32} /> <span style={{ marginLeft: '10px' }}>Cargando datos...</span>
      </div>
    );
  }

  return (
    <div style={{ padding: idPedido ? '0' : '20px' }}>
      {/* Alerta de solo lectura */}
      {esModoLectura && (
        <div style={{ backgroundColor: '#fffbeb', border: '1px solid #fef3c7', padding: '12px', borderRadius: '8px', color: '#b45309', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <strong>Modo Lectura:</strong> Este pedido se encuentra en estado {estadoPedido}. Ya no se pueden modificar sus piezas.
        </div>
      )}

      {errorGlobal && <div className="alerta-error" role="alert">{errorGlobal}</div>}

      <div className="encabezado-piezas" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '18px', margin: 0 }}>Piezas del pedido</h2>
          <p className="texto-secundario" style={{ fontSize: '13px', margin: 0 }}>{esModoLectura ? 'Detalle de las piezas solicitadas.' : 'Agrega todas las piezas que forman parte del pedido.'}</p>
        </div>
        {!esModoLectura && (
          <button type="button" className="boton-agregar" onClick={agregarPieza} disabled={isSubmitting}>
            <Plus size={16} /> Agregar pieza
          </button>
        )}
      </div>

      <div ref={listaAnimada}>
        {piezas.length === 0 ? (
          <div className="sin-piezas" style={{ padding: '40px', textAlign: 'center', background: '#f9fafb', borderRadius: '8px' }}>
            <PackagePlus size={32} />
            <strong>No hay piezas</strong>
          </div>
        ) : (
          <div className="lista-piezas" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {piezas.map((pieza, index) => (
              <div className="pieza" key={pieza.id} style={{ display: 'flex', flexDirection: 'column', gap: '16px', background: 'white', padding: '16px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <div className="numero-pieza" style={{ background: '#3b82f6', color: 'white', width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', fontSize: '12px', fontWeight: 'bold' }}>{index + 1}</div>
                    <strong>{pieza.nombre}</strong>
                  </div>
                  {!esModoLectura && (
                    <button type="button" onClick={() => eliminarPieza(pieza.id)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>
                      <Trash2 size={18} />
                    </button>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-600)' }}>Material</label>
                    <select value={pieza.tipo_vidrio_id || ''} onChange={(e) => actualizarPieza(pieza.id, 'tipo_vidrio_id', e.target.value)} disabled={esModoLectura} style={{ padding: '6px', borderRadius: '6px', border: '1px solid #d1d5db' }}>
                      <option value="">Seleccionar...</option>
                      {tiposDisponibles.map(t => <option key={t.id_tipo_vidrio} value={t.id_tipo_vidrio}>{t.nombre}</option>)}
                    </select>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-600)' }}>Espesor</label>
                    <select value={pieza.espesor || ''} onChange={(e) => actualizarPieza(pieza.id, 'espesor', e.target.value)} disabled={!pieza.tipo_vidrio_id || esModoLectura} style={{ padding: '6px', borderRadius: '6px', border: '1px solid #d1d5db' }}>
                      <option value="">Espesor...</option>
                      {obtenerEspesores(pieza.tipo_vidrio_id).map(e => <option key={e} value={e}>{e} mm</option>)}
                    </select>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-600)' }}>Forma</label>
                    <select value={pieza.tipo_forma} onChange={(e) => {
                      actualizarPieza(pieza.id, 'tipo_forma', e.target.value);
                      if (e.target.value === 'POLIGONO_CONVEXO') setPiezaEnEdicion(pieza.id);
                    }} disabled={esModoLectura} style={{ padding: '6px', borderRadius: '6px', border: '1px solid #d1d5db' }}>
                      <option value="RECTANGULO">Rectángulo / Cuadrado</option>
                      <option value="CIRCUNFERENCIA">Círculo</option>
                      <option value="POLIGONO_CONVEXO">Polígono Convexo</option>
                    </select>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-600)' }}>Cant.</label>
                    <input type="number" min="1" value={pieza.cantidad || ''} onChange={(e) => actualizarPieza(pieza.id, 'cantidad', e.target.value)} disabled={esModoLectura} style={{ width: '60px', padding: '6px', borderRadius: '6px', border: '1px solid #d1d5db' }} />
                  </div>

                  {/* Medidas Dinámicas */}
                  <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', marginLeft: 'auto', background: '#f3f4f6', padding: '8px 12px', borderRadius: '8px' }}>
                    {pieza.tipo_forma === 'RECTANGULO' && (
                      <>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <label style={{ fontSize: '12px', color: 'var(--text-600)' }}>Ancho (mm)</label>
                          <input type="number" value={pieza.dimensiones.width_mm || ''} onChange={(e) => actualizarPieza(pieza.id, 'width_mm', e.target.value)} disabled={esModoLectura} style={{ width: '80px', padding: '6px', borderRadius: '6px', border: '1px solid #d1d5db' }} />
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <label style={{ fontSize: '12px', color: 'var(--text-600)' }}>Alto (mm)</label>
                          <input type="number" value={pieza.dimensiones.height_mm || ''} onChange={(e) => actualizarPieza(pieza.id, 'height_mm', e.target.value)} disabled={esModoLectura} style={{ width: '80px', padding: '6px', borderRadius: '6px', border: '1px solid #d1d5db' }} />
                        </div>
                      </>
                    )}
                    {pieza.tipo_forma === 'CIRCUNFERENCIA' && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <label style={{ fontSize: '12px', color: 'var(--text-600)' }}>Radio (mm)</label>
                        <input type="number" value={pieza.dimensiones.radius_mm || ''} onChange={(e) => actualizarPieza(pieza.id, 'radius_mm', e.target.value)} disabled={esModoLectura} style={{ width: '80px', padding: '6px', borderRadius: '6px', border: '1px solid #d1d5db' }} />
                      </div>
                    )}
                    {pieza.tipo_forma === 'POLIGONO_CONVEXO' && (
                      <button type="button" onClick={() => setPiezaEnEdicion(pieza.id)} style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #d1d5db', backgroundColor: 'white', cursor: 'pointer', fontSize: '12px' }}>
                        {esModoLectura ? 'Ver dibujo' : 'Editar dibujo'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '16px', marginTop: '24px', paddingTop: '16px', borderTop: '1px solid #e5e7eb' }}>
        {onCerrar && (
          <button type="button" onClick={onCerrar} style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid #d1d5db', background: 'white', cursor: 'pointer' }}>
            <X size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} /> Cerrar
          </button>
        )}
        {!esModoLectura && (
          <button type="button" onClick={guardarPedido} disabled={!esPedidoValido() || isSubmitting} style={{ padding: '8px 16px', borderRadius: '6px', border: 'none', background: '#3b82f6', color: 'white', cursor: (!esPedidoValido() || isSubmitting) ? 'not-allowed' : 'pointer', opacity: (!esPedidoValido() || isSubmitting) ? 0.6 : 1 }}>
            {isSubmitting ? <Loader2 size={16} className="spin" style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} /> : <Save size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />}
            {isSubmitting ? "Guardando..." : "Guardar cambios"}
          </button>
        )}
      </div>

      {piezaEnEdicion !== null && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0, 0, 0, 0.7)', zIndex: 10000, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ backgroundColor: '#fff', borderRadius: '12px', width: '90%', maxWidth: '1000px', height: '85vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)' }}>
            
            <div style={{ padding: '16px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, color: 'var(--text-900)' }}>Dibujar Polígono Convexo</h3>
              <button onClick={() => setPiezaEnEdicion(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: 'var(--text-500)' }}>
                <X size={24} />
              </button>
            </div>

            {/* Aquí agregamos el overflowY: 'auto' y el padding de 24px para que no se corte */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '24px', backgroundColor: '#f9fafb' }}>
               <CustomPieceEditor 
                  initialState={piezas.find(p => p.id === piezaEnEdicion)?.dimensiones?.rawState}
                  readonly={esModoLectura}
                  onGuardarVertices={(datos) => {
                    if (!esModoLectura) actualizarPieza(piezaEnEdicion, 'dimensiones', datos);
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